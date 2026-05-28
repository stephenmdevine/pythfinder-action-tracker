from app.models.base_model import BaseModel


class PointPoolModel(BaseModel):
    """
    Handles point pools, sub-pool allocations, and user-entered
    modifiers for investment-scaled effects.

    Design philosophy:
        The app does not calculate how many bonus points an investment
        yields — the user knows their class rules and enters the result.
        The app records, applies, and tracks that value correctly.

    Three concepts live here:

    1. point_pools       — a resource bucket on a character_source
                           (e.g. Occultist's total focus points, Psion's power points)

    2. pool_allocations  — child slices of a parent pool, each tied to a
                           sub-source (e.g. an Occultist implement)

    3. effect_active_modifiers — the user-entered modifier currently in effect
                           for a pool-linked effect on a specific character
    """

    # ------------------------------------------------------------------
    # POINT POOLS
    # ------------------------------------------------------------------

    def create_pool(
        self,
        character_source_id: int,
        max_points: int,
        replenish_type: str,
        notes: str = "",
    ) -> int:
        """
        Creates a point pool for a character_source.
        Starts full (current_points = max_points).

        replenish_type: 'daily' | 'encounter' | 'manual'
        """
        valid = {"daily", "encounter", "manual"}
        if replenish_type not in valid:
            raise ValueError(
                f"Invalid replenish_type '{replenish_type}'. "
                f"Must be one of: {', '.join(sorted(valid))}"
            )

        sql = """
            INSERT INTO point_pools
                (character_source_id, max_points, current_points, replenish_type, notes)
            VALUES (%s, %s, %s, %s, %s)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (
                character_source_id, max_points, max_points, replenish_type, notes
            ))
            return cursor.lastrowid

    def get_pool(self, pool_id: int) -> dict | None:
        sql = """
            SELECT pp.*, cs.source_id, cs.character_id,
                   s.name AS source_name
            FROM point_pools pp
            JOIN character_sources cs ON cs.id = pp.character_source_id
            JOIN sources s ON s.id = cs.source_id
            WHERE pp.id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (pool_id,))
            return cursor.fetchone()

    def get_pool_by_character_source(self, character_source_id: int) -> dict | None:
        sql = "SELECT * FROM point_pools WHERE character_source_id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_source_id,))
            return cursor.fetchone()

    def get_all_pools_for_character(self, character_id: int) -> list[dict]:
        """
        Returns all point pools for a character, with source name and
        replenishment type. Useful for a resource-management summary view.
        """
        sql = """
            SELECT pp.*, s.name AS source_name, sc.name AS category_name
            FROM point_pools pp
            JOIN character_sources cs ON cs.id  = pp.character_source_id
            JOIN sources s            ON s.id   = cs.source_id
            JOIN source_categories sc ON sc.id  = s.source_category_id
            WHERE cs.character_id = %s
            ORDER BY sc.name ASC, s.name ASC
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id,))
            return cursor.fetchall()

    def spend_points(self, pool_id: int, amount: int) -> tuple[bool, str]:
        """
        Deducts points from a pool. Returns (success, reason).
        Fails gracefully if there aren't enough points.
        """
        pool = self.get_pool(pool_id)
        if not pool:
            return False, "Pool not found."
        if amount <= 0:
            return False, "Amount must be a positive integer."
        if pool["current_points"] < amount:
            return (
                False,
                f"Not enough points. "
                f"({pool['current_points']} remaining, {amount} required.)"
            )

        sql = """
            UPDATE point_pools
            SET current_points = current_points - %s
            WHERE id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (amount, pool_id))
        return True, ""

    def restore_points(self, pool_id: int, amount: int = None) -> None:
        """
        Restores points to a pool.
        If amount is None, restores to full (used for replenishment events).
        """
        if amount is None:
            sql = "UPDATE point_pools SET current_points = max_points WHERE id = %s"
            with self.get_db() as (conn, cursor):
                cursor.execute(sql, (pool_id,))
        else:
            sql = """
                UPDATE point_pools
                SET current_points = LEAST(current_points + %s, max_points)
                WHERE id = %s
            """
            with self.get_db() as (conn, cursor):
                cursor.execute(sql, (amount, pool_id))

    def update_max_points(self, pool_id: int, new_max: int) -> None:
        """
        Updates the pool maximum (e.g. on level-up).
        Also adjusts current_points if it now exceeds the new max.
        """
        sql = """
            UPDATE point_pools
            SET max_points     = %s,
                current_points = LEAST(current_points, %s)
            WHERE id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (new_max, new_max, pool_id))

    def replenish_by_type(self, character_id: int, replenish_type: str) -> list[str]:
        """
        Restores all pools of the given replenish_type for a character.
        Returns a list of source names that were replenished (for UI notification).

        Call with:
            'daily'     — at start of day / after full rest
            'encounter' — after combat ends
        Does not handle 'manual' — those are restored individually by the user.
        """
        sql = """
            SELECT pp.id, s.name AS source_name
            FROM point_pools pp
            JOIN character_sources cs ON cs.id = pp.character_source_id
            JOIN sources s ON s.id = cs.source_id
            WHERE cs.character_id  = %s
              AND pp.replenish_type = %s
              AND pp.current_points < pp.max_points
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id, replenish_type))
            pools_to_restore = cursor.fetchall()

        restored_names = []
        for pool in pools_to_restore:
            self.restore_points(pool["id"])
            restored_names.append(pool["source_name"])

        return restored_names

    # ------------------------------------------------------------------
    # POOL ALLOCATIONS (sub-pools)
    # ------------------------------------------------------------------

    def create_allocation(
        self,
        parent_pool_id: int,
        character_source_id: int,
        name: str,
        allocated_points: int,
    ) -> int:
        """
        Creates a named sub-pool allocation under a parent pool.
        allocated_points and remaining_points start equal.

        The controller should verify that the sum of all allocations
        does not exceed the parent pool's max_points before calling this.
        """
        sql = """
            INSERT INTO pool_allocations
                (parent_pool_id, character_source_id, name,
                 allocated_points, remaining_points)
            VALUES (%s, %s, %s, %s, %s)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (
                parent_pool_id, character_source_id, name,
                allocated_points, allocated_points
            ))
            return cursor.lastrowid

    def get_allocations_for_pool(self, parent_pool_id: int) -> list[dict]:
        """
        Returns all sub-pool allocations for a parent pool,
        with their source names.
        """
        sql = """
            SELECT pa.*, s.name AS source_name
            FROM pool_allocations pa
            JOIN character_sources cs ON cs.id = pa.character_source_id
            JOIN sources s ON s.id = cs.source_id
            WHERE pa.parent_pool_id = %s
            ORDER BY pa.name ASC
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (parent_pool_id,))
            return cursor.fetchall()

    def get_total_allocated(self, parent_pool_id: int) -> int:
        """
        Returns the sum of allocated_points across all sub-pools.
        Used by the controller to validate that a new allocation
        won't exceed the parent pool maximum.
        """
        sql = """
            SELECT COALESCE(SUM(allocated_points), 0) AS total
            FROM pool_allocations
            WHERE parent_pool_id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (parent_pool_id,))
            row = cursor.fetchone()
            return int(row["total"]) if row else 0

    def update_allocation(
        self,
        allocation_id: int,
        allocated_points: int,
        remaining_points: int,
    ) -> None:
        """
        Updates a sub-pool's allocation and remaining points.
        Typically called when the user re-invests points at rest
        or adjusts mid-session. The controller validates totals first.
        """
        sql = """
            UPDATE pool_allocations
            SET allocated_points = %s,
                remaining_points = %s
            WHERE id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (allocated_points, remaining_points, allocation_id))

    def spend_from_allocation(self, allocation_id: int, amount: int) -> tuple[bool, str]:
        """
        Spends points from a sub-pool allocation.
        Returns (success, reason).
        """
        sql = "SELECT * FROM pool_allocations WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (allocation_id,))
            allocation = cursor.fetchone()

        if not allocation:
            return False, "Allocation not found."
        if amount <= 0:
            return False, "Amount must be a positive integer."
        if allocation["remaining_points"] < amount:
            return (
                False,
                f"Not enough points in '{allocation['name']}'. "
                f"({allocation['remaining_points']} remaining, {amount} required.)"
            )

        sql = """
            UPDATE pool_allocations
            SET remaining_points = remaining_points - %s
            WHERE id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (amount, allocation_id))
        return True, ""

    def replenish_allocations_for_pool(self, parent_pool_id: int) -> None:
        """
        Resets all allocations' remaining_points back to their allocated_points.
        Called when the parent pool replenishes (daily rest, end of encounter, etc.)
        Note: does NOT change allocated_points — the user's investment choices
        are preserved, only the spent amounts reset.
        """
        sql = """
            UPDATE pool_allocations
            SET remaining_points = allocated_points
            WHERE parent_pool_id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (parent_pool_id,))

    def delete_allocation(self, allocation_id: int) -> None:
        sql = "DELETE FROM pool_allocations WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (allocation_id,))

    # ------------------------------------------------------------------
    # EFFECT ACTIVE MODIFIERS (user-entered investment-scaled values)
    # ------------------------------------------------------------------

    def set_active_modifier(
        self,
        effect_id: int,
        character_id: int,
        current_modifier: int,
    ) -> None:
        """
        Sets or updates the user-entered modifier for a pool-linked effect.
        Called whenever the user invests points and enters the resulting bonus.

        Uses INSERT ... ON DUPLICATE KEY UPDATE so it's always safe to call,
        whether the row exists yet or not.
        """
        sql = """
            INSERT INTO effect_active_modifiers (effect_id, character_id, current_modifier)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE current_modifier = VALUES(current_modifier)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (effect_id, character_id, current_modifier))

    def get_active_modifier(self, effect_id: int, character_id: int) -> int:
        """
        Returns the current user-entered modifier for a pool-linked effect.
        Returns 0 if not yet set (no investment has been made).
        """
        sql = """
            SELECT current_modifier FROM effect_active_modifiers
            WHERE effect_id = %s AND character_id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (effect_id, character_id))
            row = cursor.fetchone()
            return row["current_modifier"] if row else 0

    def clear_active_modifier(self, effect_id: int, character_id: int) -> None:
        """
        Resets a pool-linked effect's modifier to 0.
        Called when the user removes all investment from an implement/sub-source.
        """
        sql = """
            UPDATE effect_active_modifiers
            SET current_modifier = 0
            WHERE effect_id = %s AND character_id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (effect_id, character_id))

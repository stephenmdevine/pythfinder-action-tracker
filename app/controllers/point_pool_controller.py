from app.controllers.base_controller import BaseController
from app.models.point_pool_model import PointPoolModel
from app.models.source_model import SourceModel


class PointPoolController(BaseController):
    """
    Manages point pools, sub-pool allocations, and the user-entered
    modifiers for investment-scaled effects (e.g. Occultist implements).

    The controller validates allocation totals before writing, so the
    model layer can stay free of that cross-pool logic.
    """

    def __init__(self):
        self.pools   = PointPoolModel()
        self.sources = SourceModel()

    # ------------------------------------------------------------------
    # POINT POOLS
    # ------------------------------------------------------------------

    def create_pool(
        self,
        character_source_id: int,
        max_points: int,
        replenish_type: str,
        notes: str = "",
    ) -> dict:
        if max_points <= 0:
            return self._err("Max points must be greater than zero.")
        try:
            pool_id = self.pools.create_pool(
                character_source_id, max_points, replenish_type, notes
            )
            pool = self.pools.get_pool(pool_id)
            return self._ok(pool, f"Pool created with {max_points} points.")
        except ValueError as e:
            return self._err(str(e))
        except Exception as e:
            return self._err(f"Failed to create pool: {e}")

    def list_pools_for_character(self, character_id: int) -> dict:
        try:
            pools = self.pools.get_all_pools_for_character(character_id)
            # Attach allocations to any pool that has them
            for pool in pools:
                pool["allocations"] = self.pools.get_allocations_for_pool(pool["id"])
            return self._ok(pools)
        except Exception as e:
            return self._err(f"Failed to load pools: {e}")

    def spend_points(self, pool_id: int, amount: int) -> dict:
        success, reason = self.pools.spend_points(pool_id, amount)
        if not success:
            return self._err(reason)
        pool = self.pools.get_pool(pool_id)
        return self._ok(pool, f"Spent {amount} point(s).")

    def restore_pool(self, pool_id: int, amount: int = None) -> dict:
        """
        Restores a pool manually. Pass amount=None to restore fully.
        Used for 'manual' replenish_type pools (wands, rods, etc.)
        """
        try:
            self.pools.restore_points(pool_id, amount)
            pool = self.pools.get_pool(pool_id)
            msg  = "Pool fully restored." if amount is None else f"Restored {amount} point(s)."
            return self._ok(pool, msg)
        except Exception as e:
            return self._err(f"Failed to restore pool: {e}")

    def update_pool_maximum(self, pool_id: int, new_max: int) -> dict:
        """
        Updates pool maximum on level-up. Also caps current points to new max.
        """
        if new_max <= 0:
            return self._err("Max points must be greater than zero.")
        try:
            self.pools.update_max_points(pool_id, new_max)
            pool = self.pools.get_pool(pool_id)
            return self._ok(pool, f"Pool maximum updated to {new_max}.")
        except Exception as e:
            return self._err(f"Failed to update pool: {e}")

    def replenish_after_rest(self, character_id: int) -> dict:
        """
        Restores all 'daily' pools for a character.
        Call this when the user marks a full rest.
        Also replenishes all sub-pool allocations under those pools.
        """
        try:
            restored = self.pools.replenish_by_type(character_id, "daily")
            self._replenish_allocations_for_type(character_id, "daily")
            msg = (
                f"Restored {len(restored)} daily pool(s): {', '.join(restored)}."
                if restored else "No daily pools needed restoring."
            )
            return self._ok(data=restored, message=msg)
        except Exception as e:
            return self._err(f"Failed to replenish pools: {e}")

    def replenish_after_encounter(self, character_id: int) -> dict:
        """
        Restores all 'encounter' pools for a character.
        Call this when combat ends.
        """
        try:
            restored = self.pools.replenish_by_type(character_id, "encounter")
            self._replenish_allocations_for_type(character_id, "encounter")
            msg = (
                f"Restored {len(restored)} encounter pool(s): {', '.join(restored)}."
                if restored else "No encounter pools needed restoring."
            )
            return self._ok(data=restored, message=msg)
        except Exception as e:
            return self._err(f"Failed to replenish pools: {e}")

    def _replenish_allocations_for_type(
        self, character_id: int, replenish_type: str
    ) -> None:
        """
        Internal: replenishes sub-pool remaining_points for all pools
        of the given type. Does not change allocated_points (the user's
        investment choices are preserved across rests).
        """
        all_pools = self.pools.get_all_pools_for_character(character_id)
        for pool in all_pools:
            if pool["replenish_type"] == replenish_type:
                self.pools.replenish_allocations_for_pool(pool["id"])

    # ------------------------------------------------------------------
    # SUB-POOL ALLOCATIONS
    # ------------------------------------------------------------------

    def allocate_points(
        self,
        parent_pool_id: int,
        character_source_id: int,
        name: str,
        allocated_points: int,
    ) -> dict:
        """
        Creates a new sub-pool allocation under a parent pool.
        Validates that the new allocation doesn't exceed the parent max.
        """
        if allocated_points <= 0:
            return self._err("Allocated points must be greater than zero.")

        pool = self.pools.get_pool(parent_pool_id)
        if not pool:
            return self._err("Parent pool not found.")

        current_total = self.pools.get_total_allocated(parent_pool_id)
        if current_total + allocated_points > pool["max_points"]:
            available = pool["max_points"] - current_total
            return self._err(
                f"Allocation would exceed pool maximum. "
                f"({available} point(s) available, {allocated_points} requested.)"
            )

        try:
            allocation_id = self.pools.create_allocation(
                parent_pool_id, character_source_id, name, allocated_points
            )
            allocations = self.pools.get_allocations_for_pool(parent_pool_id)
            return self._ok(
                allocations,
                f"Allocated {allocated_points} point(s) to '{name}'."
            )
        except Exception as e:
            return self._err(f"Failed to create allocation: {e}")

    def reallocate_points(
        self,
        parent_pool_id: int,
        allocation_id: int,
        new_allocated_points: int,
    ) -> dict:
        """
        Changes the point allocation for an existing sub-pool.
        Validates the new total across all sibling allocations.
        Called when the user re-invests at rest (e.g. Occultist redistributing focus).
        """
        if new_allocated_points < 0:
            return self._err("Allocated points cannot be negative.")

        pool = self.pools.get_pool(parent_pool_id)
        if not pool:
            return self._err("Parent pool not found.")

        # Sum all OTHER allocations to check the new total won't exceed max
        all_allocations = self.pools.get_allocations_for_pool(parent_pool_id)
        other_total = sum(
            a["allocated_points"] for a in all_allocations
            if a["id"] != allocation_id
        )
        if other_total + new_allocated_points > pool["max_points"]:
            available = pool["max_points"] - other_total
            return self._err(
                f"Reallocation would exceed pool maximum. "
                f"({available} point(s) available for this allocation.)"
            )

        try:
            # Remaining points reset to the new allocation on reallocation
            self.pools.update_allocation(
                allocation_id,
                allocated_points=new_allocated_points,
                remaining_points=new_allocated_points,
            )
            allocations = self.pools.get_allocations_for_pool(parent_pool_id)
            return self._ok(allocations, "Allocation updated.")
        except Exception as e:
            return self._err(f"Failed to update allocation: {e}")

    def spend_from_allocation(
        self, allocation_id: int, amount: int
    ) -> dict:
        success, reason = self.pools.spend_from_allocation(allocation_id, amount)
        if not success:
            return self._err(reason)
        return self._ok(message=f"Spent {amount} point(s) from allocation.")

    def remove_allocation(self, allocation_id: int) -> dict:
        try:
            self.pools.delete_allocation(allocation_id)
            return self._ok(message="Allocation removed.")
        except Exception as e:
            return self._err(f"Failed to remove allocation: {e}")

    # ------------------------------------------------------------------
    # INVESTMENT-SCALED EFFECT MODIFIERS
    # ------------------------------------------------------------------

    def set_investment_bonus(
        self,
        effect_id: int,
        character_id: int,
        bonus_value: int,
    ) -> dict:
        """
        Records the user-entered bonus for an investment-scaled effect.
        Called after the user invests points and calculates (or looks up)
        the resulting bonus from their rulebook.

        The stacking engine will pick this value up automatically on
        the next call to resolve_modifiers_for_stat().
        """
        try:
            self.pools.set_active_modifier(effect_id, character_id, bonus_value)
            return self._ok(
                {"effect_id": effect_id, "bonus_value": bonus_value},
                f"Investment bonus set to {bonus_value:+d}."
            )
        except Exception as e:
            return self._err(f"Failed to set investment bonus: {e}")

    def clear_investment_bonus(self, effect_id: int, character_id: int) -> dict:
        """
        Resets an investment-scaled effect's bonus to 0.
        Called when the user removes all points from an implement/sub-source.
        """
        try:
            self.pools.clear_active_modifier(effect_id, character_id)
            return self._ok(message="Investment bonus cleared.")
        except Exception as e:
            return self._err(f"Failed to clear investment bonus: {e}")

from app.models.base_model import BaseModel


class SourceModel(BaseModel):
    """
    Handles DB operations for sources and source_categories.
    Sources are the generic objects (feats, spells, conditions, class features,
    magic items, etc.) that carry effects and action costs.
    """

    # ------------------------------------------------------------------
    # SOURCE CATEGORIES
    # ------------------------------------------------------------------

    def get_all_categories(self) -> list[dict]:
        sql = "SELECT * FROM source_categories ORDER BY name ASC"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql)
            return cursor.fetchall()

    def create_category(self, name: str) -> int:
        sql = "INSERT INTO source_categories (name) VALUES (%s)"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (name,))
            return cursor.lastrowid

    # ------------------------------------------------------------------
    # SOURCES — CREATE
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        source_category_id: int,
        duration_type: str,
        duration_value: int = None,
        action_type_id: int = None,
        description: str = "",
    ) -> int:
        """
        Creates a new source. Returns its new id.

        duration_type must be one of:
            'permanent', 'toggle', 'rounds', 'until_next_turn', 'encounter', 'timed'

        duration_value:
            - 'rounds' / 'timed': the number of rounds or minutes
            - all others: leave None

        action_type_id:
            - None for passive sources (Weapon Focus, ability score bonuses)
            - Set to the action required to activate (Power Attack = Free, Haste = not activated by character)
        """
        valid_duration_types = {
            "permanent", "toggle", "rounds", "until_next_turn", "encounter", "timed"
        }
        if duration_type not in valid_duration_types:
            raise ValueError(
                f"Invalid duration_type '{duration_type}'. "
                f"Must be one of: {', '.join(sorted(valid_duration_types))}"
            )

        sql = """
            INSERT INTO sources
                (name, source_category_id, duration_type, duration_value, action_type_id, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (
                name, source_category_id, duration_type,
                duration_value, action_type_id, description
            ))
            return cursor.lastrowid

    # ------------------------------------------------------------------
    # SOURCES — READ
    # ------------------------------------------------------------------

    def get_by_id(self, source_id: int) -> dict | None:
        sql = """
            SELECT s.*, sc.name AS category_name, at.name AS action_type_name
            FROM sources s
            JOIN source_categories sc ON s.source_category_id = sc.id
            LEFT JOIN action_types at ON s.action_type_id = at.id
            WHERE s.id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (source_id,))
            return cursor.fetchone()

    def get_all(self, source_category_id: int = None) -> list[dict]:
        """
        Returns all sources, optionally filtered by category.
        Joined with category name and action type name for display.
        """
        sql = """
            SELECT s.*, sc.name AS category_name, at.name AS action_type_name
            FROM sources s
            JOIN source_categories sc ON s.source_category_id = sc.id
            LEFT JOIN action_types at ON s.action_type_id = at.id
        """
        params = ()
        if source_category_id is not None:
            sql += " WHERE s.source_category_id = %s"
            params = (source_category_id,)
        sql += " ORDER BY sc.name ASC, s.name ASC"

        with self.get_db() as (conn, cursor):
            cursor.execute(sql, params)
            return cursor.fetchall()

    def search_by_name(self, query: str) -> list[dict]:
        """
        Case-insensitive partial name search across all sources.
        """
        sql = """
            SELECT s.*, sc.name AS category_name, at.name AS action_type_name
            FROM sources s
            JOIN source_categories sc ON s.source_category_id = sc.id
            LEFT JOIN action_types at ON s.action_type_id = at.id
            WHERE s.name LIKE %s
            ORDER BY s.name ASC
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (f"%{query}%",))
            return cursor.fetchall()

    # ------------------------------------------------------------------
    # SOURCES — UPDATE
    # ------------------------------------------------------------------

    def update(
        self,
        source_id: int,
        name: str = None,
        source_category_id: int = None,
        duration_type: str = None,
        duration_value: int = None,
        action_type_id: int = None,
        description: str = None,
    ) -> None:
        fields, values = [], []
        if name is not None:
            fields.append("name = %s"); values.append(name)
        if source_category_id is not None:
            fields.append("source_category_id = %s"); values.append(source_category_id)
        if duration_type is not None:
            fields.append("duration_type = %s"); values.append(duration_type)
        if duration_value is not None:
            fields.append("duration_value = %s"); values.append(duration_value)
        if action_type_id is not None:
            fields.append("action_type_id = %s"); values.append(action_type_id)
        if description is not None:
            fields.append("description = %s"); values.append(description)

        if not fields:
            return

        values.append(source_id)
        sql = f"UPDATE sources SET {', '.join(fields)} WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, tuple(values))

    # ------------------------------------------------------------------
    # SOURCES — DELETE
    # ------------------------------------------------------------------

    def delete(self, source_id: int) -> None:
        """
        Deletes a source. Cascades to its effects.
        Note: will also remove this source from any character_sources rows.
        """
        sql = "DELETE FROM sources WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (source_id,))

    # ------------------------------------------------------------------
    # CHARACTER SOURCES  (assigning sources to a character)
    # ------------------------------------------------------------------

    def assign_to_character(self, character_id: int, source_id: int) -> int:
        """
        Assigns a source to a character (e.g. they learn a feat or gain a condition).
        Returns the new character_sources id.
        """
        sql = """
            INSERT INTO character_sources (character_id, source_id, is_active, rounds_remaining)
            VALUES (%s, %s, FALSE, NULL)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id, source_id))
            return cursor.lastrowid

    def get_character_sources(self, character_id: int, active_only: bool = False) -> list[dict]:
        """
        Returns all sources assigned to a character, with full source detail.
        Pass active_only=True to get only currently activated sources.
        """
        sql = """
            SELECT
                cs.id AS character_source_id,
                cs.is_active,
                cs.rounds_remaining,
                s.*,
                sc.name AS category_name,
                at.name AS action_type_name
            FROM character_sources cs
            JOIN sources s ON cs.source_id = s.id
            JOIN source_categories sc ON s.source_category_id = sc.id
            LEFT JOIN action_types at ON s.action_type_id = at.id
            WHERE cs.character_id = %s
        """
        params = [character_id]
        if active_only:
            sql += " AND cs.is_active = TRUE"
        sql += " ORDER BY sc.name ASC, s.name ASC"

        with self.get_db() as (conn, cursor):
            cursor.execute(sql, tuple(params))
            return cursor.fetchall()

    def set_active(self, character_source_id: int, is_active: bool, rounds: int = None) -> None:
        """
        Activates or deactivates a character's source.
        When activating a 'rounds' source, pass the number of rounds remaining.
        """
        sql = """
            UPDATE character_sources
            SET is_active = %s, rounds_remaining = %s
            WHERE id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (is_active, rounds, character_source_id))

    def tick_rounds(self, character_id: int) -> list[dict]:
        """
        Called at the start of each new round.
        Decrements rounds_remaining for all active timed sources on a character.
        Deactivates any that reach 0.
        Returns a list of sources that just expired (for UI notification).
        """
        # Decrement
        decrement_sql = """
            UPDATE character_sources
            SET rounds_remaining = rounds_remaining - 1
            WHERE character_id = %s
              AND is_active = TRUE
              AND rounds_remaining IS NOT NULL
        """
        # Deactivate expired
        expire_sql = """
            UPDATE character_sources
            SET is_active = FALSE, rounds_remaining = NULL
            WHERE character_id = %s
              AND is_active = TRUE
              AND rounds_remaining IS NOT NULL
              AND rounds_remaining <= 0
        """
        # Fetch what just expired (before deactivation, rounds_remaining = 0)
        fetch_expired_sql = """
            SELECT cs.id AS character_source_id, s.name
            FROM character_sources cs
            JOIN sources s ON cs.source_id = s.id
            WHERE cs.character_id = %s
              AND cs.is_active = FALSE
              AND cs.rounds_remaining IS NULL
              AND s.duration_type = 'rounds'
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(decrement_sql, (character_id,))
            cursor.execute(expire_sql, (character_id,))
            cursor.execute(fetch_expired_sql, (character_id,))
            return cursor.fetchall()

    def remove_from_character(self, character_source_id: int) -> None:
        """
        Removes a source assignment from a character entirely
        (e.g. a condition is cured, or a feat is retrained).
        """
        sql = "DELETE FROM character_sources WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_source_id,))

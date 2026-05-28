from app.models.base_model import BaseModel


class StatModel(BaseModel):
    """
    Handles DB operations for the stats reference table and
    character_stats (per-character base values).
    """

    # ------------------------------------------------------------------
    # REFERENCE STATS (global list, seeded at setup)
    # ------------------------------------------------------------------

    def get_all(self, category: str = None) -> list[dict]:
        """
        Returns all stats, optionally filtered by category.
        category options: 'ability', 'combat', 'save', 'skill', 'other'
        """
        sql = "SELECT * FROM stats"
        params = ()
        if category:
            sql += " WHERE category = %s"
            params = (category,)
        sql += " ORDER BY category ASC, name ASC"

        with self.get_db() as (conn, cursor):
            cursor.execute(sql, params)
            return cursor.fetchall()

    def get_by_id(self, stat_id: int) -> dict | None:
        sql = "SELECT * FROM stats WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (stat_id,))
            return cursor.fetchone()

    def get_by_name(self, name: str) -> dict | None:
        sql = "SELECT * FROM stats WHERE name = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (name,))
            return cursor.fetchone()

    def create(self, name: str, abbreviation: str = "", category: str = "other") -> int:
        """
        Allows users to add custom stats beyond the seeded defaults
        (e.g. a homebrew system attribute).
        """
        sql = """
            INSERT INTO stats (name, abbreviation, category)
            VALUES (%s, %s, %s)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (name, abbreviation, category))
            return cursor.lastrowid

    # ------------------------------------------------------------------
    # CHARACTER BASE STATS (per-character values)
    # ------------------------------------------------------------------

    def set_base_value(self, character_id: int, stat_id: int, base_value: int) -> None:
        """
        Inserts or updates a character's base value for a stat.
        Uses INSERT ... ON DUPLICATE KEY UPDATE to handle both cases cleanly.
        The UNIQUE KEY on (character_id, stat_id) in the schema makes this safe.
        """
        sql = """
            INSERT INTO character_stats (character_id, stat_id, base_value)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE base_value = VALUES(base_value)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id, stat_id, base_value))

    def get_base_value(self, character_id: int, stat_id: int) -> int:
        """
        Returns a character's base value for a stat (0 if not yet set).
        """
        sql = """
            SELECT base_value FROM character_stats
            WHERE character_id = %s AND stat_id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id, stat_id))
            row = cursor.fetchone()
            return row["base_value"] if row else 0

    def get_all_base_values(self, character_id: int) -> list[dict]:
        """
        Returns all base stat values for a character, joined with stat names.
        Useful for populating a character sheet view.
        """
        sql = """
            SELECT cs.base_value, s.id AS stat_id, s.name, s.abbreviation, s.category
            FROM character_stats cs
            JOIN stats s ON s.id = cs.stat_id
            WHERE cs.character_id = %s
            ORDER BY s.category ASC, s.name ASC
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id,))
            return cursor.fetchall()

    def get_computed_value(
        self,
        character_id: int,
        stat_id: int,
        net_modifier: int,
    ) -> int:
        """
        Returns base_value + net_modifier.
        The net_modifier should come from BonusTypeModel.resolve_modifiers_for_stat().

        Keeping this as a simple addition here rather than a DB query means
        the resolution engine and the base value stay cleanly separated.
        """
        base = self.get_base_value(character_id, stat_id)
        return base + net_modifier

    def delete_base_value(self, character_id: int, stat_id: int) -> None:
        sql = """
            DELETE FROM character_stats
            WHERE character_id = %s AND stat_id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id, stat_id))

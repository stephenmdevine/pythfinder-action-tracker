from app.models.base_model import BaseModel


class CharacterModel(BaseModel):
    """
    Handles all DB operations for characters and their level history.
    """

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create(self, campaign_id: int, name: str, is_pc: bool = True, notes: str = "") -> int:
        """
        Inserts a new character and returns its new id.
        """
        sql = """
            INSERT INTO characters (campaign_id, name, is_pc, notes)
            VALUES (%s, %s, %s, %s)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (campaign_id, name, is_pc, notes))
            return cursor.lastrowid

    def add_level(self, character_id: int, level: int, class_name: str, notes: str = "") -> int:
        """
        Records a level-up event for a character.
        """
        sql = """
            INSERT INTO character_levels (character_id, level, class_name, notes)
            VALUES (%s, %s, %s, %s)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id, level, class_name, notes))
            return cursor.lastrowid

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def get_by_id(self, character_id: int) -> dict | None:
        """
        Returns a single character row as a dict, or None if not found.
        """
        sql = "SELECT * FROM characters WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id,))
            return cursor.fetchone()

    def get_all_by_campaign(self, campaign_id: int) -> list[dict]:
        """
        Returns all characters in a campaign, PCs first then NPCs,
        alphabetically within each group.
        """
        sql = """
            SELECT * FROM characters
            WHERE campaign_id = %s
            ORDER BY is_pc DESC, name ASC
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (campaign_id,))
            return cursor.fetchall()

    def get_level_history(self, character_id: int) -> list[dict]:
        """
        Returns all level-up records for a character in ascending level order.
        """
        sql = """
            SELECT * FROM character_levels
            WHERE character_id = %s
            ORDER BY level ASC
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id,))
            return cursor.fetchall()

    def get_current_level(self, character_id: int) -> int:
        """
        Returns the highest level recorded for a character (0 if none).
        """
        sql = """
            SELECT COALESCE(MAX(level), 0) AS current_level
            FROM character_levels
            WHERE character_id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id,))
            row = cursor.fetchone()
            return row["current_level"] if row else 0

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(self, character_id: int, name: str = None, notes: str = None) -> None:
        """
        Updates mutable character fields. Only updates fields that are passed in.
        """
        fields, values = [], []
        if name is not None:
            fields.append("name = %s")
            values.append(name)
        if notes is not None:
            fields.append("notes = %s")
            values.append(notes)

        if not fields:
            return  # nothing to update

        values.append(character_id)
        sql = f"UPDATE characters SET {', '.join(fields)} WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, tuple(values))

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete(self, character_id: int) -> None:
        """
        Deletes a character. Cascades to stats, sources, inventory, and ledger.
        """
        sql = "DELETE FROM characters WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id,))

from app.models.base_model import BaseModel


class CampaignModel(BaseModel):
    """
    Handles all DB operations for campaigns.
    """

    def create(self, name: str, description: str = "") -> int:
        sql = """
            INSERT INTO campaigns (name, description)
            VALUES (%s, %s)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (name, description))
            return cursor.lastrowid

    def get_by_id(self, campaign_id: int) -> dict | None:
        sql = "SELECT * FROM campaigns WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (campaign_id,))
            return cursor.fetchone()

    def get_all(self) -> list[dict]:
        sql = "SELECT * FROM campaigns ORDER BY name ASC"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql)
            return cursor.fetchall()

    def update(self, campaign_id: int, name: str = None, description: str = None) -> None:
        fields, values = [], []
        if name is not None:
            fields.append("name = %s")
            values.append(name)
        if description is not None:
            fields.append("description = %s")
            values.append(description)

        if not fields:
            return

        values.append(campaign_id)
        sql = f"UPDATE campaigns SET {', '.join(fields)} WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, tuple(values))

    def delete(self, campaign_id: int) -> None:
        sql = "DELETE FROM campaigns WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (campaign_id,))

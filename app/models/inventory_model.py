from app.models.base_model import BaseModel


class InventoryModel(BaseModel):
    """
    Handles DB operations for items, item_categories, character_inventory,
    and item_source_links. Also computes encumbrance.
    """

    # ------------------------------------------------------------------
    # ITEM CATEGORIES
    # ------------------------------------------------------------------

    def get_all_categories(self) -> list[dict]:
        sql = "SELECT * FROM item_categories ORDER BY name ASC"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql)
            return cursor.fetchall()

    def create_category(self, name: str) -> int:
        sql = "INSERT INTO item_categories (name) VALUES (%s)"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (name,))
            return cursor.lastrowid

    # ------------------------------------------------------------------
    # ITEMS (the global item library)
    # ------------------------------------------------------------------

    def create_item(
        self,
        name: str,
        item_category_id: int,
        weight_lbs: float = 0.0,
        value_gold: float = 0.0,
        is_consumable: bool = False,
        description: str = "",
    ) -> int:
        sql = """
            INSERT INTO items
                (name, item_category_id, weight_lbs, value_gold, is_consumable, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (
                name, item_category_id, weight_lbs, value_gold, is_consumable, description
            ))
            return cursor.lastrowid

    def get_item_by_id(self, item_id: int) -> dict | None:
        sql = """
            SELECT i.*, ic.name AS category_name
            FROM items i
            JOIN item_categories ic ON ic.id = i.item_category_id
            WHERE i.id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (item_id,))
            return cursor.fetchone()

    def get_all_items(self, category_id: int = None) -> list[dict]:
        sql = """
            SELECT i.*, ic.name AS category_name
            FROM items i
            JOIN item_categories ic ON ic.id = i.item_category_id
        """
        params = ()
        if category_id is not None:
            sql += " WHERE i.item_category_id = %s"
            params = (category_id,)
        sql += " ORDER BY ic.name ASC, i.name ASC"

        with self.get_db() as (conn, cursor):
            cursor.execute(sql, params)
            return cursor.fetchall()

    def search_items(self, query: str) -> list[dict]:
        sql = """
            SELECT i.*, ic.name AS category_name
            FROM items i
            JOIN item_categories ic ON ic.id = i.item_category_id
            WHERE i.name LIKE %s
            ORDER BY i.name ASC
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (f"%{query}%",))
            return cursor.fetchall()

    def update_item(
        self,
        item_id: int,
        name: str = None,
        item_category_id: int = None,
        weight_lbs: float = None,
        value_gold: float = None,
        is_consumable: bool = None,
        description: str = None,
    ) -> None:
        fields, values = [], []
        if name is not None:
            fields.append("name = %s"); values.append(name)
        if item_category_id is not None:
            fields.append("item_category_id = %s"); values.append(item_category_id)
        if weight_lbs is not None:
            fields.append("weight_lbs = %s"); values.append(weight_lbs)
        if value_gold is not None:
            fields.append("value_gold = %s"); values.append(value_gold)
        if is_consumable is not None:
            fields.append("is_consumable = %s"); values.append(is_consumable)
        if description is not None:
            fields.append("description = %s"); values.append(description)

        if not fields:
            return

        values.append(item_id)
        sql = f"UPDATE items SET {', '.join(fields)} WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, tuple(values))

    def delete_item(self, item_id: int) -> None:
        sql = "DELETE FROM items WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (item_id,))

    # ------------------------------------------------------------------
    # CHARACTER INVENTORY
    # ------------------------------------------------------------------

    def add_to_inventory(
        self,
        character_id: int,
        item_id: int,
        quantity: int = 1,
        notes: str = "",
    ) -> int:
        """
        Adds an item to a character's inventory.
        Returns the new character_inventory id.
        Note: the WealthLedgerModel should be called separately to record
        the corresponding debit entry.
        """
        sql = """
            INSERT INTO character_inventory (character_id, item_id, quantity, notes)
            VALUES (%s, %s, %s, %s)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id, item_id, quantity, notes))
            return cursor.lastrowid

    def get_inventory(self, character_id: int) -> list[dict]:
        """
        Returns a character's full inventory with item detail and total weight per row.
        """
        sql = """
            SELECT
                ci.id               AS inventory_id,
                ci.quantity,
                ci.is_equipped,
                ci.notes,
                ci.acquired_at,
                i.id                AS item_id,
                i.name,
                i.weight_lbs,
                i.value_gold,
                i.is_consumable,
                ic.name             AS category_name,
                (ci.quantity * i.weight_lbs) AS total_weight
            FROM character_inventory ci
            JOIN items i            ON i.id  = ci.item_id
            JOIN item_categories ic ON ic.id = i.item_category_id
            WHERE ci.character_id = %s
            ORDER BY ic.name ASC, i.name ASC
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id,))
            return cursor.fetchall()

    def update_inventory_row(
        self,
        inventory_id: int,
        quantity: int = None,
        is_equipped: bool = None,
        notes: str = None,
    ) -> None:
        fields, values = [], []
        if quantity is not None:
            fields.append("quantity = %s"); values.append(quantity)
        if is_equipped is not None:
            fields.append("is_equipped = %s"); values.append(is_equipped)
        if notes is not None:
            fields.append("notes = %s"); values.append(notes)

        if not fields:
            return

        values.append(inventory_id)
        sql = f"UPDATE character_inventory SET {', '.join(fields)} WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, tuple(values))

    def remove_from_inventory(self, inventory_id: int) -> None:
        sql = "DELETE FROM character_inventory WHERE id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (inventory_id,))

    # ------------------------------------------------------------------
    # ENCUMBRANCE
    # ------------------------------------------------------------------

    def get_total_weight(self, character_id: int) -> float:
        """
        Returns the total carried weight in lbs for a character.
        """
        sql = """
            SELECT COALESCE(SUM(ci.quantity * i.weight_lbs), 0) AS total_weight
            FROM character_inventory ci
            JOIN items i ON i.id = ci.item_id
            WHERE ci.character_id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id,))
            row = cursor.fetchone()
            return float(row["total_weight"]) if row else 0.0

    def get_encumbrance_label(self, total_weight: float, light_load_limit: float) -> str:
        """
        Returns 'Light', 'Medium', 'Heavy', or 'Over Limit' based on PF1e thresholds.
        light_load_limit should come from the character's Strength score lookup
        (passed in from the controller, not looked up here — keeps concerns separated).
        """
        if total_weight <= light_load_limit:
            return "Light"
        elif total_weight <= light_load_limit * 2:
            return "Medium"
        elif total_weight <= light_load_limit * 3:
            return "Heavy"
        else:
            return "Over Limit"

    # ------------------------------------------------------------------
    # ITEM SOURCE LINKS (magic items that also act as sources)
    # ------------------------------------------------------------------

    def link_item_to_source(self, item_id: int, source_id: int) -> int:
        sql = "INSERT INTO item_source_links (item_id, source_id) VALUES (%s, %s)"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (item_id, source_id))
            return cursor.lastrowid

    def get_sources_for_item(self, item_id: int) -> list[dict]:
        sql = """
            SELECT s.*, sc.name AS category_name
            FROM item_source_links isl
            JOIN sources s ON s.id = isl.source_id
            JOIN source_categories sc ON sc.id = s.source_category_id
            WHERE isl.item_id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (item_id,))
            return cursor.fetchall()

    def unlink_item_from_source(self, item_id: int, source_id: int) -> None:
        sql = "DELETE FROM item_source_links WHERE item_id = %s AND source_id = %s"
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (item_id, source_id))

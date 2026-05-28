from datetime import date
from app.models.base_model import BaseModel
from config.settings import COIN_TO_GOLD


class WealthLedgerModel(BaseModel):
    """
    Handles all entries in the wealth_ledger table.
    The ledger is append-only by design — entries are never edited,
    only added. This gives a full audit trail of all wealth changes.

    Running wealth is always computed from the sum of all entries,
    never stored as a single balance field, so it's always accurate.
    """

    # ------------------------------------------------------------------
    # CORE ENTRY CREATION
    # ------------------------------------------------------------------

    def add_entry(
        self,
        character_id: int,
        entry_type: str,                # 'credit' or 'debit'
        description: str,
        platinum: int = 0,
        gold: int = 0,
        silver: int = 0,
        copper: int = 0,
        character_inventory_id: int = None,
        session_date: date = None,
    ) -> int:
        """
        Adds a ledger entry. Returns the new entry id.
        entry_type: 'credit' (gaining wealth) or 'debit' (spending/losing wealth).
        """
        if entry_type not in ("credit", "debit"):
            raise ValueError("entry_type must be 'credit' or 'debit'")

        sql = """
            INSERT INTO wealth_ledger
                (character_id, entry_type, platinum, gold, silver, copper,
                 description, character_inventory_id, session_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (
                character_id, entry_type, platinum, gold, silver, copper,
                description, character_inventory_id, session_date or date.today()
            ))
            return cursor.lastrowid

    # ------------------------------------------------------------------
    # CONVENIENCE HELPERS
    # ------------------------------------------------------------------

    def record_item_acquired(
        self,
        character_id: int,
        item_name: str,
        value_gold: float,
        inventory_id: int,
        session_date: date = None,
    ) -> int:
        """
        Auto-generates a debit entry when an item is added to inventory.
        Converts the gold value into coin denominations for the ledger.
        Called by the controller immediately after InventoryModel.add_to_inventory().
        """
        gold_int  = int(value_gold)
        silver_int = int((value_gold - gold_int) * 10)
        copper_int = int(round((value_gold - gold_int - silver_int / 10) * 100))

        return self.add_entry(
            character_id=character_id,
            entry_type="debit",
            description=f"Acquired: {item_name}",
            gold=gold_int,
            silver=silver_int,
            copper=copper_int,
            character_inventory_id=inventory_id,
            session_date=session_date,
        )

    def record_item_sold(
        self,
        character_id: int,
        item_name: str,
        value_gold: float,
        session_date: date = None,
    ) -> int:
        """
        Auto-generates a credit entry when an item is sold.
        By default PF1e items sell for half value — pass the already-halved amount.
        """
        gold_int   = int(value_gold)
        silver_int = int((value_gold - gold_int) * 10)
        copper_int = int(round((value_gold - gold_int - silver_int / 10) * 100))

        return self.add_entry(
            character_id=character_id,
            entry_type="credit",
            description=f"Sold: {item_name}",
            gold=gold_int,
            silver=silver_int,
            copper=copper_int,
            session_date=session_date,
        )

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def get_ledger(self, character_id: int) -> list[dict]:
        """
        Returns all ledger entries for a character, newest first.
        """
        sql = """
            SELECT wl.*, ci.item_id
            FROM wealth_ledger wl
            LEFT JOIN character_inventory ci ON ci.id = wl.character_inventory_id
            WHERE wl.character_id = %s
            ORDER BY wl.created_at DESC
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id,))
            return cursor.fetchall()

    def get_running_total_gold(self, character_id: int) -> float:
        """
        Computes the character's current net wealth in gold pieces.
        Credits add, debits subtract. All coin types converted via COIN_TO_GOLD.
        Returns a float representing total gold piece equivalent.
        """
        sql = """
            SELECT entry_type, platinum, gold, silver, copper
            FROM wealth_ledger
            WHERE character_id = %s
        """
        with self.get_db() as (conn, cursor):
            cursor.execute(sql, (character_id,))
            rows = cursor.fetchall()

        total = 0.0
        for row in rows:
            value = (
                row["platinum"] * COIN_TO_GOLD["platinum"] +
                row["gold"]     * COIN_TO_GOLD["gold"]     +
                row["silver"]   * COIN_TO_GOLD["silver"]   +
                row["copper"]   * COIN_TO_GOLD["copper"]
            )
            if row["entry_type"] == "credit":
                total += value
            else:
                total -= value

        return round(total, 2)

    def get_running_total_by_coin(self, character_id: int) -> dict:
        """
        Returns the net wealth broken down into the largest coin denominations
        that divide evenly. Useful for displaying "on hand" currency.

        Returns: {"platinum": int, "gold": int, "silver": int, "copper": int}
        """
        total_gold = self.get_running_total_gold(character_id)
        total_copper = int(round(total_gold * 100))

        platinum = total_copper // 1000
        total_copper %= 1000
        gold     = total_copper // 100
        total_copper %= 100
        silver   = total_copper // 10
        copper   = total_copper % 10

        return {
            "platinum": platinum,
            "gold":     gold,
            "silver":   silver,
            "copper":   copper,
        }

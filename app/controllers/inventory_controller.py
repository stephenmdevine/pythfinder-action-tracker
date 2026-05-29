from datetime import date
from app.controllers.base_controller import BaseController
from app.models.inventory_model import InventoryModel
from app.models.wealth_ledger_model import WealthLedgerModel


class InventoryController(BaseController):
    """
    Manages character inventory and the wealth ledger together.

    The core rule: any inventory change that has monetary value
    automatically produces a corresponding ledger entry.
    The controller enforces this pairing so neither the model
    nor the view has to remember to do it.
    """

    def __init__(self):
        self.inventory = InventoryModel()
        self.ledger    = WealthLedgerModel()

    # ------------------------------------------------------------------
    # ITEM LIBRARY
    # ------------------------------------------------------------------

    def create_item(
        self,
        name: str,
        item_category_id: int,
        weight_lbs: float = 0.0,
        value_gold: float = 0.0,
        is_consumable: bool = False,
        description: str = "",
    ) -> dict:
        if not name.strip():
            return self._err("Item name cannot be empty.")
        try:
            item_id = self.inventory.create_item(
                name.strip(), item_category_id, weight_lbs,
                value_gold, is_consumable, description.strip()
            )
            item = self.inventory.get_item_by_id(item_id)
            return self._ok(item, f"Item '{name}' created.")
        except Exception as e:
            return self._err(f"Failed to create item: {e}")

    def get_item(self, item_id: int) -> dict:
        try:
            item = self.inventory.get_item_by_id(item_id)
            if not item:
                return self._err(f"Item {item_id} not found.")
            return self._ok(item)
        except Exception as e:
            return self._err(f"Failed to load item: {e}")

    def list_items(self, category_id: int = None) -> dict:
        try:
            return self._ok(self.inventory.get_all_items(category_id))
        except Exception as e:
            return self._err(f"Failed to list items: {e}")

    def search_items(self, query: str) -> dict:
        if not query.strip():
            return self._err("Search query cannot be empty.")
        try:
            return self._ok(self.inventory.search_items(query.strip()))
        except Exception as e:
            return self._err(f"Failed to search items: {e}")

    def list_item_categories(self) -> dict:
        try:
            return self._ok(self.inventory.get_all_categories())
        except Exception as e:
            return self._err(f"Failed to load categories: {e}")

    # ------------------------------------------------------------------
    # CHARACTER INVENTORY  (with automatic ledger entries)
    # ------------------------------------------------------------------

    def add_item_to_character(
        self,
        character_id: int,
        item_id: int,
        quantity: int = 1,
        notes: str = "",
        record_in_ledger: bool = True,
        session_date: date = None,
    ) -> dict:
        """
        Adds an item to a character's inventory and, if record_in_ledger
        is True, creates a corresponding debit entry in the wealth ledger.

        Pass record_in_ledger=False for items found (loot), given as gifts,
        or crafted — cases where the character didn't purchase the item.
        In those cases the caller can optionally create a custom ledger
        entry with record_custom_entry() to describe the acquisition.
        """
        if quantity <= 0:
            return self._err("Quantity must be at least 1.")

        item = self.inventory.get_item_by_id(item_id)
        if not item:
            return self._err(f"Item {item_id} not found.")

        try:
            inventory_id = self.inventory.add_to_inventory(
                character_id, item_id, quantity, notes.strip()
            )

            if record_in_ledger and item["value_gold"] > 0:
                total_value = item["value_gold"] * quantity
                self.ledger.record_item_acquired(
                    character_id  = character_id,
                    item_name     = f"{item['name']}" + (f" x{quantity}" if quantity > 1 else ""),
                    value_gold    = total_value,
                    inventory_id  = inventory_id,
                    session_date  = session_date,
                )

            inventory = self.inventory.get_inventory(character_id)
            wealth    = self.ledger.get_running_total_by_coin(character_id)
            return self._ok(
                {"inventory": inventory, "wealth": wealth},
                f"Added {quantity}x '{item['name']}' to inventory."
            )
        except Exception as e:
            return self._err(f"Failed to add item: {e}")

    def remove_item_from_character(self, inventory_id: int) -> dict:
        """
        Removes an item from inventory. Does not create a ledger entry —
        for sales, use sell_item() instead.
        """
        try:
            self.inventory.remove_from_inventory(inventory_id)
            return self._ok(message="Item removed from inventory.")
        except Exception as e:
            return self._err(f"Failed to remove item: {e}")

    def sell_item(
        self,
        character_id: int,
        inventory_id: int,
        sell_price_gold: float = None,
        session_date: date = None,
    ) -> dict:
        """
        Sells an item: removes it from inventory and records a ledger credit.
        sell_price_gold defaults to half the item's value (PF1e standard).
        Pass a custom value for negotiated or full-price sales.
        """
        # Fetch the inventory row to get item details before deleting
        inventory = self.inventory.get_inventory(character_id)
        inv_row   = next((r for r in inventory if r["inventory_id"] == inventory_id), None)
        if not inv_row:
            return self._err("Inventory item not found.")

        try:
            if sell_price_gold is None:
                sell_price_gold = (inv_row["value_gold"] * inv_row["quantity"]) / 2

            self.inventory.remove_from_inventory(inventory_id)
            self.ledger.record_item_sold(
                character_id = character_id,
                item_name    = inv_row["name"],
                value_gold   = sell_price_gold,
                session_date = session_date,
            )
            wealth = self.ledger.get_running_total_by_coin(character_id)
            return self._ok(
                {"wealth": wealth},
                f"Sold '{inv_row['name']}' for {sell_price_gold:.2f} gp."
            )
        except Exception as e:
            return self._err(f"Failed to sell item: {e}")

    def update_inventory_row(
        self,
        inventory_id: int,
        quantity: int = None,
        is_equipped: bool = None,
        notes: str = None,
    ) -> dict:
        try:
            self.inventory.update_inventory_row(
                inventory_id, quantity=quantity,
                is_equipped=is_equipped, notes=notes
            )
            return self._ok(message="Inventory updated.")
        except Exception as e:
            return self._err(f"Failed to update inventory: {e}")

    def get_character_inventory(self, character_id: int) -> dict:
        try:
            inventory = self.inventory.get_inventory(character_id)
            total_weight = self.inventory.get_total_weight(character_id)
            return self._ok({
                "inventory":    inventory,
                "total_weight": total_weight,
            })
        except Exception as e:
            return self._err(f"Failed to load inventory: {e}")

    # ------------------------------------------------------------------
    # WEALTH LEDGER
    # ------------------------------------------------------------------

    def record_custom_entry(
        self,
        character_id: int,
        entry_type: str,
        description: str,
        platinum: int = 0,
        gold: int = 0,
        silver: int = 0,
        copper: int = 0,
        session_date: date = None,
    ) -> dict:
        """
        Records a manual ledger entry for income, expenses, loot,
        donations, fines, or any other wealth event.
        entry_type: 'credit' or 'debit'
        """
        if not description.strip():
            return self._err("A description is required for manual ledger entries.")
        try:
            self.ledger.add_entry(
                character_id = character_id,
                entry_type   = entry_type,
                description  = description.strip(),
                platinum     = platinum,
                gold         = gold,
                silver       = silver,
                copper       = copper,
                session_date = session_date,
            )
            wealth = self.ledger.get_running_total_by_coin(character_id)
            return self._ok({"wealth": wealth}, "Ledger entry recorded.")
        except ValueError as e:
            return self._err(str(e))
        except Exception as e:
            return self._err(f"Failed to record ledger entry: {e}")

    def get_wealth_summary(self, character_id: int) -> dict:
        """
        Returns the current wealth broken down by denomination
        and the full ledger history for display.
        """
        try:
            total_by_coin = self.ledger.get_running_total_by_coin(character_id)
            total_gold    = self.ledger.get_running_total_gold(character_id)
            ledger        = self.ledger.get_ledger(character_id)
            return self._ok({
                "total_by_coin": total_by_coin,
                "total_gold_gp": total_gold,
                "ledger":        ledger,
            })
        except Exception as e:
            return self._err(f"Failed to load wealth summary: {e}")

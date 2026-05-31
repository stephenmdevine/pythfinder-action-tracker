from PyQt6.QtWidgets import QComboBox, QCompleter
from PyQt6.QtCore import Qt


class SearchableComboBox(QComboBox):
    """
    A QComboBox with live filtering as the user types.
    Items are stored as (display_label, id) pairs.

    Usage:
        combo = SearchableComboBox()
        combo.populate([{"id": 1, "name": "Strength"}, ...], label_key="name")
        selected_id = combo.current_id()
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setMinimumWidth(180)

        completer = QCompleter()
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setCompleter(completer)

        self._id_map: dict[int, int] = {}   # combo index -> data id

    def populate(self, items: list[dict], label_key: str = "name", id_key: str = "id"):
        """
        Clears and repopulates the combo box.
        items: list of dicts, each with at least id_key and label_key.
        """
        self.clear()
        self._id_map = {}
        for i, item in enumerate(items):
            self.addItem(str(item[label_key]))
            self._id_map[i] = item[id_key]

    def current_id(self) -> int | None:
        """Returns the data id of the currently selected item, or None."""
        idx = self.currentIndex()
        return self._id_map.get(idx)

    def select_by_id(self, target_id: int):
        """Selects the item whose data id matches target_id."""
        for combo_idx, data_id in self._id_map.items():
            if data_id == target_id:
                self.setCurrentIndex(combo_idx)
                return

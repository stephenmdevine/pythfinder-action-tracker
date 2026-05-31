from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QFrame, QMessageBox, QInputDialog, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.views.theme import palette
from app.controllers.campaign_controller import CampaignController


class CampaignPanel(QWidget):
    """
    Campaign Manager screen.
    Left column: campaign list.
    Right column: characters in the selected campaign.

    All data operations go through CampaignController.
    The view only calls controller methods and reads result dicts.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller   = CampaignController()
        self.selected_campaign_id: int | None = None
        self._build_ui()
        self._load_campaigns()

    # ------------------------------------------------------------------
    # UI CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # Screen title
        title = QLabel("Campaign Manager")
        title.setObjectName("section_title")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        root.addWidget(title)

        # Splitter: campaign list left, character list right
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        splitter.addWidget(self._build_campaign_column())
        splitter.addWidget(self._build_character_column())
        splitter.setSizes([340, 660])

        root.addWidget(splitter, stretch=1)

    # ---- Campaign column ----------------------------------------

    def _build_campaign_column(self) -> QWidget:
        col = QFrame()
        col.setObjectName("card")
        layout = QVBoxLayout(col)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header row
        header = QHBoxLayout()
        lbl = QLabel("Campaigns")
        lbl.setObjectName("subsection_title")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))

        btn_new = QPushButton("+ New")
        btn_new.setObjectName("primary_button")
        btn_new.setFixedWidth(70)
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.clicked.connect(self._on_new_campaign)

        header.addWidget(lbl)
        header.addStretch()
        header.addWidget(btn_new)
        layout.addLayout(header)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {palette['border']};")
        layout.addWidget(div)

        # Campaign list
        self.campaign_list = QListWidget()
        self.campaign_list.setAlternatingRowColors(False)
        self.campaign_list.currentItemChanged.connect(self._on_campaign_selected)
        layout.addWidget(self.campaign_list, stretch=1)

        # Action buttons row
        btn_row = QHBoxLayout()
        self.btn_rename_campaign = QPushButton("Rename")
        self.btn_rename_campaign.setObjectName("secondary_button")
        self.btn_rename_campaign.setEnabled(False)
        self.btn_rename_campaign.clicked.connect(self._on_rename_campaign)

        self.btn_delete_campaign = QPushButton("Delete")
        self.btn_delete_campaign.setObjectName("danger_button")
        self.btn_delete_campaign.setEnabled(False)
        self.btn_delete_campaign.clicked.connect(self._on_delete_campaign)

        btn_row.addWidget(self.btn_rename_campaign)
        btn_row.addWidget(self.btn_delete_campaign)
        layout.addLayout(btn_row)

        return col

    # ---- Character column ----------------------------------------

    def _build_character_column(self) -> QWidget:
        col = QFrame()
        col.setObjectName("card")
        layout = QVBoxLayout(col)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header row
        header = QHBoxLayout()

        self.char_col_label = QLabel("Characters")
        self.char_col_label.setObjectName("subsection_title")
        self.char_col_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))

        self.btn_new_char = QPushButton("+ New Character")
        self.btn_new_char.setObjectName("primary_button")
        self.btn_new_char.setEnabled(False)
        self.btn_new_char.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_char.clicked.connect(self._on_new_character)

        header.addWidget(self.char_col_label)
        header.addStretch()
        header.addWidget(self.btn_new_char)
        layout.addLayout(header)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {palette['border']};")
        layout.addWidget(div)

        # Character list
        self.character_list = QListWidget()
        self.character_list.setAlternatingRowColors(False)
        self.character_list.currentItemChanged.connect(self._on_character_selected)
        layout.addWidget(self.character_list, stretch=1)

        # Action buttons row
        btn_row = QHBoxLayout()
        self.btn_rename_char = QPushButton("Rename")
        self.btn_rename_char.setObjectName("secondary_button")
        self.btn_rename_char.setEnabled(False)
        self.btn_rename_char.clicked.connect(self._on_rename_character)

        self.btn_level_up = QPushButton("Level Up")
        self.btn_level_up.setObjectName("secondary_button")
        self.btn_level_up.setEnabled(False)
        self.btn_level_up.clicked.connect(self._on_level_up)

        self.btn_delete_char = QPushButton("Delete")
        self.btn_delete_char.setObjectName("danger_button")
        self.btn_delete_char.setEnabled(False)
        self.btn_delete_char.clicked.connect(self._on_delete_character)

        btn_row.addWidget(self.btn_rename_char)
        btn_row.addWidget(self.btn_level_up)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_delete_char)
        layout.addLayout(btn_row)

        # Character detail area
        self.char_detail = CharacterDetailWidget()
        layout.addWidget(self.char_detail)

        return col

    # ------------------------------------------------------------------
    # DATA LOADING
    # ------------------------------------------------------------------

    def _load_campaigns(self):
        self.campaign_list.clear()
        result = self.controller.list_campaigns()
        if not result["success"]:
            self._show_error(result["message"])
            return

        for campaign in result["data"]:
            item = QListWidgetItem(campaign["name"])
            item.setData(Qt.ItemDataRole.UserRole, campaign["id"])
            self.campaign_list.addItem(item)

    def _load_characters(self, campaign_id: int):
        self.character_list.clear()
        self.char_detail.clear()
        result = self.controller.list_characters(campaign_id)
        if not result["success"]:
            self._show_error(result["message"])
            return

        for char in result["data"]:
            label = char["name"] + ("  [PC]" if char["is_pc"] else "  [NPC]")
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, char["id"])
            item.setData(Qt.ItemDataRole.UserRole + 1, char)
            self.character_list.addItem(item)

    # ------------------------------------------------------------------
    # EVENT HANDLERS — CAMPAIGNS
    # ------------------------------------------------------------------

    def _on_campaign_selected(self, current: QListWidgetItem, _previous):
        has_selection = current is not None
        self.btn_rename_campaign.setEnabled(has_selection)
        self.btn_delete_campaign.setEnabled(has_selection)
        self.btn_new_char.setEnabled(has_selection)

        if has_selection:
            self.selected_campaign_id = current.data(Qt.ItemDataRole.UserRole)
            campaign_name = current.text()
            self.char_col_label.setText(f"Characters — {campaign_name}")
            self._load_characters(self.selected_campaign_id)
        else:
            self.selected_campaign_id = None
            self.char_col_label.setText("Characters")
            self.character_list.clear()
            self.char_detail.clear()

    def _on_new_campaign(self):
        name, ok = QInputDialog.getText(
            self, "New Campaign", "Campaign name:", QLineEdit.EchoMode.Normal
        )
        if not ok or not name.strip():
            return

        result = self.controller.create_campaign(name.strip())
        if result["success"]:
            self._load_campaigns()
            self._select_by_id(self.campaign_list, result["data"]["id"])
        else:
            self._show_error(result["message"])

    def _on_rename_campaign(self):
        item = self.campaign_list.currentItem()
        if not item:
            return

        name, ok = QInputDialog.getText(
            self, "Rename Campaign", "New name:", QLineEdit.EchoMode.Normal,
            item.text()
        )
        if not ok or not name.strip():
            return

        campaign_id = item.data(Qt.ItemDataRole.UserRole)
        result = self.controller.update_campaign(campaign_id, name=name.strip())
        if result["success"]:
            self._load_campaigns()
            self._select_by_id(self.campaign_list, campaign_id)
        else:
            self._show_error(result["message"])

    def _on_delete_campaign(self):
        item = self.campaign_list.currentItem()
        if not item:
            return

        confirm = QMessageBox.question(
            self, "Delete Campaign",
            f"Delete '{item.text()}' and all its characters?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        campaign_id = item.data(Qt.ItemDataRole.UserRole)
        result = self.controller.delete_campaign(campaign_id)
        if result["success"]:
            self._load_campaigns()
            self.character_list.clear()
            self.char_detail.clear()
            self.selected_campaign_id = None
        else:
            self._show_error(result["message"])

    # ------------------------------------------------------------------
    # EVENT HANDLERS — CHARACTERS
    # ------------------------------------------------------------------

    def _on_character_selected(self, current: QListWidgetItem, _previous):
        has_selection = current is not None
        self.btn_rename_char.setEnabled(has_selection)
        self.btn_level_up.setEnabled(has_selection)
        self.btn_delete_char.setEnabled(has_selection)

        if has_selection:
            char_data = current.data(Qt.ItemDataRole.UserRole + 1)
            char_id   = current.data(Qt.ItemDataRole.UserRole)
            level_result = self.controller.get_level_history(char_id)
            levels = level_result["data"] if level_result["success"] else []
            self.char_detail.load(char_data, levels)

    def _on_new_character(self):
        if self.selected_campaign_id is None:
            return

        name, ok = QInputDialog.getText(
            self, "New Character", "Character name:", QLineEdit.EchoMode.Normal
        )
        if not ok or not name.strip():
            return

        result = self.controller.create_character(
            self.selected_campaign_id, name.strip(), is_pc=True
        )
        if not result["success"]:
            self._show_error(result["message"])
            return

        character = result["data"]
        self._load_characters(self.selected_campaign_id)
        self._select_by_id(self.character_list, character["id"])

        # Open stat initialization dialog immediately after creation
        from app.views.dialogs.character_init_dialog import CharacterInitDialog
        init_dlg = CharacterInitDialog(
            character_id   = character["id"],
            character_name = character["name"],
            parent         = self,
        )
        init_dlg.exec()  # result ignored — Skip is always available

    def _on_rename_character(self):
        item = self.character_list.currentItem()
        if not item:
            return

        char_id   = item.data(Qt.ItemDataRole.UserRole)
        char_data = item.data(Qt.ItemDataRole.UserRole + 1)
        name, ok  = QInputDialog.getText(
            self, "Rename Character", "New name:",
            QLineEdit.EchoMode.Normal, char_data["name"]
        )
        if not ok or not name.strip():
            return

        result = self.controller.update_character(char_id, name=name.strip())
        if result["success"]:
            self._load_characters(self.selected_campaign_id)
            self._select_by_id(self.character_list, char_id)
        else:
            self._show_error(result["message"])

    def _on_level_up(self):
        item = self.character_list.currentItem()
        if not item:
            return

        char_id   = item.data(Qt.ItemDataRole.UserRole)
        char_data = item.data(Qt.ItemDataRole.UserRole + 1)

        class_name, ok = QInputDialog.getText(
            self, f"Level Up — {char_data['name']}",
            "Class name for this level:",
            QLineEdit.EchoMode.Normal
        )
        if not ok or not class_name.strip():
            return

        result = self.controller.level_up(char_id, class_name.strip())
        if result["success"]:
            # Reload to refresh level display
            self._load_characters(self.selected_campaign_id)
            self._select_by_id(self.character_list, char_id)

            QMessageBox.information(self, "Level Up", result["message"])
        else:
            self._show_error(result["message"])

    def _on_delete_character(self):
        item = self.character_list.currentItem()
        if not item:
            return

        char_data = item.data(Qt.ItemDataRole.UserRole + 1)
        confirm = QMessageBox.question(
            self, "Delete Character",
            f"Delete '{char_data['name']}'?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        char_id = item.data(Qt.ItemDataRole.UserRole)
        result  = self.controller.delete_character(char_id)
        if result["success"]:
            self._load_characters(self.selected_campaign_id)
            self.char_detail.clear()
        else:
            self._show_error(result["message"])

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _select_by_id(self, list_widget: QListWidget, target_id: int):
        """Selects the list item whose UserRole data matches target_id."""
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == target_id:
                list_widget.setCurrentItem(item)
                return

    def _show_error(self, message: str):
        QMessageBox.warning(self, "Error", message)


# ------------------------------------------------------------------
# CHARACTER DETAIL WIDGET
# A small read-only summary shown below the character list
# when a character is selected.
# ------------------------------------------------------------------

class CharacterDetailWidget(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card_accent")
        self.setFixedHeight(110)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        self.name_label = QLabel("")
        self.name_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.name_label.setStyleSheet(f"color: {palette['turquoise']};")

        self.level_label = QLabel("")
        self.level_label.setObjectName("label_value")

        self.notes_label = QLabel("")
        self.notes_label.setObjectName("label_muted")
        self.notes_label.setWordWrap(True)

        layout.addWidget(self.name_label)
        layout.addWidget(self.level_label)
        layout.addWidget(self.notes_label)
        layout.addStretch()

    def load(self, char: dict, levels: list[dict]):
        self.name_label.setText(char["name"])

        if levels:
            current_level = max(l["level"] for l in levels)
            classes = ", ".join(
                f"{l['class_name']} {l['level']}" for l in levels
            )
            self.level_label.setText(f"Level {current_level}  ·  {classes}")
        else:
            self.level_label.setText("Level 0  ·  No levels recorded")

        notes = char.get("notes") or ""
        self.notes_label.setText(notes if notes else "No notes.")

    def clear(self):
        self.name_label.setText("")
        self.level_label.setText("")
        self.notes_label.setText("")

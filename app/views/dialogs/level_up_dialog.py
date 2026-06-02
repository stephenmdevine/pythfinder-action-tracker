from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox,
    QTextEdit, QFrame, QScrollArea, QWidget,
    QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.views.theme import palette
from app.controllers.campaign_controller import CampaignController


class LevelUpDialog(QDialog):
    """
    Full level-up modal. Collects:
      - Class name for this level
      - HP gained
      - Skill points gained
      - Ability score increase (shown at levels 4, 8, 12, 16, 20)
      - Feats gained (one per line — created as stubs if they don't exist)
      - Class features gained (one per line — same)
      - Free-text notes

    Feats and class features are created as source stubs automatically
    and assigned to the character. Users edit their effects later in
    the Source Library.
    """

    def __init__(
        self,
        character_id: int,
        character_name: str,
        current_level: int,
        campaign_id: int = None,
        parent=None,
    ):
        super().__init__(parent)
        self.character_id   = character_id
        self.character_name = character_name
        self.current_level  = current_level
        self.new_level      = current_level + 1
        self.campaign_id    = campaign_id
        self.controller     = CampaignController()

        self.setWindowTitle(f"Level Up — {character_name}  (→ Level {self.new_level})")
        self.setMinimumWidth(500)
        self.setMinimumHeight(560)
        self.setModal(True)

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # Header
        header_label = QLabel(
            f"{self.character_name}  →  Level {self.new_level}"
        )
        header_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header_label.setStyleSheet(f"color: {palette['turquoise']};")
        root.addWidget(header_label)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {palette['border']};")
        root.addWidget(div)

        # Scrollable form body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setSpacing(14)
        body_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ---- Core stats section ----
        core_heading = QLabel("Core Gains")
        core_heading.setObjectName("subsection_title")
        body_layout.addWidget(core_heading)

        core_card = QFrame()
        core_card.setObjectName("card")
        core_form = QFormLayout(core_card)
        core_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        core_form.setSpacing(8)

        self.class_name_edit = QLineEdit()
        self.class_name_edit.setPlaceholderText("e.g. Fighter, Rogue/Fighter, Occultist")
        core_form.addRow("Class name:", self.class_name_edit)

        self.hp_spin = QSpinBox()
        self.hp_spin.setRange(0, 999)
        self.hp_spin.setValue(0)
        core_form.addRow("HP gained:", self.hp_spin)

        self.skill_spin = QSpinBox()
        self.skill_spin.setRange(0, 99)
        self.skill_spin.setValue(0)
        core_form.addRow("Skill points:", self.skill_spin)

        # Ability score increase — shown at levels 4, 8, 12, 16, 20
        self.ability_row_widget = QWidget()
        ability_row = QHBoxLayout(self.ability_row_widget)
        ability_row.setContentsMargins(0, 0, 0, 0)
        self.ability_edit = QLineEdit()
        self.ability_edit.setPlaceholderText("e.g. +1 Strength")
        ability_row.addWidget(self.ability_edit)
        ability_note = QLabel("(every 4th level)")
        ability_note.setObjectName("label_muted")
        ability_row.addWidget(ability_note)

        core_form.addRow("Ability score:", self.ability_row_widget)
        # Dim if not an ASI level
        if self.new_level % 4 != 0:
            self.ability_edit.setEnabled(False)
            self.ability_edit.setPlaceholderText("Not an ASI level")

        body_layout.addWidget(core_card)

        # ---- Feats section ----
        feat_heading = QLabel("Feats Gained")
        feat_heading.setObjectName("subsection_title")
        body_layout.addWidget(feat_heading)

        feat_note = QLabel(
            "Enter one feat name per line. New feats will be created as stubs\n"
            "in the Source Library for you to define their effects later."
        )
        feat_note.setObjectName("label_muted")
        feat_note.setWordWrap(True)
        body_layout.addWidget(feat_note)

        self.feats_edit = QTextEdit()
        self.feats_edit.setFixedHeight(80)
        self.feats_edit.setPlaceholderText(
            "Power Attack\nWeapon Focus (Longsword)"
        )
        body_layout.addWidget(self.feats_edit)

        # ---- Class features section ----
        feature_heading = QLabel("Class Features Gained")
        feature_heading.setObjectName("subsection_title")
        body_layout.addWidget(feature_heading)

        feature_note = QLabel(
            "Enter one class feature per line. Same as feats — stubs are\n"
            "created automatically if they don't already exist."
        )
        feature_note.setObjectName("label_muted")
        feature_note.setWordWrap(True)
        body_layout.addWidget(feature_note)

        self.features_edit = QTextEdit()
        self.features_edit.setFixedHeight(80)
        self.features_edit.setPlaceholderText(
            "Sneak Attack +2d6\nUncanny Dodge"
        )
        body_layout.addWidget(self.features_edit)

        # ---- Notes section ----
        notes_heading = QLabel("Additional Notes")
        notes_heading.setObjectName("subsection_title")
        body_layout.addWidget(notes_heading)

        self.notes_edit = QTextEdit()
        self.notes_edit.setFixedHeight(60)
        self.notes_edit.setPlaceholderText(
            "Any other notes about this level-up..."
        )
        body_layout.addWidget(self.notes_edit)
        body_layout.addStretch()

        scroll.setWidget(body)
        root.addWidget(scroll, stretch=1)

        # ---- Buttons ----
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        self.btn_confirm = QPushButton(f"Confirm Level {self.new_level}")
        self.btn_confirm.setObjectName("primary_button")
        self.btn_confirm.clicked.connect(self._on_confirm)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_confirm)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # SAVE
    # ------------------------------------------------------------------

    def _on_confirm(self):
        class_name = self.class_name_edit.text().strip()
        if not class_name:
            QMessageBox.warning(self, "Validation", "Class name is required.")
            return

        feats = [
            line.strip()
            for line in self.feats_edit.toPlainText().splitlines()
            if line.strip()
        ]
        features = [
            line.strip()
            for line in self.features_edit.toPlainText().splitlines()
            if line.strip()
        ]

        ability_increase = ""
        if self.new_level % 4 == 0:
            ability_increase = self.ability_edit.text().strip()

        result = self.controller.level_up(
            character_id           = self.character_id,
            class_name             = class_name,
            hp_gained              = self.hp_spin.value(),
            skill_points           = self.skill_spin.value(),
            ability_score_increase = ability_increase,
            feats                  = feats,
            class_features         = features,
            notes                  = self.notes_edit.toPlainText().strip(),
            campaign_id            = self.campaign_id,
        )

        if result["success"]:
            data = result["data"]
            msg  = result["message"]

            if data.get("created"):
                msg += (
                    f"\n\nNew source stubs created in the Source Library:\n"
                    + "\n".join(f"  • {n}" for n in data["created"])
                    + "\n\nVisit the Source Library to define their effects."
                )

            QMessageBox.information(self, "Level Up Complete", msg)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", result["message"])

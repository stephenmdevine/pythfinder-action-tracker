from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QSpinBox, QFrame,
    QScrollArea, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.views.theme import palette
from app.controllers.campaign_controller import CampaignController


# Ability score abbreviations whose modifiers we auto-calculate
ABILITY_SCORE_NAMES = {
    "Strength":     "STR",
    "Dexterity":    "DEX",
    "Constitution": "CON",
    "Intelligence": "INT",
    "Wisdom":       "WIS",
    "Charisma":     "CHA",
}

ABILITY_MOD_NAMES = {
    "Strength Modifier":     "STR Mod",
    "Dexterity Modifier":    "DEX Mod",
    "Constitution Modifier": "CON Mod",
    "Intelligence Modifier": "INT Mod",
    "Wisdom Modifier":       "WIS Mod",
    "Charisma Modifier":     "CHA Mod",
}


def ability_modifier(score: int) -> int:
    """Standard PF1e ability modifier formula: floor((score - 10) / 2)."""
    return (score - 10) // 2


class CharacterInitDialog(QDialog):
    """
    Shown immediately after a new character is created.
    Lets the user enter their ability scores, core combat stats,
    and saving throw bases before proceeding.

    Ability score modifiers are calculated and displayed live
    but stored as separate stat rows (matching how the seed data
    separates scores from modifiers).

    All other stats default to 0 and can be edited later from
    the Character Sheet panel.
    """

    def __init__(self, character_id: int, character_name: str, parent=None):
        super().__init__(parent)
        self.character_id   = character_id
        self.character_name = character_name
        self.controller     = CampaignController()

        self.setWindowTitle(f"Initialize — {character_name}")
        self.setMinimumWidth(520)
        self.setMinimumHeight(600)
        self.setModal(True)

        # Will hold {stat_id: QSpinBox} for all editable fields
        self._spin_map: dict[int, QSpinBox] = {}
        # Will hold {ability_score_stat_id: modifier_stat_id} for live calc
        self._score_to_mod: dict[int, int] = {}
        # Will hold {modifier_stat_id: QLabel} for live display
        self._mod_labels: dict[int, QLabel] = {}

        self._build_ui()
        self._load_stats()

    # ------------------------------------------------------------------
    # UI CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # Header
        title = QLabel(f"Set Starting Stats — {self.character_name}")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {palette['turquoise']};")
        root.addWidget(title)

        note = QLabel(
            "Enter your character's base values below. Ability score modifiers "
            "are calculated automatically. All stats can be adjusted later from "
            "the Character Sheet."
        )
        note.setObjectName("label_muted")
        note.setWordWrap(True)
        root.addWidget(note)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {palette['border']};")
        root.addWidget(div)

        # Scrollable stat area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.stat_body = QWidget()
        self.stat_layout = QVBoxLayout(self.stat_body)
        self.stat_layout.setSpacing(14)
        self.stat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.stat_body)
        root.addWidget(scroll, stretch=1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_skip = QPushButton("Skip for Now")
        btn_skip.setToolTip("You can set stats later from the Character Sheet.")
        btn_skip.clicked.connect(self.accept)

        btn_save = QPushButton("Save Stats")
        btn_save.setObjectName("primary_button")
        btn_save.clicked.connect(self._on_save)

        btn_row.addWidget(btn_skip)
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # DATA LOADING
    # ------------------------------------------------------------------

    def _load_stats(self):
        result = self.controller.get_core_stats()
        if not result["success"]:
            QMessageBox.warning(self, "Error", result["message"])
            return

        data = result["data"]
        self._build_ability_section(data["ability"])
        self._build_section("Combat Stats", data["combat"])
        self._build_section("Saving Throws", data["saves"])

    def _build_ability_section(self, stats: list[dict]):
        """
        Builds the ability score section with live modifier display.
        Separates scores from modifiers — scores get spinboxes,
        modifiers get read-only calculated labels.
        """
        heading = QLabel("Ability Scores")
        heading.setObjectName("subsection_title")
        heading.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.stat_layout.addWidget(heading)

        card = QFrame()
        card.setObjectName("card")
        form = QFormLayout(card)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        # Index scores and modifiers by name for linking
        scores_by_name = {s["name"]: s for s in stats if s["name"] in ABILITY_SCORE_NAMES}
        mods_by_name   = {s["name"]: s for s in stats if s["name"] in ABILITY_MOD_NAMES}

        # Map "Strength" -> "Strength Modifier"
        score_to_mod_name = {
            score_name: f"{score_name} Modifier"
            for score_name in ABILITY_SCORE_NAMES
        }

        for score_name, abbr in ABILITY_SCORE_NAMES.items():
            score_stat = scores_by_name.get(score_name)
            mod_name   = score_to_mod_name[score_name]
            mod_stat   = mods_by_name.get(mod_name)

            if not score_stat:
                continue

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)

            spin = QSpinBox()
            spin.setRange(1, 30)
            spin.setValue(10)
            spin.setFixedWidth(70)
            self._spin_map[score_stat["id"]] = spin

            mod_label = QLabel("+0")
            mod_label.setObjectName("label_value")
            mod_label.setFixedWidth(36)
            mod_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            row_layout.addWidget(spin)
            row_layout.addWidget(QLabel("→ modifier:"))
            row_layout.addWidget(mod_label)
            row_layout.addStretch()

            if mod_stat:
                self._score_to_mod[score_stat["id"]] = mod_stat["id"]
                self._mod_labels[mod_stat["id"]]     = mod_label
                # Store modifier stat id so we can write it on save
                self._spin_map[mod_stat["id"]] = None  # sentinel — no spinbox

            # Connect live update
            spin.valueChanged.connect(
                lambda val, sid=score_stat["id"]: self._on_score_changed(sid, val)
            )
            # Trigger initial label
            self._on_score_changed(score_stat["id"], 10)

            form.addRow(f"{abbr}  ({score_name}):", row_widget)

        self.stat_layout.addWidget(card)

    def _build_section(self, title: str, stats: list[dict]):
        """Builds a generic stat section with a spinbox per stat."""
        if not stats:
            return

        heading = QLabel(title)
        heading.setObjectName("subsection_title")
        heading.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.stat_layout.addWidget(heading)

        card = QFrame()
        card.setObjectName("card")
        form = QFormLayout(card)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        for stat in stats:
            # Skip modifier stats — handled in ability section
            if stat["name"] in ABILITY_MOD_NAMES:
                continue

            spin = QSpinBox()
            spin.setRange(-99, 999)
            spin.setValue(0)
            spin.setFixedWidth(80)
            self._spin_map[stat["id"]] = spin

            label_text = (
                f"{stat['abbreviation']}  ({stat['name']})"
                if stat.get("abbreviation") and stat["abbreviation"] != stat["name"]
                else stat["name"]
            )
            form.addRow(label_text + ":", spin)

        self.stat_layout.addWidget(card)

    # ------------------------------------------------------------------
    # SIGNALS
    # ------------------------------------------------------------------

    def _on_score_changed(self, score_stat_id: int, value: int):
        """Updates the modifier label when an ability score spinbox changes."""
        mod_stat_id = self._score_to_mod.get(score_stat_id)
        if mod_stat_id and mod_stat_id in self._mod_labels:
            mod = ability_modifier(value)
            self._mod_labels[mod_stat_id].setText(f"{mod:+d}")

    # ------------------------------------------------------------------
    # SAVE
    # ------------------------------------------------------------------

    def _on_save(self):
        stat_values: dict[int, int] = {}

        for stat_id, spin in self._spin_map.items():
            if spin is None:
                # Modifier stat — calculate from its paired score spinbox
                score_stat_id = next(
                    (sid for sid, mid in self._score_to_mod.items() if mid == stat_id),
                    None
                )
                if score_stat_id and self._spin_map.get(score_stat_id):
                    score = self._spin_map[score_stat_id].value()
                    stat_values[stat_id] = ability_modifier(score)
            else:
                stat_values[stat_id] = spin.value()

        result = self.controller.initialize_character_stats(
            self.character_id, stat_values
        )
        if result["success"]:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", result["message"])

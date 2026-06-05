from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QSpinBox, QFrame, QLineEdit,
    QScrollArea, QWidget, QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.views.theme import palette
from app.controllers.campaign_controller import CampaignController
from app.controllers.source_controller import SourceController


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

# Combat stats that start at 10 instead of 0
AC_BASE_STATS = {"Armor Class", "Touch AC", "Flat-Footed AC", "Combat Maneuver Defense"}


def ability_modifier(score: int) -> int:
    """Standard PF1e ability modifier formula: floor((score - 10) / 2)."""
    return (score - 10) // 2


class CharacterInitDialog(QDialog):
    """
    Shown immediately after a new character is created.

    - User enters base ability scores (without racial adjustments).
    - Combat stats and saves are silently initialized to 0 (AC-family to 10).
    - User may optionally define a racial trait source with one or more
      fixed effects, locked to category 'Racial Ability' / bonus type 'Racial'.
      The source is campaign-scoped and assigned to the character on save.
    """

    def __init__(
        self,
        character_id: int,
        character_name: str,
        campaign_id: int,
        parent=None,
    ):
        super().__init__(parent)
        self.character_id   = character_id
        self.character_name = character_name
        self.campaign_id    = campaign_id
        self.controller     = CampaignController()
        self.source_ctrl    = SourceController()

        self.setWindowTitle(f"Initialize — {character_name}")
        self.setMinimumWidth(540)
        self.setMinimumHeight(640)
        self.setModal(True)

        # {stat_id: QSpinBox}  (modifier stats stored as None sentinel)
        self._spin_map: dict[int, QSpinBox | None] = {}
        # {ability_score_stat_id: modifier_stat_id}
        self._score_to_mod: dict[int, int] = {}
        # {modifier_stat_id: QLabel}
        self._mod_labels: dict[int, QLabel] = {}

        # All stat rows returned from DB — kept for silent init
        self._all_stats: list[dict] = []

        # Pending racial effects: list of dicts ready to pass to add_effect()
        # Each: {stat_id, stat_name, modifier}
        self._racial_effects: list[dict] = []

        # Cached reference data for the racial effect builder
        self._stats_for_racial: list[dict] = []   # ability stats only
        self._racial_bonus_type_id: int | None = None
        self._racial_category_id:   int | None = None

        self._build_ui()
        self._load_reference_data()
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
            "Enter your character's base ability scores below, "
            "<b>before any racial adjustments</b>. "
            "Combat stats and saving throws are initialized to their defaults "
            "and can be adjusted from the Character Sheet."
        )
        note.setObjectName("label_muted")
        note.setWordWrap(True)
        root.addWidget(note)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {palette['border']};")
        root.addWidget(div)

        # Scrollable area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.stat_body   = QWidget()
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
    # REFERENCE DATA
    # ------------------------------------------------------------------

    def _load_reference_data(self):
        """Fetch and cache the Racial bonus type ID, Racial Ability category ID,
        and the ability stats list for the racial effect builder."""

        # Racial bonus type ID
        bt_result = self.source_ctrl.list_bonus_types()
        if bt_result["success"]:
            for bt in bt_result["data"]:
                if bt["name"] == "Racial":
                    self._racial_bonus_type_id = bt["id"]
                    break

        # Racial Ability category ID
        cat_result = self.source_ctrl.list_categories()
        if cat_result["success"]:
            for cat in cat_result["data"]:
                if cat["name"] == "Racial Ability":
                    self._racial_category_id = cat["id"]
                    break

        # Ability stats for the effect-builder combo
        stat_result = self.source_ctrl.list_stats(category="ability")
        if stat_result["success"]:
            # Only base scores, not modifiers, are meaningful racial targets
            self._stats_for_racial = [
                s for s in stat_result["data"]
                if s["name"] in ABILITY_SCORE_NAMES
            ]

    # ------------------------------------------------------------------
    # STAT LOADING
    # ------------------------------------------------------------------

    def _load_stats(self):
        result = self.controller.get_core_stats()
        if not result["success"]:
            QMessageBox.warning(self, "Error", result["message"])
            return

        data = result["data"]
        self._all_stats = (
            data["ability"] + data["combat"] + data["saves"]
        )

        self._build_ability_section(data["ability"])
        self._build_racial_section()

    def _build_ability_section(self, stats: list[dict]):
        heading = QLabel("Ability Scores")
        heading.setObjectName("subsection_title")
        heading.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.stat_layout.addWidget(heading)

        card = QFrame()
        card.setObjectName("card")
        form = QFormLayout(card)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        scores_by_name = {s["name"]: s for s in stats if s["name"] in ABILITY_SCORE_NAMES}
        mods_by_name   = {s["name"]: s for s in stats if s["name"] in ABILITY_MOD_NAMES}
        score_to_mod_name = {n: f"{n} Modifier" for n in ABILITY_SCORE_NAMES}

        for score_name, abbr in ABILITY_SCORE_NAMES.items():
            score_stat = scores_by_name.get(score_name)
            mod_stat   = mods_by_name.get(score_to_mod_name[score_name])
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
            mod_label.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

            row_layout.addWidget(spin)
            row_layout.addWidget(QLabel("→ modifier:"))
            row_layout.addWidget(mod_label)
            row_layout.addStretch()

            if mod_stat:
                self._score_to_mod[score_stat["id"]] = mod_stat["id"]
                self._mod_labels[mod_stat["id"]]     = mod_label
                self._spin_map[mod_stat["id"]]       = None  # sentinel

            spin.valueChanged.connect(
                lambda val, sid=score_stat["id"]: self._on_score_changed(sid, val)
            )
            self._on_score_changed(score_stat["id"], 10)

            form.addRow(f"{abbr}  ({score_name}):", row_widget)

        self.stat_layout.addWidget(card)

    # ------------------------------------------------------------------
    # RACIAL TRAITS SECTION
    # ------------------------------------------------------------------

    def _build_racial_section(self):
        heading = QLabel("Racial Traits  (optional)")
        heading.setObjectName("subsection_title")
        heading.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.stat_layout.addWidget(heading)

        sub = QLabel(
            "Define a racial source and add its ability score adjustments here. "
            "The source will be created as a permanent, campaign-scoped Racial Ability "
            "and immediately assigned to this character."
        )
        sub.setObjectName("label_muted")
        sub.setWordWrap(True)
        self.stat_layout.addWidget(sub)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        # Source name row
        name_form = QFormLayout()
        name_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.racial_source_name = QLineEdit()
        self.racial_source_name.setPlaceholderText("e.g. Half-Elf Racial Traits")
        name_form.addRow("Source name:", self.racial_source_name)
        card_layout.addLayout(name_form)

        # Effect list header
        effects_header = QHBoxLayout()
        effects_label = QLabel("Ability score adjustments:")
        effects_label.setObjectName("label_muted")
        effects_header.addWidget(effects_label)
        effects_header.addStretch()

        btn_add_effect = QPushButton("+ Add")
        btn_add_effect.setFixedWidth(64)
        btn_add_effect.clicked.connect(self._on_add_racial_effect)
        effects_header.addWidget(btn_add_effect)
        card_layout.addLayout(effects_header)

        # Effect builder row (inline, shown persistently)
        builder_frame = QFrame()
        builder_frame.setObjectName("card")
        builder_layout = QHBoxLayout(builder_frame)
        builder_layout.setContentsMargins(8, 6, 8, 6)
        builder_layout.setSpacing(8)

        self.racial_stat_combo = QComboBox()
        for stat in self._stats_for_racial:
            self.racial_stat_combo.addItem(stat["name"], stat["id"])
        self.racial_stat_combo.setFixedWidth(160)
        builder_layout.addWidget(self.racial_stat_combo)

        builder_layout.addWidget(QLabel("Modifier:"))
        self.racial_modifier_spin = QSpinBox()
        self.racial_modifier_spin.setRange(-10, 10)
        self.racial_modifier_spin.setValue(2)
        self.racial_modifier_spin.setFixedWidth(64)
        builder_layout.addWidget(self.racial_modifier_spin)
        builder_layout.addStretch()
        card_layout.addWidget(builder_frame)

        # Pending effects display area
        self.racial_effects_widget = QWidget()
        self.racial_effects_layout = QVBoxLayout(self.racial_effects_widget)
        self.racial_effects_layout.setContentsMargins(0, 0, 0, 0)
        self.racial_effects_layout.setSpacing(4)
        card_layout.addWidget(self.racial_effects_widget)

        self.stat_layout.addWidget(card)

    def _on_add_racial_effect(self):
        stat_id   = self.racial_stat_combo.currentData()
        stat_name = self.racial_stat_combo.currentText()
        modifier  = self.racial_modifier_spin.value()

        if stat_id is None:
            return

        # Replace if this stat already has an entry
        self._racial_effects = [
            e for e in self._racial_effects if e["stat_id"] != stat_id
        ]
        self._racial_effects.append({
            "stat_id":   stat_id,
            "stat_name": stat_name,
            "modifier":  modifier,
        })
        self._refresh_racial_effects_display()

    def _refresh_racial_effects_display(self):
        # Clear existing rows
        while self.racial_effects_layout.count():
            item = self.racial_effects_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for effect in self._racial_effects:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 2, 4, 2)
            row_layout.setSpacing(8)

            mod = effect["modifier"]
            sign = "+" if mod >= 0 else ""
            lbl = QLabel(f"{effect['stat_name']}:  {sign}{mod}  (Racial)")
            lbl.setObjectName("label_value")
            row_layout.addWidget(lbl)
            row_layout.addStretch()

            btn_remove = QPushButton("✕")
            btn_remove.setFixedWidth(28)
            btn_remove.setToolTip("Remove this effect")
            btn_remove.clicked.connect(
                lambda _, sid=effect["stat_id"]: self._on_remove_racial_effect(sid)
            )
            row_layout.addWidget(btn_remove)
            self.racial_effects_layout.addWidget(row)

    def _on_remove_racial_effect(self, stat_id: int):
        self._racial_effects = [
            e for e in self._racial_effects if e["stat_id"] != stat_id
        ]
        self._refresh_racial_effects_display()

    # ------------------------------------------------------------------
    # SIGNALS
    # ------------------------------------------------------------------

    def _on_score_changed(self, score_stat_id: int, value: int):
        mod_stat_id = self._score_to_mod.get(score_stat_id)
        if mod_stat_id and mod_stat_id in self._mod_labels:
            mod = ability_modifier(value)
            self._mod_labels[mod_stat_id].setText(f"{mod:+d}")

    # ------------------------------------------------------------------
    # SAVE
    # ------------------------------------------------------------------

    def _on_save(self):
        # --- 1. Build stat values dict from spinboxes ---
        stat_values: dict[int, int] = {}

        for stat_id, spin in self._spin_map.items():
            if spin is None:
                # Modifier stat — derive from its paired score spinbox
                score_stat_id = next(
                    (sid for sid, mid in self._score_to_mod.items() if mid == stat_id),
                    None,
                )
                if score_stat_id and self._spin_map.get(score_stat_id):
                    stat_values[stat_id] = ability_modifier(
                        self._spin_map[score_stat_id].value()
                    )
            else:
                stat_values[stat_id] = spin.value()

        # --- 2. Auto-init combat and save stats not shown in the UI ---
        shown_ids = set(stat_values.keys())
        for stat in self._all_stats:
            if stat["id"] not in shown_ids:
                default = 10 if stat["name"] in AC_BASE_STATS else 0
                stat_values[stat["id"]] = default

        # --- 3. Persist ability scores ---
        result = self.controller.initialize_character_stats(
            self.character_id, stat_values
        )
        if not result["success"]:
            QMessageBox.warning(self, "Error", result["message"])
            return

        # --- 4. Create and assign racial source if the user filled it in ---
        source_name = self.racial_source_name.text().strip()
        if source_name or self._racial_effects:
            if not source_name:
                QMessageBox.warning(
                    self, "Validation",
                    "Please enter a name for the racial source, "
                    "or remove all racial effects before saving."
                )
                return

            if not self._racial_category_id or not self._racial_bonus_type_id:
                QMessageBox.warning(
                    self, "Error",
                    "Could not locate the 'Racial Ability' category or "
                    "'Racial' bonus type in the database. "
                    "Please check that the seed data includes these entries."
                )
                return

            src_result = self.source_ctrl.create_source(
                name               = source_name,
                source_category_id = self._racial_category_id,
                duration_type      = "permanent",
                campaign_id        = self.campaign_id,
            )
            if not src_result["success"]:
                QMessageBox.warning(self, "Error", src_result["message"])
                return

            source_id = src_result["data"]["id"]

            for effect in self._racial_effects:
                eff_result = self.source_ctrl.add_effect(
                    source_id     = source_id,
                    stat_id       = effect["stat_id"],
                    bonus_type_id = self._racial_bonus_type_id,
                    modifier      = effect["modifier"],
                )
                if not eff_result["success"]:
                    QMessageBox.warning(
                        self, "Warning",
                        f"Effect on {effect['stat_name']} could not be saved: "
                        f"{eff_result['message']}"
                    )

            assign_result = self.source_ctrl.assign_source_to_character(
                self.character_id, source_id
            )
            if not assign_result["success"]:
                QMessageBox.warning(self, "Error", assign_result["message"])
                return

        self.accept()

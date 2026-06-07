"""
character_sheet_panel.py

Character Sheet panel — Phase 1: Base stats + resolved modifiers.

Layout (three columns, splitter-separated):
  LEFT   — Character selector (campaign → character dropdowns) + character header card
  CENTER — Stat table grouped by category (Ability / Combat / Save / Other),
            showing Base | Modifier | Final for every stat
  RIGHT  — Modifier breakdown for the selected stat row
            (contributing effects + suppressed effects)

The panel is stateless between loads; calling load_character() rebuilds
everything from the controller.

Signal flow:
  campaign_combo → _on_campaign_changed → repopulate character_combo
  character_combo → _on_character_changed → load_character()
  stat table row selected → _on_stat_selected → populate breakdown pane
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSplitter, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea, QSizePolicy, QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from app.views.theme import palette, fonts
from app.controllers.character_sheet_controller import CharacterSheetController
from app.controllers.campaign_controller import CampaignController


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _signed(n: int) -> str:
    """Format an integer with an explicit sign: +3, -1, +0."""
    return f"+{n}" if n >= 0 else str(n)


def _modifier_from_score(score: int) -> int:
    """PF1e ability modifier: floor((score - 10) / 2)."""
    return (score - 10) // 2


# Category display order and friendly names
_CATEGORY_ORDER = ["ability", "combat", "save", "other"]
_CATEGORY_LABELS = {
    "ability": "Ability Scores",
    "combat":  "Combat Statistics",
    "save":    "Saving Throws",
    "other":   "Other",
}

# Ability score abbreviations — shown with score AND modifier
_ABILITY_ABBREVS = {"STR", "DEX", "CON", "INT", "WIS", "CHA"}


# ---------------------------------------------------------------------------
# SMALL REUSABLE WIDGETS
# ---------------------------------------------------------------------------

class _SectionHeader(QLabel):
    """Teal-accented section divider label used inside the stat table."""
    def __init__(self, text: str, parent=None):
        super().__init__(text.upper(), parent)
        self.setStyleSheet(f"""
            color: {palette['turquoise']};
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1.5px;
            padding: 6px 8px 4px 8px;
            background-color: {palette['bg_dark']};
            border-bottom: 1px solid {palette['border']};
        """)


class _CharacterHeaderCard(QFrame):
    """
    Compact character identity card shown above the stat table.
    Displays name, level/class summary, and PC/NPC badge.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFixedHeight(80)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        # Left: name + class line
        text_col = QVBoxLayout()
        text_col.setSpacing(3)

        self.name_label = QLabel("—")
        self.name_label.setStyleSheet(
            f"color: {palette['text_primary']}; font-size: 15px; font-weight: bold;"
        )
        self.class_label = QLabel("No character selected")
        self.class_label.setStyleSheet(
            f"color: {palette['text_muted']}; font-size: 11px;"
        )

        text_col.addWidget(self.name_label)
        text_col.addWidget(self.class_label)
        layout.addLayout(text_col, stretch=1)

        # Right: PC/NPC badge + level pill
        badge_col = QVBoxLayout()
        badge_col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        badge_col.setSpacing(4)

        self.type_badge = QLabel("—")
        self.type_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.type_badge.setFixedWidth(40)

        self.level_label = QLabel("")
        self.level_label.setObjectName("label_value")
        self.level_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.level_label.setStyleSheet(
            f"color: {palette['gold']}; font-size: 13px; font-weight: bold;"
        )

        badge_col.addWidget(self.type_badge)
        badge_col.addWidget(self.level_label)
        layout.addLayout(badge_col)

    def populate(self, character: dict, level: int, class_summary: str):
        self.name_label.setText(character.get("name", "Unknown"))
        self.class_label.setText(class_summary or "No levels recorded")
        self.level_label.setText(f"Lvl {level}" if level else "—")

        is_pc = character.get("is_pc", True)
        self.type_badge.setText("PC" if is_pc else "NPC")
        self.type_badge.setObjectName("badge_active" if is_pc else "badge_inactive")
        self.type_badge.style().unpolish(self.type_badge)
        self.type_badge.style().polish(self.type_badge)

    def clear(self):
        self.name_label.setText("—")
        self.class_label.setText("No character selected")
        self.level_label.setText("")
        self.type_badge.setText("—")


# ---------------------------------------------------------------------------
# STAT TABLE
# ---------------------------------------------------------------------------

# Column indices
_COL_NAME  = 0
_COL_BASE  = 1
_COL_MOD   = 2   # net modifier from active sources
_COL_FINAL = 3
_COL_EXTRA = 4   # ability modifier (ability scores only), blank for others

_COL_COUNT = 5
_COL_HEADERS = ["Stat", "Base", "Bonus", "Final", ""]


class StatTable(QTableWidget):
    """
    Custom table for displaying stats grouped by category.
    Category headers are injected as non-selectable span rows.
    Emits stat_selected(stat_row_dict) when a data row is clicked.
    """

    stat_selected = pyqtSignal(dict)   # emits the full stat dict

    def __init__(self, parent=None):
        super().__init__(0, _COL_COUNT, parent)

        self.setHorizontalHeaderLabels(_COL_HEADERS)
        self.setObjectName("stat_table")
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setAlternatingRowColors(False)

        hh = self.horizontalHeader()
        hh.setSectionResizeMode(_COL_NAME,  QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(_COL_BASE,  QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(_COL_MOD,   QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(_COL_FINAL, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(_COL_EXTRA, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(_COL_BASE,  56)
        self.setColumnWidth(_COL_MOD,   56)
        self.setColumnWidth(_COL_FINAL, 56)
        self.setColumnWidth(_COL_EXTRA, 56)

        self.cellClicked.connect(self._on_cell_clicked)

        # Internal mapping: visual row index → stat dict (None for header rows)
        self._row_data: list[dict | None] = []

    # ------------------------------------------------------------------
    # PUBLIC
    # ------------------------------------------------------------------

    def populate(self, stats: list[dict]):
        """
        Rebuild the table from a list of stat dicts as returned by
        CharacterSheetController.get_character_sheet()["stats"].
        Stats must already be sorted by category then name.
        """
        self.clearContents()
        self.setRowCount(0)
        self._row_data.clear()

        # Group by category preserving _CATEGORY_ORDER
        grouped: dict[str, list[dict]] = {c: [] for c in _CATEGORY_ORDER}
        for s in stats:
            cat = s.get("category", "other").lower()
            grouped.setdefault(cat, [])
            grouped[cat].append(s)

        for cat in _CATEGORY_ORDER:
            rows = grouped.get(cat, [])
            if not rows:
                continue

            # ---- category header row ----
            header_row = self.rowCount()
            self.insertRow(header_row)
            self.setRowHeight(header_row, 28)
            self._row_data.append(None)  # not selectable

            header_item = QTableWidgetItem(_CATEGORY_LABELS.get(cat, cat.title()))
            header_item.setFlags(Qt.ItemFlag.ItemIsEnabled)  # not selectable
            header_item.setForeground(QColor(palette["turquoise"]))
            header_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.setItem(header_row, _COL_NAME, header_item)
            self.setSpan(header_row, 0, 1, _COL_COUNT)

            # Style the header row background
            for col in range(_COL_COUNT):
                bg_item = QTableWidgetItem()
                bg_item.setBackground(QColor(palette["bg_dark"]))
                bg_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                if col != _COL_NAME:
                    self.setItem(header_row, col, bg_item)

            # ---- stat data rows ----
            for stat in rows:
                self._insert_stat_row(stat)

    def refresh_stat_row(self, stat: dict):
        """
        Update a single stat row in-place after a source toggle,
        without rebuilding the whole table.
        """
        stat_id = stat["stat_id"]
        for row_idx, row_data in enumerate(self._row_data):
            if row_data and row_data.get("stat_id") == stat_id:
                self._update_row_cells(row_idx, stat)
                # Keep our internal copy fresh
                self._row_data[row_idx] = stat
                break

    # ------------------------------------------------------------------
    # PRIVATE
    # ------------------------------------------------------------------

    def _insert_stat_row(self, stat: dict):
        row = self.rowCount()
        self.insertRow(row)
        self.setRowHeight(row, 32)
        self._row_data.append(stat)
        self._update_row_cells(row, stat)

    def _update_row_cells(self, row: int, stat: dict):
        name  = stat.get("name", "")
        abbr  = stat.get("abbreviation", "")
        base  = stat.get("base_value", 0)
        mod   = stat.get("net_modifier", 0)
        final = stat.get("final_value", base + mod)
        cat   = stat.get("category", "").lower()

        # Stat name cell
        name_item = QTableWidgetItem(name)
        name_item.setData(Qt.ItemDataRole.UserRole, stat)
        self.setItem(row, _COL_NAME, name_item)

        # Base value
        base_item = QTableWidgetItem(str(base))
        base_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        base_item.setForeground(QColor(palette["text_secondary"]))
        self.setItem(row, _COL_BASE, base_item)

        # Net modifier — colored by sign
        mod_text = _signed(mod) if mod != 0 else "—"
        mod_item = QTableWidgetItem(mod_text)
        mod_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if mod > 0:
            mod_item.setForeground(QColor(palette["success"]))
        elif mod < 0:
            mod_item.setForeground(QColor(palette["danger"]))
        else:
            mod_item.setForeground(QColor(palette["text_muted"]))
        self.setItem(row, _COL_MOD, mod_item)

        # Final value — bold, gold if modified
        final_item = QTableWidgetItem(str(final))
        final_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        final_font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        final_item.setFont(final_font)
        if mod != 0:
            final_item.setForeground(QColor(palette["gold"]))
        else:
            final_item.setForeground(QColor(palette["text_primary"]))
        self.setItem(row, _COL_FINAL, final_item)

        # Extra column: ability modifier for ability scores
        if cat == "ability" and abbr in _ABILITY_ABBREVS:
            ab_mod = _modifier_from_score(final)
            extra_item = QTableWidgetItem(_signed(ab_mod))
            extra_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            extra_item.setForeground(QColor(palette["turquoise"]))
            extra_item.setToolTip("Ability modifier (used for skill/attack rolls)")
            self.setItem(row, _COL_EXTRA, extra_item)
        else:
            self.setItem(row, _COL_EXTRA, QTableWidgetItem(""))

    def _on_cell_clicked(self, row: int, _col: int):
        data = self._row_data[row] if row < len(self._row_data) else None
        if data:
            self.stat_selected.emit(data)


# ---------------------------------------------------------------------------
# MODIFIER BREAKDOWN PANE
# ---------------------------------------------------------------------------

class _EffectRow(QFrame):
    """Single row in the breakdown list: source name + bonus type + value."""

    def __init__(self, effect: dict, suppressed: bool = False, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        # Source name
        source = effect.get("source_name", effect.get("name", "Unknown"))
        bonus_type = effect.get("bonus_type_name", effect.get("bonus_type", ""))
        value = effect.get("modifier", effect.get("value", 0))

        name_label = QLabel(source)
        name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        type_label = QLabel(bonus_type)
        type_label.setFixedWidth(90)
        type_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        value_label = QLabel(_signed(value) if isinstance(value, int) else str(value))
        value_label.setFixedWidth(40)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        if suppressed:
            dim = palette["text_muted"]
            name_label.setStyleSheet(
                f"color: {dim}; font-style: italic; text-decoration: line-through;"
            )
            type_label.setStyleSheet(f"color: {dim}; font-size: 10px;")
            value_label.setStyleSheet(f"color: {dim}; font-weight: bold;")
            self.setToolTip("Suppressed — a higher bonus of the same type is already active.")
        else:
            name_label.setStyleSheet(f"color: {palette['text_primary']};")
            type_label.setStyleSheet(f"color: {palette['text_muted']}; font-size: 10px;")
            val_color = palette["success"] if value > 0 else palette["danger"]
            value_label.setStyleSheet(f"color: {val_color}; font-weight: bold;")

        layout.addWidget(name_label)
        layout.addWidget(type_label)
        layout.addWidget(value_label)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {'rgba(255,255,255,0.02)' if not suppressed else 'transparent'};
                border-bottom: 1px solid {palette['border']};
            }}
        """)


class BreakdownPane(QWidget):
    """
    Right pane: shows the modifier breakdown for a selected stat.
    Lists contributing (active) effects and suppressed effects separately.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self._header = QLabel("Select a stat to see breakdown")
        self._header.setStyleSheet(f"""
            color: {palette['turquoise']};
            font-size: 13px;
            font-weight: bold;
            padding: 12px 14px 8px 14px;
            border-bottom: 1px solid {palette['border']};
            background-color: {palette['bg_surface']};
        """)
        layout.addWidget(self._header)

        # Summary row (base + modifier = final)
        self._summary = QLabel("")
        self._summary.setStyleSheet(f"""
            color: {palette['text_secondary']};
            font-size: 11px;
            padding: 6px 14px;
            background-color: {palette['bg_surface']};
        """)
        layout.addWidget(self._summary)

        # Scroll area for effect rows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._effects_container = QWidget()
        self._effects_layout = QVBoxLayout(self._effects_container)
        self._effects_layout.setContentsMargins(0, 0, 0, 0)
        self._effects_layout.setSpacing(0)
        self._effects_layout.addStretch()

        scroll.setWidget(self._effects_container)
        layout.addWidget(scroll, stretch=1)

        self.setStyleSheet(f"background-color: {palette['bg_surface']};")

    def populate(self, stat: dict):
        name    = stat.get("name", "Stat")
        base    = stat.get("base_value", 0)
        mod     = stat.get("net_modifier", 0)
        final   = stat.get("final_value", base + mod)
        contrib = stat.get("breakdown", [])
        suppressed = stat.get("suppressed", [])

        self._header.setText(name)

        # Summary line
        if mod != 0:
            self._summary.setText(
                f"Base {base}  {_signed(mod)} active bonuses  =  {final}"
            )
        else:
            self._summary.setText(f"Base {base}  (no active modifiers)")

        # Clear old effect rows (keep the stretch at end)
        while self._effects_layout.count() > 1:
            item = self._effects_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not contrib and not suppressed:
            empty = QLabel("No active effects on this stat.")
            empty.setStyleSheet(
                f"color: {palette['text_muted']}; padding: 16px 14px; font-style: italic;"
            )
            self._effects_layout.insertWidget(0, empty)
            return

        insert_pos = 0

        if contrib:
            sec = QLabel("CONTRIBUTING")
            sec.setStyleSheet(f"""
                color: {palette['text_muted']};
                font-size: 9px;
                font-weight: bold;
                letter-spacing: 1px;
                padding: 8px 14px 4px 14px;
            """)
            self._effects_layout.insertWidget(insert_pos, sec)
            insert_pos += 1
            for eff in contrib:
                row = _EffectRow(eff, suppressed=False)
                self._effects_layout.insertWidget(insert_pos, row)
                insert_pos += 1

        if suppressed:
            sec2 = QLabel("SUPPRESSED")
            sec2.setStyleSheet(f"""
                color: {palette['text_muted']};
                font-size: 9px;
                font-weight: bold;
                letter-spacing: 1px;
                padding: 8px 14px 4px 14px;
            """)
            self._effects_layout.insertWidget(insert_pos, sec2)
            insert_pos += 1
            for eff in suppressed:
                row = _EffectRow(eff, suppressed=True)
                self._effects_layout.insertWidget(insert_pos, row)
                insert_pos += 1

    def clear(self):
        self._header.setText("Select a stat to see breakdown")
        self._summary.setText("")
        while self._effects_layout.count() > 1:
            item = self._effects_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


# ---------------------------------------------------------------------------
# MAIN PANEL
# ---------------------------------------------------------------------------

class CharacterSheetPanel(QWidget):
    """
    Character Sheet panel — base stats + resolved modifiers.

    Integrates with the main window via the standard panel contract:
      - No required constructor args beyond parent
      - Does not call any other panel directly
      - Receives character_id via set_character(character_id) called from
        CampaignPanel (or can self-select via its own campaign/character dropdowns)
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._controller = CharacterSheetController()
        self._campaign_ctrl = CampaignController()

        self._current_character_id: int | None = None
        self._sheet_data: dict | None = None

        self._build_ui()

    # ------------------------------------------------------------------
    # PUBLIC API — called by main_window or campaign_panel
    # ------------------------------------------------------------------

    def set_character(self, character_id: int):
        """
        Load a character by ID. Called externally (e.g. from CampaignPanel
        after a character is selected or after Level Up completes).
        """
        # Sync the combo if possible (don't trigger _on_character_changed again)
        self._character_combo.blockSignals(True)
        for i in range(self._character_combo.count()):
            if self._character_combo.itemData(i) == character_id:
                self._character_combo.setCurrentIndex(i)
                break
        self._character_combo.blockSignals(False)

        self._load_character(character_id)

    def refresh(self):
        """Re-load current character (e.g. after source toggle)."""
        if self._current_character_id:
            self._load_character(self._current_character_id)

    # ------------------------------------------------------------------
    # UI CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top bar: panel title + selectors
        root.addWidget(self._build_top_bar())

        # Splitter: left selector+header | center stat table | right breakdown
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)

        splitter.addWidget(self._build_left_pane())
        splitter.addWidget(self._build_center_pane())
        splitter.addWidget(self._build_right_pane())

        splitter.setSizes([220, 480, 280])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        root.addWidget(splitter, stretch=1)

        # Populate selectors now that all child widgets exist
        self._populate_campaigns()

    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet(f"""
            background-color: {palette['bg_surface']};
            border-bottom: 1px solid {palette['border']};
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        title = QLabel("Character Sheet")
        title.setObjectName("section_title")
        title.setStyleSheet(
            f"color: {palette['turquoise']}; font-size: 15px; font-weight: bold; border: none;"
        )
        layout.addWidget(title)
        layout.addStretch()

        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setFixedWidth(100)
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)

        return bar

    def _build_left_pane(self) -> QWidget:
        pane = QWidget()
        pane.setFixedWidth(220)
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Campaign selector
        layout.addWidget(self._make_label("Campaign"))
        self._campaign_combo = QComboBox()
        self._campaign_combo.setPlaceholderText("Select campaign…")
        self._campaign_combo.currentIndexChanged.connect(self._on_campaign_changed)
        layout.addWidget(self._campaign_combo)

        # Character selector
        layout.addWidget(self._make_label("Character"))
        self._character_combo = QComboBox()
        self._character_combo.setPlaceholderText("Select character…")
        self._character_combo.setEnabled(False)
        self._character_combo.currentIndexChanged.connect(self._on_character_changed)
        layout.addWidget(self._character_combo)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"color: {palette['border']};")
        layout.addWidget(divider)

        # Character header card
        self._header_card = _CharacterHeaderCard()
        layout.addWidget(self._header_card)

        layout.addStretch()

        return pane

    def _build_center_pane(self) -> QWidget:
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stat_table = StatTable()
        self._stat_table.stat_selected.connect(self._on_stat_selected)
        layout.addWidget(self._stat_table)

        return pane

    def _build_right_pane(self) -> QWidget:
        self._breakdown_pane = BreakdownPane()
        return self._breakdown_pane

    # ------------------------------------------------------------------
    # POPULATE SELECTORS
    # ------------------------------------------------------------------

    def _populate_campaigns(self):
        result = self._campaign_ctrl.list_campaigns()
        self._campaign_combo.blockSignals(True)
        self._campaign_combo.clear()
        if result["success"]:
            for c in result["data"]:
                self._campaign_combo.addItem(c["name"], c["id"])
        self._campaign_combo.blockSignals(False)

        # Trigger population of character combo for first campaign
        if self._campaign_combo.count():
            self._on_campaign_changed(0)

    def _populate_characters(self, campaign_id: int):
        result = self._campaign_ctrl.list_characters(campaign_id)
        self._character_combo.blockSignals(True)
        self._character_combo.clear()
        if result["success"] and result["data"]:
            for ch in result["data"]:
                label = ch["name"] + ("" if ch.get("is_pc", True) else " [NPC]")
                self._character_combo.addItem(label, ch["id"])
            self._character_combo.setEnabled(True)
        else:
            self._character_combo.setEnabled(False)
        self._character_combo.blockSignals(False)

        # Auto-select first character
        if self._character_combo.count():
            self._on_character_changed(0)

    # ------------------------------------------------------------------
    # LOAD CHARACTER SHEET
    # ------------------------------------------------------------------

    def _load_character(self, character_id: int):
        self._current_character_id = character_id
        result = self._controller.get_character_sheet(character_id)

        if not result["success"]:
            self._header_card.clear()
            self._stat_table.populate([])
            self._breakdown_pane.clear()
            return

        data = result["data"]
        self._sheet_data = data

        # Header card
        character = data["character"]
        level = data["level"]
        level_history = self._build_class_summary(character_id)
        self._header_card.populate(character, level, level_history)

        # Stat table
        self._stat_table.populate(data["stats"])

        # Clear breakdown (no row selected yet)
        self._breakdown_pane.clear()

    def _build_class_summary(self, character_id: int) -> str:
        """
        Build a compact class summary string like 'Fighter 4 / Rogue 2'
        from the level history.
        """
        result = self._campaign_ctrl.get_level_history(character_id) \
            if hasattr(self._campaign_ctrl, "get_level_history") else {"success": False}

        if not result.get("success") or not result.get("data"):
            # Fall back to character model directly via controller
            try:
                from app.models.character_model import CharacterModel
                cm = CharacterModel()
                rows = cm.get_level_history(character_id)
                if not rows:
                    return "No levels recorded"
                # Count levels per class
                class_counts: dict[str, int] = {}
                for row in rows:
                    cls = row.get("class_name", "Unknown")
                    class_counts[cls] = class_counts.get(cls, 0) + 1
                return " / ".join(f"{cls} {lvl}" for cls, lvl in class_counts.items())
            except Exception:
                return ""

        rows = result["data"]
        class_counts: dict[str, int] = {}
        for row in rows:
            cls = row.get("class_name", "Unknown")
            class_counts[cls] = class_counts.get(cls, 0) + 1
        return " / ".join(f"{cls} {lvl}" for cls, lvl in class_counts.items())

    # ------------------------------------------------------------------
    # SIGNAL HANDLERS
    # ------------------------------------------------------------------

    def _on_campaign_changed(self, index: int):
        campaign_id = self._campaign_combo.itemData(index)
        if campaign_id is None:
            self._character_combo.clear()
            self._character_combo.setEnabled(False)
            return
        self._populate_characters(campaign_id)

    def _on_character_changed(self, index: int):
        character_id = self._character_combo.itemData(index)
        if character_id is None:
            self._header_card.clear()
            self._stat_table.populate([])
            self._breakdown_pane.clear()
            return
        self._load_character(character_id)

    def _on_stat_selected(self, stat: dict):
        self._breakdown_pane.populate(stat)

    # ------------------------------------------------------------------
    # UTILITIES
    # ------------------------------------------------------------------

    @staticmethod
    def _make_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {palette['text_muted']}; font-size: 10px; "
            f"font-weight: bold; letter-spacing: 0.5px;"
        )
        return lbl

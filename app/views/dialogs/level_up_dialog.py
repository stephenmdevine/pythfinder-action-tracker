from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox,
    QTextEdit, QFrame, QScrollArea, QWidget,
    QMessageBox, QSizePolicy, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.views.theme import palette
from app.controllers.campaign_controller import CampaignController
from app.models.stat_model import StatModel


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
        self.stat_model     = StatModel()
        self._skill_spins: dict[int, QSpinBox] = {}  # stat_id → spinbox

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

        # Tab widget — Level Up tab + Skill Ranks tab
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        root.addWidget(self._tabs, stretch=1)

        # ── Level Up tab (original scrollable form) ───────────────────
        level_tab = QWidget()
        level_tab_layout = QVBoxLayout(level_tab)
        level_tab_layout.setContentsMargins(0, 8, 0, 0)
        level_tab_layout.setSpacing(0)
        self._tabs.addTab(level_tab, "Level Up")

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
        level_tab_layout.addWidget(scroll, stretch=1)

        # ── Skill Ranks tab ───────────────────────────────────────────
        self._tabs.addTab(self._build_skill_ranks_tab(), "Skill Ranks")

        # ---- Buttons (outside tabs, always visible) ----
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
    # SKILL RANKS TAB
    # ------------------------------------------------------------------

    def _build_skill_ranks_tab(self) -> QWidget:
        """
        Builds the Skill Ranks tab.

        Shows every skill with:
          - Current ranks (from character_stats, 0 if none)
          - A spinbox to invest additional ranks this level
          - Max cap per skill = new_level total ranks
          - Running tally of points spent vs skill_points_gained (read
            from self.skill_spin, updated live as the user changes it
            on the Level Up tab)

        The cap is enforced per-skill: existing_ranks + new_ranks <= new_level.
        Total points spent is advisory — the GM may award bonus points,
        favored class bonuses, etc., so we warn but don't hard-block.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Points remaining bar
        points_bar = QWidget()
        points_bar_layout = QHBoxLayout(points_bar)
        points_bar_layout.setContentsMargins(0, 0, 0, 0)
        points_bar_layout.setSpacing(6)

        points_bar_layout.addWidget(QLabel("Points to spend:"))
        self._points_available_label = QLabel(str(self.skill_spin.value()))
        self._points_available_label.setStyleSheet(
            f"color: {palette['gold']}; font-weight: bold; font-size: 13px;"
        )
        points_bar_layout.addWidget(self._points_available_label)
        points_bar_layout.addWidget(QLabel("  |  Spent:"))
        self._points_spent_label = QLabel("0")
        self._points_spent_label.setStyleSheet(
            f"color: {palette['turquoise']}; font-weight: bold; font-size: 13px;"
        )
        points_bar_layout.addWidget(self._points_spent_label)
        points_bar_layout.addStretch()

        hint = QLabel(f"Max ranks per skill at level {self.new_level}: {self.new_level}")
        hint.setStyleSheet(f"color: {palette['text_muted']}; font-size: 11px;")
        points_bar_layout.addWidget(hint)
        layout.addWidget(points_bar)

        # Update points bar when skill_spin on Level Up tab changes
        self.skill_spin.valueChanged.connect(self._refresh_points_bar)

        # Skill table: Skill | Current | +Ranks (spinbox) | New Total
        self._skill_rank_table = QTableWidget(0, 4)
        self._skill_rank_table.setHorizontalHeaderLabels(
            ["Skill", "Current Ranks", "+ This Level", "New Total"]
        )
        self._skill_rank_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._skill_rank_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self._skill_rank_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._skill_rank_table.verticalHeader().setVisible(False)
        self._skill_rank_table.setShowGrid(False)

        hh = self._skill_rank_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._skill_rank_table.setColumnWidth(1, 100)
        self._skill_rank_table.setColumnWidth(2, 110)
        self._skill_rank_table.setColumnWidth(3, 90)

        self._populate_skill_table()
        layout.addWidget(self._skill_rank_table, stretch=1)

        return widget

    def _populate_skill_table(self):
        """Fetch all skills and current ranks, build table rows."""
        skills = self.stat_model.get_all(category="skill")
        # Current ranks for this character
        base_rows = self.stat_model.get_all_base_values(self.character_id)
        ranks_map = {
            r["stat_id"]: r["base_value"]
            for r in base_rows
            if r.get("category", "").lower() == "skill"
        }

        self._skill_rank_table.setRowCount(0)
        self._skill_spins.clear()

        for skill in sorted(skills, key=lambda s: s["name"]):
            sid          = skill["id"]
            name         = skill["name"]
            current      = ranks_map.get(sid, 0)
            max_new      = max(0, self.new_level - current)

            row = self._skill_rank_table.rowCount()
            self._skill_rank_table.insertRow(row)
            self._skill_rank_table.setRowHeight(row, 30)

            # Skill name
            name_item = QTableWidgetItem(name)
            self._skill_rank_table.setItem(row, 0, name_item)

            # Current ranks
            cur_item = QTableWidgetItem(str(current))
            cur_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            from PyQt6.QtGui import QColor
            cur_item.setForeground(
                QColor(palette["turquoise"]) if current > 0
                else QColor(palette["text_muted"])
            )
            self._skill_rank_table.setItem(row, 1, cur_item)

            # Spinbox for new ranks
            spin = QSpinBox()
            spin.setRange(0, max_new)
            spin.setValue(0)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if max_new == 0:
                spin.setEnabled(False)
                spin.setToolTip(
                    f"Already at max ranks for level {self.new_level}."
                )
            spin.valueChanged.connect(self._on_rank_changed)
            self._skill_rank_table.setCellWidget(row, 2, spin)
            self._skill_spins[sid] = spin

            # New total (updated live)
            total_item = QTableWidgetItem(str(current))
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._skill_rank_table.setItem(row, 3, total_item)

    def _on_rank_changed(self):
        """Recompute spent points and update the New Total column live."""
        spent = sum(s.value() for s in self._skill_spins.values())
        self._points_spent_label.setText(str(spent))

        available = self.skill_spin.value()
        color = palette["danger"] if spent > available else palette["turquoise"]
        self._points_spent_label.setStyleSheet(
            f"color: {color}; font-weight: bold; font-size: 13px;"
        )

        # Refresh New Total column
        for row in range(self._skill_rank_table.rowCount()):
            spin_widget = self._skill_rank_table.cellWidget(row, 2)
            cur_item    = self._skill_rank_table.item(row, 1)
            total_item  = self._skill_rank_table.item(row, 3)
            if spin_widget and cur_item and total_item:
                current   = int(cur_item.text())
                new_total = current + spin_widget.value()
                total_item.setText(str(new_total))

    def _refresh_points_bar(self, value: int):
        """Called when the skill points spinbox on the Level Up tab changes."""
        self._points_available_label.setText(str(value))
        self._on_rank_changed()  # recheck the over-budget colour


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

            # Save skill rank investments
            ranks_saved   = 0
            ranks_errors  = []
            for stat_id, spin in self._skill_spins.items():
                new_ranks = spin.value()
                if new_ranks > 0:
                    # Get current ranks and add the new investment
                    current = self.stat_model.get_base_value(
                        self.character_id, stat_id
                    )
                    total = current + new_ranks
                    try:
                        self.stat_model.set_base_value(
                            self.character_id, stat_id, total
                        )
                        ranks_saved += 1
                    except Exception as e:
                        ranks_errors.append(str(e))

            if data.get("created"):
                msg += (
                    f"\n\nNew source stubs created in the Source Library:\n"
                    + "\n".join(f"  • {n}" for n in data["created"])
                    + "\n\nVisit the Source Library to define their effects."
                )

            if ranks_saved:
                msg += f"\n\n{ranks_saved} skill(s) updated."
            if ranks_errors:
                msg += f"\n\nSome skill ranks failed to save:\n" + "\n".join(ranks_errors)

            # Warn if over budget (advisory only — GM may have granted bonus points)
            spent     = sum(s.value() for s in self._skill_spins.values())
            available = self.skill_spin.value()
            if spent > available:
                msg += (
                    f"\n\nNote: You invested {spent} rank(s) but only "
                    f"{available} skill point(s) were recorded. "
                    f"Verify with your GM."
                )

            QMessageBox.information(self, "Level Up Complete", msg)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", result["message"])

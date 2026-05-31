from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QFrame, QLineEdit, QComboBox, QTextEdit, QFormLayout,
    QMessageBox, QSpinBox, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from app.views.theme import palette
from app.views.widgets.searchable_combo import SearchableComboBox
from app.views.dialogs.effect_dialog import EffectDialog
from app.controllers.source_controller import SourceController


# Duration type display labels
DURATION_LABELS = {
    "permanent":       "Permanent",
    "toggle":          "Toggle (on/off)",
    "rounds":          "N Rounds",
    "until_next_turn": "Until Next Turn",
    "encounter":       "Encounter",
    "timed":           "Timed (minutes)",
}


class SourceLibraryPanel(QWidget):
    """
    Source Library screen — three-column layout:
      Left:   category filter + search
      Centre: source list
      Right:  source detail / edit form
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = SourceController()
        self.selected_source_id: int | None = None
        self._edit_mode = False

        # Debounce timer for search field
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._do_search)

        self._build_ui()
        self._load_filter_data()
        self._load_sources()

    # ------------------------------------------------------------------
    # UI CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title = QLabel("Source Library")
        title.setObjectName("section_title")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        root.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.addWidget(self._build_filter_column())
        splitter.addWidget(self._build_list_column())
        splitter.addWidget(self._build_detail_column())
        splitter.setSizes([180, 280, 520])

        root.addWidget(splitter, stretch=1)

    # ---- Filter column ------------------------------------------

    def _build_filter_column(self) -> QWidget:
        col = QFrame()
        col.setObjectName("card")
        layout = QVBoxLayout(col)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(10)

        heading = QLabel("Filter")
        heading.setObjectName("subsection_title")
        layout.addWidget(heading)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {palette['border']};")
        layout.addWidget(div)

        # Category filter
        cat_label = QLabel("Category")
        cat_label.setObjectName("label_muted")
        layout.addWidget(cat_label)

        self.category_filter = QComboBox()
        self.category_filter.currentIndexChanged.connect(self._load_sources)
        layout.addWidget(self.category_filter)

        # Duration filter
        dur_label = QLabel("Duration")
        dur_label.setObjectName("label_muted")
        layout.addWidget(dur_label)

        self.duration_filter = QComboBox()
        self.duration_filter.addItem("All durations", None)
        for key, label in DURATION_LABELS.items():
            self.duration_filter.addItem(label, key)
        self.duration_filter.currentIndexChanged.connect(self._load_sources)
        layout.addWidget(self.duration_filter)

        layout.addStretch()

        # Clear filters
        btn_clear = QPushButton("Clear Filters")
        btn_clear.clicked.connect(self._clear_filters)
        layout.addWidget(btn_clear)

        return col

    # ---- List column --------------------------------------------

    def _build_list_column(self) -> QWidget:
        col = QFrame()
        col.setObjectName("card")
        layout = QVBoxLayout(col)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(8)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search sources…")
        self.search_bar.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.search_bar)

        # Source list
        self.source_list = QListWidget()
        self.source_list.currentItemChanged.connect(self._on_source_selected)
        layout.addWidget(self.source_list, stretch=1)

        # New source button
        btn_new = QPushButton("+ New Source")
        btn_new.setObjectName("primary_button")
        btn_new.clicked.connect(self._on_new_source)
        layout.addWidget(btn_new)

        return col

    # ---- Detail / edit column -----------------------------------

    def _build_detail_column(self) -> QWidget:
        self.detail_col = QFrame()
        self.detail_col.setObjectName("card")
        layout = QVBoxLayout(self.detail_col)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header row
        header = QHBoxLayout()
        self.detail_title = QLabel("Select a source")
        self.detail_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.detail_title.setStyleSheet(f"color: {palette['turquoise']};")

        self.btn_edit   = QPushButton("Edit")
        self.btn_edit.setObjectName("secondary_button")
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._enter_edit_mode)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("danger_button")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._on_delete_source)

        header.addWidget(self.detail_title, stretch=1)
        header.addWidget(self.btn_edit)
        header.addWidget(self.btn_delete)
        layout.addLayout(header)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {palette['border']};")
        layout.addWidget(div)

        # Scrollable body — store the QScrollArea so we can swap its widget
        self.detail_scroll = QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._reset_detail_body()           # creates initial empty body
        layout.addWidget(self.detail_scroll, stretch=1)

        # Save/Cancel (hidden until edit mode)
        self.edit_btn_row = QHBoxLayout()
        self.btn_save_edit   = QPushButton("Save Changes")
        self.btn_save_edit.setObjectName("primary_button")
        self.btn_save_edit.clicked.connect(self._on_save_edit)

        self.btn_cancel_edit = QPushButton("Cancel")
        self.btn_cancel_edit.clicked.connect(self._exit_edit_mode)

        self.edit_btn_row.addStretch()
        self.edit_btn_row.addWidget(self.btn_cancel_edit)
        self.edit_btn_row.addWidget(self.btn_save_edit)

        self.edit_btn_widget = QWidget()
        self.edit_btn_widget.setLayout(self.edit_btn_row)
        self.edit_btn_widget.setVisible(False)
        layout.addWidget(self.edit_btn_widget)

        return self.detail_col

    # ------------------------------------------------------------------
    # DATA LOADING
    # ------------------------------------------------------------------

    def _load_filter_data(self):
        result = self.controller.list_categories()
        self.category_filter.clear()
        self.category_filter.addItem("All categories", None)
        if result["success"]:
            for cat in result["data"]:
                self.category_filter.addItem(cat["name"], cat["id"])

    def _load_sources(self):
        query    = self.search_bar.text().strip() if hasattr(self, "search_bar") else ""
        cat_id   = self.category_filter.currentData() if hasattr(self, "category_filter") else None
        dur_type = self.duration_filter.currentData() if hasattr(self, "duration_filter") else None

        if query:
            result = self.controller.search_sources(query)
        else:
            result = self.controller.list_sources(cat_id)

        self.source_list.clear()
        if not result["success"]:
            return

        sources = result["data"]
        if dur_type:
            sources = [s for s in sources if s["duration_type"] == dur_type]

        for source in sources:
            label = f"{source['name']}  [{source['category_name']}]"
            item  = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, source["id"])
            self.source_list.addItem(item)

    def _load_source_detail(self, source_id: int):
        result = self.controller.get_source(source_id)
        if not result["success"]:
            return

        source = result["data"]
        self._render_detail_view(source)

    # ------------------------------------------------------------------
    # DETAIL VIEW (read-only)
    # ------------------------------------------------------------------

    def _reset_detail_body(self):
        """
        Creates a fresh QWidget and installs it as the scroll area's widget.
        This is the only reliable way to clear a QScrollArea's content in PyQt6 —
        replacing the widget entirely avoids stale geometry and visual overlap
        that occur when trying to clear and re-add children in place.
        """
        self.detail_body = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_body)
        self.detail_layout.setSpacing(10)
        self.detail_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.detail_scroll.setWidget(self.detail_body)

    def _render_detail_view(self, source: dict):
        self._reset_detail_body()
        self._edit_mode = False
        self.edit_btn_widget.setVisible(False)

        # Meta info
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def meta_value(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setObjectName("label_value")
            return lbl

        form.addRow("Category:",
            meta_value(source.get("category_name", "—")))
        form.addRow("Duration:",
            meta_value(DURATION_LABELS.get(source["duration_type"], source["duration_type"])))

        dur_val = source.get("duration_value")
        if dur_val:
            form.addRow("Duration value:", meta_value(str(dur_val)))

        action = source.get("action_type_name") or "Passive (no action)"
        form.addRow("Action cost:", meta_value(action))

        self.detail_layout.addLayout(form)

        # Description
        if source.get("description"):
            desc_label = QLabel("Description")
            desc_label.setObjectName("subsection_title")
            self.detail_layout.addWidget(desc_label)
            desc = QLabel(source["description"])
            desc.setWordWrap(True)
            desc.setObjectName("label_muted")
            self.detail_layout.addWidget(desc)

        # Effects section
        effects_label = QLabel("Effects")
        effects_label.setObjectName("subsection_title")
        self.detail_layout.addWidget(effects_label)

        effects = source.get("effects", [])
        if effects:
            for e in effects:
                self.detail_layout.addWidget(self._build_effect_row(e, source["id"]))
        else:
            no_effects = QLabel("No effects defined yet.")
            no_effects.setObjectName("label_muted")
            self.detail_layout.addWidget(no_effects)

        # Add effect button
        btn_add_effect = QPushButton("+ Add Effect")
        btn_add_effect.setObjectName("secondary_button")
        btn_add_effect.clicked.connect(lambda: self._on_add_effect(source["id"]))
        self.detail_layout.addWidget(btn_add_effect)

        self.detail_layout.addStretch()

    def _build_effect_row(self, effect: dict, source_id: int) -> QFrame:
        """Builds a single effect display row with edit/delete buttons."""
        row = QFrame()
        row.setObjectName("card_accent")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 6, 10, 6)

        # Left: stat + modifier summary
        stat_name  = effect.get("stat_name", "?")
        bonus_type = effect.get("bonus_type_name", "?")

        if effect.get("scaling_stat_id") is not None:
            base       = effect.get("base_value") or 0
            mult       = float(effect.get("multiplier") or 1.0)
            div_       = effect.get("divisor") or 1
            sc_stat    = effect.get("scaling_stat_name") or "stat"
            mult_str   = f"{mult:.2f}".rstrip("0").rstrip(".")
            base_str   = f"{base:+d} + " if base != 0 else ""
            div_str    = f" ÷ {div_}" if div_ != 1 else ""
            mod_text   = f"{base_str}floor({sc_stat} × {mult_str}{div_str})"
        elif effect.get("pool_allocation_id") is not None:
            mod_text = "Investment-scaled"
        else:
            mod = effect.get("modifier") or 0
            mod_text = f"{mod:+d}"

        summary = QLabel(f"{stat_name}   {mod_text}   [{bonus_type}]")
        summary.setObjectName("label_value")

        layout.addWidget(summary, stretch=1)

        # Condition note badge
        if effect.get("condition_note"):
            note_btn = QPushButton("⚠")
            note_btn.setFixedWidth(28)
            note_btn.setToolTip(effect["condition_note"])
            note_btn.setStyleSheet(
                f"color: {palette['gold']}; border: none; font-size: 14px;"
            )
            layout.addWidget(note_btn)

        # Edit / delete buttons
        btn_edit = QPushButton("Edit")
        btn_edit.setObjectName("secondary_button")
        btn_edit.setFixedWidth(50)
        btn_edit.clicked.connect(lambda _, e=effect: self._on_edit_effect(e, source_id))

        btn_del = QPushButton("✕")
        btn_del.setObjectName("danger_button")
        btn_del.setFixedWidth(30)
        btn_del.clicked.connect(lambda _, e=effect: self._on_delete_effect(e, source_id))

        layout.addWidget(btn_edit)
        layout.addWidget(btn_del)

        return row

    # ------------------------------------------------------------------
    # EDIT MODE (inline source editing)
    # ------------------------------------------------------------------

    def _enter_edit_mode(self):
        if self.selected_source_id is None:
            return

        result = self.controller.get_source(self.selected_source_id)
        if not result["success"]:
            return

        source = result["data"]
        self._render_edit_form(source)
        self._edit_mode = True
        self.edit_btn_widget.setVisible(True)
        self.btn_edit.setEnabled(False)

    def _exit_edit_mode(self):
        self._edit_mode = False
        self.edit_btn_widget.setVisible(False)
        self.btn_edit.setEnabled(True)
        if self.selected_source_id:
            self._load_source_detail(self.selected_source_id)

    def _render_edit_form(self, source: dict):
        self._reset_detail_body()

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._edit_name = QLineEdit(source["name"])
        form.addRow("Name:", self._edit_name)

        self._edit_category = SearchableComboBox()
        cats = self.controller.list_categories()
        if cats["success"]:
            self._edit_category.populate(cats["data"])
            self._edit_category.select_by_id(source["source_category_id"])
        form.addRow("Category:", self._edit_category)

        self._edit_duration = QComboBox()
        for key, label in DURATION_LABELS.items():
            self._edit_duration.addItem(label, key)
        cur_idx = list(DURATION_LABELS.keys()).index(source["duration_type"])
        self._edit_duration.setCurrentIndex(cur_idx)
        form.addRow("Duration:", self._edit_duration)

        self._edit_duration_value = QSpinBox()
        self._edit_duration_value.setRange(0, 9999)
        self._edit_duration_value.setValue(source.get("duration_value") or 0)
        form.addRow("Duration value:", self._edit_duration_value)

        # Action type combo
        self._edit_action = SearchableComboBox()
        action_types_result = self._get_action_types()
        if action_types_result:
            self._edit_action.populate(action_types_result)
            if source.get("action_type_id"):
                self._edit_action.select_by_id(source["action_type_id"])
        form.addRow("Action cost:", self._edit_action)

        self.detail_layout.addLayout(form)

        desc_label = QLabel("Description:")
        desc_label.setObjectName("label_muted")
        self.detail_layout.addWidget(desc_label)

        self._edit_description = QTextEdit()
        self._edit_description.setFixedHeight(80)
        self._edit_description.setPlainText(source.get("description") or "")
        self.detail_layout.addWidget(self._edit_description)

        self.detail_layout.addStretch()

    def _get_action_types(self) -> list[dict]:
        """Fetches action types directly from the DB for the edit form dropdown."""
        from app.models.combat_model import CombatModel
        # Reuse the DB connection pattern via a quick inline query
        from config.database import get_connection, close_connection
        try:
            conn   = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM action_types ORDER BY name ASC")
            rows = cursor.fetchall()
            close_connection(conn, cursor)
            # Prepend a "Passive" option
            return [{"id": None, "name": "Passive (no action)"}] + rows
        except Exception:
            return []

    # ------------------------------------------------------------------
    # EVENT HANDLERS
    # ------------------------------------------------------------------

    def _on_search_changed(self, text: str):
        self._search_timer.start()

    def _do_search(self):
        self._load_sources()

    def _clear_filters(self):
        self.search_bar.clear()
        self.category_filter.setCurrentIndex(0)
        self.duration_filter.setCurrentIndex(0)
        self._load_sources()

    def _on_source_selected(self, current: QListWidgetItem, _previous):
        has = current is not None
        self.btn_edit.setEnabled(has)
        self.btn_delete.setEnabled(has)

        if has:
            self.selected_source_id = current.data(Qt.ItemDataRole.UserRole)
            result = self.controller.get_source(self.selected_source_id)
            if result["success"]:
                self.detail_title.setText(result["data"]["name"])
                self._render_detail_view(result["data"])
        else:
            self.selected_source_id = None
            self.detail_title.setText("Select a source")
            self._reset_detail_body()

    def _on_new_source(self):
        from app.views.dialogs.source_dialog import SourceDialog
        dlg = SourceDialog(parent=self)
        if dlg.exec():
            self._load_sources()

    def _on_delete_source(self):
        if self.selected_source_id is None:
            return

        name = self.detail_title.text()
        confirm = QMessageBox.question(
            self, "Delete Source",
            f"Delete '{name}' and all its effects?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        result = self.controller.delete_source(self.selected_source_id)
        if result["success"]:
            self.selected_source_id = None
            self.detail_title.setText("Select a source")
            self._reset_detail_body()
            self.btn_edit.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self._load_sources()
        else:
            QMessageBox.warning(self, "Error", result["message"])

    def _on_save_edit(self):
        if self.selected_source_id is None:
            return

        name = self._edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Name cannot be empty.")
            return

        dur_value = self._edit_duration_value.value() or None
        action_id = self._edit_action.current_id()

        result = self.controller.update_source(
            self.selected_source_id,
            name               = name,
            source_category_id = self._edit_category.current_id(),
            duration_type      = self._edit_duration.currentData(),
            duration_value     = dur_value,
            action_type_id     = action_id,
            description        = self._edit_description.toPlainText().strip(),
        )
        if result["success"]:
            self.detail_title.setText(name)
            self._exit_edit_mode()
            self._load_sources()
        else:
            QMessageBox.warning(self, "Error", result["message"])

    def _on_add_effect(self, source_id: int):
        dlg = EffectDialog(source_id=source_id, parent=self)
        if dlg.exec():
            self._load_source_detail(source_id)

    def _on_edit_effect(self, effect: dict, source_id: int):
        dlg = EffectDialog(source_id=source_id, effect=effect, parent=self)
        if dlg.exec():
            self._load_source_detail(source_id)

    def _on_delete_effect(self, effect: dict, source_id: int):
        confirm = QMessageBox.question(
            self, "Delete Effect",
            f"Remove this effect from the source?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        result = self.controller.delete_effect(effect["effect_id"])
        if result["success"]:
            self._load_source_detail(source_id)
        else:
            QMessageBox.warning(self, "Error", result["message"])

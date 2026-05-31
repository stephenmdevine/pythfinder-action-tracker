from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit,
    QComboBox, QSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt

from app.views.theme import palette
from app.views.widgets.searchable_combo import SearchableComboBox
from app.controllers.source_controller import SourceController
from app.views.panels.source_library_panel import DURATION_LABELS


class SourceDialog(QDialog):
    """
    Modal dialog for creating a new source.
    Editing an existing source is handled inline in SourceLibraryPanel.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = SourceController()
        self.setWindowTitle("New Source")
        self.setMinimumWidth(440)
        self.setModal(True)
        self._build_ui()
        self._load_reference_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Power Attack")
        form.addRow("Name:", self.name_edit)

        self.category_combo = SearchableComboBox()
        form.addRow("Category:", self.category_combo)

        self.duration_combo = QComboBox()
        for key, label in DURATION_LABELS.items():
            self.duration_combo.addItem(label, key)
        form.addRow("Duration:", self.duration_combo)

        self.duration_value_spin = QSpinBox()
        self.duration_value_spin.setRange(0, 9999)
        self.duration_value_spin.setValue(0)
        form.addRow("Duration value:", self.duration_value_spin)

        self.action_combo = SearchableComboBox()
        form.addRow("Action cost:", self.action_combo)

        layout.addLayout(form)

        desc_label = QLabel("Description  (optional):")
        desc_label.setObjectName("label_muted")
        layout.addWidget(desc_label)

        self.description_edit = QTextEdit()
        self.description_edit.setFixedHeight(80)
        layout.addWidget(self.description_edit)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_create = QPushButton("Create Source")
        btn_create.setObjectName("primary_button")
        btn_create.clicked.connect(self._on_create)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_create)
        layout.addLayout(btn_row)

    def _load_reference_data(self):
        cats = self.controller.list_categories()
        if cats["success"]:
            self.category_combo.populate(cats["data"])

        # Load action types
        from config.database import get_connection, close_connection
        try:
            conn   = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM action_types ORDER BY name ASC")
            rows = cursor.fetchall()
            close_connection(conn, cursor)
            action_types = [{"id": None, "name": "Passive (no action)"}] + rows
            self.action_combo.populate(action_types)
        except Exception:
            pass

    def _on_create(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Name cannot be empty.")
            return

        dur_type  = self.duration_combo.currentData()
        dur_value = self.duration_value_spin.value() or None
        action_id = self.action_combo.current_id()
        desc      = self.description_edit.toPlainText().strip()
        cat_id    = self.category_combo.current_id()

        if cat_id is None:
            QMessageBox.warning(self, "Validation", "Please select a category.")
            return

        result = self.controller.create_source(
            name               = name,
            source_category_id = cat_id,
            duration_type      = dur_type,
            duration_value     = dur_value,
            action_type_id     = action_id,
            description        = desc,
        )
        if result["success"]:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", result["message"])

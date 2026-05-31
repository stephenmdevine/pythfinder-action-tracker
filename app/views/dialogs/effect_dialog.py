from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit,
    QRadioButton, QButtonGroup, QDoubleSpinBox,
    QSpinBox, QFrame, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.views.theme import palette
from app.views.widgets.searchable_combo import SearchableComboBox
from app.controllers.source_controller import SourceController


class EffectDialog(QDialog):
    """
    Modal dialog for adding or editing a single effect on a source.
    Presents three effect type options via radio buttons:
        Fixed         — user enters a static modifier integer
        Formula-based — scales with a stat using base + floor(stat * mult / div)
        Pool-linked   — investment-scaled, linked to a pool allocation

    On accept, calls SourceController to persist the effect.
    """

    def __init__(self, source_id: int, effect: dict = None, parent=None):
        """
        source_id: the source this effect belongs to.
        effect: if editing, pass the existing effect dict. None for new.
        """
        super().__init__(parent)
        self.source_id  = source_id
        self.effect     = effect        # None = new effect
        self.controller = SourceController()

        self.setWindowTitle("Edit Effect" if effect else "Add Effect")
        self.setMinimumWidth(480)
        self.setModal(True)

        self._build_ui()
        self._load_reference_data()
        if effect:
            self._populate_from_effect(effect)

    # ------------------------------------------------------------------
    # UI CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # ---- Stat selector ----
        stat_row = QFormLayout()
        stat_row.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.stat_combo = SearchableComboBox()
        stat_row.addRow("Stat affected:", self.stat_combo)

        self.bonus_type_combo = SearchableComboBox()
        stat_row.addRow("Bonus type:", self.bonus_type_combo)
        layout.addLayout(stat_row)

        # ---- Effect type selector ----
        type_label = QLabel("Effect type:")
        type_label.setObjectName("subsection_title")
        layout.addWidget(type_label)

        self.type_group   = QButtonGroup(self)
        self.radio_fixed  = QRadioButton("Fixed modifier")
        self.radio_formula = QRadioButton("Formula-scaled  (base + floor(stat × multiplier ÷ divisor))")
        self.radio_pool   = QRadioButton("Investment-scaled  (pool-linked, user enters bonus)")

        self.radio_fixed.setChecked(True)
        for rb in (self.radio_fixed, self.radio_formula, self.radio_pool):
            self.type_group.addButton(rb)
            layout.addWidget(rb)

        # ---- Fixed modifier panel ----
        self.fixed_panel = QFrame()
        fixed_form = QFormLayout(self.fixed_panel)
        fixed_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.modifier_spin = QSpinBox()
        self.modifier_spin.setRange(-999, 999)
        self.modifier_spin.setValue(0)
        fixed_form.addRow("Modifier:", self.modifier_spin)
        layout.addWidget(self.fixed_panel)

        # ---- Formula panel ----
        self.formula_panel = QFrame()
        formula_form = QFormLayout(self.formula_panel)
        formula_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.scaling_stat_combo = SearchableComboBox()
        formula_form.addRow("Scaling stat:", self.scaling_stat_combo)

        self.base_value_spin = QSpinBox()
        self.base_value_spin.setRange(-999, 999)
        self.base_value_spin.setValue(0)
        formula_form.addRow("Base value:", self.base_value_spin)

        self.multiplier_spin = QDoubleSpinBox()
        self.multiplier_spin.setRange(0.01, 99.99)
        self.multiplier_spin.setSingleStep(0.5)
        self.multiplier_spin.setValue(1.0)
        self.multiplier_spin.setDecimals(2)
        formula_form.addRow("Multiplier:", self.multiplier_spin)

        self.divisor_spin = QSpinBox()
        self.divisor_spin.setRange(1, 99)
        self.divisor_spin.setValue(1)
        formula_form.addRow("Divisor:", self.divisor_spin)

        # Live preview label
        self.formula_preview = QLabel("")
        self.formula_preview.setObjectName("label_muted")
        formula_form.addRow("Formula:", self.formula_preview)

        layout.addWidget(self.formula_panel)
        self.formula_panel.setVisible(False)

        # ---- Pool panel ----
        self.pool_panel = QFrame()
        pool_layout = QVBoxLayout(self.pool_panel)
        pool_note = QLabel(
            "This effect's modifier will be entered manually by the user\n"
            "when they invest points. No value is needed here."
        )
        pool_note.setObjectName("label_muted")
        pool_note.setWordWrap(True)
        pool_layout.addWidget(pool_note)
        layout.addWidget(self.pool_panel)
        self.pool_panel.setVisible(False)

        # ---- Condition note ----
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"color: {palette['border']};")
        layout.addWidget(divider)

        cond_label = QLabel("Condition note  (optional):")
        cond_label.setObjectName("label_muted")
        layout.addWidget(cond_label)

        self.condition_note = QTextEdit()
        self.condition_note.setFixedHeight(60)
        self.condition_note.setPlaceholderText(
            "e.g. Only applies on attack rolls against flat-footed targets."
        )
        layout.addWidget(self.condition_note)

        # ---- Buttons ----
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Save Effect")
        self.btn_save.setObjectName("primary_button")
        self.btn_save.clicked.connect(self._on_save)

        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        layout.addLayout(btn_row)

        # ---- Signal connections ----
        self.radio_fixed.toggled.connect(self._on_type_changed)
        self.radio_formula.toggled.connect(self._on_type_changed)
        self.radio_pool.toggled.connect(self._on_type_changed)
        self.scaling_stat_combo.currentIndexChanged.connect(self._update_formula_preview)
        self.base_value_spin.valueChanged.connect(self._update_formula_preview)
        self.multiplier_spin.valueChanged.connect(self._update_formula_preview)
        self.divisor_spin.valueChanged.connect(self._update_formula_preview)

    # ------------------------------------------------------------------
    # DATA
    # ------------------------------------------------------------------

    def _load_reference_data(self):
        stats_result      = self.controller.list_stats()
        bonus_result      = self.controller.list_bonus_types()

        if stats_result["success"]:
            self.stat_combo.populate(stats_result["data"])
            self.scaling_stat_combo.populate(stats_result["data"])
        if bonus_result["success"]:
            self.bonus_type_combo.populate(bonus_result["data"])

    def _populate_from_effect(self, e: dict):
        """Pre-fills all fields when editing an existing effect."""
        self.stat_combo.select_by_id(e["stat_id"])
        self.bonus_type_combo.select_by_id(e["bonus_type_id"])
        self.condition_note.setPlainText(e.get("condition_note") or "")

        if e.get("scaling_stat_id") is not None:
            self.radio_formula.setChecked(True)
            self.scaling_stat_combo.select_by_id(e["scaling_stat_id"])
            self.base_value_spin.setValue(e.get("base_value") or 0)
            self.multiplier_spin.setValue(float(e.get("multiplier") or 1.0))
            self.divisor_spin.setValue(e.get("divisor") or 1)
        elif e.get("pool_allocation_id") is not None:
            self.radio_pool.setChecked(True)
        else:
            self.radio_fixed.setChecked(True)
            self.modifier_spin.setValue(e.get("modifier") or 0)

    # ------------------------------------------------------------------
    # SIGNALS
    # ------------------------------------------------------------------

    def _on_type_changed(self):
        self.fixed_panel.setVisible(self.radio_fixed.isChecked())
        self.formula_panel.setVisible(self.radio_formula.isChecked())
        self.pool_panel.setVisible(self.radio_pool.isChecked())
        self._update_formula_preview()

    def _update_formula_preview(self):
        if not self.radio_formula.isChecked():
            return
        stat_name   = self.scaling_stat_combo.currentText() or "stat"
        base        = self.base_value_spin.value()
        multiplier  = self.multiplier_spin.value()
        divisor     = self.divisor_spin.value()

        base_str = f"{base:+d} + " if base != 0 else ""
        mult_str = f"{multiplier:.2f}".rstrip("0").rstrip(".")
        div_str  = f" ÷ {divisor}" if divisor != 1 else ""
        self.formula_preview.setText(
            f"{base_str}floor({stat_name} × {mult_str}{div_str})"
        )

    # ------------------------------------------------------------------
    # SAVE
    # ------------------------------------------------------------------

    def _on_save(self):
        stat_id       = self.stat_combo.current_id()
        bonus_type_id = self.bonus_type_combo.current_id()
        condition     = self.condition_note.toPlainText().strip()

        if stat_id is None:
            QMessageBox.warning(self, "Validation", "Please select a stat.")
            return
        if bonus_type_id is None:
            QMessageBox.warning(self, "Validation", "Please select a bonus type.")
            return

        # Build kwargs depending on effect type
        kwargs = dict(
            source_id      = self.source_id,
            stat_id        = stat_id,
            bonus_type_id  = bonus_type_id,
            condition_note = condition,
        )

        if self.radio_fixed.isChecked():
            kwargs["modifier"] = self.modifier_spin.value()

        elif self.radio_formula.isChecked():
            scaling_stat_id = self.scaling_stat_combo.current_id()
            if scaling_stat_id is None:
                QMessageBox.warning(self, "Validation", "Please select a scaling stat.")
                return
            kwargs["scaling_stat_id"] = scaling_stat_id
            kwargs["base_value"]      = self.base_value_spin.value()
            kwargs["multiplier"]      = self.multiplier_spin.value()
            kwargs["divisor"]         = self.divisor_spin.value()

        # pool type: no extra kwargs needed — pool_allocation_id linked later

        if self.effect:
            # effect dict may use 'effect_id' (from most queries) or 'id'
            # (from get_by_id). Support both defensively.
            effect_id = self.effect.get("effect_id") or self.effect.get("id")
            if effect_id is None:
                QMessageBox.warning(self, "Error", "Could not determine effect ID.")
                return

            if self.radio_pool.isChecked():
                result = self._ok_pool_update(effect_id)
            else:
                update_kwargs = {k: v for k, v in kwargs.items() if k != "source_id"}
                result = self.controller.update_effect(effect_id, **update_kwargs)
        else:
            result = self.controller.add_effect(**kwargs)

        if result["success"]:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", result["message"])

    def _ok_pool_update(self, effect_id: int) -> dict:
        """
        For pool-linked effects when editing, we simply preserve the
        existing pool_allocation_id link. No changes needed in this dialog.
        """
        return {"success": True, "data": None, "message": ""}

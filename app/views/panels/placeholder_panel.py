from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from app.views.theme import palette


class PlaceholderPanel(QWidget):
    """
    Temporary panel displayed for screens not yet implemented.
    Replaced one by one as each screen is built out.
    """

    def __init__(self, title: str, description: str = "", parent=None):
        super().__init__(parent)
        self._build_ui(title, description)

    def _build_ui(self, title: str, description: str):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {palette['teal']};")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        desc_label = QLabel(description)
        desc_label.setFont(QFont("Segoe UI", 11))
        desc_label.setStyleSheet(f"color: {palette['text_muted']};")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        coming_label = QLabel("— Coming soon —")
        coming_label.setFont(QFont("Segoe UI", 10))
        coming_label.setStyleSheet(f"color: {palette['orchid']};")
        coming_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addWidget(coming_label)

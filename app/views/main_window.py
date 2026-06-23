from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QStatusBar
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont

from app.views.theme import palette, fonts
from app.views.panels.campaign_panel import CampaignPanel
from app.views.panels.source_library_panel import SourceLibraryPanel
from app.views.panels.character_sheet_panel import CharacterSheetPanel
from app.views.panels.placeholder_panel import PlaceholderPanel
from config.settings import APP_NAME, APP_VERSION


class MainWindow(QMainWindow):
    """
    Root application window.
    Contains a fixed sidebar for navigation and a QStackedWidget
    as the content area. Switching screens swaps the stacked page.
    """

    NAV_ITEMS = [
        ("Campaigns",        "campaign"),
        ("Source Library",   "sources"),
        ("Character Sheet",  "character"),
        ("Inventory",        "inventory"),
        ("Action Tracker",   "combat"),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}  v{APP_VERSION}")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

        self._nav_buttons: list[QPushButton] = []
        self._active_character_id: int | None = None
        self._active_campaign_id:  int | None = None
        self._build_ui()
        self._navigate(0)   # open on Campaign Manager by default

        # Wire active-character signals — both panels can drive activation
        self.campaign_panel.character_activated.connect(
            self.set_active_character
        )
        self.character_sheet_panel.character_activated.connect(
            self.set_active_character
        )

    # ------------------------------------------------------------------
    # UI CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self._build_content_area(), stretch=1)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # App title block
        title_block = QWidget()
        title_block.setFixedHeight(72)
        title_layout = QVBoxLayout(title_block)
        title_layout.setContentsMargins(16, 14, 16, 10)
        title_layout.setSpacing(2)

        title_label = QLabel("PYTHFINDER")
        title_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {palette['turquoise']}; letter-spacing: 2px;")

        subtitle_label = QLabel("Action Tracker")
        subtitle_label.setFont(QFont("Segoe UI", 9))
        subtitle_label.setStyleSheet(f"color: {palette['text_muted']};")

        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)

        # Divider under title
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"color: {palette['border']};")

        layout.addWidget(title_block)
        layout.addWidget(divider)

        # Navigation buttons
        for index, (label, _) in enumerate(self.NAV_ITEMS):
            btn = QPushButton(label)
            btn.setObjectName("nav_button")
            btn.setCheckable(True)
            btn.setFixedHeight(44)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=index: self._navigate(i))
            self._nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # Active character block
        active_block = QWidget()
        active_block.setStyleSheet(
            f"background-color: {palette['bg_raised']};"
            f"border-top: 1px solid {palette['border']};"
        )
        active_layout = QVBoxLayout(active_block)
        active_layout.setContentsMargins(14, 8, 14, 8)
        active_layout.setSpacing(2)

        active_heading = QLabel("ACTIVE CHARACTER")
        active_heading.setStyleSheet(
            f"color: {palette['text_muted']}; font-size: 9px; "
            f"font-weight: bold; letter-spacing: 1px;"
        )

        self._active_char_label = QLabel("None")
        self._active_char_label.setStyleSheet(
            f"color: {palette['turquoise']}; font-size: 12px; font-weight: bold;"
        )
        self._active_char_label.setWordWrap(True)

        active_layout.addWidget(active_heading)
        active_layout.addWidget(self._active_char_label)
        layout.addWidget(active_block)

        # Version label at bottom
        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setObjectName("label_muted")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setContentsMargins(0, 0, 0, 8)
        layout.addWidget(version_label)

        return sidebar

    def _build_content_area(self) -> QStackedWidget:
        self.stack = QStackedWidget()
        self.stack.setObjectName("content_panel")

        # Index 0 — Campaign Manager
        self.campaign_panel = CampaignPanel(self)
        self.stack.addWidget(self.campaign_panel)

        # Index 1 — Source Library
        self.stack.addWidget(SourceLibraryPanel(self))

        # Index 2 — Character Sheet
        self.character_sheet_panel = CharacterSheetPanel(self)
        self.stack.addWidget(self.character_sheet_panel)

        self.stack.addWidget(PlaceholderPanel("Inventory & Wealth",
            "Manage items, encumbrance,\n"
            "and the wealth ledger here."))
        self.stack.addWidget(PlaceholderPanel("Action Tracker",
            "Run combat round-by-round:\n"
            "initiative, actions, source activation, and HP."))

        return self.stack

    # ------------------------------------------------------------------
    # ACTIVE CHARACTER
    # ------------------------------------------------------------------

    def set_active_character(self, character_id: int, campaign_id: int):
        """
        Called whenever the active character changes.
        Broadcasts to every panel that tracks a character.
        New panels (Inventory, Combat) should be added here when built.
        """
        self._active_character_id = character_id
        self._active_campaign_id  = campaign_id

        # Character Sheet
        self.character_sheet_panel.set_character(character_id)

        # Update status bar and sidebar label
        name = self.character_sheet_panel.get_active_character_name()
        label = name if name else f"Character #{character_id}"
        self.status_bar.showMessage(f"Active character: {label}")
        self._active_char_label.setText(label)

    # ------------------------------------------------------------------
    # NAVIGATION
    # ------------------------------------------------------------------

    def _navigate(self, index: int):
        # Update button checked states
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)

        self.stack.setCurrentIndex(index)
        self.status_bar.showMessage(self.NAV_ITEMS[index][0])

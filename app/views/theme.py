# ============================================================
# PYTHFINDER ACTION TRACKER — Theme
# ============================================================
# Single source of truth for all colors, spacing, and the
# application-wide QSS stylesheet.
#
# Usage:
#   from app.views.theme import palette, get_stylesheet
#   app.setStyleSheet(get_stylesheet())
#   widget.setStyleSheet(f"background-color: {palette['surface']};")
# ============================================================


# ------------------------------------------------------------------
# COLOR PALETTE
# ------------------------------------------------------------------

palette = {
    # Primary dark colors
    "teal":         "#008080",   # primary accent — headers, active states, key buttons
    "orchid":       "#9932CC",   # secondary accent — highlights, selection, badges

    # Light / supporting colors
    "turquoise":    "#40E0D0",   # teal tint — hover states, subtle backgrounds, icons
    "gold":         "#DA9100",   # harvest gold — warnings, level indicators, coins
    "gray":         "#CBCBCB",   # cool gray — borders, disabled states, dividers

    # Derived surface colors (built from palette)
    "bg_dark":      "#0D1F1F",   # very dark teal-tinted black — main window background
    "bg_surface":   "#122828",   # dark teal surface — panels, cards
    "bg_raised":    "#1A3535",   # slightly lighter — list items, form fields
    "bg_hover":     "#1F4040",   # hover state on raised surfaces

    # Text colors
    "text_primary":   "#F0F8F8",   # near-white with teal tint — main text
    "text_secondary": "#CBCBCB",   # cool gray — labels, secondary info
    "text_muted":     "#7A9E9E",   # muted teal — placeholders, disabled text
    "text_gold":      "#DA9100",   # harvest gold — values, numbers, currency
    "text_orchid":    "#C060E0",   # light orchid — active source names, links

    # Semantic colors
    "success":   "#3DAA6A",   # green — active, healthy, confirmed
    "warning":   "#DA9100",   # gold — caution, limited resource
    "danger":    "#CC3333",   # red — expired, depleted, errors
    "info":      "#40E0D0",   # turquoise — informational

    # Border colors
    "border":         "#2A5050",   # subtle teal border
    "border_active":  "#008080",   # teal — focused/selected border
    "border_orchid":  "#7020A0",   # orchid — special section borders
}


# ------------------------------------------------------------------
# FONT SIZES
# ------------------------------------------------------------------

fonts = {
    "title":    "16px",
    "heading":  "13px",
    "body":     "12px",
    "small":    "11px",
    "tiny":     "10px",
}


# ------------------------------------------------------------------
# QSS STYLESHEET
# ============================================================
# Qt Style Sheets use CSS-like syntax with Qt-specific selectors.
# Widget classes are referenced by their Qt class name.
# ------------------------------------------------------------------

def get_stylesheet() -> str:
    p = palette
    return f"""

    /* ---- Main window & base ---- */
    QMainWindow, QDialog {{
        background-color: {p['bg_dark']};
        color: {p['text_primary']};
    }}

    QWidget {{
        background-color: transparent;
        color: {p['text_primary']};
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        font-size: 12px;
    }}

    /* ---- Sidebar / nav panel ---- */
    QWidget#sidebar {{
        background-color: {p['bg_surface']};
        border-right: 1px solid {p['border']};
    }}

    QPushButton#nav_button {{
        background-color: transparent;
        color: {p['text_secondary']};
        border: none;
        border-left: 3px solid transparent;
        padding: 12px 16px;
        text-align: left;
        font-size: 12px;
    }}

    QPushButton#nav_button:hover {{
        background-color: {p['bg_raised']};
        color: {p['text_primary']};
        border-left: 3px solid {p['teal']};
    }}

    QPushButton#nav_button:checked {{
        background-color: {p['bg_hover']};
        color: {p['turquoise']};
        border-left: 3px solid {p['teal']};
        font-weight: bold;
    }}

    /* ---- Content panels ---- */
    QWidget#content_panel {{
        background-color: {p['bg_dark']};
        padding: 16px;
    }}

    /* ---- Section headers ---- */
    QLabel#section_title {{
        color: {p['turquoise']};
        font-size: 16px;
        font-weight: bold;
        padding-bottom: 4px;
        border-bottom: 1px solid {p['border']};
    }}

    QLabel#subsection_title {{
        color: {p['text_secondary']};
        font-size: 13px;
        font-weight: bold;
    }}

    /* ---- Cards / raised surfaces ---- */
    QFrame#card {{
        background-color: {p['bg_surface']};
        border: 1px solid {p['border']};
        border-radius: 6px;
        padding: 12px;
    }}

    QFrame#card_accent {{
        background-color: {p['bg_surface']};
        border: 1px solid {p['border_orchid']};
        border-left: 3px solid {p['orchid']};
        border-radius: 6px;
        padding: 12px;
    }}

    /* ---- Buttons ---- */
    QPushButton {{
        background-color: {p['bg_raised']};
        color: {p['text_primary']};
        border: 1px solid {p['border']};
        border-radius: 4px;
        padding: 6px 14px;
        font-size: 12px;
    }}

    QPushButton:hover {{
        background-color: {p['bg_hover']};
        border-color: {p['teal']};
        color: {p['turquoise']};
    }}

    QPushButton:pressed {{
        background-color: {p['teal']};
        color: {p['bg_dark']};
    }}

    QPushButton:disabled {{
        color: {p['text_muted']};
        border-color: {p['border']};
        background-color: {p['bg_surface']};
    }}

    QPushButton#primary_button {{
        background-color: {p['teal']};
        color: {p['bg_dark']};
        border: none;
        font-weight: bold;
        padding: 7px 18px;
    }}

    QPushButton#primary_button:hover {{
        background-color: {p['turquoise']};
        color: {p['bg_dark']};
    }}

    QPushButton#secondary_button {{
        background-color: transparent;
        color: {p['orchid']};
        border: 1px solid {p['border_orchid']};
    }}

    QPushButton#secondary_button:hover {{
        background-color: {p['bg_raised']};
        color: {p['text_orchid']};
        border-color: {p['orchid']};
    }}

    QPushButton#danger_button {{
        background-color: transparent;
        color: {p['danger']};
        border: 1px solid {p['danger']};
    }}

    QPushButton#danger_button:hover {{
        background-color: {p['danger']};
        color: {p['text_primary']};
    }}

    /* ---- Inputs ---- */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {p['bg_raised']};
        color: {p['text_primary']};
        border: 1px solid {p['border']};
        border-radius: 4px;
        padding: 5px 8px;
        selection-background-color: {p['teal']};
        selection-color: {p['bg_dark']};
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {p['teal']};
    }}

    QLineEdit::placeholder {{
        color: {p['text_muted']};
    }}

    QComboBox {{
        background-color: {p['bg_raised']};
        color: {p['text_primary']};
        border: 1px solid {p['border']};
        border-radius: 4px;
        padding: 5px 8px;
    }}

    QComboBox:focus {{
        border-color: {p['teal']};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {p['bg_surface']};
        color: {p['text_primary']};
        border: 1px solid {p['border']};
        selection-background-color: {p['teal']};
        selection-color: {p['bg_dark']};
    }}

    QSpinBox {{
        background-color: {p['bg_raised']};
        color: {p['text_primary']};
        border: 1px solid {p['border']};
        border-radius: 4px;
        padding: 4px 6px;
    }}

    QSpinBox:focus {{
        border-color: {p['teal']};
    }}

    /* ---- Tables ---- */
    QTableWidget {{
        background-color: {p['bg_surface']};
        color: {p['text_primary']};
        border: 1px solid {p['border']};
        gridline-color: {p['border']};
        selection-background-color: {p['bg_hover']};
        selection-color: {p['turquoise']};
    }}

    QTableWidget::item {{
        padding: 6px 8px;
        border-bottom: 1px solid {p['border']};
    }}

    QTableWidget::item:selected {{
        background-color: {p['bg_hover']};
        color: {p['turquoise']};
    }}

    QHeaderView::section {{
        background-color: {p['bg_surface']};
        color: {p['text_secondary']};
        border: none;
        border-bottom: 1px solid {p['teal']};
        padding: 6px 8px;
        font-weight: bold;
        font-size: 11px;
        text-transform: uppercase;
    }}

    /* ---- Lists ---- */
    QListWidget {{
        background-color: {p['bg_surface']};
        color: {p['text_primary']};
        border: 1px solid {p['border']};
        border-radius: 4px;
    }}

    QListWidget::item {{
        padding: 8px 10px;
        border-bottom: 1px solid {p['border']};
    }}

    QListWidget::item:hover {{
        background-color: {p['bg_raised']};
        color: {p['text_primary']};
    }}

    QListWidget::item:selected {{
        background-color: {p['bg_hover']};
        color: {p['turquoise']};
        border-left: 2px solid {p['teal']};
    }}

    /* ---- Scrollbars ---- */
    QScrollBar:vertical {{
        background-color: {p['bg_surface']};
        width: 8px;
        border-radius: 4px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {p['border']};
        border-radius: 4px;
        min-height: 20px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {p['teal']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: {p['bg_surface']};
        height: 8px;
        border-radius: 4px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {p['border']};
        border-radius: 4px;
        min-width: 20px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {p['teal']};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* ---- Splitters ---- */
    QSplitter::handle {{
        background-color: {p['border']};
    }}

    QSplitter::handle:hover {{
        background-color: {p['teal']};
    }}

    /* ---- Tabs ---- */
    QTabWidget::pane {{
        border: 1px solid {p['border']};
        background-color: {p['bg_surface']};
    }}

    QTabBar::tab {{
        background-color: {p['bg_surface']};
        color: {p['text_secondary']};
        padding: 8px 16px;
        border: none;
        border-bottom: 2px solid transparent;
    }}

    QTabBar::tab:hover {{
        color: {p['text_primary']};
        border-bottom: 2px solid {p['border']};
    }}

    QTabBar::tab:selected {{
        color: {p['turquoise']};
        border-bottom: 2px solid {p['teal']};
        font-weight: bold;
    }}

    /* ---- Labels ---- */
    QLabel {{
        color: {p['text_primary']};
    }}

    QLabel#label_muted {{
        color: {p['text_muted']};
        font-size: 11px;
    }}

    QLabel#label_value {{
        color: {p['text_gold']};
        font-weight: bold;
    }}

    QLabel#label_orchid {{
        color: {p['text_orchid']};
    }}

    QLabel#badge_active {{
        color: {p['bg_dark']};
        background-color: {p['success']};
        border-radius: 3px;
        padding: 1px 6px;
        font-size: 10px;
        font-weight: bold;
    }}

    QLabel#badge_inactive {{
        color: {p['text_muted']};
        background-color: {p['bg_raised']};
        border-radius: 3px;
        padding: 1px 6px;
        font-size: 10px;
    }}

    /* ---- Dividers ---- */
    QFrame[frameShape="4"],
    QFrame[frameShape="5"] {{
        color: {p['border']};
    }}

    /* ---- Tooltips ---- */
    QToolTip {{
        background-color: {p['bg_surface']};
        color: {p['text_primary']};
        border: 1px solid {p['teal']};
        padding: 4px 8px;
        border-radius: 4px;
    }}

    /* ---- Message boxes ---- */
    QMessageBox {{
        background-color: {p['bg_surface']};
        color: {p['text_primary']};
    }}

    /* ---- Status bar ---- */
    QStatusBar {{
        background-color: {p['bg_surface']};
        color: {p['text_muted']};
        border-top: 1px solid {p['border']};
        font-size: 11px;
    }}

    """

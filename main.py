"""
Pythfinder Action Tracker
Entry point — run this file to launch the application.

Usage:
    python main.py
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from config.settings import APP_NAME, APP_VERSION
from config.database import get_connection, close_connection
from app.views.main_window import MainWindow
from app.views.theme import get_stylesheet


def check_db_connection() -> bool:
    """Verifies the database is reachable before launching the UI."""
    try:
        conn = get_connection()
        close_connection(conn)
        print(f"[OK] Connected to pythfinder_tracker database.")
        return True
    except ConnectionError as e:
        print(f"[ERROR] {e}")
        print("Check your credentials in config/settings.py")
        return False


def main():
    print(f"{APP_NAME} v{APP_VERSION}")
    print("-" * 40)

    if not check_db_connection():
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # Apply global font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Apply theme stylesheet
    app.setStyleSheet(get_stylesheet())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

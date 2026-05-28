"""
Pythfinder Action Tracker
Entry point — run this file to launch the application.

Usage:
    python main.py
"""

from config.settings import APP_NAME, APP_VERSION
from config.database import get_connection, close_connection


def check_db_connection():
    """Verifies the database is reachable before launching the UI."""
    try:
        conn = get_connection()
        close_connection(conn)
        print(f"[OK] Connected to pythfinder_tracker database.")
        return True
    except ConnectionError as e:
        print(f"[ERROR] {e}")
        print("Check your credentials in config/settings.py (or settings_local.py).")
        return False


def main():
    print(f"{APP_NAME} v{APP_VERSION}")
    print("-" * 40)

    if not check_db_connection():
        return

    # UI will be initialized here once PyQt6 views are built
    print("Application started. UI coming soon.")


if __name__ == "__main__":
    main()

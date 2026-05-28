# ============================================================
# PYTHFINDER ACTION TRACKER — Settings
# ============================================================
# Copy this file to settings_local.py and fill in your credentials.
# settings_local.py is gitignored so passwords are never committed.
# ============================================================

DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "database": "pythfinder_tracker",
    "user":     "pythfinder_user",
    "password": "MageHand",
}

# Application-wide constants
APP_NAME    = "Pythfinder Action Tracker"
APP_VERSION = "0.1.0"

# Encumbrance thresholds (PF1e, medium load as % of light load limit)
# These are used by the inventory/wealth model layer
ENCUMBRANCE_LIGHT_MAX_MULTIPLIER  = 1.0
ENCUMBRANCE_MEDIUM_MAX_MULTIPLIER = 2.0
ENCUMBRANCE_HEAVY_MAX_MULTIPLIER  = 3.0

# Coin conversion to gold pieces (used by wealth ledger calculations)
COIN_TO_GOLD = {
    "platinum": 10.0,
    "gold":      1.0,
    "silver":    0.1,
    "copper":    0.01,
}

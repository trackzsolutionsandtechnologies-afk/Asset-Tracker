"""
Configuration file for Asset Tracker Application
"""
import os

# Default values - will be overridden by secrets if available
GOOGLE_SHEET_ID = "1kFlJLYC6I7NojaXr2UUX68Al4SO76bDlr-ojBl1mvZo"
GOOGLE_CREDENTIALS_FILE = "credentials.json"
GOOGLE_DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "16D-x6aZKUq9Tl2Ijx3-tqrnF9GB0YJsk")

# Default sheet names
SHEETS = {
    "users": "Users",
    "locations": "Locations",
    "suppliers": "Suppliers",
    "categories": "Categories",
    "subcategories": "SubCategories",
    "assets": "Assets",
    "transfers": "Transfers",
    "maintenance": "AssetMaintenance",
    "assignments": "EmployeeAssignments",
    "asset_history": "AssetHistory",
    "password_resets": "PasswordResets",
    "depreciation": "Depreciation",
    "attachments": "Attachments",
    "drive_credentials": "DriveCredentials",
}

def get_config():
    """
    Get configuration from Streamlit secrets if available.
    This function should be called after Streamlit is initialized.
    Updates the module-level variables.
    """
    try:
        import streamlit as st
        # Google Sheets Configuration from secrets
        if hasattr(st, 'secrets') and "google_sheets" in st.secrets:
            global GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_FILE
            sheet_id = st.secrets["google_sheets"].get("sheet_id")
            if sheet_id:
                GOOGLE_SHEET_ID = sheet_id
            creds_file = st.secrets["google_sheets"].get("credentials_file")
            if creds_file:
                GOOGLE_CREDENTIALS_FILE = creds_file

        if hasattr(st, 'secrets') and "google_drive" in st.secrets:
            global GOOGLE_DRIVE_FOLDER_ID
            folder_id = st.secrets["google_drive"].get("folder_id")
            if folder_id:
                GOOGLE_DRIVE_FOLDER_ID = folder_id
        
        # Sheet Names from secrets
        if hasattr(st, 'secrets') and "sheets" in st.secrets:
            global SHEETS
            sheets_config = st.secrets["sheets"]
            SHEETS = {
                "users": sheets_config.get("users", SHEETS["users"]),
                "locations": sheets_config.get("locations", SHEETS["locations"]),
                "suppliers": sheets_config.get("suppliers", SHEETS["suppliers"]),
                "categories": sheets_config.get("categories", SHEETS["categories"]),
                "subcategories": sheets_config.get("subcategories", SHEETS["subcategories"]),
                "assets": sheets_config.get("assets", SHEETS["assets"]),
                "transfers": sheets_config.get("transfers", SHEETS["transfers"]),
                "maintenance": sheets_config.get("maintenance", SHEETS["maintenance"]),
                "assignments": sheets_config.get("assignments", SHEETS["assignments"]),
                "asset_history": sheets_config.get("asset_history", SHEETS["asset_history"]),
                "password_resets": sheets_config.get("password_resets", SHEETS["password_resets"]),
                "depreciation": sheets_config.get("depreciation", SHEETS["depreciation"]),
                "attachments": sheets_config.get("attachments", SHEETS["attachments"]),
                "drive_credentials": sheets_config.get("drive_credentials", SHEETS["drive_credentials"]),
            }
    except Exception as e:
        # If secrets are not available, use defaults
        # Silently fail - defaults will be used
        pass

# Session State Keys
SESSION_KEYS = {
    "authenticated": "authenticated",
    "username": "username",
    "user_role": "user_role",
    "auth_token": "auth_token",
}

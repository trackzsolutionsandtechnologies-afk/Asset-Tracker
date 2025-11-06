"""
Configuration file for Asset Tracker Application
"""
import os

# Try to read from Streamlit secrets, fallback to defaults
try:
    import streamlit as st
    # Google Sheets Configuration from secrets
    if hasattr(st, 'secrets') and "google_sheets" in st.secrets:
        GOOGLE_SHEET_ID = st.secrets["google_sheets"].get("sheet_id", "1kFlJLYC6I7NojaXr2UUX68Al4SO76bDlr-ojBl1mvZo")
        GOOGLE_CREDENTIALS_FILE = st.secrets["google_sheets"].get("credentials_file", "credentials.json")
    else:
        GOOGLE_SHEET_ID = "1kFlJLYC6I7NojaXr2UUX68Al4SO76bDlr-ojBl1mvZo"
        GOOGLE_CREDENTIALS_FILE = "credentials.json"
except:
    # Fallback if not running in Streamlit or secrets not available
    GOOGLE_SHEET_ID = "1kFlJLYC6I7NojaXr2UUX68Al4SO76bDlr-ojBl1mvZo"
    GOOGLE_CREDENTIALS_FILE = "credentials.json"

# Sheet Names - Try to read from secrets, fallback to defaults
try:
    import streamlit as st
    if hasattr(st, 'secrets') and "sheets" in st.secrets:
        SHEETS = {
            "users": st.secrets["sheets"].get("users", "Users"),
            "locations": st.secrets["sheets"].get("locations", "Locations"),
            "suppliers": st.secrets["sheets"].get("suppliers", "Suppliers"),
            "categories": st.secrets["sheets"].get("categories", "Categories"),
            "subcategories": st.secrets["sheets"].get("subcategories", "SubCategories"),
            "assets": st.secrets["sheets"].get("assets", "Assets"),
            "transfers": st.secrets["sheets"].get("transfers", "Transfers"),
            "password_resets": st.secrets["sheets"].get("password_resets", "PasswordResets")
        }
    else:
        SHEETS = {
            "users": "Users",
            "locations": "Locations",
            "suppliers": "Suppliers",
            "categories": "Categories",
            "subcategories": "SubCategories",
            "assets": "Assets",
            "transfers": "Transfers",
            "password_resets": "PasswordResets"
        }
except:
    # Fallback if not running in Streamlit or secrets not available
    SHEETS = {
        "users": "Users",
        "locations": "Locations",
        "suppliers": "Suppliers",
        "categories": "Categories",
        "subcategories": "SubCategories",
        "assets": "Assets",
        "transfers": "Transfers",
        "password_resets": "PasswordResets"
    }

# Session State Keys
SESSION_KEYS = {
    "authenticated": "authenticated",
    "username": "username",
    "user_role": "user_role"
}

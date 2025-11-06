"""
Configuration file for Asset Tracker Application
"""
import os

# Google Sheets Configuration
GOOGLE_SHEET_ID = "1kFlJLYC6I7NojaXr2UUX68Al4SO76bDlr-ojBl1mvZo"
GOOGLE_CREDENTIALS_FILE = "credentials.json"

# Sheet Names
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

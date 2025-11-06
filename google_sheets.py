"""
Google Sheets integration module for database operations
"""
import os
import time
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from typing import List, Dict, Optional
import streamlit as st
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_FILE, SHEETS

# Define the scope
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Rate limiting - track last request time
_last_request_time = 0
_min_request_interval = 1.0  # Minimum 1 second between requests

@st.cache_resource
def get_google_client():
    """Initialize and return Google Sheets client"""
    try:
        # Try to use service account credentials
        if os.path.exists(GOOGLE_CREDENTIALS_FILE):
            creds = Credentials.from_service_account_file(
                GOOGLE_CREDENTIALS_FILE, scopes=SCOPE
            )
            client = gspread.authorize(creds)
            return client
        else:
            # Try to access as public sheet (read-only)
            try:
                client = gspread.service_account()
                return client
            except:
                # If that fails, return None - user needs to set up credentials
                if "credentials_warning_shown" not in st.session_state:
                    st.warning("⚠️ Google Sheets credentials not found. Please set up credentials.json for full functionality. See README for instructions.")
                    st.session_state["credentials_warning_shown"] = True
                return None
    except Exception as e:
        if "connection_error_shown" not in st.session_state:
            st.error(f"Error connecting to Google Sheets: {str(e)}")
            st.session_state["connection_error_shown"] = True
        return None

def _rate_limit():
    """Enforce rate limiting between API requests"""
    global _last_request_time
    current_time = time.time()
    time_since_last = current_time - _last_request_time
    if time_since_last < _min_request_interval:
        time.sleep(_min_request_interval - time_since_last)
    _last_request_time = time.time()

def get_worksheet(sheet_name: str):
    """Get a specific worksheet from the Google Sheet"""
    try:
        _rate_limit()  # Rate limit before API call
        client = get_google_client()
        if client is None:
            return None
        
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # Create worksheet if it doesn't exist
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
            # Add headers if it's a new sheet
            if sheet_name == SHEETS["users"]:
                worksheet.append_row(["Username", "Password", "Email", "Role"])
            elif sheet_name == SHEETS["locations"]:
                worksheet.append_row(["Location ID", "Location Name", "Department"])
            elif sheet_name == SHEETS["suppliers"]:
                worksheet.append_row(["Supplier ID", "Supplier Name"])
            elif sheet_name == SHEETS["categories"]:
                worksheet.append_row(["Category ID", "Category Name"])
            elif sheet_name == SHEETS["subcategories"]:
                worksheet.append_row(["SubCategory ID", "Category ID", "SubCategory Name"])
            elif sheet_name == SHEETS["assets"]:
                worksheet.append_row([
                    "Asset ID", "Asset Name", "Category", "Sub Category", 
                    "Model/Serial No", "Purchase Date", "Purchase Cost", 
                    "Supplier", "Location", "Assigned To", "Condition", 
                    "Status", "Remarks", "Attachment"
                ])
            elif sheet_name == SHEETS["transfers"]:
                worksheet.append_row([
                    "Transfer ID", "Asset ID", "From Location", "To Location", 
                    "Date", "Approved By"
                ])
            elif sheet_name == SHEETS["password_resets"]:
                worksheet.append_row(["Username", "Reset Token", "Expiry"])
        
        return worksheet
    except gspread.exceptions.APIError as e:
        error_msg = str(e)
        if '429' in error_msg or 'RESOURCE_EXHAUSTED' in error_msg or 'RATE_LIMIT_EXCEEDED' in error_msg:
            st.warning("⚠️ Rate limit exceeded. Please wait a moment and refresh the page.")
            st.info("The application is making too many requests. Please wait 60 seconds before trying again.")
            return None
        else:
            st.error(f"Error accessing worksheet {sheet_name}: {str(e)}")
            return None
    except Exception as e:
        st.error(f"Error accessing worksheet {sheet_name}: {str(e)}")
        return None

@st.cache_data(ttl=60, show_spinner=False)  # Cache for 60 seconds to reduce API calls, hide spinner
def read_data(sheet_name: str) -> pd.DataFrame:
    """Read data from a worksheet and return as DataFrame with caching"""
    worksheet = get_worksheet(sheet_name)
    if worksheet is None:
        return pd.DataFrame()
    
    try:
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        # Store in session state as backup cache
        cache_key = f"cached_{sheet_name}"
        st.session_state[cache_key] = df
        return df
    except gspread.exceptions.APIError as e:
        error_msg = str(e)
        if '429' in error_msg or 'RESOURCE_EXHAUSTED' in error_msg or 'RATE_LIMIT_EXCEEDED' in error_msg:
            st.warning("⚠️ Rate limit exceeded. Using cached data if available.")
            # Try to return cached data from session state
            cache_key = f"cached_{sheet_name}"
            if cache_key in st.session_state:
                return st.session_state[cache_key]
            st.error("No cached data available. Please wait 60 seconds and refresh the page.")
            return pd.DataFrame()
        else:
            st.error(f"Error reading data from {sheet_name}: {str(e)}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error reading data from {sheet_name}: {str(e)}")
        return pd.DataFrame()

def clear_cache():
    """Clear all cached data"""
    read_data.clear()
    if "cached_data" in st.session_state:
        del st.session_state["cached_data"]

def append_data(sheet_name: str, data: List) -> bool:
    """Append a new row to a worksheet"""
    worksheet = get_worksheet(sheet_name)
    if worksheet is None:
        return False
    
    try:
        worksheet.append_row(data)
        # Clear cache after write operation
        read_data.clear()
        return True
    except gspread.exceptions.APIError as e:
        error_msg = str(e)
        if '429' in error_msg or 'RESOURCE_EXHAUSTED' in error_msg or 'RATE_LIMIT_EXCEEDED' in error_msg:
            st.warning("⚠️ Rate limit exceeded. Please wait a moment and try again.")
            return False
        else:
            st.error(f"Error appending data to {sheet_name}: {str(e)}")
            return False
    except Exception as e:
        st.error(f"Error appending data to {sheet_name}: {str(e)}")
        return False

def update_data(sheet_name: str, row_index: int, data: List) -> bool:
    """Update a specific row in a worksheet"""
    worksheet = get_worksheet(sheet_name)
    if worksheet is None:
        return False
    
    try:
        # Get all data to find the correct row
        all_values = worksheet.get_all_values()
        if len(all_values) <= row_index + 1:
            return False
        
        # Update the row (row_index is 0-based, add 1 for header, add 1 more for 1-based indexing)
        row_num = row_index + 2
        
        # Calculate end column letter
        def get_column_letter(n):
            """Convert column number to letter (1 -> A, 27 -> AA, etc.)"""
            result = ""
            while n > 0:
                n -= 1
                result = chr(65 + (n % 26)) + result
                n //= 26
            return result
        
        end_col = get_column_letter(len(data))
        range_name = f"A{row_num}:{end_col}{row_num}"
        worksheet.update(range_name, [data])
        # Clear cache after write operation
        read_data.clear()
        return True
    except gspread.exceptions.APIError as e:
        error_msg = str(e)
        if '429' in error_msg or 'RESOURCE_EXHAUSTED' in error_msg or 'RATE_LIMIT_EXCEEDED' in error_msg:
            st.warning("⚠️ Rate limit exceeded. Please wait a moment and try again.")
            return False
        else:
            st.error(f"Error updating data in {sheet_name}: {str(e)}")
            return False
    except Exception as e:
        st.error(f"Error updating data in {sheet_name}: {str(e)}")
        return False

def delete_data(sheet_name: str, row_index: int) -> bool:
    """Delete a specific row from a worksheet"""
    worksheet = get_worksheet(sheet_name)
    if worksheet is None:
        return False
    
    try:
        # row_index is 1-based, add 2 to account for header row
        worksheet.delete_rows(row_index + 2)
        # Clear cache after write operation
        read_data.clear()
        return True
    except gspread.exceptions.APIError as e:
        error_msg = str(e)
        if '429' in error_msg or 'RESOURCE_EXHAUSTED' in error_msg or 'RATE_LIMIT_EXCEEDED' in error_msg:
            st.warning("⚠️ Rate limit exceeded. Please wait a moment and try again.")
            return False
        else:
            st.error(f"Error deleting data from {sheet_name}: {str(e)}")
            return False
    except Exception as e:
        st.error(f"Error deleting data from {sheet_name}: {str(e)}")
        return False

def find_row(sheet_name: str, column: str, value: str) -> Optional[int]:
    """Find the row index where a column matches a value"""
    df = read_data(sheet_name)
    if df.empty:
        return None
    
    try:
        matches = df[df[column] == value]
        if not matches.empty:
            # Return the index (0-based), but we need to add 1 for gspread
            return matches.index[0]
        return None
    except Exception as e:
        st.error(f"Error finding row in {sheet_name}: {str(e)}")
        return None

"""
Google Sheets integration module for database operations
"""
import os
import time
import logging
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from typing import List, Dict, Optional
import streamlit as st
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_FILE, SHEETS, get_config

# Define the scope
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Rate limiting - track last request time
_last_request_time = 0
_min_request_interval = 1.0  # Minimum 1 second between requests

_cached_credentials: Optional[Credentials] = None

logger = logging.getLogger(__name__)

@st.cache_resource
def get_google_client():
    """Initialize and return Google Sheets client"""
    global _cached_credentials
    # Ensure config is loaded from secrets
    try:
        get_config()
    except:
        pass
    
    try:
        # First, try to get credentials from secrets.toml (as JSON string)
        try:
            if hasattr(st, 'secrets') and "google_sheets" in st.secrets:
                # Check if credentials are stored directly in secrets
                if "credentials_json" in st.secrets["google_sheets"]:
                    import json
                    creds_json = st.secrets["google_sheets"]["credentials_json"]
                    
                    # Debug: Log what we received (only once)
                    if "creds_debug_logged" not in st.session_state:
                        st.session_state["creds_debug_logged"] = True
                        # Store debug info but don't show unless in debug mode
                        st.session_state["creds_debug_type"] = type(creds_json).__name__
                    
                    # Handle both string and dict formats (Streamlit Cloud may parse JSON)
                    if isinstance(creds_json, str):
                        try:
                            # Try to parse as JSON string
                            creds_dict = json.loads(creds_json)
                        except json.JSONDecodeError as e:
                            # If parsing fails, it might be a multi-line string that needs processing
                            # Try to clean it up and parse again
                            try:
                                # Remove extra whitespace and newlines
                                cleaned = creds_json.strip()
                                creds_dict = json.loads(cleaned)
                            except json.JSONDecodeError as e2:
                                # If still fails, log error but continue to file-based
                                if "credentials_json_error" not in st.session_state:
                                    st.session_state["credentials_json_error"] = f"JSON parse error: {str(e2)}"
                                raise
                    else:
                        # Already a dict (Streamlit Cloud parsed it from TOML)
                        creds_dict = creds_json
                    
                    # Validate that we have the required fields
                    if not isinstance(creds_dict, dict) or "type" not in creds_dict:
                        if "credentials_json_error" not in st.session_state:
                            st.session_state["credentials_json_error"] = "Invalid credentials format: missing 'type' field"
                        raise ValueError("Invalid credentials format")
                    
                    # Validate private_key is present and properly formatted
                    if "private_key" not in creds_dict:
                        if "credentials_json_error" not in st.session_state:
                            st.session_state["credentials_json_error"] = "Invalid credentials format: missing 'private_key' field"
                        raise ValueError("Missing private_key in credentials")
                    
                    # Fix private_key newlines if needed (replace \\n with actual newlines)
                    if isinstance(creds_dict.get("private_key"), str):
                        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                    
                    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
                    _cached_credentials = creds
                    client = gspread.authorize(creds)
                    # Clear any previous warnings since we found credentials
                    if "credentials_warning_shown" in st.session_state:
                        del st.session_state["credentials_warning_shown"]
                    if "credentials_json_error" in st.session_state:
                        del st.session_state["credentials_json_error"]
                    return client
                else:
                    # credentials_json not found in secrets
                    if "creds_debug_logged" not in st.session_state:
                        st.session_state["creds_debug_logged"] = True
                        available_keys = list(st.secrets["google_sheets"].keys()) if hasattr(st.secrets["google_sheets"], 'keys') else []
                        st.session_state["creds_available_keys"] = available_keys
            else:
                # google_sheets section not found in secrets
                if "creds_debug_logged" not in st.session_state:
                    st.session_state["creds_debug_logged"] = True
                    available_sections = list(st.secrets.keys()) if hasattr(st.secrets, 'keys') else []
                    st.session_state["creds_available_sections"] = available_sections
        except Exception as e:
            # Store error for debugging
            if "credentials_json_error" not in st.session_state:
                st.session_state["credentials_json_error"] = str(e)
            pass  # Fall through to file-based credentials
        
        # Get credentials file path - try from secrets first, then config
        credentials_file = GOOGLE_CREDENTIALS_FILE
        try:
            if hasattr(st, 'secrets') and "google_sheets" in st.secrets:
                credentials_file = st.secrets["google_sheets"].get("credentials_file", GOOGLE_CREDENTIALS_FILE)
        except:
            pass
        
        # Check if credentials file exists (try both relative and absolute paths)
        possible_paths = [
            credentials_file,
            os.path.join(os.getcwd(), credentials_file),
            os.path.join(os.path.dirname(__file__), credentials_file)
        ]
        
        credentials_found = False
        for cred_path in possible_paths:
            if os.path.exists(cred_path) and os.path.isfile(cred_path):
                try:
                    creds = Credentials.from_service_account_file(
                        cred_path, scopes=SCOPE
                    )
                    _cached_credentials = creds
                    client = gspread.authorize(creds)
                    # Clear any previous warnings since we found credentials
                    if "credentials_warning_shown" in st.session_state:
                        del st.session_state["credentials_warning_shown"]
                    return client
                except Exception as e:
                    if "credentials_error_shown" not in st.session_state:
                        st.error(f"Error loading credentials from {cred_path}: {str(e)}")
                        st.info("Please check that your credentials.json file is valid and has the correct format.")
                        st.session_state["credentials_error_shown"] = True
                    return None
                credentials_found = True
                break
        
        if not credentials_found:
            # Try to use gspread's default service account (if set up via environment)
            try:
                client = gspread.service_account()
                _cached_credentials = getattr(client, "auth", None)
                return client
            except:
                # If that fails, show warning only once with debug info
                if "credentials_warning_shown" not in st.session_state:
                    st.warning(f"⚠️ Google Sheets credentials not found.")
                    
                    # Show debug information if available
                    debug_info = []
                    if "creds_available_sections" in st.session_state:
                        debug_info.append(f"Available secret sections: {st.session_state['creds_available_sections']}")
                    if "creds_available_keys" in st.session_state:
                        debug_info.append(f"Available keys in google_sheets: {st.session_state['creds_available_keys']}")
                    if "credentials_json_error" in st.session_state:
                        debug_info.append(f"Error: {st.session_state['credentials_json_error']}")
                    if "creds_debug_type" in st.session_state:
                        debug_info.append(f"credentials_json type: {st.session_state['creds_debug_type']}")
                    
                    if debug_info:
                        with st.expander("🔍 Debug Information"):
                            for info in debug_info:
                                st.text(info)
                    
                    st.info(f"💡 **Options to fix:**\n1. Go to Streamlit Cloud → Settings → Secrets\n2. Add `[google_sheets]` section with `credentials_json`\n3. Make sure secrets are saved and app is redeployed")
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
                    "Warranty",
                    "Supplier", "Location", "Assigned To", "Condition", 
                    "Status", "Remarks", "Attachment"
                ])
            elif sheet_name == SHEETS["depreciation"]:
                worksheet.append_row([
                    "Schedule ID",
                    "Asset ID",
                    "Asset Name",
                    "Purchase Date",
                    "Purchase Cost",
                    "Useful Life (Years)",
                    "Salvage Value",
                    "Method",
                    "Period",
                    "Period End",
                    "Opening Value",
                    "Depreciation",
                    "Closing Value",
                    "Generated On",
                ])
            elif sheet_name == SHEETS["transfers"]:
                worksheet.append_row([
                    "Transfer ID", "Asset ID", "From Location", "To Location", 
                    "Date", "Approved By"
                ])
            elif sheet_name == SHEETS["password_resets"]:
                worksheet.append_row(["Username", "Reset Token", "Expiry"])
            elif sheet_name == SHEETS["attachments"]:
                worksheet.append_row([
                    "Timestamp",
                    "Asset ID",
                    "Asset Name",
                    "File Name",
                    "Drive URL",
                    "Uploaded By",
                    "Notes",
                ])
        
        return worksheet
    except gspread.exceptions.APIError as e:
        error_msg = str(e)
        if '429' in error_msg or 'RESOURCE_EXHAUSTED' in error_msg or 'RATE_LIMIT_EXCEEDED' in error_msg:
            logger.warning("Rate limit exceeded when accessing worksheet %s", sheet_name)
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
            logger.warning("Rate limit exceeded when reading %s; attempting to use cached data", sheet_name)
            # Try to return cached data from session state
            cache_key = f"cached_{sheet_name}"
            if cache_key in st.session_state:
                return st.session_state[cache_key]
            logger.error("No cached data available for %s after rate limit hit", sheet_name)
            return pd.DataFrame()
        else:
            st.error(f"Error reading data from {sheet_name}: {str(e)}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error reading data from {sheet_name}: {str(e)}")
        return pd.DataFrame()


def get_cached_credentials() -> Optional[Credentials]:
    """Return the cached Google credentials used for Sheets access."""
    return _cached_credentials


def ensure_sheet_headers(sheet_name: str, headers: List[str]) -> bool:
    """Ensure the worksheet has the expected header row."""
    worksheet = get_worksheet(sheet_name)
    if worksheet is None:
        return False

    try:
        current_header = worksheet.row_values(1)
        normalized_current = [str(h).strip().lower() for h in current_header]
        normalized_expected = [str(h).strip().lower() for h in headers]

        needs_update = False
        if not current_header:
            needs_update = True
        elif len(normalized_current) < len(normalized_expected):
            needs_update = True
        elif normalized_current[: len(normalized_expected)] != normalized_expected:
            needs_update = True

        if needs_update:
            worksheet.update("1:1", [headers])
            read_data.clear()
        return True
    except Exception as e:
        st.error(f"Error ensuring headers for {sheet_name}: {str(e)}")
        return False

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
            logger.warning("Rate limit exceeded while appending to %s", sheet_name)
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
        # Ensure row_index is a Python int (not numpy int64)
        row_index = int(row_index)
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
            logger.warning("Rate limit exceeded while updating %s row %s", sheet_name, row_index)
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
        # Ensure row_index is a Python int (not numpy int64)
        row_index = int(row_index)
        # row_index is 0-based, add 2 to account for header row (1) and 1-based indexing (1)
        worksheet.delete_rows(row_index + 2)
        # Clear cache after write operation
        read_data.clear()
        return True
    except gspread.exceptions.APIError as e:
        error_msg = str(e)
        if '429' in error_msg or 'RESOURCE_EXHAUSTED' in error_msg or 'RATE_LIMIT_EXCEEDED' in error_msg:
            logger.warning("Rate limit exceeded while deleting row %s from %s", row_index, sheet_name)
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

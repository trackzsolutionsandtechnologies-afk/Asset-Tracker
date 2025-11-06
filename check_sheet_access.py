"""
Check Google Sheet access and list worksheets
"""
import os
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_FILE

# Define the scope
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def check_sheet_access():
    """Check if we can access the Google Sheet"""
    print("Checking Google Sheet access...")
    print(f"Sheet ID: {GOOGLE_SHEET_ID}")
    print()
    
    try:
        # Load credentials
        creds = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_FILE, scopes=SCOPE
        )
        client = gspread.authorize(creds)
        print("[OK] Client authorized")
        
        # Try to open the spreadsheet
        try:
            spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
            print("[OK] Spreadsheet opened successfully")
            print(f"   Title: {spreadsheet.title}")
            
            # List all worksheets
            print("\nExisting worksheets:")
            worksheets = spreadsheet.worksheets()
            if worksheets:
                for ws in worksheets:
                    print(f"   - {ws.title} ({ws.row_count} rows)")
            else:
                print("   (No worksheets found)")
            
            # Try to create Users worksheet if it doesn't exist
            print("\nChecking for 'Users' worksheet...")
            try:
                users_ws = spreadsheet.worksheet("Users")
                print("[OK] 'Users' worksheet exists")
            except gspread.exceptions.WorksheetNotFound:
                print("[INFO] 'Users' worksheet not found, attempting to create...")
                try:
                    users_ws = spreadsheet.add_worksheet(title="Users", rows=1000, cols=20)
                    print("[OK] 'Users' worksheet created successfully")
                    # Add headers
                    users_ws.append_row(["Username", "Password", "Email", "Role"])
                    print("[OK] Headers added to 'Users' worksheet")
                except Exception as e:
                    print(f"[ERROR] Failed to create 'Users' worksheet: {str(e)}")
                    return False
            
            return True
            
        except gspread.exceptions.SpreadsheetNotFound:
            print("[ERROR] Spreadsheet not found!")
            print("   Make sure the Google Sheet ID is correct")
            return False
        except gspread.exceptions.APIError as e:
            print(f"[ERROR] API Error: {str(e)}")
            if "PERMISSION_DENIED" in str(e):
                print("   The service account doesn't have access to this sheet")
                print("   Make sure you shared the sheet with:")
                print("   asset-tracker@asset-tracker-477410.iam.gserviceaccount.com")
            return False
            
    except Exception as e:
        print(f"[ERROR] Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_sheet_access()
    if success:
        print("\n[SUCCESS] Sheet access verified!")
    else:
        print("\n[FAILED] Could not access sheet. Please check the errors above.")


"""
Test Google Sheets connection
"""
import os
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
from google_sheets import get_google_client, get_worksheet
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_FILE

def test_connection():
    """Test Google Sheets connection"""
    print("Testing Google Sheets connection...")
    print(f"Sheet ID: {GOOGLE_SHEET_ID}")
    print(f"Credentials file: {GOOGLE_CREDENTIALS_FILE}")
    print()
    
    # Check if credentials file exists
    if os.path.exists(GOOGLE_CREDENTIALS_FILE):
        print("[OK] credentials.json file found")
    else:
        print("[ERROR] credentials.json file NOT found!")
        print("Please download credentials from Google Cloud Console")
        return False
    
    # Test client connection
    print("\nTesting client connection...")
    try:
        client = get_google_client()
        if client:
            print("[OK] Google Sheets client connected successfully")
        else:
            print("[ERROR] Failed to create Google Sheets client")
            return False
    except Exception as e:
        print(f"[ERROR] Connection error: {str(e)}")
        return False
    
    # Test worksheet access
    print("\nTesting worksheet access...")
    try:
        worksheet = get_worksheet("Users")
        if worksheet:
            print("[OK] Successfully accessed 'Users' worksheet")
            print(f"   Worksheet has {worksheet.row_count} rows")
            return True
        else:
            print("[ERROR] Could not access 'Users' worksheet")
            print("   Make sure the Google Sheet is shared with the service account")
            return False
    except Exception as e:
        print(f"[ERROR] Worksheet access error: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Check that credentials.json is valid")
        print("2. Verify the Google Sheet is shared with the service account email")
        print("3. Make sure the service account has 'Editor' permissions")
        return False

if __name__ == "__main__":
    success = test_connection()
    if success:
        print("\n[SUCCESS] Connection test passed! You can now create users.")
    else:
        print("\n[FAILED] Connection test failed. Please fix the issues above.")



"""
Get the service account email from credentials.json
"""
import json
import os
from config import GOOGLE_CREDENTIALS_FILE

def get_service_account_email():
    """Extract service account email from credentials"""
    if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
        print(f"[ERROR] {GOOGLE_CREDENTIALS_FILE} not found!")
        return None
    
    try:
        with open(GOOGLE_CREDENTIALS_FILE, 'r') as f:
            creds = json.load(f)
            email = creds.get('client_email', 'Not found')
            print(f"Service Account Email: {email}")
            print("\nCopy this email and share your Google Sheet with it:")
            print(f"  {email}")
            print("\nSteps:")
            print("1. Open your Google Sheet")
            print("2. Click 'Share' button")
            print("3. Paste the email above")
            print("4. Set permission to 'Editor'")
            print("5. Click 'Share'")
            return email
    except Exception as e:
        print(f"[ERROR] Could not read credentials: {str(e)}")
        return None

if __name__ == "__main__":
    get_service_account_email()


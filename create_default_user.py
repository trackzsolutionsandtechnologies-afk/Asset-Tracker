"""
Create a default admin user for testing
Run: python create_default_user.py
Or: python create_default_user.py username password email
"""
import bcrypt
import sys
import os
# Suppress streamlit warnings when running outside streamlit
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
from google_sheets import append_data, read_data
from config import SHEETS

def create_default_user(username="admin", password="admin123", email="admin@example.com", role="admin"):
    """Create a default user in the system"""
    print(f"Creating user: {username}")
    
    # Check if user already exists
    try:
        df = read_data(SHEETS["users"])
        if not df.empty and username in df["Username"].values:
            print(f"User '{username}' already exists!")
            return False
    except Exception as e:
        print(f"Warning: Could not check existing users: {str(e)}")
    
    # Hash password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Add user to Google Sheet
    if append_data(SHEETS["users"], [username, hashed_password, email, role]):
        print(f"[SUCCESS] User '{username}' created successfully!")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Email: {email}")
        print(f"   Role: {role}")
        print("\n[IMPORTANT] Change the default password after first login!")
        return True
    else:
        print("[ERROR] Failed to create user. Please check your Google Sheets connection.")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Use command line arguments
        username = sys.argv[1] if len(sys.argv) > 1 else "admin"
        password = sys.argv[2] if len(sys.argv) > 2 else "admin123"
        email = sys.argv[3] if len(sys.argv) > 3 else "admin@example.com"
        role = sys.argv[4] if len(sys.argv) > 4 else "admin"
        create_default_user(username, password, email, role)
    else:
        # Create default admin user
        print("Creating default admin user...")
        print("Default credentials:")
        print("  Username: admin")
        print("  Password: admin123")
        print("\nTo create a custom user, run:")
        print("  python create_default_user.py username password email role")
        print()
        create_default_user()


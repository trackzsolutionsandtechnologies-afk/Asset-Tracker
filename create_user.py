"""
Helper script to create the first user in the system
Run this script to create an initial admin user
"""
import bcrypt
from google_sheets import append_data
from config import SHEETS

def create_first_user():
    """Create the first user in the system"""
    print("Creating first user...")
    
    username = input("Enter username: ")
    password = input("Enter password: ")
    email = input("Enter email: ")
    role = input("Enter role (default: admin): ") or "admin"
    
    # Hash password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Add user to Google Sheet
    if append_data(SHEETS["users"], [username, hashed_password, email, role]):
        print(f"User '{username}' created successfully!")
        print(f"Role: {role}")
    else:
        print("Failed to create user. Please check your Google Sheets connection.")

if __name__ == "__main__":
    create_first_user()



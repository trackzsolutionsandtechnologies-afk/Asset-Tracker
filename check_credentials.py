"""
Quick script to check if credentials are set up correctly
"""
import os
import json

print("Checking Google Sheets credentials setup...")
print()

# Check credentials.json file
credentials_file = "credentials.json"
if os.path.exists(credentials_file):
    print(f"[OK] Found credentials.json at: {os.path.abspath(credentials_file)}")
    try:
        with open(credentials_file, 'r') as f:
            creds = json.load(f)
            if "type" in creds and creds["type"] == "service_account":
                print(f"[OK] Valid service account credentials")
                print(f"   Project ID: {creds.get('project_id', 'N/A')}")
                print(f"   Client Email: {creds.get('client_email', 'N/A')}")
            else:
                print("[ERROR] Invalid credentials format")
    except Exception as e:
        print(f"[ERROR] Error reading credentials.json: {str(e)}")
else:
    print(f"[ERROR] credentials.json not found at: {os.path.abspath(credentials_file)}")
    print("   Please place your credentials.json file in the project root directory")

print()
print("Checking secrets.toml...")
secrets_file = ".streamlit/secrets.toml"
if os.path.exists(secrets_file):
    print(f"[OK] Found secrets.toml at: {os.path.abspath(secrets_file)}")
else:
    print(f"[WARNING] secrets.toml not found (optional)")

print()
print("Setup complete!" if os.path.exists(credentials_file) else "Please set up credentials.json")


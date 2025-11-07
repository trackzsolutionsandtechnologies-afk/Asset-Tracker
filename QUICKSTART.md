# Quick Start Guide

## Prerequisites
- Python 3.8 or higher
- Google Cloud account (for Google Sheets API access)

## Installation Steps

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Google Sheets Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Google Sheets API
   - Google Drive API
4. Create a Service Account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Give it a name (e.g., "asset-tracker")
   - Click "Create and Continue"
   - Skip role assignment, click "Continue"
   - Click "Done"
5. Create a key for the service account:
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Select JSON format
   - Download the JSON file
6. Rename the downloaded file to `credentials.json` and place it in the project root
7. Share your Google Sheet with the service account:
   - Open your Google Sheet: https://docs.google.com/spreadsheets/d/1kFlJLYC6I7NojaXr2UUX68Al4SO76bDlr-ojBl1mvZo
   - Click "Share" button
   - Add the service account email (found in credentials.json as `client_email`)
   - Give it "Editor" access
   - Click "Send"

### 3. Create Your First User

Run the user creation script:
```bash
python create_user.py
```

Enter:
- Username: (your choice)
- Password: (your choice)
- Email: (your email)
- Role: admin (or leave blank for default)

### 4. Run the Application

```bash
streamlit run streamlit_app.py
```

The application will open in your default web browser at `http://localhost:8501`

### 5. Login

Use the username and password you created in step 3 to log in.

## First Steps After Login

1. **Add Locations**: Go to "Location" and add your locations
2. **Add Suppliers**: Go to "Supplier" and add suppliers
3. **Add Categories**: Go to "Category" and add asset categories
4. **Add Assets**: Go to "Asset Master" and start adding assets
5. **View Dashboard**: Check the "Dashboard" for visualizations

## Features Overview

- **Dashboard**: View key metrics and charts
- **Location**: Manage locations and departments
- **Supplier**: Manage suppliers
- **Category**: Organize assets by categories and subcategories
- **Asset Master**: Add, edit, and manage assets with automatic barcode generation
- **Asset Transfer**: Track asset transfers between locations
- **Scan Barcode**: Search assets by barcode or name
- **Print Barcodes**: Generate printable barcode sheets for multiple assets

## Troubleshooting

### "Credentials not found" error
- Make sure `credentials.json` is in the project root directory
- Verify the file name is exactly `credentials.json` (case-sensitive)

### "Permission denied" error
- Make sure you shared the Google Sheet with the service account email
- Verify the service account has "Editor" access (not just "Viewer")

### "Sheet not found" error
- The application will automatically create missing sheets
- Make sure the service account has permission to create sheets

### Import errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Try upgrading pip: `pip install --upgrade pip`

## Need Help?

Check the main README.md for more detailed information.

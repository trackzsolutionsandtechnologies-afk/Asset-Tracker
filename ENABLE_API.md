# Enable Google Sheets API - REQUIRED STEP

## ⚠️ Important: API Not Enabled

The Google Sheets API needs to be enabled in your Google Cloud project before the application can work.

## Quick Fix

**Click this link to enable the API:**
👉 https://console.developers.google.com/apis/api/sheets.googleapis.com/overview?project=926605619385

Or follow these steps:

### Step 1: Enable Google Sheets API

1. Go to: https://console.developers.google.com/apis/api/sheets.googleapis.com/overview?project=926605619385
2. Click the **"ENABLE"** button
3. Wait for the API to be enabled (usually takes a few seconds)

### Step 2: Enable Google Drive API

1. Go to: https://console.developers.google.com/apis/api/drive.googleapis.com/overview?project=926605619385
2. Click the **"ENABLE"** button
3. Wait for the API to be enabled

### Step 3: Verify

After enabling both APIs, run:
```bash
python check_sheet_access.py
```

You should see:
- `[OK] Spreadsheet opened successfully`
- `[OK] 'Users' worksheet created successfully` (if it doesn't exist)

### Step 4: Create Your First User

Once the APIs are enabled, create your first user:
```bash
python create_default_user.py
```

## Why This Is Needed

The Google Sheets API allows the application to:
- Read data from your Google Sheet
- Write data to your Google Sheet
- Create new worksheets
- Update existing data

Without it enabled, the application cannot access your Google Sheet.

## After Enabling

1. ✅ Enable Google Sheets API
2. ✅ Enable Google Drive API  
3. ✅ Share Google Sheet with service account (if not done already)
4. ✅ Test connection: `python check_sheet_access.py`
5. ✅ Create user: `python create_default_user.py`
6. ✅ Run app: `streamlit run streamlit_app.py`

---

**Once you've enabled the APIs, run the check script again to verify everything works!**



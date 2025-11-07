# Setup Guide - Next Steps

## ✅ Step 1: Dependencies Installed
All Python packages have been successfully installed!

## 🔑 Step 2: Google Sheets Credentials Setup

You need to set up Google Sheets API credentials to enable the application to read and write to your Google Sheet.

### Option A: Quick Setup (Recommended)

1. **Go to Google Cloud Console**: https://console.cloud.google.com/

2. **Create or Select a Project**:
   - Click on the project dropdown at the top
   - Click "New Project" or select an existing one
   - Give it a name (e.g., "Asset Tracker")

3. **Enable APIs**:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API" and enable it
   - Search for "Google Drive API" and enable it

4. **Create Service Account**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Name it "asset-tracker-service"
   - Click "Create and Continue"
   - Skip role assignment (click "Continue")
   - Click "Done"

5. **Create Key**:
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Select "JSON" format
   - Click "Create"
   - The JSON file will download automatically

6. **Place Credentials File**:
   - Rename the downloaded file to `credentials.json`
   - Move it to your project folder: `C:\Users\tonyc\OneDrive - TZ\PUBLISHED REPORTS\Development\AssetTracker\`

7. **Share Google Sheet**:
   - Open your Google Sheet: https://docs.google.com/spreadsheets/d/1kFlJLYC6I7NojaXr2UUX68Al4SO76bDlr-ojBl1mvZo
   - Click the "Share" button (top right)
   - Open the `credentials.json` file and find the `client_email` field (looks like: `xxx@xxx.iam.gserviceaccount.com`)
   - Copy that email address
   - Paste it in the "Share" dialog
   - Set permission to "Editor"
   - Uncheck "Notify people" (optional)
   - Click "Share"

## 👤 Step 3: Create Your First User

Once credentials are set up, create your first admin user:

```bash
python create_user.py
```

Enter:
- Username: (choose a username)
- Password: (choose a secure password)
- Email: (your email address)
- Role: admin (or press Enter for default)

## 🚀 Step 4: Run the Application

```bash
streamlit run streamlit_app.py
```

The application will open automatically in your browser at `http://localhost:8501`

## 📝 Step 5: Login and Start Using

1. Login with the username and password you created
2. Start by adding:
   - Locations (Location)
   - Suppliers (Supplier)
   - Categories (Category)
   - Assets (Asset Master)

## ⚠️ Important Notes

- **Without credentials.json**: The app will show warnings but you can still view the structure
- **With credentials.json**: Full functionality including adding, editing, and deleting records
- The app will automatically create the required sheets/tabs in your Google Sheet if they don't exist

## 🆘 Troubleshooting

### "Credentials not found" warning
- Make sure `credentials.json` is in the project root folder
- Check the file name is exactly `credentials.json` (case-sensitive)

### "Permission denied" error
- Verify you shared the Google Sheet with the service account email
- Make sure the service account has "Editor" access (not "Viewer")

### Can't find service account email
- Open `credentials.json` in a text editor
- Look for the `"client_email"` field
- Copy that email address (it ends with `.iam.gserviceaccount.com`)

## 🎯 What's Next?

After setup, you can:
1. Add your locations and departments
2. Add suppliers
3. Create asset categories
4. Start adding assets with automatic barcode generation
5. Use the barcode scanner to find assets
6. Print barcode labels for your assets
7. Track asset transfers between locations

Happy tracking! 📦



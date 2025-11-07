# Next Steps - Getting Started

## Current Status

✅ **Dependencies Installed** - All Python packages are ready  
✅ **Application Created** - All features are implemented  
⚠️ **Google Sheets Setup** - Needs verification  

## Immediate Next Steps

### Step 1: Test Google Sheets Connection

Run the connection test:
```bash
python test_connection.py
```

This will check if:
- Your `credentials.json` file is valid
- The Google Sheet is accessible
- The service account has proper permissions

### Step 2: Fix Connection Issues (if any)

If the test fails, check:

1. **Credentials File**:
   - Make sure `credentials.json` is in the project folder
   - Verify it's a valid JSON file from Google Cloud Console

2. **Google Sheet Sharing**:
   - Open your Google Sheet: https://docs.google.com/spreadsheets/d/1kFlJLYC6I7NojaXr2UUX68Al4SO76bDlr-ojBl1mvZo
   - Click "Share" button
   - Open `credentials.json` and find the `client_email` field
   - Copy that email (looks like: `xxx@xxx.iam.gserviceaccount.com`)
   - Share the sheet with that email with "Editor" permissions

### Step 3: Create Your First User

Once connection is working, create a user:

**Option A: Default Admin User**
```bash
python create_default_user.py
```
This creates:
- Username: `admin`
- Password: `admin123`

**Option B: Custom User**
```bash
python create_default_user.py your_username your_password your_email admin
```

### Step 4: Access the Application

The application should already be running. If not, start it:

```bash
streamlit run streamlit_app.py
```

Then:
1. Open your browser to `http://localhost:8501`
2. Login with your credentials
3. Start using the application!

## What to Do After Login

### 1. Set Up Master Data (Recommended Order)

1. **Locations** → Add your locations and departments
2. **Suppliers** → Add your suppliers
3. **Categories** → Create asset categories
4. **Sub Categories** → Add subcategories under each category

### 2. Start Adding Assets

1. Go to **Asset Master**
2. Click **Add New Asset**
3. Fill in the form (Asset ID is auto-generated)
4. Save the asset

### 3. Explore Features

- **Dashboard**: View analytics and charts
- **Scan Barcode**: Search for assets by barcode
- **Print Barcodes**: Generate printable barcode labels
- **Asset Transfer**: Track asset movements

## Quick Reference

| Task | Command |
|------|---------|
| Test Connection | `python test_connection.py` |
| Create Default User | `python create_default_user.py` |
| Create Custom User | `python create_default_user.py username password email role` |
| Run Application | `streamlit run streamlit_app.py` |

## Troubleshooting

### Application won't start
- Make sure port 8501 is not in use
- Check if Streamlit is installed: `python -m pip list | findstr streamlit`

### Can't login
- Verify user was created successfully
- Check Google Sheet "Users" tab has your user
- Try creating user again

### Data not saving
- Verify Google Sheets connection
- Check service account has "Editor" permissions
- Run `python test_connection.py` to diagnose

### Sheets not appearing
- The app creates sheets automatically
- Check your Google Sheet for new tabs
- Refresh the application

## Need Help?

- Check `README.md` for detailed documentation
- Check `SETUP_GUIDE.md` for setup instructions
- Check `QUICKSTART.md` for quick start guide

## Default Login Credentials

After running `create_default_user.py`:
- **Username**: admin
- **Password**: admin123

⚠️ **IMPORTANT**: Change the password after first login!

---

**You're all set! Start by running the connection test and then create your first user.**



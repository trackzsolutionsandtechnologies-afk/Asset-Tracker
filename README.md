# Asset Tracker Web Application

A comprehensive asset tracking system built with Streamlit and Google Sheets as the database.

## Features

- 🔐 **User Authentication**: Secure login with username/password and forgot password functionality
- 📊 **Dashboard**: Visual analytics with charts and key metrics
- 📍 **Location Management**: Add, edit, and manage locations
- 🏢 **Supplier Management**: Manage supplier information
- 📂 **Category Management**: Organize assets by categories and subcategories
- 📦 **Asset Master**: Complete asset management with barcode generation
- 🚚 **Asset Transfer**: Track asset transfers between locations
- 🔍 **Barcode Scanner**: Search and scan assets by barcode
- 🖨️ **Barcode Printing**: Print multiple barcodes at once

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Sheets Setup

Your Google Sheet is already configured: `1kFlJLYC6I7NojaXr2UUX68Al4SO76bDlr-ojBl1mvZo`

To enable full functionality (read and write):

1. Create a Google Cloud Project at https://console.cloud.google.com/
2. Enable Google Sheets API and Google Drive API
3. Create a Service Account and download the credentials JSON file
4. Rename the credentials file to `credentials.json` and place it in the project root
5. Share your Google Sheet with the service account email (found in credentials.json - it looks like `xxx@xxx.iam.gserviceaccount.com`)

**Important**: The service account email must be given "Editor" access to your Google Sheet for the application to work properly.

### 3. Google Sheet Structure

The application will automatically create the following sheets if they don't exist:
- **Users**: Username, Password, Email, Role
- **Locations**: Location ID, Location Name, Department
- **Suppliers**: Supplier ID, Supplier Name
- **Categories**: Category ID, Category Name
- **SubCategories**: SubCategory ID, Category ID, SubCategory Name
- **Assets**: Asset ID, Asset Name, Category, Sub Category, Model/Serial No, Purchase Date, Purchase Cost, Supplier, Location, Assigned To, Condition, Status, Remarks, Attachment
- **Transfers**: Transfer ID, Asset ID, From Location, To Location, Date, Approved By
- **PasswordResets**: Username, Reset Token, Expiry

### 4. Create Initial User

You can use the provided script to create your first user:

```bash
python create_user.py
```

This will prompt you for username, password, email, and role. Make sure your Google Sheets credentials are set up before running this script.

Alternatively, you can manually add a user to the Google Sheet. The password should be hashed using bcrypt:

```python
import bcrypt
password = "your_password"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
# Add to Users sheet: username, hashed_password, email, role
```

### 5. Run the Application

```bash
streamlit run streamlit_app.py
```

## Usage

1. **Login**: Use your username and password to access the system
2. **Dashboard**: View key metrics and visualizations
3. **Forms**: Use the navigation menu to access different forms
4. **Barcode Scanner**: Enter or scan barcodes to find assets
5. **Print Barcodes**: Select multiple assets and generate printable barcode sheets

## Notes

- The Google Sheet ID is configured in `config.py`
- All data is stored in Google Sheets
- Barcodes are generated automatically for new assets
- Asset transfers automatically update asset locations

## Troubleshooting

- **Authentication Error**: Make sure `credentials.json` is in the project root and the service account has access to the Google Sheet
- **Sheet Not Found**: The application will create missing sheets automatically
- **Import Errors**: Make sure all dependencies are installed using `pip install -r requirements.txt`

# How to Create a User for Login

Since you're getting "Invalid username or password", you need to create a user first. Here are two methods:

## Method 1: Create User via Google Sheet (Easiest)

1. **Open your Google Sheet**: https://docs.google.com/spreadsheets/d/1kFlJLYC6I7NojaXr2UUX68Al4SO76bDlr-ojBl1mvZo

2. **Find or create the "Users" sheet**:
   - If it doesn't exist, create a new sheet named "Users"
   - Add these column headers in row 1: `Username`, `Password`, `Email`, `Role`

3. **Create a password hash**:
   - You can use this Python code to generate a hash:
   ```python
   import bcrypt
   password = "admin123"  # Your desired password
   hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
   print(hashed)
   ```

4. **Add a user row**:
   - Username: `admin`
   - Password: (paste the hashed password from step 3)
   - Email: `admin@example.com`
   - Role: `admin`

## Method 2: Run Script Locally (If you have Python)

1. Make sure you have `credentials.json` locally
2. Run:
   ```bash
   python create_default_user.py
   ```
   This will create a default user:
   - Username: `admin`
   - Password: `admin123`

## Method 3: Use Python in Streamlit Cloud (Temporary)

You can temporarily add this code to your app to create a user, then remove it:

```python
# Temporary code to create user - add to app.py temporarily
import bcrypt
from google_sheets import append_data
from config import SHEETS

def create_admin_user():
    username = "admin"
    password = "admin123"
    email = "admin@example.com"
    role = "admin"
    
    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Add to Users sheet
    append_data(SHEETS["users"], [username, hashed_password, email, role])
    st.success(f"User '{username}' created with password '{password}'")

# Call this once, then remove the code
if st.button("Create Admin User (One-time)"):
    create_admin_user()
```

## Default Credentials (if using create_default_user.py)

- **Username**: `admin`
- **Password**: `admin123`

**Important**: Change the password after first login!



# Fixing "Invalid username or password" Issue

## Common Causes

### 1. Password Not Hashed with bcrypt
If you manually added a user to the Google Sheet, the password might be stored as plain text instead of a bcrypt hash.

**Solution**: The password MUST be hashed using bcrypt.

### 2. Column Names Don't Match
The sheet must have these exact column names (case-sensitive):
- `Username` (not `username` or `user`)
- `Password` (not `password` or `pass`)
- `Email` (optional)
- `Role` (optional)

### 3. Extra Whitespace
There might be extra spaces in the username or password.

## How to Fix

### Option 1: Use the App to Create User (Recommended)
1. Click "Create Admin User (One-time setup)" in the login page
2. This will create a properly formatted user with hashed password

### Option 2: Fix Existing User in Google Sheet

1. **Open your Google Sheet**: https://docs.google.com/spreadsheets/d/1kFlJLYC6I7NojaXr2UUX68Al4SO76bDlr-ojBl1mvZo

2. **Check the "Users" sheet structure**:
   - Row 1 should have headers: `Username`, `Password`, `Email`, `Role`
   - Make sure there are no extra spaces

3. **Hash the password properly**:
   - Run this Python code locally:
   ```python
   import bcrypt
   password = "your_password_here"  # The password you want to use
   hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
   print(hashed)
   ```
   - Copy the hashed password (it will look like: `$2b$12$...`)
   - Replace the password in the Google Sheet with this hash

4. **Verify the username**:
   - Make sure there are no extra spaces before/after the username
   - Username matching is case-insensitive, but it's best to be consistent

### Option 3: Delete and Recreate User

1. Delete the existing user row from the Google Sheet
2. Use the "Create Admin User" button in the app to create a new one

## Verify Your Sheet Structure

Your "Users" sheet should look like this:

| Username | Password | Email | Role |
|----------|----------|-------|------|
| admin | $2b$12$... | admin@example.com | admin |

**Important**:
- Column names must match exactly (case-sensitive)
- Password must be a bcrypt hash (starts with `$2b$` or `$2a$`)
- No extra spaces in cells

## Test Login

After fixing:
1. Try logging in with the username and password
2. If it still doesn't work, check the Streamlit Cloud logs for errors
3. Make sure the service account has access to the Google Sheet


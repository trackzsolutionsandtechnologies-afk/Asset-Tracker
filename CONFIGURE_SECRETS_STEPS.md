# How to Configure Secrets in Streamlit Cloud

## Step-by-Step Instructions

### Step 1: Get Your Credentials JSON

1. Open your local `credentials.json` file
2. Copy the entire JSON content
3. You'll need to paste it into Streamlit Cloud secrets

### Step 2: Access Streamlit Cloud Secrets

1. Go to https://share.streamlit.io/
2. Sign in with your GitHub account
3. Find your app: `asset-tracker-sfsu9uucxfdaqgksb5napm`
4. Click on your app
5. Click "⚙️ Settings" (or "Manage app" → "⚙️ Settings")
6. Click "Secrets" in the left sidebar

### Step 3: Add Secrets

Paste the following into the secrets editor, replacing the placeholder values with your actual credentials:

```toml
[google_sheets]
sheet_id = "1kFlJLYC6I7NojaXr2UUX68Al4SO76bDlr-ojBl1mvZo"
credentials_json = '''
{
  "type": "service_account",
  "project_id": "YOUR_PROJECT_ID",
  "private_key_id": "YOUR_PRIVATE_KEY_ID",
  "private_key": "-----BEGIN PRIVATE KEY-----\\nYOUR_PRIVATE_KEY_HERE\\n-----END PRIVATE KEY-----\\n",
  "client_email": "YOUR_SERVICE_ACCOUNT_EMAIL@YOUR_PROJECT.iam.gserviceaccount.com",
  "client_id": "YOUR_CLIENT_ID",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/YOUR_SERVICE_ACCOUNT_EMAIL%40YOUR_PROJECT.iam.gserviceaccount.com"
}
'''
```

### Step 4: Important - Format the Private Key

**CRITICAL**: In the `private_key` field, you must replace actual newlines with `\\n` (double backslash + n).

**Example:**
- **Original** (from credentials.json):
  ```
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n"
  ```

- **For Streamlit Cloud** (with escaped newlines):
  ```
  "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\\n-----END PRIVATE KEY-----\\n"
  ```

### Step 5: Save and Deploy

1. Click "Save" at the bottom of the secrets editor
2. Streamlit Cloud will automatically redeploy your app
3. Wait for the deployment to complete
4. Refresh your app - the credentials warning should be gone!

## Quick Method: Copy Entire JSON

Alternatively, you can copy your entire `credentials.json` content and paste it directly, but you still need to:
1. Wrap it in triple quotes: `''' ... '''`
2. Replace newlines in `private_key` with `\\n`

## Verify It Works

After saving secrets:
1. Check the app logs - there should be no credential errors
2. Try logging in to the app
3. The app should be able to access Google Sheets

## Troubleshooting

### Still seeing "Credentials not found"?
- Verify secrets are saved in Streamlit Cloud
- Check that `credentials_json` is properly formatted
- Ensure `private_key` has `\\n` for newlines (double backslash)
- Check the app logs for specific errors

### Getting JSON parsing errors?
- Make sure the JSON is valid
- Check that all quotes are properly escaped
- Verify the triple quotes `'''` are around the JSON

### App still not working?
- Check Streamlit Cloud logs for specific errors
- Verify the service account email has access to the Google Sheet
- Ensure Google Sheets API and Drive API are enabled


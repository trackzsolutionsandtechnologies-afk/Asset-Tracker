# Debugging Secrets in Streamlit Cloud

## Quick Check: Are Secrets Actually Saved?

1. Go to https://share.streamlit.io/
2. Open your app: `asset-tracker-sfsu9uucxfdaqgksb5napm`
3. Click "⚙️ Settings" → "Secrets"
4. **Verify** you can see your secrets there

## Common Issues

### Issue 1: Secrets Not Saved
- Make sure you clicked "Save" after pasting secrets
- Check that the secrets editor shows your configuration

### Issue 2: Format Issues
The secrets should look EXACTLY like this (with your actual values):

```toml
[google_sheets]
sheet_id = "YOUR_SHEET_ID_HERE"
credentials_json = '''
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\\nYOUR_PRIVATE_KEY_HERE\\n-----END PRIVATE KEY-----\\n",
  "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
'''
```

**Important points:**
- No extra spaces before `[google_sheets]`
- `credentials_json` uses triple single quotes: `'''`
- `private_key` has `\\n` (double backslash + n) for newlines
- The JSON is properly formatted

### Issue 3: App Not Reading Secrets
- After saving secrets, the app should automatically redeploy
- Wait 1-2 minutes for redeployment
- Clear your browser cache and refresh
- Check the Streamlit Cloud logs for errors

## Test: Create User First

Even if credentials show a warning, try creating a user:
1. Click "Create Admin User (One-time setup)"
2. Click "Create Default Admin User"
3. If it works, credentials are actually working (just the warning is showing)
4. If it fails, check the error message

## Verify Service Account Access

Make sure the service account has access:
1. Open: https://docs.google.com/spreadsheets/d/1kFlJLYC6I7NojaXr2UUX68Al4SO76bDlr-ojBl1mvZo
2. Click "Share"
3. Add: `asset-tracker@asset-tracker-477410.iam.gserviceaccount.com`
4. Give "Editor" access
5. Click "Send"


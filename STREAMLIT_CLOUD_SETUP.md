# Streamlit Cloud Deployment Setup

## Quick Setup Guide

### Step 1: Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Sign in with your GitHub account
3. Click "New app"
4. Select repository: `trackzsolutionsandtechnologies-afk/Asset-Tracker`
5. Set **Main file path**: `app.py`
6. Click "Deploy!"

### Step 2: Configure Secrets (CRITICAL)

After deployment, you **MUST** configure secrets for the app to work:

1. In Streamlit Cloud, go to your app dashboard
2. Click "⚙️ Settings" (or "Manage app" → "⚙️ Settings")
3. Click "Secrets" in the left sidebar
4. Paste the following configuration:

```toml
[google_sheets]
sheet_id = "1kFlJLYC6I7NojaXr2UUX68Al4SO76bDlr-ojBl1mvZo"
credentials_json = '''
{
  "type": "service_account",
  "project_id": "asset-tracker-477410",
  "private_key_id": "YOUR_PRIVATE_KEY_ID_FROM_CREDENTIALS_JSON",
  "private_key": "-----BEGIN PRIVATE KEY-----\\nYOUR_PRIVATE_KEY_HERE\\n-----END PRIVATE KEY-----\\n",
  "client_email": "asset-tracker@asset-tracker-477410.iam.gserviceaccount.com",
  "client_id": "YOUR_CLIENT_ID",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/asset-tracker%40asset-tracker-477410.iam.gserviceaccount.com"
}
'''
```

**How to get the values:**
1. Open your local `credentials.json` file
2. Copy the entire JSON content
3. Replace the values in the secrets above
4. **Important**: In the `private_key` field, replace actual newlines with `\\n`

### Step 3: Verify Deployment

1. After adding secrets, Streamlit Cloud will automatically redeploy
2. Check the logs to ensure no errors
3. Access your app at the provided URL
4. Login with your credentials

## Troubleshooting

### Health Check Error
- **Cause**: App not starting or secrets not configured
- **Fix**: 
  1. Check that secrets are properly configured
  2. Verify `app.py` is set as the main file
  3. Check deployment logs for errors

### Credentials Not Found
- **Cause**: Secrets not set or incorrectly formatted
- **Fix**: 
  1. Verify secrets are saved in Streamlit Cloud
  2. Check that `credentials_json` contains valid JSON
  3. Ensure private_key has `\\n` for newlines

### Import Errors
- **Cause**: Missing dependencies
- **Fix**: Verify `requirements.txt` is in the repository

## Important Notes

- ✅ Main file: `app.py`
- ✅ Secrets must be configured in Streamlit Cloud dashboard
- ✅ Never commit `credentials.json` to git
- ✅ Use `credentials_json` in secrets (not file path)
- ✅ The app will automatically read from Streamlit Cloud secrets

## Your App URL

After successful deployment, your app will be available at:
`https://YOUR_APP_NAME.streamlit.app`



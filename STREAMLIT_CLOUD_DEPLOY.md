# Streamlit Cloud Deployment Guide

## Prerequisites

1. **GitHub Repository**: Your code should be pushed to GitHub
   - Repository: `https://github.com/trackzsolutionsandtechnologies-afk/Asset-Tracker`

2. **Streamlit Cloud Account**: Sign up at https://streamlit.io/cloud

## Deployment Steps

### Step 1: Connect Repository to Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Sign in with your GitHub account
3. Click "New app"
4. Select your repository: `trackzsolutionsandtechnologies-afk/Asset-Tracker`
5. Set the **Main file path**: `app.py`
6. Click "Deploy!"

### Step 2: Configure Secrets in Streamlit Cloud (CRITICAL!)

**⚠️ IMPORTANT**: Without secrets, the app will not work! You must configure this.

1. In your Streamlit Cloud app dashboard, click "⚙️ Settings" (or "Manage app" → "⚙️ Settings")
2. Click "Secrets" in the sidebar
3. Add the following secrets (replace with your actual values from credentials.json):

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

**How to get the values from your credentials.json:**
1. Open your local `credentials.json` file
2. Copy each field value
3. Replace the placeholders in the secrets above
4. **CRITICAL**: In the `private_key` field, replace actual newlines with `\\n` (double backslash + n)
   - Example: `"-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n"` 
   - Becomes: `"-----BEGIN PRIVATE KEY-----\\nMIIE...\\n-----END PRIVATE KEY-----\\n"`

**Alternative: Copy entire JSON as string**
If you prefer, you can copy your entire `credentials.json` content and paste it directly, but you still need to escape newlines in the private_key field.

### Step 3: Verify Deployment

1. After adding secrets, Streamlit Cloud will automatically redeploy
2. Check the logs in the Streamlit Cloud dashboard
3. The app should be accessible at the provided URL
4. Login with your credentials (create a user first if needed)

## Troubleshooting

### Health Check Error / App Won't Start
- **Cause**: Secrets not configured or incorrectly formatted
- **Fix**: 
  1. Verify secrets are saved in Streamlit Cloud dashboard
  2. Check that `credentials_json` contains valid JSON
  3. Ensure `app.py` is set as the main file
  4. Check deployment logs for specific errors

### Credentials Not Found
- **Cause**: Secrets not set or incorrectly formatted
- **Fix**: 
  1. Verify secrets are saved in Streamlit Cloud
  2. Check that `credentials_json` contains valid JSON
  3. Ensure private_key has `\\n` for newlines (double backslash)
  4. Verify the JSON structure matches your credentials.json

### Google Sheets API errors
- **Cause**: Service account doesn't have access or APIs not enabled
- **Fix**: 
  1. Verify the service account email has "Editor" access to the Google Sheet
  2. Check that Google Sheets API and Drive API are enabled in Google Cloud Console
  3. Verify the service account email matches the one in credentials.json

### Rate limit errors
- **Cause**: Too many API requests
- **Fix**: 
  1. The app includes caching to reduce API calls
  2. Wait 60 seconds and refresh if you see rate limit errors
  3. Consider requesting a higher quota in Google Cloud Console

### Import Errors
- **Cause**: Missing dependencies
- **Fix**: 
  1. Verify `requirements.txt` is in the repository
  2. Check that all dependencies are listed correctly
  3. Check deployment logs for specific import errors

## Security Notes

- ✅ Never commit `credentials.json` to git
- ✅ Use Streamlit Cloud secrets for sensitive data
- ✅ The `secrets.toml.example` file is safe to commit
- ✅ Your actual `secrets.toml` should not be in the repository
- ✅ Secrets in Streamlit Cloud are encrypted and secure

## App URL

After successful deployment, your app will be available at:
`https://YOUR_APP_NAME.streamlit.app`

## Quick Checklist

- [ ] Code pushed to GitHub
- [ ] Repository connected to Streamlit Cloud
- [ ] Main file set to `app.py`
- [ ] Secrets configured in Streamlit Cloud dashboard
- [ ] credentials_json properly formatted with escaped newlines
- [ ] Service account has access to Google Sheet
- [ ] Google Sheets API and Drive API enabled
- [ ] App deployed and accessible
- [ ] Can login and use the application

## Support

If you encounter issues:
1. Check the Streamlit Cloud logs (most important!)
2. Verify all secrets are set correctly
3. Test locally first to ensure the app works
4. Check the GitHub repository for the latest code
5. Verify Google Cloud project settings

# Streamlit Cloud Troubleshooting Guide

## Common Errors and Solutions

### Error: "The service has encountered an error while checking the health of the Streamlit app"

This error typically means the app failed to start. Common causes:

#### 1. **Missing or Incorrect Secrets Configuration**

**Symptom**: App won't start, health check fails

**Solution**:
1. Go to Streamlit Cloud → Your App → Settings → Secrets
2. Verify secrets are configured correctly
3. Check the format matches `STREAMLIT_SECRETS_EXAMPLE.toml`
4. Ensure `credentials_json` is properly formatted with escaped newlines (`\\n`)

#### 2. **Import Errors**

**Symptom**: App crashes on startup, check logs for ImportError

**Solution**:
1. Verify `requirements.txt` is in the repository
2. Check that all dependencies are listed
3. Ensure Python version is compatible (3.8+)

#### 3. **Main File Path Incorrect**

**Symptom**: App can't find the entry point

**Solution**:
1. In Streamlit Cloud settings, verify "Main file path" is set to `app.py`
2. Ensure `app.py` exists in the repository root

#### 4. **Credentials JSON Format Error**

**Symptom**: App starts but shows "Credentials not found" error

**Solution**:
1. Verify `credentials_json` in secrets is valid JSON
2. Check that `private_key` has `\\n` for newlines (double backslash)
3. Ensure all required fields are present:
   - `type`: "service_account"
   - `project_id`
   - `private_key_id`
   - `private_key`
   - `client_email`
   - `client_id`
   - `auth_uri`
   - `token_uri`
   - `auth_provider_x509_cert_url`
   - `client_x509_cert_url`

#### 5. **Google Sheets API Access Issues**

**Symptom**: App starts but can't access Google Sheets

**Solution**:
1. Verify service account email has "Editor" access to the Google Sheet
2. Check that Google Sheets API and Drive API are enabled in Google Cloud Console
3. Verify the service account email matches the one in credentials.json

## How to Check Logs

1. Go to Streamlit Cloud dashboard
2. Click on your app
3. Click "Manage app" → "Logs"
4. Look for error messages or stack traces

## Quick Checklist

- [ ] Main file path is `app.py`
- [ ] `requirements.txt` is in repository
- [ ] Secrets are configured in Streamlit Cloud
- [ ] `credentials_json` is properly formatted
- [ ] `private_key` has `\\n` for newlines
- [ ] Service account has access to Google Sheet
- [ ] Google Sheets API and Drive API are enabled
- [ ] No syntax errors in code
- [ ] All imports are available in requirements.txt

## Testing Locally First

Before deploying to Streamlit Cloud, test locally:

1. Set up `secrets.toml` locally (in `.streamlit/` folder)
2. Run `streamlit run app.py`
3. Verify the app works locally
4. Then deploy to Streamlit Cloud

## Getting Help

If you're still having issues:

1. Check the Streamlit Cloud logs (most important!)
2. Verify all secrets are set correctly
3. Test locally first
4. Check the GitHub repository for latest code
5. Review `STREAMLIT_CLOUD_DEPLOY.md` for detailed setup instructions


# Credentials Setup Guide

## ⚠️ Important: For Streamlit Cloud

**DO NOT** commit `credentials.json` to GitHub! Use Streamlit Cloud secrets instead.

## For Local Development

If you want to test locally, you can place `credentials.json` in the project root:

1. **Get your credentials.json file** (from Google Cloud Console)
2. **Place it in the project root** (same folder as `app.py`)
3. **Make sure it's in .gitignore** (it already is)
4. **Never commit it to git!**

## For Streamlit Cloud Deployment

**Use Streamlit Cloud Secrets** (not a file):

1. Go to Streamlit Cloud → Your App → Settings → Secrets
2. Paste your credentials as shown in `STREAMLIT_SECRETS_EXAMPLE.toml`
3. The app will read from secrets automatically

## Why Not Use credentials.json in Cloud?

- ❌ Files in the repository are visible (security risk)
- ❌ Even in private repos, it's not best practice
- ❌ Streamlit Cloud can't access local files anyway
- ✅ Secrets are encrypted and secure
- ✅ Secrets are the recommended approach

## Current Status

Your `.gitignore` already excludes `credentials.json`, so if you add it locally for testing, it won't be committed to git.

## Next Steps

1. **For local testing**: Place `credentials.json` in project root (optional)
2. **For Streamlit Cloud**: Use secrets (required) - see `STREAMLIT_CLOUD_DEPLOY.md`



"""
Google OAuth utilities for authenticating end users to Google Drive.
"""
from __future__ import annotations

import json
from typing import Dict, Optional

import streamlit as st
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]

STORE_KEY = "drive_credentials_store"
STATE_KEY = "drive_oauth_states"


def _ensure_store() -> Dict[str, str]:
    if STORE_KEY not in st.session_state:
        st.session_state[STORE_KEY] = {}
    return st.session_state[STORE_KEY]


def _get_client_config() -> dict:
    oauth_section = st.secrets.get("google_oauth")
    if not oauth_section:
        raise RuntimeError(
            "Missing google_oauth configuration in Streamlit secrets."
        )

    redirect_uri = oauth_section.get("redirect_uri", "http://localhost:8501/")
    return {
        "web": {
            "client_id": oauth_section["client_id"],
            "client_secret": oauth_section["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }


def _create_flow(state: Optional[str] = None) -> Flow:
    config = _get_client_config()
    redirect_uri = config["web"]["redirect_uris"][0]
    flow = Flow.from_client_config(config, scopes=DRIVE_SCOPES, state=state)
    flow.redirect_uri = redirect_uri
    return flow


def _store_credentials(creds: Credentials, user_id: Optional[str]) -> None:
    creds_json = creds.to_json()
    store = _ensure_store()
    key = str(user_id or "default")
    store[key] = creds_json


def _load_credentials_from_state(user_id: Optional[str]) -> Optional[Credentials]:
    store = _ensure_store()
    key = str(user_id or "default")
    stored = store.get(key)
    if not stored:
        return None
    data = json.loads(stored)
    creds = Credentials.from_authorized_user_info(data, scopes=DRIVE_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _store_credentials(creds, user_id)
    if creds.valid:
        return creds
    return None


def get_drive_credentials(user_id: Optional[str] = None) -> Optional[Credentials]:
    """Ensure the user is authenticated with Google Drive and return credentials."""
    creds = _load_credentials_from_state(user_id)
    if creds:
        return creds

    params = st.experimental_get_query_params()
    states = st.session_state.setdefault(STATE_KEY, {})
    key = str(user_id or "default")
    stored_state = states.get(key)

    if "code" in params:
        flow = _create_flow(state=stored_state)
        flow.fetch_token(code=params["code"][0])
        creds = flow.credentials
        _store_credentials(creds, user_id)
        st.experimental_set_query_params()  # Clear query params
        st.success("Google Drive connected successfully.")
        return creds

    # No credentials yet – prompt the user to authorize
    flow = _create_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    states[key] = state
    st.info("Connect your Google Drive to upload attachments.")
    st.markdown(
        f'<a href="{auth_url}" target="_self" style="text-decoration: none;">'
        "Authorize Google Drive</a>",
        unsafe_allow_html=True,
    )
    return None


def disconnect_drive_credentials(user_id: Optional[str] = None) -> None:
    store = _ensure_store()
    key = str(user_id or "default")
    store.pop(key, None)
    states = st.session_state.get(STATE_KEY, {})
    states.pop(key, None)
    st.experimental_rerun()

"""
Google OAuth utilities for authenticating end users to Google Drive.
"""
from __future__ import annotations

import json
from typing import Optional

import streamlit as st
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


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


def _store_credentials(creds: Credentials) -> None:
    st.session_state["drive_credentials"] = creds.to_json()


def _load_credentials_from_state() -> Optional[Credentials]:
    stored = st.session_state.get("drive_credentials")
    if not stored:
        return None
    data = json.loads(stored)
    creds = Credentials.from_authorized_user_info(data, scopes=DRIVE_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _store_credentials(creds)
    if creds.valid:
        return creds
    return None


def get_drive_credentials() -> Optional[Credentials]:
    """Ensure the user is authenticated with Google Drive and return credentials."""
    creds = _load_credentials_from_state()
    if creds:
        return creds

    params = st.experimental_get_query_params()
    stored_state = st.session_state.get("drive_oauth_state")

    if "code" in params:
        flow = _create_flow(state=stored_state)
        flow.fetch_token(code=params["code"][0])
        creds = flow.credentials
        _store_credentials(creds)
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
    st.session_state["drive_oauth_state"] = state
    st.info("Connect your Google Drive to upload attachments.")
    st.markdown(f"[Authorize Google Drive]({auth_url})")
    return None


def disconnect_drive_credentials() -> None:
    st.session_state.pop("drive_credentials", None)
    st.session_state.pop("drive_oauth_state", None)
    st.experimental_rerun()

"""
Google OAuth utilities for authenticating end users to Google Drive.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

import streamlit as st
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from config import SHEETS, SESSION_KEYS
from google_sheets import (
    append_data,
    delete_data,
    ensure_sheet_headers,
    find_row,
    read_data,
    update_data,
)

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
DEFAULT_USER_ID = "default"
CREDENTIAL_HEADERS = ["Username", "Credentials", "Updated At"]


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


def _resolve_user_id(user_id: Optional[str]) -> str:
    if user_id:
        resolved = str(user_id).strip()
        if resolved:
            return resolved
    session_username_key = SESSION_KEYS.get("username")
    if session_username_key:
        session_value = st.session_state.get(session_username_key)
        if session_value:
            resolved = str(session_value).strip()
            if resolved:
                return resolved
    return DEFAULT_USER_ID


def _ensure_credentials_sheet() -> None:
    ensure_sheet_headers(SHEETS["drive_credentials"], CREDENTIAL_HEADERS)


def _persist_credentials(user_key: str, creds_json: str) -> None:
    _ensure_credentials_sheet()
    row_index = find_row(SHEETS["drive_credentials"], "Username", user_key)
    row_data = [user_key, creds_json, datetime.utcnow().isoformat()]
    if row_index is None:
        success = append_data(SHEETS["drive_credentials"], row_data)
    else:
        success = update_data(SHEETS["drive_credentials"], row_index, row_data)
    if not success:
        st.warning(
            "We connected to Google Drive but could not save the credential token. "
            "Please try again or contact support."
        )


def _load_credentials_from_sheet(user_key: str) -> Optional[str]:
    _ensure_credentials_sheet()
    df = read_data(SHEETS["drive_credentials"])
    if df.empty:
        return None
    if "Username" not in df.columns or "Credentials" not in df.columns:
        return None
    matches = df[df["Username"].astype(str) == user_key]
    if matches.empty:
        return None
    creds_value = matches.iloc[0].get("Credentials")
    if not creds_value:
        return None
    return str(creds_value)


def _store_credentials(creds: Credentials, user_id: Optional[str]) -> None:
    creds_json = creds.to_json()
    user_key = _resolve_user_id(user_id)
    st.session_state[f"drive_credentials::{user_key}"] = creds_json
    _persist_credentials(user_key, creds_json)


def _load_credentials_from_state(user_id: Optional[str]) -> Optional[Credentials]:
    user_key = _resolve_user_id(user_id)
    stored = st.session_state.get(f"drive_credentials::{user_key}")
    if not stored:
        stored = _load_credentials_from_sheet(user_key)
        if stored:
            st.session_state[f"drive_credentials::{user_key}"] = stored
    if not stored:
        return None
    data = json.loads(stored)
    creds = Credentials.from_authorized_user_info(data, scopes=DRIVE_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _store_credentials(creds, user_key)
    if creds.valid:
        return creds
    return None


def get_drive_credentials(user_id: Optional[str] = None) -> Optional[Credentials]:
    """Ensure the user is authenticated with Google Drive and return credentials."""
    creds = _load_credentials_from_state(user_id)
    if creds:
        return creds

    params = st.experimental_get_query_params()
    user_key = _resolve_user_id(user_id)
    stored_state = st.session_state.get(f"drive_oauth_state::{user_key}")

    if "code" in params:
        flow = _create_flow(state=stored_state)
        flow.fetch_token(code=params["code"][0])
        creds = flow.credentials
        _store_credentials(creds, user_key)
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
    st.session_state[f"drive_oauth_state::{user_key}"] = state
    st.info("Connect your Google Drive to upload attachments.")
    st.markdown(f"[Authorize Google Drive]({auth_url})")
    return None


def disconnect_drive_credentials(user_id: Optional[str] = None) -> None:
    user_key = _resolve_user_id(user_id)
    st.session_state.pop(f"drive_credentials::{user_key}", None)
    st.session_state.pop(f"drive_oauth_state::{user_key}", None)
    # Remove persisted credentials
    _ensure_credentials_sheet()
    row_index = find_row(SHEETS["drive_credentials"], "Username", user_key)
    if row_index is not None:
        success = delete_data(SHEETS["drive_credentials"], row_index)
        if not success:
            st.warning("Failed to remove stored Drive credentials from Google Sheets.")
    st.experimental_rerun()

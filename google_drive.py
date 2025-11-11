"""
Google Drive integration helpers
"""
from __future__ import annotations

import io
from typing import Optional

import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

from config import GOOGLE_DRIVE_FOLDER_ID
from google_sheets import get_google_client, get_cached_credentials

DRIVE_FILE_FIELDS = "id, name, webViewLink"


@st.cache_resource(show_spinner=False)
def get_drive_service():
    """Build and cache the Google Drive service using the gspread client's credentials."""
    client = get_google_client()
    if client is None:
        return None

    credentials = get_cached_credentials()
    if credentials is None:
        credentials = getattr(client, "auth", None)
    if credentials is None:
        st.error("Google credentials are not available. Please check configuration.")
        return None

    try:
        scoped = credentials.with_scopes(["https://www.googleapis.com/auth/drive"])
    except AttributeError:
        scoped = credentials

    return build("drive", "v3", credentials=scoped, cache_discovery=False)


def upload_file_to_drive(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    folder_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Upload a file to Google Drive and return metadata containing the shareable link.

    Returns:
        dict with keys  id, name, webViewLink  if successful, otherwise None.
    """
    service = get_drive_service()
    if service is None:
        st.error("Google Drive service is not available. Please check credentials.")
        return None

    if not folder_id:
        folder_id = GOOGLE_DRIVE_FOLDER_ID

    if not folder_id:
        st.error("No Google Drive folder ID configured.")
        return None

    media = MediaIoBaseUpload(
        io.BytesIO(file_bytes),
        mimetype=mime_type,
        resumable=True,
    )

    file_metadata = {
        "name": filename,
        "parents": [folder_id],
    }

    try:
        request = service.files().create(
            body=file_metadata,
            media_body=media,
            fields=DRIVE_FILE_FIELDS,
            supportsAllDrives=True,
        )

        drive_file = None
        while drive_file is None:
            status, drive_file = request.next_chunk()
            if status and hasattr(status, "progress"):
                st.write(f"Upload progress: {int(status.progress() * 100)}%")

        # Make file publicly readable via link
        service.permissions().create(
            fileId=drive_file["id"],
            body={"role": "reader", "type": "anyone"},
            supportsAllDrives=True,
        ).execute()

        # Refresh to include shareable links
        drive_file = (
            service.files()
            .get(fileId=drive_file["id"], fields=DRIVE_FILE_FIELDS, supportsAllDrives=True)
            .execute()
        )
        return drive_file
    except HttpError as exc:
        st.error(f"Error uploading file to Google Drive: {exc}")
        return None


"""
Downloads the live Google Sheet as an .xlsx so sheet_parser can read it
with openpyxl (openpyxl can't read Google Sheets directly).

Auth: a Google Cloud service account, JSON key stored in the
GOOGLE_SERVICE_ACCOUNT_JSON secret (see README). Share the sheet with
the service account's email address (Viewer is enough) before running.
"""

from __future__ import annotations

import io
import json
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def download_sheet_as_xlsx(sheet_id: str, dest_path: str) -> str:
    creds_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    creds_info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        creds_info, scopes=SCOPES
    )

    drive = build("drive", "v3", credentials=creds)
    request = drive.files().export_media(
        fileId=sheet_id,
        mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    with open(dest_path, "wb") as f:
        f.write(buf.getvalue())

    return dest_path

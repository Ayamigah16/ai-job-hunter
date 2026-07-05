"""Google Sheets auth + raw client construction.

Uses a service account JSON key (not OAuth) since this runs unattended — see
docs/adr/0001-stack-and-datastore.md and the README's Google Sheets setup
section for how to create one and share your spreadsheet with it.
"""

from __future__ import annotations

import gspread
from google.oauth2.service_account import Credentials

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class SheetsConfigError(Exception):
    """Raised when Google Sheets credentials/spreadsheet access can't be established."""


def get_gspread_client(credentials_path: str) -> gspread.Client:
    try:
        credentials = Credentials.from_service_account_file(credentials_path, scopes=_SCOPES)
    except (FileNotFoundError, ValueError) as exc:
        raise SheetsConfigError(
            f"Couldn't load Google service account credentials from {credentials_path!r}. "
            "See the README's Google Sheets setup section."
        ) from exc
    return gspread.authorize(credentials)


def open_spreadsheet(client: gspread.Client, spreadsheet_id: str) -> gspread.Spreadsheet:
    try:
        return client.open_by_key(spreadsheet_id)
    except gspread.exceptions.APIError as exc:
        raise SheetsConfigError(
            f"Couldn't open spreadsheet {spreadsheet_id!r} — check the id and that the "
            "spreadsheet is shared with the service account's client_email as an Editor."
        ) from exc

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
    # gspread's open_by_key doesn't just raise APIError - for a 403 it catches
    # that internally and re-raises the builtin PermissionError, and for a
    # 404 its own SpreadsheetNotFound. All three mean the same thing here:
    # wrong id, or the sheet isn't shared with the service account.
    sheet_errors = (
        gspread.exceptions.APIError,
        PermissionError,
        gspread.exceptions.SpreadsheetNotFound,
    )
    try:
        return client.open_by_key(spreadsheet_id)
    except sheet_errors as exc:
        raise SheetsConfigError(
            f"Couldn't open spreadsheet {spreadsheet_id!r} — check the id and that the "
            "spreadsheet is shared with the service account's client_email as an Editor."
        ) from exc

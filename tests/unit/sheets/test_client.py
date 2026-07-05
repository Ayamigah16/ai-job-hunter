from unittest.mock import MagicMock

import gspread
import pytest

from ai_job_hunter.sheets.client import SheetsConfigError, get_gspread_client, open_spreadsheet


def test_get_gspread_client_missing_file_raises_clear_error(tmp_path):
    missing_path = tmp_path / "does-not-exist.json"
    with pytest.raises(SheetsConfigError, match="Couldn't load Google service account"):
        get_gspread_client(str(missing_path))


def test_open_spreadsheet_wraps_api_error():
    client = MagicMock()
    client.open_by_key.side_effect = gspread.exceptions.APIError(MagicMock())

    with pytest.raises(SheetsConfigError, match="Couldn't open spreadsheet"):
        open_spreadsheet(client, "bad-id")


def test_open_spreadsheet_wraps_permission_error():
    """Regression test: gspread's open_by_key doesn't raise APIError for a
    403 - it catches that internally and re-raises the builtin
    PermissionError instead. This is what a real "sheet not shared with the
    service account" failure looks like in production."""
    client = MagicMock()
    client.open_by_key.side_effect = PermissionError()

    with pytest.raises(SheetsConfigError, match="Couldn't open spreadsheet"):
        open_spreadsheet(client, "bad-id")


def test_open_spreadsheet_wraps_spreadsheet_not_found():
    client = MagicMock()
    client.open_by_key.side_effect = gspread.exceptions.SpreadsheetNotFound()

    with pytest.raises(SheetsConfigError, match="Couldn't open spreadsheet"):
        open_spreadsheet(client, "bad-id")


def test_open_spreadsheet_success_passthrough():
    client = MagicMock()
    expected = MagicMock()
    client.open_by_key.return_value = expected

    assert open_spreadsheet(client, "good-id") is expected

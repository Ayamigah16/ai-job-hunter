import pytest

from ai_job_hunter.sheets.client import SheetsConfigError, get_gspread_client


def test_get_gspread_client_missing_file_raises_clear_error(tmp_path):
    missing_path = tmp_path / "does-not-exist.json"
    with pytest.raises(SheetsConfigError, match="Couldn't load Google service account"):
        get_gspread_client(str(missing_path))

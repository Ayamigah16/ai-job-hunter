from unittest.mock import MagicMock

import pytest

from ai_job_hunter.models import ATSType
from ai_job_hunter.registry import CompanyEntry
from ai_job_hunter.sheets.schema import OPEN_ROLES_COLUMNS, TARGET_COMPANIES_COLUMNS
from ai_job_hunter.sheets.writer import GoogleSheetsWriter, SheetSchemaError


def make_worksheet(headers, records):
    worksheet = MagicMock()
    worksheet.row_values.return_value = headers
    worksheet.get_all_records.return_value = records
    return worksheet


def make_spreadsheet(open_roles_ws=None, target_companies_ws=None):
    spreadsheet = MagicMock()
    spreadsheet.worksheet.side_effect = lambda name: {
        "Open Roles": open_roles_ws,
        "Target Companies": target_companies_ws,
    }[name]
    return spreadsheet


def test_sync_open_roles_raises_on_header_drift(make_scored_job):
    worksheet = make_worksheet(["Wrong", "Headers"], [])
    spreadsheet = make_spreadsheet(open_roles_ws=worksheet)
    writer = GoogleSheetsWriter(spreadsheet)

    with pytest.raises(SheetSchemaError, match="don't match the expected schema"):
        writer.sync_open_roles([make_scored_job()], score_threshold=0)


def test_sync_open_roles_appends_new_row_with_correct_shape(make_scored_job):
    worksheet = make_worksheet(OPEN_ROLES_COLUMNS, [])
    spreadsheet = make_spreadsheet(open_roles_ws=worksheet)
    writer = GoogleSheetsWriter(spreadsheet)

    job = make_scored_job(score=80.0, company="Acme", title="Platform Engineer")
    result = writer.sync_open_roles([job], score_threshold=40)

    assert len(result.appended) == 1
    worksheet.append_rows.assert_called_once()
    (rows_arg,), kwargs = worksheet.append_rows.call_args
    assert len(rows_arg) == 1
    assert len(rows_arg[0]) == len(OPEN_ROLES_COLUMNS)
    assert rows_arg[0][OPEN_ROLES_COLUMNS.index("Company")] == "Acme"
    assert rows_arg[0][OPEN_ROLES_COLUMNS.index("Status")] == "New"
    assert kwargs["value_input_option"] == "USER_ENTERED"
    worksheet.update.assert_not_called()


def test_sync_open_roles_updates_existing_row_at_correct_range(make_scored_job):
    job = make_scored_job(
        score=80.0, company="Acme", title="Platform Engineer", url="https://acme.com/jobs/1"
    )
    existing_record = {
        "Company": "Acme",
        "Role": "Platform Engineer",
        "Apply Link": "https://acme.com/jobs/1",
    }
    worksheet = make_worksheet(OPEN_ROLES_COLUMNS, [existing_record])
    spreadsheet = make_spreadsheet(open_roles_ws=worksheet)
    writer = GoogleSheetsWriter(spreadsheet)

    result = writer.sync_open_roles([job], score_threshold=40)

    assert len(result.updated) == 1
    worksheet.append_rows.assert_not_called()
    worksheet.update.assert_called_once()
    # Regression guard: gspread's Worksheet.update signature is
    # (values, range_name, ...) - values first. Row 2 is the first data row
    # (row 1 is the header), so the range must start at A2.
    (values_arg, range_arg), _kwargs = worksheet.update.call_args
    assert range_arg.startswith("A2")
    assert values_arg[0][0] == "Acme"


def test_sync_target_companies_appends_new_row_with_correct_shape():
    worksheet = make_worksheet(TARGET_COMPANIES_COLUMNS, [])
    spreadsheet = make_spreadsheet(target_companies_ws=worksheet)
    writer = GoogleSheetsWriter(spreadsheet)

    company = CompanyEntry(
        name="Acme", slug="acme", ats_type=ATSType.GREENHOUSE, board_token="acme"
    )
    result = writer.sync_target_companies([company])

    assert len(result.appended) == 1
    worksheet.append_rows.assert_called_once()
    (rows_arg,), _kwargs = worksheet.append_rows.call_args
    assert rows_arg[0][TARGET_COMPANIES_COLUMNS.index("Company")] == "Acme"
    worksheet.update.assert_not_called()


def test_sync_target_companies_updates_existing_row_at_correct_range():
    existing_record = {"Company": "Acme", "Industry": "Old", "Careers Page": ""}
    worksheet = make_worksheet(TARGET_COMPANIES_COLUMNS, [existing_record])
    spreadsheet = make_spreadsheet(target_companies_ws=worksheet)
    writer = GoogleSheetsWriter(spreadsheet)

    company = CompanyEntry(
        name="Acme",
        slug="acme",
        ats_type=ATSType.GREENHOUSE,
        board_token="acme",
        industry="DevOps",
    )
    result = writer.sync_target_companies([company])

    assert len(result.updated) == 1
    worksheet.update.assert_called_once()
    (values_arg, range_arg), _kwargs = worksheet.update.call_args
    assert range_arg.startswith("B2")  # Industry is column B, Company (A) is never rewritten
    assert values_arg[0][0] == "DevOps"

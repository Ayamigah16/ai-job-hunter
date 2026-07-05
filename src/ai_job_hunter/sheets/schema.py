"""Column layout for each Google Sheet tab — single source of truth.

The pipeline validates a worksheet's actual header row against these lists at
sync time and fails loudly on drift, rather than silently writing values into
the wrong columns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import gspread

OPEN_ROLES_SHEET = "Open Roles"
OPEN_ROLES_COLUMNS = [
    "Company",
    "Role",
    "Country",
    "Remote",
    "Region",
    "Salary",
    "Tech Stack",
    "Apply Link",
    "Date Posted",
    "Deadline",
    "Status",
    "Notes",
]
# Columns the pipeline may write on an EXISTING row. Status/Notes are excluded
# on purpose: they're user-owned once a row exists, only set (to "New" / "")
# when the pipeline creates the row in the first place.
OPEN_ROLES_MANAGED_COLUMNS = [
    "Company",
    "Role",
    "Country",
    "Remote",
    "Region",
    "Salary",
    "Tech Stack",
    "Apply Link",
    "Date Posted",
    "Deadline",
]

TARGET_COMPANIES_SHEET = "Target Companies"
TARGET_COMPANIES_COLUMNS = [
    "Company",
    "Industry",
    "Careers Page",
    "Remote Friendly",
    "Hires in Africa?",
    "Referral Needed?",
    "Priority",
]
# Same idea: Remote Friendly/Hires in Africa?/Referral Needed?/Priority are
# curated by hand once a company row exists; the pipeline only refreshes
# Industry/Careers Page from config/companies.yaml on existing rows.
TARGET_COMPANIES_MANAGED_COLUMNS = ["Industry", "Careers Page"]

NETWORKING_SHEET = "Networking"

APPLICATIONS_SHEET = "Applications"
APPLICATIONS_COLUMNS = [
    "Date Applied",
    "Company",
    "Role",
    "Resume Used",
    "Cover Letter",
    "Interview Stage",
    "Feedback",
]

WEEKLY_DASHBOARD_SHEET = "Weekly Dashboard"
WEEKLY_DASHBOARD_COLUMNS = ["Metric", "Value"]


class SheetSchemaError(Exception):
    """Raised when a worksheet's actual header row doesn't match this schema."""


def validate_headers(worksheet: gspread.Worksheet, expected_columns: list[str]) -> None:
    actual = worksheet.row_values(1)
    if actual != expected_columns:
        raise SheetSchemaError(
            f"Worksheet {worksheet.title!r} headers don't match the expected schema.\n"
            f"Expected: {expected_columns}\nActual:   {actual}\n"
            "Fix the sheet's header row (or update sheets/schema.py) before syncing."
        )

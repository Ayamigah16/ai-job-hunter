"""SheetsWriter: syncs scored jobs and companies into the spreadsheet without
ever clobbering user-owned columns (Status, Notes, Priority, ...).

`GoogleSheetsWriter` is the real gspread-backed implementation; `FakeSheetsWriter`
is an in-memory test double implementing the same surface so the unit suite
never calls the real Google API. Both share the row-building helpers below so
"what a row looks like" can't drift between the fake and the real thing.

Idempotency: job_id / company identity is recomputed from each existing row's
own cells on every sync (see dedup.compute_job_id) rather than stored
separately — see docs/adr/0003-dedup-and-idempotency-via-sheet-state.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

import gspread.utils

from ai_job_hunter.dedup import compute_job_id
from ai_job_hunter.models import ATSType, HiresInAfrica
from ai_job_hunter.regions import lookup_location
from ai_job_hunter.sheets.schema import (
    OPEN_ROLES_COLUMNS,
    OPEN_ROLES_MANAGED_COLUMNS,
    OPEN_ROLES_SHEET,
    TARGET_COMPANIES_COLUMNS,
    TARGET_COMPANIES_MANAGED_COLUMNS,
    TARGET_COMPANIES_SHEET,
    validate_headers,
)
from ai_job_hunter.sheets.schema import SheetSchemaError as SheetSchemaError  # re-exported

if TYPE_CHECKING:
    import gspread

    from ai_job_hunter.models import JobPosting, ScoredJob
    from ai_job_hunter.registry import CompanyEntry

_CAREERS_PAGE_TEMPLATES: dict[ATSType, str] = {
    ATSType.GREENHOUSE: "https://job-boards.greenhouse.io/{token}",
    ATSType.LEVER: "https://jobs.lever.co/{token}",
    ATSType.ASHBY: "https://jobs.ashbyhq.com/{token}",
    ATSType.WORKABLE: "https://apply.workable.com/{token}",
    ATSType.SMARTRECRUITERS: "https://jobs.smartrecruiters.com/{token}",
    ATSType.BAMBOOHR: "https://{token}.bamboohr.com/careers",
    ATSType.RECRUITEE: "https://{token}.recruitee.com",
    ATSType.PERSONIO: "https://{token}.jobs.personio.de",
}


_APPLY_LINK_COLUMN = "Apply Link"


@dataclass
class SyncResult:
    appended: list = field(default_factory=list)
    updated: list = field(default_factory=list)
    skipped: list = field(default_factory=list)


class SheetsWriter(Protocol):
    def sync_open_roles(
        self, scored_jobs: list[ScoredJob], score_threshold: float
    ) -> SyncResult: ...

    def sync_target_companies(self, companies: list[CompanyEntry]) -> SyncResult: ...


def careers_page_url(company: CompanyEntry) -> str:
    template = _CAREERS_PAGE_TEMPLATES.get(company.ats_type)
    if template is None or not company.board_token:
        return ""
    return template.format(token=company.board_token)


def _format_salary(job: JobPosting) -> str:
    if job.salary_min is None and job.salary_max is None:
        return ""
    currency = job.salary_currency or ""
    if job.salary_min is not None and job.salary_max is not None:
        return f"{currency}{job.salary_min:,}-{job.salary_max:,}"
    return f"{currency}{job.salary_min or job.salary_max:,}"


def _remote_label(remote: bool | None) -> str:
    if remote is True:
        return "Yes"
    if remote is False:
        return "No"
    return "Unknown"


def build_open_roles_row(scored: ScoredJob) -> dict[str, str]:
    job = scored.job
    country, region = lookup_location(job.location_raw)
    return {
        "Company": job.company,
        "Role": job.title,
        "Country": country,
        "Remote": _remote_label(job.remote),
        "Region": region,
        "Salary": _format_salary(job),
        "Tech Stack": ", ".join(job.tech_stack),
        _APPLY_LINK_COLUMN: job.url or "",
        "Date Posted": job.posted_date.isoformat() if job.posted_date else "",
        "Deadline": job.deadline.isoformat() if job.deadline else "",
    }


def build_target_company_row(company: CompanyEntry) -> dict[str, str]:
    hires_in_africa = ""
    if company.hires_in_africa != HiresInAfrica.UNKNOWN:
        hires_in_africa = company.hires_in_africa.value

    return {
        "Company": company.name,
        "Industry": company.industry,
        "Careers Page": careers_page_url(company),
        "Remote Friendly": "",
        "Hires in Africa?": hires_in_africa,
        "Referral Needed?": "",
        "Priority": company.priority.value,
    }


class FakeSheetsWriter:
    """In-memory test double — no network calls, same surface as GoogleSheetsWriter."""

    def __init__(self) -> None:
        self.open_roles_rows: list[dict[str, str]] = []
        self.target_companies_rows: list[dict[str, str]] = []

    def sync_open_roles(self, scored_jobs: list[ScoredJob], score_threshold: float) -> SyncResult:
        result = SyncResult()
        existing_by_id = {
            compute_job_id(row["Company"], row["Role"], row.get(_APPLY_LINK_COLUMN) or None): index
            for index, row in enumerate(self.open_roles_rows)
        }

        for scored in scored_jobs:
            if scored.score.total_score < score_threshold:
                result.skipped.append(scored)
                continue

            row = build_open_roles_row(scored)
            if scored.job_id in existing_by_id:
                self.open_roles_rows[existing_by_id[scored.job_id]].update(row)
                result.updated.append(scored)
            else:
                row["Status"] = "New"
                row["Notes"] = ""
                self.open_roles_rows.append(row)
                result.appended.append(scored)

        return result

    def sync_target_companies(self, companies: list[CompanyEntry]) -> SyncResult:
        result = SyncResult()
        existing_by_name = {
            row["Company"].lower(): index for index, row in enumerate(self.target_companies_rows)
        }

        for company in companies:
            key = company.name.lower()
            if key in existing_by_name:
                row = self.target_companies_rows[existing_by_name[key]]
                row["Industry"] = company.industry
                row["Careers Page"] = careers_page_url(company)
                result.updated.append(company)
            else:
                self.target_companies_rows.append(build_target_company_row(company))
                result.appended.append(company)

        return result


class GoogleSheetsWriter:
    """Real gspread-backed writer. See FakeSheetsWriter for the same logic offline."""

    def __init__(self, spreadsheet: gspread.Spreadsheet) -> None:
        self._spreadsheet = spreadsheet

    def sync_open_roles(self, scored_jobs: list[ScoredJob], score_threshold: float) -> SyncResult:
        worksheet = self._spreadsheet.worksheet(OPEN_ROLES_SHEET)
        validate_headers(worksheet, OPEN_ROLES_COLUMNS)

        existing_records = worksheet.get_all_records()
        existing_by_id = {}
        for row_number, record in enumerate(existing_records, start=2):
            apply_link = record.get(_APPLY_LINK_COLUMN) or None
            job_id = compute_job_id(record.get("Company", ""), record.get("Role", ""), apply_link)
            existing_by_id[job_id] = row_number

        result = SyncResult()
        rows_to_append: list[list[str]] = []

        for scored in scored_jobs:
            if scored.score.total_score < score_threshold:
                result.skipped.append(scored)
                continue

            row = build_open_roles_row(scored)
            if scored.job_id in existing_by_id:
                row_number = existing_by_id[scored.job_id]
                values = [row[column] for column in OPEN_ROLES_MANAGED_COLUMNS]
                end_col = gspread.utils.rowcol_to_a1(row_number, len(OPEN_ROLES_MANAGED_COLUMNS))
                start_col = gspread.utils.rowcol_to_a1(row_number, 1)
                worksheet.update([values], f"{start_col}:{end_col}")
                result.updated.append(scored)
            else:
                row["Status"] = "New"
                row["Notes"] = ""
                rows_to_append.append([row[column] for column in OPEN_ROLES_COLUMNS])
                result.appended.append(scored)

        if rows_to_append:
            worksheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")

        return result

    def sync_target_companies(self, companies: list[CompanyEntry]) -> SyncResult:
        worksheet = self._spreadsheet.worksheet(TARGET_COMPANIES_SHEET)
        validate_headers(worksheet, TARGET_COMPANIES_COLUMNS)

        existing_records = worksheet.get_all_records()
        existing_by_name = {
            str(record.get("Company", "")).lower(): row_number
            for row_number, record in enumerate(existing_records, start=2)
        }

        result = SyncResult()
        rows_to_append: list[list[str]] = []

        for company in companies:
            key = company.name.lower()
            if key in existing_by_name:
                row_number = existing_by_name[key]
                row = build_target_company_row(company)
                values = [row[column] for column in TARGET_COMPANIES_MANAGED_COLUMNS]
                num_managed = len(TARGET_COMPANIES_MANAGED_COLUMNS)
                start_col = gspread.utils.rowcol_to_a1(row_number, 2)
                end_col = gspread.utils.rowcol_to_a1(row_number, 1 + num_managed)
                worksheet.update([values], f"{start_col}:{end_col}")
                result.updated.append(company)
            else:
                row = build_target_company_row(company)
                rows_to_append.append([row[column] for column in TARGET_COMPANIES_COLUMNS])
                result.appended.append(company)

        if rows_to_append:
            worksheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")

        return result

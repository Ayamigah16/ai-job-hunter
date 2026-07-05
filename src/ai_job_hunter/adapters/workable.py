"""Adapter for companies whose careers site is powered by Workable.

Workable exposes a public, unauthenticated job-board widget API per company:
`GET https://apply.workable.com/api/v1/widget/accounts/{board_token}`, returning
`{"name": str, "description": str | None, "jobs": [...]}`.

Top-level shape verified live against `apply.workable.com/api/v1/widget/accounts/hashicorp`
and `.../gitguardian` (both returned `{"name": ..., "description": ..., "jobs": []}` —
neither company had open reqs at check time, so no live job object was observable).
Job-object field names below are corroborated by Workable's official API reference
(https://workable.readme.io/reference/jobs-1) and third-party integration write-ups:
`shortcode`, `department`, `published_on`, `url`, and a `location` object with
`city` / `region` / `country` / `country_code` / `telecommuting` / `workplace_type`.
Docs disagree with some ATS-agnostic assumptions about where the remote flag lives
(nested under `location.telecommuting` rather than a top-level `telecommute`), so
`_is_remote` below checks both spots before falling back to a text regex.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from ai_job_hunter.adapters.base import BaseATSAdapter, strip_html
from ai_job_hunter.models import ATSType, JobPosting

if TYPE_CHECKING:
    from ai_job_hunter.registry import CompanyEntry

_REMOTE_RE = re.compile(r"remote", re.IGNORECASE)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _location_raw(location: dict) -> str:
    parts = [location.get("city"), location.get("region"), location.get("country")]
    return ", ".join(part for part in parts if part)


def _is_remote(raw: dict, location: dict, title: str, location_raw: str) -> bool | None:
    # Some sources expose the flag at the top level, others nest it under `location`.
    for telecommute in (raw.get("telecommute"), location.get("telecommuting")):
        if isinstance(telecommute, bool):
            return telecommute
    combined = f"{location_raw} {title}"
    return bool(_REMOTE_RE.search(combined))


class WorkableAdapter(BaseATSAdapter):
    """Fetches and normalizes postings from a Workable job board widget."""

    ats_type = ATSType.WORKABLE

    def fetch_raw(self, company: CompanyEntry) -> list[dict]:
        if not company.board_token:
            return []

        url = f"https://apply.workable.com/api/v1/widget/accounts/{company.board_token}"
        response = self.session.get(url)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        if not response.content:
            return []

        data = response.json()
        return data.get("jobs", []) or []

    def parse(self, raw: dict, company: CompanyEntry) -> JobPosting | None:
        native_id = raw.get("shortcode") or raw.get("id")
        title = raw.get("title")
        if not native_id or not title:
            return None

        location = raw.get("location") or {}
        location_raw = _location_raw(location)

        return JobPosting(
            company=company.name,
            title=title,
            location_raw=location_raw,
            remote=_is_remote(raw, location, title, location_raw),
            department=raw.get("department"),
            salary_min=None,
            salary_max=None,
            salary_currency=None,
            tech_stack=[],
            url=raw.get("url"),
            posted_date=_parse_date(raw.get("published_on")),
            deadline=None,
            source_ats=self.ats_type.value,
            raw_native_id=str(native_id),
            description_raw=strip_html(raw.get("description") or ""),
            fetched_at=datetime.now(UTC),
        )

"""Adapter for companies whose careers site is powered by Greenhouse.

Greenhouse exposes a public, unauthenticated job board API per company:
`GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`.
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


class GreenhouseAdapter(BaseATSAdapter):
    """Fetches and normalizes postings from a Greenhouse job board."""

    ats_type = ATSType.GREENHOUSE

    def fetch_raw(self, company: CompanyEntry) -> list[dict]:
        if not company.board_token:
            return []

        url = (
            f"https://boards-api.greenhouse.io/v1/boards/{company.board_token}/jobs"
            "?content=true"
        )
        response = self.session.get(url)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        if not response.content:
            return []

        data = response.json()
        return data.get("jobs", []) or []

    def parse(self, raw: dict, company: CompanyEntry) -> JobPosting | None:
        job_id = raw.get("id")
        title = raw.get("title")
        if job_id is None or not title:
            return None

        location_raw = (raw.get("location") or {}).get("name") or ""
        departments = raw.get("departments") or []
        department = departments[0].get("name") if departments else None

        remote = bool(_REMOTE_RE.search(location_raw) or _REMOTE_RE.search(title))

        posted_date = _parse_date(raw.get("first_published") or raw.get("updated_at"))

        return JobPosting(
            company=company.name,
            title=title,
            location_raw=location_raw,
            remote=remote,
            department=department,
            salary_min=None,
            salary_max=None,
            salary_currency=None,
            tech_stack=[],
            url=raw.get("absolute_url"),
            posted_date=posted_date,
            deadline=None,
            source_ats=self.ats_type.value,
            raw_native_id=str(job_id),
            description_raw=strip_html(raw.get("content") or ""),
            fetched_at=datetime.now(UTC),
        )

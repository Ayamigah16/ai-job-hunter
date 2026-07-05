"""Adapter for companies whose careers site is powered by Lever.

Lever exposes a public, unauthenticated postings API per company:
`GET https://api.lever.co/v0/postings/{board_token}?mode=json`, returning a
bare JSON array of posting objects (verified live against jobs.lever.co/ro).
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


def _parse_created_at(value: int | None) -> date | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value / 1000, tz=UTC).date()
    except (OverflowError, OSError, ValueError):
        return None


class LeverAdapter(BaseATSAdapter):
    """Fetches and normalizes postings from a Lever job board."""

    ats_type = ATSType.LEVER

    def fetch_raw(self, company: CompanyEntry) -> list[dict]:
        if not company.board_token:
            return []

        url = f"https://api.lever.co/v0/postings/{company.board_token}?mode=json"
        response = self.session.get(url)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        if not response.content:
            return []

        data = response.json()
        return data or []

    def parse(self, raw: dict, company: CompanyEntry) -> JobPosting | None:
        native_id = raw.get("id")
        title = raw.get("text")
        if not native_id or not title:
            return None

        categories = raw.get("categories") or {}
        location_raw = categories.get("location") or ""
        department = categories.get("team")

        workplace_type = raw.get("workplaceType")
        if workplace_type:
            remote = workplace_type == "remote"
        else:
            remote = bool(_REMOTE_RE.search(location_raw))

        posted_date = _parse_created_at(raw.get("createdAt"))

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
            url=raw.get("hostedUrl") or raw.get("applyUrl"),
            posted_date=posted_date,
            deadline=None,
            source_ats=self.ats_type.value,
            raw_native_id=str(native_id),
            description_raw=strip_html(raw.get("descriptionPlain") or raw.get("description", "")),
            fetched_at=datetime.now(UTC),
        )

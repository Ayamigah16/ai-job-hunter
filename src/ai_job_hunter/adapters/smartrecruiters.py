"""Adapter for companies whose careers site is powered by SmartRecruiters.

SmartRecruiters exposes a public, unauthenticated postings API per company:
`GET https://api.smartrecruiters.com/v1/companies/{board_token}/postings`, returning
`{"offset": int, "limit": int, "totalFound": int, "content": [...]}`.

Verified live against `api.smartrecruiters.com/v1/companies/Visa/postings` (Visa is a
real, currently-active SmartRecruiters customer; `bosch`, `skechers`, and `ikea` all
resolved but had zero open postings at check time). The live list-endpoint posting
objects confirm `id`, `name`, `releasedDate`, `ref`, and a `location` object with
`city` / `region` / `country` / `remote` / `hybrid` / `fullLocation`, plus a
`department` object with `id` / `label` — matching the documented public shape.
Notably, the live list endpoint does **not** include `applyUrl` (that only appears
on the single-posting detail endpoint, `.../postings/{id}`), so the constructed-URL
fallback below (`https://jobs.smartrecruiters.com/{board_token}/{id}`) is the common
path in practice, not just a defensive edge case.
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


def _is_remote(location: dict, title: str, location_raw: str) -> bool | None:
    remote = location.get("remote")
    if isinstance(remote, bool):
        return remote
    combined = f"{location_raw} {title}"
    return bool(_REMOTE_RE.search(combined))


class SmartRecruitersAdapter(BaseATSAdapter):
    """Fetches and normalizes postings from a SmartRecruiters company job board."""

    ats_type = ATSType.SMARTRECRUITERS

    def fetch_raw(self, company: CompanyEntry) -> list[dict]:
        if not company.board_token:
            return []

        url = f"https://api.smartrecruiters.com/v1/companies/{company.board_token}/postings"
        response = self.session.get(url)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        if not response.content:
            return []

        data = response.json()
        return data.get("content", []) or []

    def parse(self, raw: dict, company: CompanyEntry) -> JobPosting | None:
        native_id = raw.get("id")
        title = raw.get("name")
        if not native_id or not title:
            return None

        location = raw.get("location") or {}
        location_raw = _location_raw(location)

        department = raw.get("department") or {}

        url = raw.get("applyUrl") or (
            f"https://jobs.smartrecruiters.com/{company.board_token}/{native_id}"
        )

        return JobPosting(
            company=company.name,
            title=title,
            location_raw=location_raw,
            remote=_is_remote(location, title, location_raw),
            department=department.get("label"),
            salary_min=None,
            salary_max=None,
            salary_currency=None,
            tech_stack=[],
            url=url,
            posted_date=_parse_date(raw.get("releasedDate")),
            deadline=None,
            source_ats=self.ats_type.value,
            raw_native_id=str(native_id),
            description_raw=strip_html(raw.get("description") or ""),
            fetched_at=datetime.now(UTC),
        )

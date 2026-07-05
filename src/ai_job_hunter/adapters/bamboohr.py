"""Adapter for companies whose careers site is powered by BambooHR.

BambooHR exposes a public, unauthenticated careers-list API per company:
`GET https://{board_token}.bamboohr.com/careers/list`, returning
`{"meta": {"totalCount": int}, "result": [...]}`.

Verified live against `flyio.bamboohr.com/careers/list` (Fly.io is a real,
currently-active BambooHR customer with 11 open postings at check time; `posthog`
and `palantir` also resolve but only expose a single placeholder/demo listing each).
The live response confirms the top-level shape is `{"meta": ..., "result": [...]}`
(not a bare list) and that each entry has `id`, `jobOpeningName`, `departmentId`,
`departmentLabel`, `location` (`city` / `state` only — no `country` key), an
`atsLocation` object, and a `locationType` code, but notably **no** `department`
key (it's `departmentLabel` in practice, not the documented `department`) and
**no** `datePosted` or `description` on the list entry — those two only appear on
the per-job detail endpoint (`/careers/{id}/detail`), which is out of scope here.
`isRemote` is present but was `null` on every live entry observed, so it's an
unreliable signal in practice; `_is_remote` below still checks it defensively (in
case some company populates it as a real bool) before falling back to a text
regex across the combined location + title, per BambooHR's lack of a dependable
structured remote flag. Mapping stays defensive for `department`/`datePosted` so
a company whose data does follow the documented shape still parses correctly.
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
    parts = [location.get("city"), location.get("state"), location.get("country")]
    return ", ".join(part for part in parts if part)


def _is_remote(raw: dict, title: str, location_raw: str) -> bool | None:
    is_remote = raw.get("isRemote")
    if isinstance(is_remote, bool):
        return is_remote
    combined = f"{location_raw} {title}"
    return bool(_REMOTE_RE.search(combined))


class BambooHRAdapter(BaseATSAdapter):
    """Fetches and normalizes postings from a BambooHR careers list."""

    ats_type = ATSType.BAMBOOHR

    def fetch_raw(self, company: CompanyEntry) -> list[dict]:
        if not company.board_token:
            return []

        url = f"https://{company.board_token}.bamboohr.com/careers/list"
        response = self.session.get(url)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        if not response.content:
            return []

        data = response.json()
        # The live shape is `{"result": [...]}`, but tolerate a bare top-level
        # list too in case some deployment (or a future BambooHR revision) skips
        # the wrapper.
        if isinstance(data, list):
            return data or []
        return data.get("result", []) or []

    def parse(self, raw: dict, company: CompanyEntry) -> JobPosting | None:
        native_id = raw.get("id")
        title = raw.get("jobOpeningName")
        if not native_id or not title:
            return None

        location = raw.get("location") or {}
        location_raw = _location_raw(location)

        return JobPosting(
            company=company.name,
            title=title,
            location_raw=location_raw,
            remote=_is_remote(raw, title, location_raw),
            department=raw.get("departmentLabel") or raw.get("department"),
            salary_min=None,
            salary_max=None,
            salary_currency=None,
            tech_stack=[],
            url=f"https://{company.board_token}.bamboohr.com/careers/{native_id}",
            posted_date=_parse_date(raw.get("datePosted")),
            deadline=None,
            source_ats=self.ats_type.value,
            raw_native_id=str(native_id),
            description_raw=strip_html(raw.get("description") or ""),
            fetched_at=datetime.now(UTC),
        )

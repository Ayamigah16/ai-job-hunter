"""Adapter for companies whose careers site is powered by Recruitee.

Recruitee exposes a public, unauthenticated offers API per company:
`GET https://{board_token}.recruitee.com/api/offers`, returning
`{"offers": [...]}`.

Verified live against `greatminds.recruitee.com/api/offers` (Great Minds is a
real, currently-active Recruitee customer with open postings at check time).
The live response confirms the top-level shape is `{"offers": [...]}` and that
each entry carries `id` (int), `title`, `careers_url`, a direct boolean
`remote` flag, `department`, and a `location` field that is a plain string
(observed as `"Remote job"` for fully-remote postings; Recruitee's docs and
third-party integration write-ups describe it holding a city/region string for
on-site postings instead of a structured object). `published_at` on the live
entries is `"2026-06-26 15:26:52 UTC"` — space-separated with a trailing zone
name, not a bare ISO datetime — so `_parse_date` below takes the leading
`YYYY-MM-DD` token rather than relying on `datetime.fromisoformat` on the
whole string. `remote` was `true` on every live entry observed (no onsite
example was available to confirm `false` in practice), so `_is_remote` still
falls back to a text regex across location + title for records where the key
is altogether absent, per Recruitee's own docs not guaranteeing the flag is
always populated.
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
    # Live shape is "YYYY-MM-DD HH:MM:SS UTC"; take the leading date token so
    # a trailing zone name (or any other suffix) never breaks parsing.
    date_token = value.split(" ", 1)[0]
    try:
        return date.fromisoformat(date_token)
    except ValueError:
        return None


def _is_remote(raw: dict, title: str, location_raw: str) -> bool | None:
    remote = raw.get("remote")
    if isinstance(remote, bool):
        return remote
    combined = f"{location_raw} {title}"
    return bool(_REMOTE_RE.search(combined))


class RecruiteeAdapter(BaseATSAdapter):
    """Fetches and normalizes postings from a Recruitee offers API."""

    ats_type = ATSType.RECRUITEE

    def fetch_raw(self, company: CompanyEntry) -> list[dict]:
        if not company.board_token:
            return []

        url = f"https://{company.board_token}.recruitee.com/api/offers"
        response = self.session.get(url)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        if not response.content:
            return []

        data = response.json()
        return data.get("offers", []) or []

    def parse(self, raw: dict, company: CompanyEntry) -> JobPosting | None:
        native_id = raw.get("id")
        title = raw.get("title")
        if not native_id or not title:
            return None

        location_raw = raw.get("location") or ""

        return JobPosting(
            company=company.name,
            title=title,
            location_raw=location_raw,
            remote=_is_remote(raw, title, location_raw),
            department=raw.get("department"),
            salary_min=None,
            salary_max=None,
            salary_currency=None,
            tech_stack=[],
            url=raw.get("careers_url"),
            posted_date=_parse_date(raw.get("published_at")),
            deadline=None,
            source_ats=self.ats_type.value,
            raw_native_id=str(native_id),
            description_raw=strip_html(raw.get("description") or ""),
            fetched_at=datetime.now(UTC),
        )

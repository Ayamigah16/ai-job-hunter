"""Adapter for the RemoteOK job aggregator.

RemoteOK exposes a public, unauthenticated JSON API at
`GET https://remoteok.com/api` (verified live). The response is a bare JSON
array, but its FIRST element is metadata about the API itself (it has a
`"legal"` key and no `"company"`/`"position"` fields) rather than a real job
posting, so it must be skipped.

Attribution note: RemoteOK's API Terms of Service ask that any public display
of their listings link back to remoteok.com and credit "Remote OK" as the
source. This is a personal-use tool with no public display surface, so no
attribution UI is implemented here — noted for future reference if that
changes.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from ai_job_hunter.adapters.base import BaseAggregatorAdapter, strip_html
from ai_job_hunter.models import AggregatorType, JobPosting

if TYPE_CHECKING:
    from ai_job_hunter.registry import AggregatorEntry

_API_URL = "https://remoteok.com/api"


def _parse_posted_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _parse_salary(value: int | None) -> int | None:
    # RemoteOK uses 0 (or omits the field) to mean "undisclosed", not an
    # actual $0 salary.
    return value if value else None


class RemoteOKAdapter(BaseAggregatorAdapter):
    """Fetches and normalizes postings from the RemoteOK aggregator."""

    source_type = AggregatorType.REMOTEOK

    def fetch_raw(self, aggregator: AggregatorEntry) -> list[dict]:
        response = self.session.get(_API_URL)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        if not response.content:
            return []

        data = response.json()
        if not data:
            return []

        # First element is API metadata (has "legal", not a job posting).
        return data[1:]

    def parse(self, raw: dict, aggregator: AggregatorEntry) -> JobPosting | None:
        company = raw.get("company")
        title = raw.get("position")
        if not company or not title:
            return None

        native_id = raw.get("id") or raw.get("slug")

        return JobPosting(
            company=company,
            title=title,
            location_raw=raw.get("location") or "",
            remote=True,
            department=None,
            salary_min=_parse_salary(raw.get("salary_min")),
            salary_max=_parse_salary(raw.get("salary_max")),
            salary_currency=None,
            tech_stack=raw.get("tags", []),
            url=raw.get("url"),
            posted_date=_parse_posted_date(raw.get("date")),
            deadline=None,
            source_ats=self.source_type.value,
            raw_native_id=str(native_id) if native_id else None,
            description_raw=strip_html(raw.get("description", "")),
            fetched_at=datetime.now(UTC),
        )

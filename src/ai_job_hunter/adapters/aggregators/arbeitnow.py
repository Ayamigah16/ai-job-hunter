"""Adapter for the Arbeitnow job aggregator.

Arbeitnow exposes a public, unauthenticated JSON API at
`GET https://arbeitnow.com/api/job-board-api` (verified live; the bare
`arbeitnow.com` host 301-redirects to `www.arbeitnow.com`, so requests must
follow redirects — `requests` does this by default). The response is an
envelope of `{"data": [...], "links": {...}, "meta": {...}}` where `data` is
the list of job postings.

Unlike most sources, `remote` is an explicit boolean field on each record
(not inferred from location text), and `tags` is reasonably clean structured
data, so both are passed through directly.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from ai_job_hunter.adapters.base import BaseAggregatorAdapter, strip_html
from ai_job_hunter.models import AggregatorType, JobPosting

if TYPE_CHECKING:
    from ai_job_hunter.registry import AggregatorEntry

_API_URL = "https://arbeitnow.com/api/job-board-api"


def _parse_posted_date(value: int | None) -> date | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value, tz=UTC).date()
    except (OverflowError, OSError, ValueError):
        return None


class ArbeitnowAdapter(BaseAggregatorAdapter):
    """Fetches and normalizes postings from the Arbeitnow aggregator."""

    source_type = AggregatorType.ARBEITNOW

    def fetch_raw(self, aggregator: AggregatorEntry) -> list[dict]:
        # MVP: only page 1 (~100 postings). The API is paginated via
        # `?page=N` (see `meta`/`links` in the response) — following pages
        # would give broader coverage but is left as a future improvement.
        response = self.session.get(_API_URL)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        if not response.content:
            return []

        payload = response.json()
        if not payload:
            return []

        return payload.get("data") or []

    def parse(self, raw: dict, aggregator: AggregatorEntry) -> JobPosting | None:
        company = raw.get("company_name")
        title = raw.get("title")
        if not company or not title:
            return None

        native_id = raw.get("slug")

        return JobPosting(
            company=company,
            title=title,
            location_raw=raw.get("location", ""),
            remote=raw.get("remote"),
            department=None,
            salary_min=None,
            salary_max=None,
            salary_currency=None,
            tech_stack=raw.get("tags", []),
            url=raw.get("url"),
            posted_date=_parse_posted_date(raw.get("created_at")),
            deadline=None,
            source_ats=self.source_type.value,
            raw_native_id=str(native_id) if native_id else None,
            description_raw=strip_html(raw.get("description", "")),
            fetched_at=datetime.now(UTC),
        )

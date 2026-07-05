"""Adapter for the Remotive job aggregator.

Remotive exposes a public, unauthenticated JSON API at
`GET https://remotive.com/api/remote-jobs` (verified live). An optional
`category` query param filters server-side (cheaper than downloading
everything and filtering locally); `search_terms` from the registry are not
sent individually to keep this to one request per aggregator entry. The
response envelope is `{"job-count": int, "jobs": [...]}` (plus warning/legal
notice keys that are irrelevant here).

Remotive is a remote-only job board by definition, so `remote` is always
`True` rather than inferred from `candidate_required_location`. That field is
kept as-is in `location_raw` (e.g. "USA Only", "Worldwide") since parsing it
into a structured region is a later scoring/Africa-friendly heuristic concern,
not this adapter's job. Likewise `salary` is unstructured free text (e.g.
"$90k - $110k" or empty) and is intentionally left unparsed.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from ai_job_hunter.adapters.base import BaseAggregatorAdapter, strip_html
from ai_job_hunter.models import AggregatorType, JobPosting

if TYPE_CHECKING:
    from ai_job_hunter.registry import AggregatorEntry

_API_URL = "https://remotive.com/api/remote-jobs"


def _parse_posted_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


class RemotiveAdapter(BaseAggregatorAdapter):
    """Fetches and normalizes postings from the Remotive aggregator."""

    source_type = AggregatorType.REMOTIVE

    def fetch_raw(self, aggregator: AggregatorEntry) -> list[dict]:
        url = _API_URL
        if aggregator.category:
            url = f"{_API_URL}?category={aggregator.category}"

        response = self.session.get(url)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        if not response.content:
            return []

        payload = response.json()
        if not payload:
            return []

        return payload.get("jobs") or []

    def parse(self, raw: dict, aggregator: AggregatorEntry) -> JobPosting | None:
        company = raw.get("company_name")
        title = raw.get("title")
        if not company or not title:
            return None

        native_id = raw.get("id")

        return JobPosting(
            company=company,
            title=title,
            location_raw=raw.get("candidate_required_location", ""),
            remote=True,
            department=None,
            salary_min=None,
            salary_max=None,
            salary_currency=None,
            tech_stack=raw.get("tags", []),
            url=raw.get("url"),
            posted_date=_parse_posted_date(raw.get("publication_date")),
            deadline=None,
            source_ats=self.source_type.value,
            raw_native_id=str(native_id) if native_id is not None else None,
            description_raw=strip_html(raw.get("description", "")),
            fetched_at=datetime.now(UTC),
        )

"""Adapter for the Himalayas job aggregator.

Himalayas exposes a public, unauthenticated JSON API at
`GET https://himalayas.app/jobs/api` (verified live). The response envelope
is `{"comments": str, "updatedAt": int, "offset": int, "limit": int,
"totalCount": int, "jobs": [...]}`; `limit` is ~20 postings per page and
`totalCount` is in the six figures, so this MVP only fetches the default
first page — following `offset`/`limit` for further pages is left as a
future improvement.

Two things differ from the shape documented for this API:
  - `pubDate` (and `expiryDate`) are Unix timestamps (seconds, int), not ISO
    datetime strings.
  - Each record has a full HTML `description` field in addition to the
    plain-text `excerpt`; the fuller `description` is preferred here and
    `excerpt` is only a fallback.
`guid` is a stable per-posting URL (observed identical to
`applicationLink` in practice, but they are logically distinct fields, so
`guid` is what is used for `raw_native_id`).

Himalayas is a remote-only job board by definition, so `remote` is always
`True`. `locationRestrictions` (e.g. `["United States"]`, `["Worldwide"]`,
or multiple countries) is kept as free text in `location_raw` rather than
parsed into a structured region.

`categories` is Himalayas's own per-posting skill/role taxonomy (e.g.
"DevOps-Engineering", "Kubernetes" style slugs) — observed to be relevant
skill/category tags, so it is passed through as `tech_stack` as-is.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from ai_job_hunter.adapters.base import BaseAggregatorAdapter, strip_html
from ai_job_hunter.models import AggregatorType, JobPosting

if TYPE_CHECKING:
    from ai_job_hunter.registry import AggregatorEntry

_API_URL = "https://himalayas.app/jobs/api"


def _parse_posted_date(value: int | None) -> date | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value, tz=UTC).date()
    except (OverflowError, OSError, ValueError, TypeError):
        return None


class HimalayasAdapter(BaseAggregatorAdapter):
    """Fetches and normalizes postings from the Himalayas aggregator."""

    source_type = AggregatorType.HIMALAYAS

    def fetch_raw(self, aggregator: AggregatorEntry) -> list[dict]:
        # MVP: only the default first page (~20 postings). The API supports
        # `offset`/`limit` pagination — following further pages would give
        # broader coverage but is left as a future improvement.
        response = self.session.get(_API_URL)
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
        company = raw.get("companyName")
        title = raw.get("title")
        if not company or not title:
            return None

        native_id = raw.get("guid")
        description = raw.get("description") or raw.get("excerpt") or ""

        return JobPosting(
            company=company,
            title=title,
            location_raw=", ".join(raw.get("locationRestrictions") or []),
            remote=True,
            department=None,
            salary_min=raw.get("minSalary"),
            salary_max=raw.get("maxSalary"),
            salary_currency=raw.get("currency"),
            tech_stack=raw.get("categories", []),
            url=raw.get("applicationLink"),
            posted_date=_parse_posted_date(raw.get("pubDate")),
            deadline=None,
            source_ats=self.source_type.value,
            raw_native_id=str(native_id) if native_id else None,
            description_raw=strip_html(description),
            fetched_at=datetime.now(UTC),
        )

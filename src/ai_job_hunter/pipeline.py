"""Orchestrates fetching across all sources.

Filter/score (Phase 3), dedup (Phase 3), and Sheets sync (Phase 4) extend this
module in later phases — for now it's fetch-only.
"""

from __future__ import annotations

from ai_job_hunter.adapters.base import RateLimitedSession
from ai_job_hunter.adapters.registry_map import AGGREGATOR_ADAPTERS, ATS_ADAPTERS
from ai_job_hunter.models import JobPosting
from ai_job_hunter.registry import AggregatorEntry, CompanyEntry


def fetch_all(
    companies: list[CompanyEntry],
    aggregators: list[AggregatorEntry],
    session: RateLimitedSession | None = None,
) -> dict[str, list[JobPosting]]:
    """Fetch every enabled/fetchable source, keyed by source name.

    Companies whose ats_type has no adapter (ATSType.UNSUPPORTED, or any future
    type not yet wired into registry_map) are silently skipped here — that's
    expected, not an error; see CompanyEntry.notes for what they actually use.
    """
    session = session or RateLimitedSession()
    results: dict[str, list[JobPosting]] = {}

    for company in companies:
        adapter_cls = ATS_ADAPTERS.get(company.ats_type)
        if adapter_cls is None:
            continue
        results[company.name] = adapter_cls(session=session).fetch_and_parse(company)

    for aggregator in aggregators:
        if not aggregator.enabled:
            continue
        adapter_cls = AGGREGATOR_ADAPTERS.get(aggregator.source_type)
        if adapter_cls is None:
            continue
        results[aggregator.name] = adapter_cls(session=session).fetch_and_parse(aggregator)

    return results

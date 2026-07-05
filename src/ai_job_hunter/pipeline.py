"""Orchestrates fetching across all sources.

Filter/score (Phase 3), dedup (Phase 3), and Sheets sync (Phase 4) extend this
module in later phases — for now it's fetch-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ai_job_hunter.adapters.base import RateLimitedSession
from ai_job_hunter.adapters.registry_map import AGGREGATOR_ADAPTERS, ATS_ADAPTERS
from ai_job_hunter.dedup import compute_job_id, dedup_jobs
from ai_job_hunter.models import JobPosting, ScoredJob
from ai_job_hunter.registry import AggregatorEntry, CompanyEntry
from ai_job_hunter.scoring.filters import is_relevant
from ai_job_hunter.scoring.profile import ScoringProfile
from ai_job_hunter.scoring.scorer import score_job

if TYPE_CHECKING:
    from ai_job_hunter.notifiers.dispatcher import NotifierDispatcher
    from ai_job_hunter.sheets.writer import SheetsWriter, SyncResult


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


def fetch_score_and_dedup(
    companies: list[CompanyEntry],
    aggregators: list[AggregatorEntry],
    profile: ScoringProfile,
    session: RateLimitedSession | None = None,
) -> list[ScoredJob]:
    """Fetch every source, keep only relevant postings, dedup, score, rank.

    Ranked descending by score.total_score. Sheet-write/notify are Phase 4/5
    concerns layered on top of this, not part of it.
    """
    results = fetch_all(companies, aggregators, session=session)
    all_jobs = [job for jobs in results.values() for job in jobs]
    relevant_jobs = [job for job in all_jobs if is_relevant(job, profile)]
    deduped_jobs = dedup_jobs(relevant_jobs)

    scored_jobs = [
        ScoredJob(
            job=job,
            score=score_job(job, profile),
            job_id=compute_job_id(job.company, job.title, job.url),
        )
        for job in deduped_jobs
    ]
    scored_jobs.sort(key=lambda scored: scored.score.total_score, reverse=True)
    return scored_jobs


@dataclass
class RunResult:
    open_roles: SyncResult
    target_companies: SyncResult


def run(
    companies: list[CompanyEntry],
    aggregators: list[AggregatorEntry],
    profile: ScoringProfile,
    writer: SheetsWriter,
    score_threshold: float,
    notify_threshold: float = float("inf"),
    notifier: NotifierDispatcher | None = None,
    session: RateLimitedSession | None = None,
) -> RunResult:
    """The full pipeline: fetch, filter, dedup, score, sync, then notify.

    Notifications fire only for jobs newly appended THIS run (never for rows
    that already existed) — "already notified" is structural, not a separate
    log; see docs/adr/0003 for the tradeoff this implies.
    """
    scored_jobs = fetch_score_and_dedup(companies, aggregators, profile, session=session)
    open_roles_result = writer.sync_open_roles(scored_jobs, score_threshold)
    target_companies_result = writer.sync_target_companies(companies)

    if notifier is not None:
        notifiable = [
            scored
            for scored in open_roles_result.appended
            if scored.score.total_score >= notify_threshold
        ]
        notifier.notify(notifiable)

    return RunResult(open_roles=open_roles_result, target_companies=target_companies_result)

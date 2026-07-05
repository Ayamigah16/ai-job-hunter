"""Notifier interface.

Implementations should raise on failure (SMTP/HTTP errors) rather than
swallow it — `NotifierDispatcher` is what isolates one channel's failure from
the others, not the individual notifiers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ai_job_hunter.models import ScoredJob


class Notifier(Protocol):
    def notify(self, new_jobs: list[ScoredJob]) -> None: ...


def format_job_summary(new_jobs: list[ScoredJob]) -> str:
    """Plain-text summary shared by every notifier — one line per job, score first."""
    lines = [f"{len(new_jobs)} new high-match role(s):", ""]
    for scored in new_jobs:
        job = scored.job
        lines.append(f"[{scored.score.total_score:.0f}] {job.company} - {job.title}")
        if job.url:
            lines.append(f"  {job.url}")
    return "\n".join(lines)

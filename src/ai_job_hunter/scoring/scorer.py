"""Pure scoring function: JobPosting + ScoringProfile -> ScoreResult. No I/O."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_job_hunter.models import ScoreResult
from ai_job_hunter.scoring.filters import (
    africa_friendly_hint,
    is_remote_friendly,
    matched_must_have_skills,
    matched_nice_to_have_skills,
    matches_role_title,
    sponsorship_mentioned,
)

if TYPE_CHECKING:
    from ai_job_hunter.models import JobPosting
    from ai_job_hunter.scoring.profile import ScoringProfile


def score_job(job: JobPosting, profile: ScoringProfile) -> ScoreResult:
    must_have = matched_must_have_skills(job, profile)
    nice_to_have = matched_nice_to_have_skills(job, profile)
    role_title_matched = matches_role_title(job, profile)
    remote_positive = is_remote_friendly(job, profile)
    salary_disclosed = job.salary_min is not None or job.salary_max is not None
    sponsorship = sponsorship_mentioned(job, profile)

    weights = profile.weights
    total_score = (
        len(must_have) * weights.get("must_have_match", 0)
        + len(nice_to_have) * weights.get("nice_to_have_match", 0)
        + (weights.get("role_title_match", 0) if role_title_matched else 0)
        + (weights.get("remote_positive", 0) if remote_positive else 0)
        + (weights.get("salary_disclosed", 0) if salary_disclosed else 0)
        + (weights.get("sponsorship_mentioned", 0) if sponsorship else 0)
    )

    return ScoreResult(
        total_score=total_score,
        matched_must_have=must_have,
        matched_nice_to_have=nice_to_have,
        sponsorship_mentioned=sponsorship,
        salary_disclosed=salary_disclosed,
        africa_friendly_hint=africa_friendly_hint(job, profile),
    )

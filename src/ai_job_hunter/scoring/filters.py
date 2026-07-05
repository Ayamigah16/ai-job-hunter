"""Pure filter predicates over a JobPosting + ScoringProfile. No I/O."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ai_job_hunter.models import JobPosting
    from ai_job_hunter.scoring.profile import ScoringProfile

AfricaFriendlyHint = Literal["likely", "unlikely", "unknown"]


def _searchable_text(job: JobPosting) -> str:
    return f"{job.title}\n{job.description_raw}\n{job.location_raw}".lower()


def matches_role_title(job: JobPosting, profile: ScoringProfile) -> bool:
    title_lower = job.title.lower()
    return any(keyword.lower() in title_lower for keyword in profile.role_title_keywords)


def matched_must_have_skills(job: JobPosting, profile: ScoringProfile) -> list[str]:
    text = _searchable_text(job)
    return [skill for skill in profile.must_have_skills if skill.lower() in text]


def matched_nice_to_have_skills(job: JobPosting, profile: ScoringProfile) -> list[str]:
    text = _searchable_text(job)
    return [skill for skill in profile.nice_to_have_skills if skill.lower() in text]


def is_relevant(job: JobPosting, profile: ScoringProfile) -> bool:
    """The primary noise filter.

    Company-scoped ATS adapters return every open role at that company, not
    just DevOps/Platform postings — GitLab's board alone has 100+ jobs across
    every department. A posting only survives if it matches one of the target
    role titles OR mentions at least one must-have skill; everything else
    (Sales, Marketing, unrelated engineering roles, ...) is dropped before
    scoring rather than just scored low.
    """
    return matches_role_title(job, profile) or bool(matched_must_have_skills(job, profile))


def is_remote_friendly(job: JobPosting, profile: ScoringProfile) -> bool:
    if job.remote is True:
        return True
    text = _searchable_text(job)
    return any(keyword.lower() in text for keyword in profile.remote_positive_keywords)


def sponsorship_mentioned(job: JobPosting, profile: ScoringProfile) -> bool:
    text = _searchable_text(job)
    return any(keyword.lower() in text for keyword in profile.sponsorship_keywords)


def africa_friendly_hint(job: JobPosting, profile: ScoringProfile) -> AfricaFriendlyHint:
    text = _searchable_text(job)
    if any(keyword.lower() in text for keyword in profile.africa_friendly_negative_keywords):
        return "unlikely"
    if any(keyword.lower() in text for keyword in profile.africa_friendly_positive_keywords):
        return "likely"
    return "unknown"

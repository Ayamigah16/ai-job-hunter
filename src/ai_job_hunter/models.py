"""Core data models shared across adapters, scoring, sheets, and notifiers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


class ATSType(StrEnum):
    """ATS platforms with a working adapter (see adapters/registry_map.py)."""

    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    WORKABLE = "workable"
    SMARTRECRUITERS = "smartrecruiters"
    BAMBOOHR = "bamboohr"
    RECRUITEE = "recruitee"
    PERSONIO = "personio"
    # Tracked (e.g. in the Target Companies sheet) but its real ATS (Workday,
    # Teamtailor, an in-house board, ...) has no adapter yet — the pipeline
    # skips fetching for these without treating it as an error.
    UNSUPPORTED = "unsupported"


class AggregatorType(StrEnum):
    """Standalone job aggregator sources (not tied to one company)."""

    REMOTEOK = "remoteok"
    ARBEITNOW = "arbeitnow"
    REMOTIVE = "remotive"
    HIMALAYAS = "himalayas"
    WEWORKREMOTELY = "weworkremotely"


class HiresInAfrica(StrEnum):
    UNKNOWN = "unknown"
    YES = "yes"
    NO = "no"


class Priority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class JobPosting:
    """A single job posting, normalized from whatever shape its source returns."""

    company: str
    title: str
    location_raw: str
    remote: bool | None
    department: str | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    tech_stack: list[str]
    url: str | None
    posted_date: date | None
    deadline: date | None
    source_ats: str
    raw_native_id: str | None
    description_raw: str
    fetched_at: datetime


@dataclass(frozen=True)
class ScoreResult:
    total_score: float
    matched_must_have: list[str] = field(default_factory=list)
    matched_nice_to_have: list[str] = field(default_factory=list)
    sponsorship_mentioned: bool = False
    salary_disclosed: bool = False
    africa_friendly_hint: str = "unknown"  # "likely" | "unlikely" | "unknown"


@dataclass(frozen=True)
class ScoredJob:
    job: JobPosting
    score: ScoreResult
    job_id: str

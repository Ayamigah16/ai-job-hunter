"""Stable job identity + cross-source dedup.

The same posting is often visible from more than one source (a company's own
board and an aggregator that also indexed it). `compute_job_id` gives both
occurrences the same id so they collapse into one. It's also recomputed
against existing Google Sheet rows during sync (Phase 4) rather than stored
separately — see docs/adr/0003 once that phase lands.
"""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ai_job_hunter.models import JobPosting

_WHITESPACE_RE = re.compile(r"\s+")
_TRACKING_PREFIXES = ("utm_", "ref", "source", "gh_src")


def _normalize_url(url: str) -> str:
    parts = urlsplit(url.strip().lower())
    query_pairs = [
        pair
        for pair in parts.query.split("&")
        if pair and not pair.split("=", 1)[0].startswith(_TRACKING_PREFIXES)
    ]
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc, path, "&".join(query_pairs), ""))


def _normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.strip().lower())


def compute_job_id(company: str, title: str, url: str | None) -> str:
    """A stable id for one job posting, independent of which source found it."""
    if url:
        key_source = _normalize_url(url)
    else:
        key_source = f"{_normalize_text(company)}|{_normalize_text(title)}"
    return hashlib.sha256(key_source.encode("utf-8")).hexdigest()[:16]


def dedup_jobs(jobs: Iterable[JobPosting]) -> list[JobPosting]:
    """Collapse postings that resolve to the same job_id.

    Keeps the first occurrence encountered — callers that care which source
    "wins" should order `jobs` accordingly before calling this.
    """
    seen: set[str] = set()
    deduped: list[JobPosting] = []
    for job in jobs:
        job_id = compute_job_id(job.company, job.title, job.url)
        if job_id in seen:
            continue
        seen.add(job_id)
        deduped.append(job)
    return deduped

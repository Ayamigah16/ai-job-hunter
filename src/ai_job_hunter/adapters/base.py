"""Shared adapter interfaces + a rate-limited HTTP session.

Company-scoped ATS adapters implement `BaseATSAdapter`; standalone job-board
aggregators implement `BaseAggregatorAdapter`. Both funnel through
`_safe_parse_many` so one malformed record never aborts a whole fetch.
"""

from __future__ import annotations

import html
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import urlparse

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from ai_job_hunter.models import AggregatorType, ATSType, JobPosting
    from ai_job_hunter.registry import AggregatorEntry, CompanyEntry

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"[ \t]+")


def strip_html(raw_html: str) -> str:
    """Best-effort plain-text extraction from a job description's HTML.

    Not a full HTML parser — good enough for scoring/keyword-matching, not for
    re-rendering. Collapses tags to spaces and unescapes entities.
    """
    if not raw_html:
        return ""
    # Unescape before stripping tags: some sources (e.g. certain Greenhouse
    # boards) double-encode their content, so a literal "&lt;div&gt;" only
    # becomes a real "<div>" tag after this pass — stripping tags first would
    # miss it and leave visible "<div>" text behind.
    text = html.unescape(raw_html)
    text = _TAG_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


class RateLimitedSession:
    """requests.Session wrapper that enforces a minimum delay per host."""

    def __init__(self, min_interval_seconds: float = 1.0, timeout: float = 15.0):
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "ai-job-hunter/0.1 (+personal job search tool)"
        self._min_interval = min_interval_seconds
        self._timeout = timeout
        self._last_request_at: dict[str, float] = {}

    def get(self, url: str, **kwargs) -> requests.Response:
        host = urlparse(url).netloc
        last = self._last_request_at.get(host)
        if last is not None:
            elapsed = time.monotonic() - last
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
        kwargs.setdefault("timeout", self._timeout)
        response = self._get_with_retry(url, **kwargs)
        self._last_request_at[host] = time.monotonic()
        return response

    # Retries transient network failures (connection resets, timeouts) up to
    # 3 attempts with exponential backoff. Deliberately does NOT retry on
    # HTTP error status codes (e.g. 5xx) — adapters interpret 404 specially
    # (empty board) and call response.raise_for_status() themselves for
    # everything else, so retrying here too would double up that decision.
    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _get_with_retry(self, url: str, **kwargs) -> requests.Response:
        return self._session.get(url, **kwargs)


def _safe_parse_many(raw_list: list[dict], parse_one, source_label: str) -> list[JobPosting]:
    postings: list[JobPosting] = []
    for raw in raw_list:
        try:
            job = parse_one(raw)
        except Exception:
            logger.warning("Skipping unparseable record from %s", source_label, exc_info=True)
            continue
        if job is not None:
            postings.append(job)
    return postings


class BaseATSAdapter(ABC):
    """One subclass per ATS platform; `registry_map.py` maps ATSType -> class."""

    ats_type: ClassVar[ATSType]

    def __init__(self, session: RateLimitedSession | None = None):
        self.session = session or RateLimitedSession()
        self.last_fetch_error: str | None = None

    @abstractmethod
    def fetch_raw(self, company: CompanyEntry) -> list[dict]:
        """Fetch raw postings for one company. Return [] on 404 / no postings."""

    @abstractmethod
    def parse(self, raw: dict, company: CompanyEntry) -> JobPosting | None:
        """Parse one raw record; return None if it can't be mapped."""

    def fetch_and_parse(self, company: CompanyEntry) -> list[JobPosting]:
        self.last_fetch_error = None
        try:
            raw_list = self.fetch_raw(company)
        except Exception as exc:
            logger.warning("Fetch failed for company %s", company.name, exc_info=True)
            self.last_fetch_error = str(exc)
            return []
        return _safe_parse_many(
            raw_list, lambda raw: self.parse(raw, company), source_label=company.name
        )


class BaseAggregatorAdapter(ABC):
    """One subclass per standalone job aggregator; not tied to a single company."""

    source_type: ClassVar[AggregatorType]

    def __init__(self, session: RateLimitedSession | None = None):
        self.session = session or RateLimitedSession()
        self.last_fetch_error: str | None = None

    @abstractmethod
    def fetch_raw(self, aggregator: AggregatorEntry) -> list[dict]:
        """Fetch raw postings for this aggregator source."""

    @abstractmethod
    def parse(self, raw: dict, aggregator: AggregatorEntry) -> JobPosting | None:
        """Parse one raw record; return None if it can't be mapped."""

    def fetch_and_parse(self, aggregator: AggregatorEntry) -> list[JobPosting]:
        self.last_fetch_error = None
        try:
            raw_list = self.fetch_raw(aggregator)
        except Exception as exc:
            logger.warning("Fetch failed for aggregator %s", aggregator.name, exc_info=True)
            self.last_fetch_error = str(exc)
            return []
        return _safe_parse_many(
            raw_list, lambda raw: self.parse(raw, aggregator), source_label=aggregator.name
        )

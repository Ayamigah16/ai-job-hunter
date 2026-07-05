"""Adapter for the We Work Remotely job aggregator.

We Work Remotely does not offer a JSON API; each job category publishes an
RSS 2.0 feed at `GET https://weworkremotely.com/categories/{category}.rss`
(verified live against the "remote-devops-sysadmin-jobs" category). The feed
is parsed with `feedparser`, and each entry is converted into a plain dict so
`parse()` has the same consistent-dict interface as the JSON-backed
aggregators.

We Work Remotely's RSS `<title>` is conventionally formatted as
`"Company Name: Job Title"`. This is split on the FIRST `": "` to separate
company from title; if no `": "` is present, the whole string is treated as
the title and `company` is left as `None` (the record is then dropped by
`parse()` since `company` is a required `JobPosting` field).

We Work Remotely is a remote-only job board by definition, so `remote` is
always `True` rather than inferred from any field. `department`, `salary_*`,
and `tech_stack` are not available from this feed and are left as
None/None/[]. There's no separate numeric job ID readily available in the
RSS, so `raw_native_id` reuses the job's URL.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING

import feedparser

from ai_job_hunter.adapters.base import BaseAggregatorAdapter, strip_html
from ai_job_hunter.models import AggregatorType, JobPosting

if TYPE_CHECKING:
    from ai_job_hunter.registry import AggregatorEntry

_FEED_URL_TEMPLATE = "https://weworkremotely.com/categories/{category}.rss"
_TITLE_SEPARATOR = ": "


def _split_company_and_title(raw_title: str) -> tuple[str | None, str]:
    if _TITLE_SEPARATOR in raw_title:
        company, title = raw_title.split(_TITLE_SEPARATOR, 1)
        return company, title
    return None, raw_title


def _parse_posted_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).date()
    except (TypeError, ValueError):
        return None


class WeWorkRemotelyAdapter(BaseAggregatorAdapter):
    """Fetches and normalizes postings from the We Work Remotely RSS feeds."""

    source_type = AggregatorType.WEWORKREMOTELY

    def fetch_raw(self, aggregator: AggregatorEntry) -> list[dict]:
        if not aggregator.category:
            return []

        url = _FEED_URL_TEMPLATE.format(category=aggregator.category)
        response = self.session.get(url)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        if not response.text:
            return []

        feed = feedparser.parse(response.text)
        if not feed.entries:
            return []

        return [
            {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", ""),
            }
            for entry in feed.entries
        ]

    def parse(self, raw: dict, aggregator: AggregatorEntry) -> JobPosting | None:
        company, title = _split_company_and_title(raw.get("title", ""))
        if not company or not title:
            return None

        link = raw.get("link") or None

        return JobPosting(
            company=company,
            title=title,
            location_raw="",
            remote=True,
            department=None,
            salary_min=None,
            salary_max=None,
            salary_currency=None,
            tech_stack=[],
            url=link,
            posted_date=_parse_posted_date(raw.get("published")),
            deadline=None,
            source_ats=self.source_type.value,
            raw_native_id=link,
            description_raw=strip_html(raw.get("summary", "")),
            fetched_at=datetime.now(UTC),
        )

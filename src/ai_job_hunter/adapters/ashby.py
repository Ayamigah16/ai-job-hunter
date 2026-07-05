"""Adapter for companies whose careers site is powered by Ashby.

Ashby exposes a public, unauthenticated job board API per company:
`GET https://api.ashbyhq.com/posting-api/job-board/{board_token}?includeCompensation=true`,
returning `{"jobs": [...], "apiVersion": ...}` (verified live against
jobs.ashbyhq.com/supabase). Compensation is only present/populated when a
company opts in to disclosing it; most postings return empty
`compensation.summaryComponents`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from ai_job_hunter.adapters.base import BaseATSAdapter, strip_html
from ai_job_hunter.models import ATSType, JobPosting

if TYPE_CHECKING:
    from ai_job_hunter.registry import CompanyEntry


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


class AshbyAdapter(BaseATSAdapter):
    """Fetches and normalizes postings from an Ashby job board."""

    ats_type = ATSType.ASHBY

    def fetch_raw(self, company: CompanyEntry) -> list[dict]:
        if not company.board_token:
            return []

        url = (
            f"https://api.ashbyhq.com/posting-api/job-board/{company.board_token}"
            "?includeCompensation=true"
        )
        response = self.session.get(url)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        if not response.content:
            return []

        data = response.json()
        return data.get("jobs", []) or []

    def parse(self, raw: dict, company: CompanyEntry) -> JobPosting | None:
        native_id = raw.get("id")
        title = raw.get("title")
        if not native_id or not title:
            return None

        salary_min, salary_max, salary_currency = _extract_compensation(raw.get("compensation"))

        return JobPosting(
            company=company.name,
            title=title,
            location_raw=raw.get("location") or "",
            remote=raw.get("isRemote"),
            department=raw.get("department"),
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            tech_stack=[],
            url=raw.get("jobUrl") or raw.get("applyUrl"),
            posted_date=_parse_date(raw.get("publishedAt")),
            deadline=None,
            source_ats=self.ats_type.value,
            raw_native_id=str(native_id),
            description_raw=strip_html(raw.get("descriptionHtml") or ""),
            fetched_at=datetime.now(UTC),
        )


def _extract_compensation(
    compensation: dict | None,
) -> tuple[int | None, int | None, str | None]:
    if not compensation:
        return None, None, None

    components = compensation.get("summaryComponents") or []
    if not components:
        return None, None, None

    first = components[0]
    min_value = first.get("minValue")
    max_value = first.get("maxValue")
    currency = first.get("currencyCode")

    salary_min = int(min_value) if min_value is not None else None
    salary_max = int(max_value) if max_value is not None else None
    return salary_min, salary_max, currency

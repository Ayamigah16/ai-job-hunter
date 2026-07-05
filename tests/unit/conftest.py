from datetime import UTC, datetime

import pytest

from ai_job_hunter.models import JobPosting


@pytest.fixture
def make_job():
    def _make_job(
        company: str = "Acme",
        title: str = "Platform Engineer",
        location_raw: str = "Remote",
        remote: bool | None = True,
        description_raw: str = "",
        url: str | None = "https://example.com/jobs/1",
        salary_min: int | None = None,
        salary_max: int | None = None,
        source_ats: str = "greenhouse",
    ) -> JobPosting:
        return JobPosting(
            company=company,
            title=title,
            location_raw=location_raw,
            remote=remote,
            department=None,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=None,
            tech_stack=[],
            url=url,
            posted_date=None,
            deadline=None,
            source_ats=source_ats,
            raw_native_id=None,
            description_raw=description_raw,
            fetched_at=datetime.now(UTC),
        )

    return _make_job

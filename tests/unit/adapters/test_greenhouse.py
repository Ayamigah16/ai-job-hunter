from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from ai_job_hunter.adapters.greenhouse import GreenhouseAdapter
from ai_job_hunter.models import ATSType
from ai_job_hunter.registry import CompanyEntry

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent / "fixtures" / "greenhouse" / "sample_response.json"
)


@pytest.fixture
def company() -> CompanyEntry:
    return CompanyEntry(
        name="Example Co",
        slug="exampleco",
        ats_type=ATSType.GREENHOUSE,
        board_token="exampleco",
    )


@pytest.fixture
def raw_jobs() -> list[dict]:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return data["jobs"]


def test_ats_type_is_greenhouse():
    assert GreenhouseAdapter.ats_type == ATSType.GREENHOUSE


def test_parse_remote_posting(raw_jobs: list[dict], company: CompanyEntry):
    adapter = GreenhouseAdapter()
    job = adapter.parse(raw_jobs[0], company)

    assert job is not None
    assert job.company == "Example Co"
    assert job.title == "Senior Platform Engineer"
    assert job.location_raw == "Remote - US"
    assert job.remote is True
    assert job.department == "Engineering"
    assert job.url == "https://job-boards.greenhouse.io/exampleco/jobs/1111111"
    assert job.posted_date == date(2026, 5, 20)
    assert job.raw_native_id == "1111111"
    assert job.source_ats == "greenhouse"
    assert job.tech_stack == []
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency is None
    assert job.deadline is None
    assert "Senior Platform Engineer" in job.description_raw
    assert "<p>" not in job.description_raw
    assert "<strong>" not in job.description_raw


def test_parse_onsite_posting(raw_jobs: list[dict], company: CompanyEntry):
    adapter = GreenhouseAdapter()
    job = adapter.parse(raw_jobs[1], company)

    assert job is not None
    assert job.location_raw == "Berlin, Germany"
    assert job.remote is False
    assert job.department == "Infrastructure"
    assert job.posted_date == date(2026, 5, 10)


def test_parse_infers_remote_from_title_when_location_ambiguous(
    raw_jobs: list[dict], company: CompanyEntry
):
    adapter = GreenhouseAdapter()
    job = adapter.parse(raw_jobs[2], company)

    assert job is not None
    assert job.location_raw == "Anywhere"
    assert job.remote is True  # "Remote" only appears in the title, not the location
    assert job.department is None
    # No first_published in this fixture entry -> falls back to updated_at.
    assert job.posted_date == date(2026, 4, 1)


def test_parse_returns_none_for_missing_required_fields(company: CompanyEntry):
    adapter = GreenhouseAdapter()
    assert adapter.parse({"title": "No ID"}, company) is None
    assert adapter.parse({"id": 42}, company) is None


def test_fetch_raw_returns_empty_list_on_404(company: CompanyEntry, monkeypatch):
    adapter = GreenhouseAdapter()

    class FakeResponse:
        status_code = 404
        content = b""

        def raise_for_status(self):
            raise AssertionError("should not be called for a 404")

        def json(self):
            raise AssertionError("should not be called for a 404")

    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: FakeResponse())
    assert adapter.fetch_raw(company) == []


def test_fetch_raw_returns_empty_list_without_board_token():
    adapter = GreenhouseAdapter()
    company = CompanyEntry(
        name="No Token Co",
        slug="notoken",
        ats_type=ATSType.GREENHOUSE,
        board_token=None,
    )
    assert adapter.fetch_raw(company) == []

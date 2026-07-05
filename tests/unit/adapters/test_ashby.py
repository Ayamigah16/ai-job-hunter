from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from ai_job_hunter.adapters.ashby import AshbyAdapter
from ai_job_hunter.models import ATSType
from ai_job_hunter.registry import CompanyEntry

FIXTURE_PATH = Path(__file__).parent.parent.parent / "fixtures" / "ashby" / "sample_response.json"


@pytest.fixture
def company() -> CompanyEntry:
    return CompanyEntry(
        name="Example Co",
        slug="exampleco",
        ats_type=ATSType.ASHBY,
        board_token="exampleco",
    )


@pytest.fixture
def raw_postings() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["jobs"]


def test_ats_type_is_ashby():
    assert AshbyAdapter.ats_type == ATSType.ASHBY


def test_parse_remote_posting_with_disclosed_compensation(
    raw_postings: list[dict], company: CompanyEntry
):
    adapter = AshbyAdapter()
    job = adapter.parse(raw_postings[0], company)

    assert job is not None
    assert job.company == "Example Co"
    assert job.title == "Senior Platform Engineer"
    assert job.location_raw == "Remote"
    assert job.remote is True
    assert job.department == "Engineering"
    assert job.url == (
        "https://jobs.ashbyhq.com/exampleco/11111111-aaaa-bbbb-cccc-111111111111"
    )
    assert job.posted_date == date(2026, 5, 18)
    assert job.raw_native_id == "11111111-aaaa-bbbb-cccc-111111111111"
    assert job.source_ats == "ashby"
    assert job.tech_stack == []
    assert job.deadline is None
    assert job.salary_min == 150000
    assert job.salary_max == 190000
    assert job.salary_currency == "USD"
    assert "Senior Platform Engineer" in job.description_raw
    assert "<p>" not in job.description_raw
    assert "<strong>" not in job.description_raw


def test_parse_onsite_posting_without_disclosed_compensation(
    raw_postings: list[dict], company: CompanyEntry
):
    adapter = AshbyAdapter()
    job = adapter.parse(raw_postings[1], company)

    assert job is not None
    assert job.title == "Office Coordinator"
    assert job.location_raw == "Berlin, Germany"
    assert job.remote is False
    assert job.department == "Operations"
    assert job.posted_date == date(2026, 5, 10)
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency is None


def test_parse_handles_missing_compensation_key(raw_postings: list[dict], company: CompanyEntry):
    adapter = AshbyAdapter()
    raw = raw_postings[2]
    assert "compensation" not in raw  # exercising the missing-key path

    job = adapter.parse(raw, company)

    assert job is not None
    assert job.title == "Data Engineer"
    assert job.location_raw == "Remote - EMEA"
    assert job.remote is True
    assert job.department == "Data"
    assert job.posted_date == date(2026, 4, 22)
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency is None


def test_parse_returns_none_for_missing_required_fields(company: CompanyEntry):
    adapter = AshbyAdapter()
    assert adapter.parse({"title": "No ID"}, company) is None
    assert adapter.parse({"id": "abc-123"}, company) is None


def test_fetch_raw_returns_empty_list_on_404(company: CompanyEntry, monkeypatch):
    adapter = AshbyAdapter()

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
    adapter = AshbyAdapter()
    company = CompanyEntry(
        name="No Token Co",
        slug="notoken",
        ats_type=ATSType.ASHBY,
        board_token=None,
    )
    assert adapter.fetch_raw(company) == []


def test_fetch_raw_returns_all_postings_from_jobs_key(company: CompanyEntry, monkeypatch):
    adapter = AshbyAdapter()
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    class FakeResponse:
        status_code = 200
        content = b"{...}"

        def raise_for_status(self):
            pass

        def json(self):
            return payload

    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: FakeResponse())
    result = adapter.fetch_raw(company)
    assert result == payload["jobs"]
    assert len(result) == 3

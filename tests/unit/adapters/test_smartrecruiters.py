from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from ai_job_hunter.adapters.smartrecruiters import SmartRecruitersAdapter
from ai_job_hunter.models import ATSType
from ai_job_hunter.registry import CompanyEntry

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent / "fixtures" / "smartrecruiters" / "sample_response.json"
)


@pytest.fixture
def company() -> CompanyEntry:
    return CompanyEntry(
        name="Example Co",
        slug="exampleco",
        ats_type=ATSType.SMARTRECRUITERS,
        board_token="exampleco",
    )


@pytest.fixture
def raw_postings() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["content"]


def test_ats_type_is_smartrecruiters():
    assert SmartRecruitersAdapter.ats_type == ATSType.SMARTRECRUITERS


def test_parse_remote_via_explicit_location_flag(raw_postings: list[dict], company: CompanyEntry):
    adapter = SmartRecruitersAdapter()
    job = adapter.parse(raw_postings[0], company)

    assert job is not None
    assert job.company == "Example Co"
    assert job.title == "Senior Data Engineer"
    assert job.location_raw == "de"
    assert job.remote is True
    assert job.department == "Engineering"
    assert job.url == (
        "https://jobs.smartrecruiters.com/exampleco/744000111222333-senior-data-engineer?oga=true"
    )
    assert job.posted_date == date(2026, 6, 15)
    assert job.raw_native_id == "744000111222333"
    assert job.source_ats == "smartrecruiters"
    assert job.tech_stack == []
    assert job.deadline is None
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency is None
    assert "data platform" in job.description_raw
    assert "<p>" not in job.description_raw
    assert "<strong>" not in job.description_raw


def test_parse_onsite_posting_with_explicit_remote_false(
    raw_postings: list[dict], company: CompanyEntry
):
    adapter = SmartRecruitersAdapter()
    job = adapter.parse(raw_postings[1], company)

    assert job is not None
    assert job.title == "Office Manager"
    assert job.location_raw == "Munich, Bavaria, de"
    assert job.remote is False
    assert job.department == "Operations"
    assert job.url == (
        "https://jobs.smartrecruiters.com/exampleco/744000111222334-office-manager?oga=true"
    )
    assert job.posted_date == date(2026, 5, 28)
    assert job.raw_native_id == "744000111222334"


def test_parse_missing_apply_url_falls_back_to_constructed_url(
    raw_postings: list[dict], company: CompanyEntry
):
    adapter = SmartRecruitersAdapter()
    raw = raw_postings[2]
    assert "applyUrl" not in raw
    assert "remote" not in (raw.get("location") or {})

    job = adapter.parse(raw, company)

    assert job is not None
    assert job.title == "Remote Site Reliability Engineer"
    assert job.location_raw == ""  # city/region/country all blank for this posting
    assert job.remote is True  # inferred from "Remote" in the title, no location.remote key
    assert job.department == "Engineering"
    assert job.url == "https://jobs.smartrecruiters.com/exampleco/744000111222335"
    assert job.posted_date == date(2026, 4, 10)
    assert job.raw_native_id == "744000111222335"


def test_parse_returns_none_for_missing_required_fields(company: CompanyEntry):
    adapter = SmartRecruitersAdapter()
    assert adapter.parse({"name": "No id"}, company) is None
    assert adapter.parse({"id": "123"}, company) is None


def test_fetch_raw_returns_empty_list_on_404(company: CompanyEntry, monkeypatch):
    adapter = SmartRecruitersAdapter()

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
    adapter = SmartRecruitersAdapter()
    company = CompanyEntry(
        name="No Token Co",
        slug="notoken",
        ats_type=ATSType.SMARTRECRUITERS,
        board_token=None,
    )
    assert adapter.fetch_raw(company) == []


def test_fetch_raw_returns_empty_list_when_content_array_is_empty(
    company: CompanyEntry, monkeypatch
):
    adapter = SmartRecruitersAdapter()

    class FakeResponse:
        status_code = 200
        content = b'{"offset": 0, "limit": 100, "totalFound": 0, "content": []}'

        def raise_for_status(self):
            pass

        def json(self):
            return {"offset": 0, "limit": 100, "totalFound": 0, "content": []}

    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: FakeResponse())
    assert adapter.fetch_raw(company) == []


def test_fetch_raw_returns_all_postings_from_content_key(company: CompanyEntry, monkeypatch):
    adapter = SmartRecruitersAdapter()
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
    assert result == payload["content"]
    assert len(result) == 3

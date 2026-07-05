from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from ai_job_hunter.adapters.recruitee import RecruiteeAdapter
from ai_job_hunter.models import ATSType
from ai_job_hunter.registry import CompanyEntry

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent / "fixtures" / "recruitee" / "sample_response.json"
)


@pytest.fixture
def company() -> CompanyEntry:
    return CompanyEntry(
        name="Example Co",
        slug="exampleco",
        ats_type=ATSType.RECRUITEE,
        board_token="exampleco",
    )


@pytest.fixture
def raw_postings() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["offers"]


def test_ats_type_is_recruitee():
    assert RecruiteeAdapter.ats_type == ATSType.RECRUITEE


def test_parse_remote_via_explicit_remote_flag(raw_postings: list[dict], company: CompanyEntry):
    adapter = RecruiteeAdapter()
    job = adapter.parse(raw_postings[0], company)

    assert job is not None
    assert job.company == "Example Co"
    assert job.title == "Senior Contracts Administrator"
    assert job.location_raw == "Remote job"
    assert job.remote is True  # explicit remote=true
    assert job.department == "Legal"
    assert job.url == "https://exampleco.recruitee.com/o/senior-contracts-administrator"
    assert job.posted_date == date(2026, 6, 26)
    assert job.raw_native_id == "2656780"
    assert job.source_ats == "recruitee"
    assert job.tech_stack == []
    assert job.deadline is None
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency is None
    assert "Senior Contracts Administrator" in job.description_raw
    assert "<p>" not in job.description_raw
    assert "<strong>" not in job.description_raw


def test_parse_onsite_posting_with_explicit_remote_false(
    raw_postings: list[dict], company: CompanyEntry
):
    adapter = RecruiteeAdapter()
    job = adapter.parse(raw_postings[1], company)

    assert job is not None
    assert job.title == "Office Coordinator"
    assert job.location_raw == "Berlin, Germany"
    assert job.remote is False  # explicit remote=false
    assert job.department == "Operations"
    assert job.url == "https://exampleco.recruitee.com/o/office-coordinator"
    assert job.posted_date == date(2026, 5, 20)
    assert job.raw_native_id == "2660123"
    # No `description` key on this record at all.
    assert job.description_raw == ""


def test_parse_infers_remote_from_title_when_remote_key_missing(
    raw_postings: list[dict], company: CompanyEntry
):
    adapter = RecruiteeAdapter()
    raw = raw_postings[2]
    assert "remote" not in raw

    job = adapter.parse(raw, company)

    assert job is not None
    assert job.title == "Remote Site Reliability Engineer"
    assert job.location_raw == "Remote job"
    assert job.remote is True  # inferred via regex on location + title
    assert job.department == "Engineering"
    assert job.url == "https://exampleco.recruitee.com/o/remote-site-reliability-engineer"
    assert job.posted_date == date(2026, 4, 15)
    assert job.raw_native_id == "2664501"


def test_parse_returns_none_for_missing_required_fields(company: CompanyEntry):
    adapter = RecruiteeAdapter()
    assert adapter.parse({"title": "No id"}, company) is None
    assert adapter.parse({"id": 99}, company) is None


def test_fetch_raw_returns_empty_list_on_404(company: CompanyEntry, monkeypatch):
    adapter = RecruiteeAdapter()

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
    adapter = RecruiteeAdapter()
    company = CompanyEntry(
        name="No Token Co",
        slug="notoken",
        ats_type=ATSType.RECRUITEE,
        board_token=None,
    )
    assert adapter.fetch_raw(company) == []


def test_fetch_raw_returns_empty_list_when_offers_is_empty(company: CompanyEntry, monkeypatch):
    adapter = RecruiteeAdapter()

    class FakeResponse:
        status_code = 200
        content = b'{"offers": []}'

        def raise_for_status(self):
            pass

        def json(self):
            return {"offers": []}

    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: FakeResponse())
    assert adapter.fetch_raw(company) == []


def test_fetch_raw_returns_all_postings_from_offers_key(company: CompanyEntry, monkeypatch):
    adapter = RecruiteeAdapter()
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
    assert result == payload["offers"]
    assert len(result) == 3

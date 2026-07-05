from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from ai_job_hunter.adapters.workable import WorkableAdapter
from ai_job_hunter.models import ATSType
from ai_job_hunter.registry import CompanyEntry

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent / "fixtures" / "workable" / "sample_response.json"
)


@pytest.fixture
def company() -> CompanyEntry:
    return CompanyEntry(
        name="Example Co",
        slug="exampleco",
        ats_type=ATSType.WORKABLE,
        board_token="exampleco",
    )


@pytest.fixture
def raw_postings() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["jobs"]


def test_ats_type_is_workable():
    assert WorkableAdapter.ats_type == ATSType.WORKABLE


def test_parse_remote_via_nested_telecommuting_flag(
    raw_postings: list[dict], company: CompanyEntry
):
    adapter = WorkableAdapter()
    job = adapter.parse(raw_postings[0], company)

    assert job is not None
    assert job.company == "Example Co"
    assert job.title == "Senior Backend Engineer"
    assert job.location_raw == "San Francisco, CA, United States"
    assert job.remote is True  # location.telecommuting=true wins even though text isn't remote-y
    assert job.department == "Engineering"
    assert job.url == "https://apply.workable.com/exampleco/j/ABC123/"
    assert job.posted_date == date(2026, 6, 1)
    assert job.raw_native_id == "ABC123"
    assert job.source_ats == "workable"
    assert job.tech_stack == []
    assert job.deadline is None
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency is None
    assert "Senior Backend Engineer" in job.description_raw
    assert "<p>" not in job.description_raw
    assert "<strong>" not in job.description_raw


def test_parse_onsite_posting_with_explicit_telecommuting_false(
    raw_postings: list[dict], company: CompanyEntry
):
    adapter = WorkableAdapter()
    job = adapter.parse(raw_postings[1], company)

    assert job is not None
    assert job.title == "Office Coordinator"
    assert job.location_raw == "Berlin, Germany"
    assert job.remote is False
    assert job.department == "Operations"
    assert job.posted_date == date(2026, 5, 20)
    assert job.raw_native_id == "DEF456"


def test_parse_infers_remote_from_title_when_no_telecommuting_key(
    raw_postings: list[dict], company: CompanyEntry
):
    adapter = WorkableAdapter()
    raw = raw_postings[2]
    assert "telecommuting" not in (raw.get("location") or {})
    assert "telecommute" not in raw

    job = adapter.parse(raw, company)

    assert job is not None
    assert job.title == "Remote Site Reliability Engineer"
    assert job.location_raw == ""  # city/region/country all blank for this posting
    assert job.remote is True  # inferred from "Remote" in the title
    assert job.department == "Engineering"
    assert job.posted_date == date(2026, 4, 15)
    assert job.raw_native_id == "GHI789"


def test_parse_returns_none_for_missing_required_fields(company: CompanyEntry):
    adapter = WorkableAdapter()
    assert adapter.parse({"title": "No shortcode or id"}, company) is None
    assert adapter.parse({"shortcode": "XYZ"}, company) is None


def test_fetch_raw_returns_empty_list_on_404(company: CompanyEntry, monkeypatch):
    adapter = WorkableAdapter()

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
    adapter = WorkableAdapter()
    company = CompanyEntry(
        name="No Token Co",
        slug="notoken",
        ats_type=ATSType.WORKABLE,
        board_token=None,
    )
    assert adapter.fetch_raw(company) == []


def test_fetch_raw_returns_empty_list_when_jobs_array_is_empty(
    company: CompanyEntry, monkeypatch
):
    adapter = WorkableAdapter()

    class FakeResponse:
        status_code = 200
        content = b'{"name": "Example Co", "description": null, "jobs": []}'

        def raise_for_status(self):
            pass

        def json(self):
            return {"name": "Example Co", "description": None, "jobs": []}

    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: FakeResponse())
    assert adapter.fetch_raw(company) == []


def test_fetch_raw_returns_all_postings_from_jobs_key(company: CompanyEntry, monkeypatch):
    adapter = WorkableAdapter()
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

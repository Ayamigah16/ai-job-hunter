from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from ai_job_hunter.adapters.lever import LeverAdapter
from ai_job_hunter.models import ATSType
from ai_job_hunter.registry import CompanyEntry

FIXTURE_PATH = Path(__file__).parent.parent.parent / "fixtures" / "lever" / "sample_response.json"


@pytest.fixture
def company() -> CompanyEntry:
    return CompanyEntry(
        name="Example Co",
        slug="exampleco",
        ats_type=ATSType.LEVER,
        board_token="exampleco",
    )


@pytest.fixture
def raw_postings() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_ats_type_is_lever():
    assert LeverAdapter.ats_type == ATSType.LEVER


def test_parse_remote_posting_via_workplace_type(raw_postings: list[dict], company: CompanyEntry):
    adapter = LeverAdapter()
    job = adapter.parse(raw_postings[0], company)

    assert job is not None
    assert job.company == "Example Co"
    assert job.title == "Senior Backend Engineer"
    assert job.location_raw == "New York, NY or Remote"
    assert job.remote is True
    assert job.department == "Engineering"
    assert job.url == "https://jobs.lever.co/exampleco/aaaaaaaa-1111-2222-3333-444444444444"
    assert job.posted_date == date(2026, 5, 20)
    assert job.raw_native_id == "aaaaaaaa-1111-2222-3333-444444444444"
    assert job.source_ats == "lever"
    assert job.tech_stack == []
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency is None
    assert job.deadline is None
    assert "Senior Backend Engineer" in job.description_raw
    assert "<p>" not in job.description_raw
    assert "<strong>" not in job.description_raw


def test_parse_onsite_posting_via_workplace_type(raw_postings: list[dict], company: CompanyEntry):
    adapter = LeverAdapter()
    job = adapter.parse(raw_postings[1], company)

    assert job is not None
    assert job.title == "Office Manager"
    assert job.location_raw == "Berlin, Germany"
    assert job.remote is False
    assert job.department == "Operations"
    assert job.posted_date == date(2026, 5, 11)


def test_parse_falls_back_to_location_regex_when_workplace_type_missing(
    raw_postings: list[dict], company: CompanyEntry
):
    adapter = LeverAdapter()
    raw = raw_postings[2]
    assert "workplaceType" not in raw  # exercising the fallback path

    job = adapter.parse(raw, company)

    assert job is not None
    assert job.title == "Data Engineer"
    assert job.location_raw == "Remote - EMEA"
    assert job.remote is True  # inferred from "Remote" in categories.location
    assert job.department == "Data"
    assert job.posted_date == date(2026, 4, 26)


def test_parse_returns_none_for_missing_required_fields(company: CompanyEntry):
    adapter = LeverAdapter()
    assert adapter.parse({"text": "No ID"}, company) is None
    assert adapter.parse({"id": "abc-123"}, company) is None


def test_fetch_raw_returns_empty_list_on_404(company: CompanyEntry, monkeypatch):
    adapter = LeverAdapter()

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
    adapter = LeverAdapter()
    company = CompanyEntry(
        name="No Token Co",
        slug="notoken",
        ats_type=ATSType.LEVER,
        board_token=None,
    )
    assert adapter.fetch_raw(company) == []


def test_fetch_raw_returns_all_postings_from_json_array(company: CompanyEntry, monkeypatch):
    adapter = LeverAdapter()
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    class FakeResponse:
        status_code = 200
        content = b"[...]"

        def raise_for_status(self):
            pass

        def json(self):
            return payload

    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: FakeResponse())
    result = adapter.fetch_raw(company)
    assert result == payload
    assert len(result) == 3

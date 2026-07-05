from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from ai_job_hunter.adapters.bamboohr import BambooHRAdapter
from ai_job_hunter.models import ATSType
from ai_job_hunter.registry import CompanyEntry

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent / "fixtures" / "bamboohr" / "sample_response.json"
)


@pytest.fixture
def company() -> CompanyEntry:
    return CompanyEntry(
        name="Example Co",
        slug="exampleco",
        ats_type=ATSType.BAMBOOHR,
        board_token="exampleco",
    )


@pytest.fixture
def raw_postings() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["result"]


def test_ats_type_is_bamboohr():
    assert BambooHRAdapter.ats_type == ATSType.BAMBOOHR


def test_parse_remote_via_explicit_isremote_flag(raw_postings: list[dict], company: CompanyEntry):
    adapter = BambooHRAdapter()
    job = adapter.parse(raw_postings[0], company)

    assert job is not None
    assert job.company == "Example Co"
    assert job.title == "Senior Backend Engineer"
    assert job.location_raw == ""  # city/state both null for this fully-remote posting
    assert job.remote is True  # isRemote=true wins even though location text is empty
    assert job.department == "Engineering"
    assert job.url == "https://exampleco.bamboohr.com/careers/35"
    assert job.posted_date == date(2026, 6, 1)
    assert job.raw_native_id == "35"
    assert job.source_ats == "bamboohr"
    assert job.tech_stack == []
    assert job.deadline is None
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency is None
    assert "Senior Backend Engineer" in job.description_raw
    assert "<p>" not in job.description_raw
    assert "<strong>" not in job.description_raw


def test_parse_onsite_posting_with_explicit_isremote_false(
    raw_postings: list[dict], company: CompanyEntry
):
    adapter = BambooHRAdapter()
    job = adapter.parse(raw_postings[1], company)

    assert job is not None
    assert job.title == "Office Coordinator"
    assert job.location_raw == "Berlin, Berlin, Germany"
    assert job.remote is False
    # No `departmentLabel` key on this record — falls back to the documented
    # `department` key.
    assert job.department == "Operations"
    assert job.url == "https://exampleco.bamboohr.com/careers/36"
    assert job.posted_date == date(2026, 5, 20)
    assert job.raw_native_id == "36"


def test_parse_infers_remote_from_title_when_no_isremote_key(
    raw_postings: list[dict], company: CompanyEntry
):
    adapter = BambooHRAdapter()
    raw = raw_postings[2]
    assert "isRemote" not in raw

    job = adapter.parse(raw, company)

    assert job is not None
    assert job.title == "Remote Site Reliability Engineer"
    assert job.location_raw == ""  # city/state both null for this posting
    assert job.remote is True  # inferred from "Remote" in the title
    assert job.department == "Engineering"
    assert job.url == "https://exampleco.bamboohr.com/careers/37"
    assert job.posted_date == date(2026, 4, 15)
    assert job.raw_native_id == "37"
    # This record has no `description` key at all (matches the live list
    # endpoint, which only carries the full description on the detail page).
    assert job.description_raw == ""


def test_parse_returns_none_for_missing_required_fields(company: CompanyEntry):
    adapter = BambooHRAdapter()
    assert adapter.parse({"jobOpeningName": "No id"}, company) is None
    assert adapter.parse({"id": "99"}, company) is None


def test_fetch_raw_returns_empty_list_on_404(company: CompanyEntry, monkeypatch):
    adapter = BambooHRAdapter()

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
    adapter = BambooHRAdapter()
    company = CompanyEntry(
        name="No Token Co",
        slug="notoken",
        ats_type=ATSType.BAMBOOHR,
        board_token=None,
    )
    assert adapter.fetch_raw(company) == []


def test_fetch_raw_returns_empty_list_when_result_is_empty(company: CompanyEntry, monkeypatch):
    adapter = BambooHRAdapter()

    class FakeResponse:
        status_code = 200
        content = b'{"meta": {"totalCount": 0}, "result": []}'

        def raise_for_status(self):
            pass

        def json(self):
            return {"meta": {"totalCount": 0}, "result": []}

    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: FakeResponse())
    assert adapter.fetch_raw(company) == []


def test_fetch_raw_returns_all_postings_from_result_key(company: CompanyEntry, monkeypatch):
    adapter = BambooHRAdapter()
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
    assert result == payload["result"]
    assert len(result) == 3


def test_fetch_raw_handles_bare_top_level_list(company: CompanyEntry, monkeypatch):
    adapter = BambooHRAdapter()
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["result"]

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

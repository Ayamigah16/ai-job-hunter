from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from ai_job_hunter.adapters.aggregators.himalayas import HimalayasAdapter
from ai_job_hunter.models import AggregatorType
from ai_job_hunter.registry import AggregatorEntry

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "fixtures"
    / "aggregators"
    / "himalayas_sample_response.json"
)


@pytest.fixture
def aggregator() -> AggregatorEntry:
    return AggregatorEntry(
        name="Himalayas",
        source_type=AggregatorType.HIMALAYAS,
        search_terms=["backend", "python", "remote"],
    )


@pytest.fixture
def raw_payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_source_type_is_himalayas():
    assert HimalayasAdapter.source_type == AggregatorType.HIMALAYAS


class _FakeResponse:
    def __init__(self, status_code: int, content: bytes, payload: dict | None = None):
        self.status_code = status_code
        self.content = content
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_raw_returns_jobs_list(aggregator: AggregatorEntry, raw_payload: dict, monkeypatch):
    adapter = HimalayasAdapter()
    captured_url = {}

    def fake_get(url, **kwargs):
        captured_url["url"] = url
        return _FakeResponse(200, b"...", raw_payload)

    monkeypatch.setattr(adapter.session, "get", fake_get)

    result = adapter.fetch_raw(aggregator)

    assert result == raw_payload["jobs"]
    assert len(result) == 3
    assert captured_url["url"] == "https://himalayas.app/jobs/api"


def test_fetch_raw_returns_empty_list_on_404(aggregator: AggregatorEntry, monkeypatch):
    adapter = HimalayasAdapter()
    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: _FakeResponse(404, b""))

    assert adapter.fetch_raw(aggregator) == []


def test_fetch_raw_returns_empty_list_on_empty_response(aggregator: AggregatorEntry, monkeypatch):
    adapter = HimalayasAdapter()
    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: _FakeResponse(200, b""))

    assert adapter.fetch_raw(aggregator) == []


def test_fetch_raw_returns_empty_list_when_jobs_key_missing(
    aggregator: AggregatorEntry, monkeypatch
):
    adapter = HimalayasAdapter()
    monkeypatch.setattr(
        adapter.session,
        "get",
        lambda url, **kwargs: _FakeResponse(200, b"{}", {"totalCount": 0}),
    )

    assert adapter.fetch_raw(aggregator) == []


def test_parse_worldwide_posting_with_salary_and_full_description(
    raw_payload: dict, aggregator: AggregatorEntry
):
    adapter = HimalayasAdapter()
    job = adapter.parse(raw_payload["jobs"][0], aggregator)

    assert job is not None
    assert job.company == "CloudNine"
    assert job.title == "Senior Backend Engineer"
    assert job.location_raw == "Worldwide"
    assert job.remote is True
    assert job.department is None
    assert job.salary_min == 90000
    assert job.salary_max == 130000
    assert job.salary_currency == "USD"
    assert job.tech_stack == ["Backend-Engineering", "Python", "Django"]
    # url comes from applicationLink, which is distinct from guid here.
    assert job.url == "https://himalayas.app/apply/cloudnine/senior-backend-engineer"
    assert job.posted_date == date(2026, 7, 4)
    assert job.deadline is None
    # raw_native_id comes from guid, not applicationLink.
    expected_guid = "https://himalayas.app/companies/cloudnine/jobs/senior-backend-engineer"
    assert job.raw_native_id == expected_guid
    assert job.source_ats == "himalayas"
    # description (fuller HTML field) is preferred over excerpt, and stripped.
    assert "Senior Backend Engineer" in job.description_raw
    assert "5+ years Python" in job.description_raw
    assert "<strong>" not in job.description_raw
    assert "<li>" not in job.description_raw


def test_parse_multi_country_posting_with_no_salary_falls_back_to_excerpt(
    raw_payload: dict, aggregator: AggregatorEntry
):
    adapter = HimalayasAdapter()
    job = adapter.parse(raw_payload["jobs"][1], aggregator)

    assert job is not None
    assert job.company == "Nordic Analytics"
    # location_raw joins multiple restrictions with ", ".
    assert job.location_raw == "Germany, Netherlands"
    assert job.remote is True
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency is None
    # empty categories list is passed through as-is.
    assert job.tech_stack == []
    assert job.posted_date == date(2026, 5, 28)
    # no "description" key on this record; falls back to "excerpt".
    expected_excerpt = "Nordic Analytics needs a Data Analyst to support our reporting team."
    assert job.description_raw == expected_excerpt
    # applicationLink and guid are identical for this record.
    assert job.url == job.raw_native_id


def test_parse_single_country_posting(raw_payload: dict, aggregator: AggregatorEntry):
    adapter = HimalayasAdapter()
    job = adapter.parse(raw_payload["jobs"][2], aggregator)

    assert job is not None
    assert job.company == "Riverbend"
    assert job.location_raw == "Nigeria"
    assert job.remote is True
    assert job.salary_min == 40000
    assert job.salary_max == 55000
    assert job.salary_currency == "USD"
    assert job.tech_stack == ["Customer-Support", "Zendesk"]
    assert job.posted_date == date(2026, 6, 15)


def test_parse_returns_none_for_missing_required_fields(aggregator: AggregatorEntry):
    adapter = HimalayasAdapter()
    assert adapter.parse({"title": "No Company"}, aggregator) is None
    assert adapter.parse({"companyName": "No Title Co"}, aggregator) is None


def test_parse_handles_missing_location_and_pub_date(aggregator: AggregatorEntry):
    adapter = HimalayasAdapter()
    job = adapter.parse(
        {
            "guid": "https://himalayas.app/companies/umbrella/jobs/mystery-role",
            "companyName": "Umbrella Corp",
            "title": "Mystery Role",
            "applicationLink": None,
            "excerpt": "",
        },
        aggregator,
    )

    assert job is not None
    assert job.location_raw == ""
    assert job.remote is True
    assert job.posted_date is None
    assert job.url is None
    assert job.tech_stack == []
    assert job.description_raw == ""
    assert job.raw_native_id == "https://himalayas.app/companies/umbrella/jobs/mystery-role"

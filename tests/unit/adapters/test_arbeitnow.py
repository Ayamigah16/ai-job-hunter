from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from ai_job_hunter.adapters.aggregators.arbeitnow import ArbeitnowAdapter
from ai_job_hunter.models import AggregatorType
from ai_job_hunter.registry import AggregatorEntry

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "fixtures"
    / "aggregators"
    / "arbeitnow_sample_response.json"
)


@pytest.fixture
def aggregator() -> AggregatorEntry:
    return AggregatorEntry(name="Arbeitnow", source_type=AggregatorType.ARBEITNOW)


@pytest.fixture
def raw_payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_source_type_is_arbeitnow():
    assert ArbeitnowAdapter.source_type == AggregatorType.ARBEITNOW


class _FakeResponse:
    def __init__(self, status_code: int, content: bytes, payload: dict | None = None):
        self.status_code = status_code
        self.content = content
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_raw_returns_data_list(aggregator: AggregatorEntry, raw_payload: dict, monkeypatch):
    adapter = ArbeitnowAdapter()
    monkeypatch.setattr(
        adapter.session,
        "get",
        lambda url, **kwargs: _FakeResponse(200, b"...", raw_payload),
    )

    result = adapter.fetch_raw(aggregator)

    assert result == raw_payload["data"]
    assert len(result) == 3


def test_fetch_raw_returns_empty_list_on_404(aggregator: AggregatorEntry, monkeypatch):
    adapter = ArbeitnowAdapter()
    monkeypatch.setattr(
        adapter.session, "get", lambda url, **kwargs: _FakeResponse(404, b"")
    )

    assert adapter.fetch_raw(aggregator) == []


def test_fetch_raw_returns_empty_list_on_empty_response(
    aggregator: AggregatorEntry, monkeypatch
):
    adapter = ArbeitnowAdapter()
    monkeypatch.setattr(
        adapter.session, "get", lambda url, **kwargs: _FakeResponse(200, b"")
    )

    assert adapter.fetch_raw(aggregator) == []


def test_fetch_raw_returns_empty_list_when_data_key_missing(
    aggregator: AggregatorEntry, monkeypatch
):
    adapter = ArbeitnowAdapter()
    monkeypatch.setattr(
        adapter.session,
        "get",
        lambda url, **kwargs: _FakeResponse(200, b"{}", {"links": {}, "meta": {}}),
    )

    assert adapter.fetch_raw(aggregator) == []


def test_parse_remote_posting(raw_payload: dict, aggregator: AggregatorEntry):
    adapter = ArbeitnowAdapter()
    job = adapter.parse(raw_payload["data"][0], aggregator)

    assert job is not None
    assert job.company == "Acme Corp"
    assert job.title == "Senior Backend Engineer"
    assert job.location_raw == "Berlin, Germany"
    assert job.remote is True
    assert job.department is None
    assert job.tech_stack == ["Python", "Django", "PostgreSQL"]
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency is None
    assert job.url == (
        "https://www.arbeitnow.com/jobs/companies/acme-corp/senior-backend-engineer-209961"
    )
    assert job.posted_date == date(2026, 7, 5)
    assert job.deadline is None
    assert job.raw_native_id == "senior-backend-engineer-acme-corp-209961"
    assert job.source_ats == "arbeitnow"
    assert "Senior Backend Engineer" in job.description_raw
    assert "<p>" not in job.description_raw
    assert "<strong>" not in job.description_raw


def test_parse_non_remote_posting(raw_payload: dict, aggregator: AggregatorEntry):
    adapter = ArbeitnowAdapter()
    job = adapter.parse(raw_payload["data"][1], aggregator)

    assert job is not None
    assert job.company == "Taxtalente.de"
    assert job.remote is False
    assert job.tech_stack == ["Directors", "Chief Executives"]
    assert job.location_raw == "Göllheim, Germany"
    assert job.posted_date == date(2026, 7, 5)


def test_parse_second_remote_posting(raw_payload: dict, aggregator: AggregatorEntry):
    adapter = ArbeitnowAdapter()
    job = adapter.parse(raw_payload["data"][2], aggregator)

    assert job is not None
    assert job.company == "Globex"
    assert job.remote is True
    assert job.tech_stack == ["Figma", "UX", "Design Systems"]
    assert job.posted_date == date(2026, 7, 4)


def test_parse_returns_none_for_missing_required_fields(aggregator: AggregatorEntry):
    adapter = ArbeitnowAdapter()
    assert adapter.parse({"title": "No Company"}, aggregator) is None
    assert adapter.parse({"company_name": "No Title Co"}, aggregator) is None


def test_parse_handles_missing_created_at(aggregator: AggregatorEntry):
    adapter = ArbeitnowAdapter()
    job = adapter.parse(
        {
            "slug": "no-date-job",
            "company_name": "Umbrella Corp",
            "title": "Mystery Role",
            "description": "",
            "remote": False,
            "url": None,
            "tags": [],
        },
        aggregator,
    )

    assert job is not None
    assert job.posted_date is None
    assert job.url is None
    assert job.tech_stack == []

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from ai_job_hunter.adapters.aggregators.remoteok import RemoteOKAdapter
from ai_job_hunter.models import AggregatorType
from ai_job_hunter.registry import AggregatorEntry

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "fixtures"
    / "aggregators"
    / "remoteok_sample_response.json"
)


@pytest.fixture
def aggregator() -> AggregatorEntry:
    return AggregatorEntry(name="RemoteOK", source_type=AggregatorType.REMOTEOK)


@pytest.fixture
def raw_payload() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_source_type_is_remoteok():
    assert RemoteOKAdapter.source_type == AggregatorType.REMOTEOK


def test_fixture_first_element_is_metadata_not_a_job(raw_payload: list[dict]):
    # Sanity-check the fixture itself models the real API's quirk.
    assert "legal" in raw_payload[0]
    assert "company" not in raw_payload[0]


def test_fetch_raw_skips_metadata_element(aggregator: AggregatorEntry, monkeypatch):
    adapter = RemoteOKAdapter()
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    class FakeResponse:
        status_code = 200
        content = b"[...]"

        def raise_for_status(self):
            pass

        def json(self):
            return payload

    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: FakeResponse())
    result = adapter.fetch_raw(aggregator)

    assert len(result) == 3
    assert all("legal" not in raw for raw in result)
    assert all(raw.get("company") for raw in result)


def test_fetch_raw_returns_empty_list_on_404(aggregator: AggregatorEntry, monkeypatch):
    adapter = RemoteOKAdapter()

    class FakeResponse:
        status_code = 404
        content = b""

        def raise_for_status(self):
            raise AssertionError("should not be called for a 404")

        def json(self):
            raise AssertionError("should not be called for a 404")

    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: FakeResponse())
    assert adapter.fetch_raw(aggregator) == []


def test_fetch_raw_returns_empty_list_on_empty_response(aggregator: AggregatorEntry, monkeypatch):
    adapter = RemoteOKAdapter()

    class FakeResponse:
        status_code = 200
        content = b""

        def raise_for_status(self):
            pass

        def json(self):
            raise AssertionError("should not be called for an empty body")

    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: FakeResponse())
    assert adapter.fetch_raw(aggregator) == []


def test_parse_posting_with_disclosed_salary(raw_payload: list[dict], aggregator: AggregatorEntry):
    adapter = RemoteOKAdapter()
    job = adapter.parse(raw_payload[1], aggregator)

    assert job is not None
    assert job.company == "Acme Corp"
    assert job.title == "Senior Backend Engineer"
    assert job.location_raw == "Worldwide"
    assert job.remote is True
    assert job.department is None
    assert job.tech_stack == ["python", "django", "postgres", "aws"]
    assert job.salary_min == 90000
    assert job.salary_max == 130000
    assert job.salary_currency is None
    assert job.url == "https://remoteok.com/remote-jobs/senior-backend-engineer-acme-corp-1000001"
    assert job.posted_date == date(2026, 6, 28)
    assert job.deadline is None
    assert job.raw_native_id == "1000001"
    assert job.source_ats == "remoteok"
    assert "Senior Backend Engineer" in job.description_raw
    assert "<p>" not in job.description_raw
    assert "<strong>" not in job.description_raw


def test_parse_posting_with_undisclosed_zero_salary_becomes_none(
    raw_payload: list[dict], aggregator: AggregatorEntry
):
    adapter = RemoteOKAdapter()
    job = adapter.parse(raw_payload[2], aggregator)

    assert job is not None
    assert job.company == "Globex"
    assert job.salary_min is None
    assert job.salary_max is None


def test_parse_posting_missing_salary_fields_entirely(
    raw_payload: list[dict], aggregator: AggregatorEntry
):
    adapter = RemoteOKAdapter()
    raw = raw_payload[3]
    assert "salary_min" not in raw and "salary_max" not in raw  # exercising .get() fallback

    job = adapter.parse(raw, aggregator)

    assert job is not None
    assert job.company == "Initech"
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.tech_stack == ["python", "sql", "machine-learning"]
    assert job.posted_date == date(2026, 6, 25)


def test_parse_returns_none_for_metadata_record(
    raw_payload: list[dict], aggregator: AggregatorEntry
):
    adapter = RemoteOKAdapter()
    assert adapter.parse(raw_payload[0], aggregator) is None


def test_parse_returns_none_for_missing_required_fields(aggregator: AggregatorEntry):
    adapter = RemoteOKAdapter()
    assert adapter.parse({"position": "No Company"}, aggregator) is None
    assert adapter.parse({"company": "No Title Co"}, aggregator) is None

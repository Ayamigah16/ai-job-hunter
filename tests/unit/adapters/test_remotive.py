from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from ai_job_hunter.adapters.aggregators.remotive import RemotiveAdapter
from ai_job_hunter.models import AggregatorType
from ai_job_hunter.registry import AggregatorEntry

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "fixtures"
    / "aggregators"
    / "remotive_sample_response.json"
)


@pytest.fixture
def aggregator() -> AggregatorEntry:
    return AggregatorEntry(
        name="Remotive",
        source_type=AggregatorType.REMOTIVE,
        category="devops",
        search_terms=["devops", "platform", "sre", "kubernetes", "cloud"],
    )


@pytest.fixture
def raw_payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_source_type_is_remotive():
    assert RemotiveAdapter.source_type == AggregatorType.REMOTIVE


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
    adapter = RemotiveAdapter()
    captured_url = {}

    def fake_get(url, **kwargs):
        captured_url["url"] = url
        return _FakeResponse(200, b"...", raw_payload)

    monkeypatch.setattr(adapter.session, "get", fake_get)

    result = adapter.fetch_raw(aggregator)

    assert result == raw_payload["jobs"]
    assert len(result) == 3
    # category is passed through server-side as a query param.
    assert captured_url["url"] == "https://remotive.com/api/remote-jobs?category=devops"


def test_fetch_raw_omits_category_param_when_not_set(monkeypatch):
    adapter = RemotiveAdapter()
    aggregator_no_category = AggregatorEntry(name="Remotive", source_type=AggregatorType.REMOTIVE)
    captured_url = {}

    def fake_get(url, **kwargs):
        captured_url["url"] = url
        return _FakeResponse(200, b"...", {"job-count": 0, "jobs": []})

    monkeypatch.setattr(adapter.session, "get", fake_get)

    adapter.fetch_raw(aggregator_no_category)

    assert captured_url["url"] == "https://remotive.com/api/remote-jobs"


def test_fetch_raw_returns_empty_list_on_404(aggregator: AggregatorEntry, monkeypatch):
    adapter = RemotiveAdapter()
    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: _FakeResponse(404, b""))

    assert adapter.fetch_raw(aggregator) == []


def test_fetch_raw_returns_empty_list_on_empty_response(aggregator: AggregatorEntry, monkeypatch):
    adapter = RemotiveAdapter()
    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: _FakeResponse(200, b""))

    assert adapter.fetch_raw(aggregator) == []


def test_fetch_raw_returns_empty_list_when_jobs_key_missing(
    aggregator: AggregatorEntry, monkeypatch
):
    adapter = RemotiveAdapter()
    monkeypatch.setattr(
        adapter.session,
        "get",
        lambda url, **kwargs: _FakeResponse(200, b"{}", {"job-count": 0}),
    )

    assert adapter.fetch_raw(aggregator) == []


def test_parse_worldwide_posting_with_salary_text(raw_payload: dict, aggregator: AggregatorEntry):
    adapter = RemotiveAdapter()
    job = adapter.parse(raw_payload["jobs"][0], aggregator)

    assert job is not None
    assert job.company == "Acme Cloud"
    assert job.title == "Platform Engineer"
    assert job.location_raw == "Worldwide"
    assert job.remote is True
    assert job.department is None
    assert job.tech_stack == ["kubernetes", "terraform", "aws"]
    # raw["salary"] is non-empty free text ("$90k - $110k") but must NOT be parsed.
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency is None
    assert job.url == "https://remotive.com/remote-jobs/devops/platform-engineer-1712345"
    assert job.posted_date == date(2026, 7, 2)
    assert job.deadline is None
    assert job.raw_native_id == "1712345"
    assert job.source_ats == "remotive"
    assert "Platform Engineer" in job.description_raw
    assert "<p>" not in job.description_raw
    assert "<strong>" not in job.description_raw


def test_parse_usa_only_posting_with_empty_salary(raw_payload: dict, aggregator: AggregatorEntry):
    adapter = RemotiveAdapter()
    job = adapter.parse(raw_payload["jobs"][1], aggregator)

    assert job is not None
    assert job.company == "Globex Systems"
    # location_raw preserves the raw eligibility string as-is, unparsed.
    assert job.location_raw == "USA Only"
    assert job.remote is True
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency is None
    assert job.posted_date == date(2026, 6, 28)


def test_parse_eu_timezones_posting_with_non_dollar_salary_text(
    raw_payload: dict, aggregator: AggregatorEntry
):
    adapter = RemotiveAdapter()
    job = adapter.parse(raw_payload["jobs"][2], aggregator)

    assert job is not None
    assert job.company == "Initech"
    assert job.location_raw == "EU Timezones"
    assert job.remote is True
    assert job.tech_stack == ["azure", "cloud", "ci/cd"]
    # raw["salary"] uses a non-USD currency in free text; still must stay None.
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency is None
    assert job.posted_date == date(2026, 6, 30)


def test_parse_returns_none_for_missing_required_fields(aggregator: AggregatorEntry):
    adapter = RemotiveAdapter()
    assert adapter.parse({"title": "No Company"}, aggregator) is None
    assert adapter.parse({"company_name": "No Title Co"}, aggregator) is None


def test_parse_handles_missing_publication_date(aggregator: AggregatorEntry):
    adapter = RemotiveAdapter()
    job = adapter.parse(
        {
            "id": 999,
            "company_name": "Umbrella Corp",
            "title": "Mystery Role",
            "description": "",
            "url": None,
            "tags": [],
            "candidate_required_location": "",
            "salary": "",
        },
        aggregator,
    )

    assert job is not None
    assert job.posted_date is None
    assert job.url is None
    assert job.tech_stack == []
    assert job.location_raw == ""
    assert job.remote is True

from __future__ import annotations

from datetime import date
from pathlib import Path

import feedparser
import pytest

from ai_job_hunter.adapters.aggregators.weworkremotely import WeWorkRemotelyAdapter
from ai_job_hunter.models import AggregatorType
from ai_job_hunter.registry import AggregatorEntry

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "fixtures"
    / "aggregators"
    / "weworkremotely_sample_response.xml"
)


@pytest.fixture
def aggregator() -> AggregatorEntry:
    return AggregatorEntry(
        name="We Work Remotely",
        source_type=AggregatorType.WEWORKREMOTELY,
        category="remote-devops-sysadmin-jobs",
    )


@pytest.fixture
def raw_entries() -> list[dict]:
    """Mirror what fetch_raw does: parse the fixture XML and flatten to dicts."""
    feed = feedparser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert feed.entries, "fixture must contain at least one <item>"
    return [
        {
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "summary": entry.get("summary", ""),
        }
        for entry in feed.entries
    ]


def test_source_type_is_weworkremotely():
    assert WeWorkRemotelyAdapter.source_type == AggregatorType.WEWORKREMOTELY


def test_fixture_has_three_entries(raw_entries: list[dict]):
    assert len(raw_entries) == 3


def test_parse_splits_company_and_title_on_first_colon(
    raw_entries: list[dict], aggregator: AggregatorEntry
):
    adapter = WeWorkRemotelyAdapter()
    job = adapter.parse(raw_entries[0], aggregator)

    assert job is not None
    assert job.company == "Acme Cloud"
    assert job.title == "Senior DevOps Engineer"
    assert job.remote is True
    assert job.url == "https://weworkremotely.com/remote-jobs/acme-cloud-senior-devops-engineer"
    assert job.raw_native_id == job.url
    assert job.source_ats == "weworkremotely"
    assert job.department is None
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency is None
    assert job.tech_stack == []
    assert job.deadline is None
    assert job.posted_date == date(2026, 6, 30)
    assert "Senior DevOps Engineer" in job.description_raw or "Acme Cloud" in job.description_raw
    assert "<p>" not in job.description_raw
    assert "<strong>" not in job.description_raw


def test_parse_handles_titles_with_extra_colons_via_split_on_first(
    raw_entries: list[dict], aggregator: AggregatorEntry
):
    adapter = WeWorkRemotelyAdapter()
    job = adapter.parse(raw_entries[1], aggregator)

    assert job is not None
    assert job.company == "Globex Systems"
    assert job.title == "Site Reliability Engineer (SRE)"
    assert job.remote is True
    assert job.posted_date == date(2026, 6, 24)


def test_parse_returns_none_when_title_has_no_colon_fallback(
    raw_entries: list[dict], aggregator: AggregatorEntry
):
    # raw_entries[2]'s title has no ": " separator, so the adapter's internal
    # split falls back to company=None / whole string as title. Since
    # `company` is a required JobPosting field, parse() must drop the record
    # rather than raise.
    no_colon_raw = raw_entries[2]
    assert ": " not in no_colon_raw["title"]

    adapter = WeWorkRemotelyAdapter()
    assert adapter.parse(no_colon_raw, aggregator) is None


def test_split_company_and_title_fallback_directly():
    from ai_job_hunter.adapters.aggregators.weworkremotely import _split_company_and_title

    company, title = _split_company_and_title("Platform Engineer Wanted For Growing Startup")
    assert company is None
    assert title == "Platform Engineer Wanted For Growing Startup"

    company, title = _split_company_and_title("Acme Cloud: Senior DevOps Engineer")
    assert company == "Acme Cloud"
    assert title == "Senior DevOps Engineer"


def test_all_parsed_jobs_are_remote(raw_entries: list[dict], aggregator: AggregatorEntry):
    adapter = WeWorkRemotelyAdapter()
    jobs = [adapter.parse(raw, aggregator) for raw in raw_entries]
    parsed = [job for job in jobs if job is not None]

    assert len(parsed) == 2  # the no-colon entry is dropped
    assert all(job.remote is True for job in parsed)


class _FakeResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        pass


def test_fetch_raw_returns_empty_list_on_404(aggregator: AggregatorEntry, monkeypatch):
    adapter = WeWorkRemotelyAdapter()
    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: _FakeResponse(404, ""))

    assert adapter.fetch_raw(aggregator) == []


def test_fetch_raw_returns_empty_list_on_empty_body(aggregator: AggregatorEntry, monkeypatch):
    adapter = WeWorkRemotelyAdapter()
    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: _FakeResponse(200, ""))

    assert adapter.fetch_raw(aggregator) == []


def test_fetch_raw_returns_empty_list_when_no_category(monkeypatch):
    adapter = WeWorkRemotelyAdapter()
    aggregator_no_category = AggregatorEntry(
        name="We Work Remotely", source_type=AggregatorType.WEWORKREMOTELY
    )

    assert adapter.fetch_raw(aggregator_no_category) == []


def test_fetch_raw_builds_url_from_category_and_parses_feed(
    aggregator: AggregatorEntry, monkeypatch
):
    adapter = WeWorkRemotelyAdapter()
    captured_url = {}
    fixture_text = FIXTURE_PATH.read_text(encoding="utf-8")

    def fake_get(url, **kwargs):
        captured_url["url"] = url
        return _FakeResponse(200, fixture_text)

    monkeypatch.setattr(adapter.session, "get", fake_get)

    result = adapter.fetch_raw(aggregator)

    assert (
        captured_url["url"]
        == "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss"
    )
    assert len(result) == 3
    assert result[0]["title"] == "Acme Cloud: Senior DevOps Engineer"

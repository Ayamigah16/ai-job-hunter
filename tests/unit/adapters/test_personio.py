from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from ai_job_hunter.adapters.personio import PersonioAdapter, _positions_from_xml
from ai_job_hunter.models import ATSType
from ai_job_hunter.registry import CompanyEntry

FIXTURE_PATH = Path(__file__).parent.parent.parent / "fixtures" / "personio" / "sample_response.xml"


@pytest.fixture
def company() -> CompanyEntry:
    return CompanyEntry(
        name="Example Co",
        slug="exampleco",
        ats_type=ATSType.PERSONIO,
        board_token="exampleco",
    )


@pytest.fixture
def raw_postings() -> list[dict]:
    return _positions_from_xml(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_ats_type_is_personio():
    assert PersonioAdapter.ats_type == ATSType.PERSONIO


def test_positions_from_xml_returns_all_positions(raw_postings: list[dict]):
    assert len(raw_postings) == 3
    assert raw_postings[0]["id"] == "2696582"
    assert raw_postings[0]["name"] == "(Senior) Site Reliability Engineer (m/f/d)"


def test_positions_from_xml_ignores_nested_additional_offices(raw_postings: list[dict]):
    # The direct <office> child of <position> should win; the <office> nested
    # under <additionalOffices> ("Konstanz") must not overwrite it.
    assert raw_postings[0]["office"] == "Berlin"


def test_positions_from_xml_flattens_job_descriptions(raw_postings: list[dict]):
    combined = raw_postings[0]["jobDescriptions"]
    assert "Mission" in combined
    assert "Keep our platform reliable" in combined
    assert "Requirements" in combined
    assert "Kubernetes" in combined


def test_parse_onsite_posting(raw_postings: list[dict], company: CompanyEntry):
    adapter = PersonioAdapter()
    job = adapter.parse(raw_postings[0], company)

    assert job is not None
    assert job.company == "Example Co"
    assert job.title == "(Senior) Site Reliability Engineer (m/f/d)"
    assert job.location_raw == "Berlin"
    assert job.remote is False
    assert job.department == "Technology"
    assert job.url == "https://exampleco.jobs.personio.de/job/2696582"
    assert job.posted_date == date(2026, 7, 2)
    assert job.raw_native_id == "2696582"
    assert job.source_ats == "personio"
    assert job.tech_stack == []
    assert job.deadline is None
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.salary_currency is None
    assert "Keep our platform reliable" in job.description_raw
    assert "<p>" not in job.description_raw
    assert "<ul>" not in job.description_raw


def test_parse_remote_via_office_text(raw_postings: list[dict], company: CompanyEntry):
    adapter = PersonioAdapter()
    job = adapter.parse(raw_postings[1], company)

    assert job is not None
    assert job.title == "Backend Engineer (m/f/d)"
    assert job.location_raw == "Remote - Germany"
    assert job.remote is True  # "Remote" in office text
    assert job.department == "Engineering"
    assert job.url == "https://exampleco.jobs.personio.de/job/2701234"
    assert job.posted_date == date(2026, 6, 15)
    assert job.raw_native_id == "2701234"


def test_parse_remote_via_title_text_when_office_is_onsite(
    raw_postings: list[dict], company: CompanyEntry
):
    adapter = PersonioAdapter()
    job = adapter.parse(raw_postings[2], company)

    assert job is not None
    assert job.title == "Remote Customer Success Manager (m/f/d)"
    assert job.location_raw == "Munich"
    assert job.remote is True  # inferred from "Remote" in the title, not the office
    assert job.department is None  # <department></department> -> "" -> None
    assert job.posted_date is None  # no <createdAt> tag on this record at all
    assert job.description_raw == ""  # empty <jobDescriptions> container
    assert job.raw_native_id == "2701999"


def test_parse_returns_none_for_missing_required_fields(company: CompanyEntry):
    adapter = PersonioAdapter()
    assert adapter.parse({"name": "No id"}, company) is None
    assert adapter.parse({"id": "99"}, company) is None


def test_fetch_raw_returns_empty_list_on_404(company: CompanyEntry, monkeypatch):
    adapter = PersonioAdapter()

    class FakeResponse:
        status_code = 404
        content = b""

        def raise_for_status(self):
            raise AssertionError("should not be called for a 404")

    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: FakeResponse())
    assert adapter.fetch_raw(company) == []


def test_fetch_raw_returns_empty_list_without_board_token():
    adapter = PersonioAdapter()
    company = CompanyEntry(
        name="No Token Co",
        slug="notoken",
        ats_type=ATSType.PERSONIO,
        board_token=None,
    )
    assert adapter.fetch_raw(company) == []


def test_fetch_raw_returns_empty_list_on_empty_content(company: CompanyEntry, monkeypatch):
    adapter = PersonioAdapter()

    class FakeResponse:
        status_code = 200
        content = b""

        def raise_for_status(self):
            pass

    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: FakeResponse())
    assert adapter.fetch_raw(company) == []


def test_fetch_raw_parses_xml_into_positions(company: CompanyEntry, monkeypatch):
    adapter = PersonioAdapter()
    xml_text = FIXTURE_PATH.read_text(encoding="utf-8")

    class FakeResponse:
        status_code = 200
        content = xml_text.encode("utf-8")
        text = xml_text

        def raise_for_status(self):
            pass

    monkeypatch.setattr(adapter.session, "get", lambda url, **kwargs: FakeResponse())
    result = adapter.fetch_raw(company)
    assert len(result) == 3
    assert result[0]["id"] == "2696582"

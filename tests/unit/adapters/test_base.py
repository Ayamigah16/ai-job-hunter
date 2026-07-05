import requests
import responses

from ai_job_hunter.adapters.base import BaseATSAdapter, RateLimitedSession, strip_html


class _DummyAdapter(BaseATSAdapter):
    ats_type = "dummy"

    def __init__(self, session=None, raw_list=None, raise_on_fetch=None, raise_on_parse_for=None):
        super().__init__(session)
        self._raw_list = raw_list or []
        self._raise_on_fetch = raise_on_fetch
        self._raise_on_parse_for = raise_on_parse_for or set()

    def fetch_raw(self, company):
        if self._raise_on_fetch is not None:
            raise self._raise_on_fetch
        return self._raw_list

    def parse(self, raw, company):
        if raw.get("id") in self._raise_on_parse_for:
            raise ValueError("bad record")
        if raw.get("id") is None:
            return None
        from datetime import UTC, datetime

        from ai_job_hunter.models import JobPosting

        return JobPosting(
            company=company.name,
            title=raw["title"],
            location_raw="",
            remote=None,
            department=None,
            salary_min=None,
            salary_max=None,
            salary_currency=None,
            tech_stack=[],
            url=None,
            posted_date=None,
            deadline=None,
            source_ats="dummy",
            raw_native_id=str(raw["id"]),
            description_raw="",
            fetched_at=datetime.now(UTC),
        )


def _make_company():
    from ai_job_hunter.models import ATSType
    from ai_job_hunter.registry import CompanyEntry

    return CompanyEntry(name="Acme", slug="acme", ats_type=ATSType.GREENHOUSE, board_token="acme")


def test_fetch_and_parse_success_clears_last_error():
    adapter = _DummyAdapter(raw_list=[{"id": 1, "title": "Engineer"}])
    postings = adapter.fetch_and_parse(_make_company())
    assert len(postings) == 1
    assert adapter.last_fetch_error is None


def test_fetch_and_parse_records_failure_and_returns_empty():
    adapter = _DummyAdapter(raise_on_fetch=ConnectionError("network unreachable"))
    postings = adapter.fetch_and_parse(_make_company())
    assert postings == []
    assert "network unreachable" in adapter.last_fetch_error


def test_fetch_and_parse_skips_unparseable_records_but_keeps_others():
    adapter = _DummyAdapter(
        raw_list=[{"id": 1, "title": "Good"}, {"id": 2, "title": "Bad"}],
        raise_on_parse_for={2},
    )
    postings = adapter.fetch_and_parse(_make_company())
    assert len(postings) == 1
    assert postings[0].title == "Good"
    assert adapter.last_fetch_error is None


def test_strip_html_handles_empty_string():
    assert strip_html("") == ""


@responses.activate
def test_rate_limited_session_retries_on_connection_error_then_succeeds():
    responses.add(
        responses.GET,
        "https://example.com/jobs",
        body=requests.exceptions.ConnectionError("boom"),
    )
    responses.add(responses.GET, "https://example.com/jobs", status=200, body="ok")

    session = RateLimitedSession(min_interval_seconds=0)
    response = session.get("https://example.com/jobs")

    assert response.status_code == 200
    assert len(responses.calls) == 2

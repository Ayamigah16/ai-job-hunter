"""Network-touching smoke tests against real endpoints.

Excluded from the default `pytest` run (see pyproject.toml's `addopts`). Run
manually via `pytest -m integration`, or on the integration-smoke.yml
schedule. Asserts structural shape (fields present, right types), not exact
content — job postings churn constantly, so asserting specific titles/counts
would make this flaky on totally normal upstream changes, not real breakage.
"""

from __future__ import annotations

import time

import pytest

from ai_job_hunter.adapters.aggregators.remoteok import RemoteOKAdapter
from ai_job_hunter.adapters.ashby import AshbyAdapter
from ai_job_hunter.adapters.greenhouse import GreenhouseAdapter
from ai_job_hunter.adapters.workable import WorkableAdapter
from ai_job_hunter.models import AggregatorType, JobPosting
from ai_job_hunter.registry import AggregatorEntry, CompanyEntry

pytestmark = pytest.mark.integration


def _assert_valid_posting(job: JobPosting) -> None:
    assert job.company
    assert job.title
    assert isinstance(job.tech_stack, list)
    assert job.source_ats


@pytest.mark.parametrize(
    ("adapter_cls", "board_token"),
    [
        (GreenhouseAdapter, "gitlab"),
        (AshbyAdapter, "supabase"),
        (WorkableAdapter, "hashicorp"),
    ],
)
def test_ats_adapter_returns_structurally_valid_postings(adapter_cls, board_token):
    company = CompanyEntry(
        name=board_token,
        slug=board_token,
        ats_type=adapter_cls.ats_type,
        board_token=board_token,
    )
    postings = adapter_cls().fetch_and_parse(company)
    # HashiCorp in particular has had zero open reqs at times we checked live;
    # only assert shape on whatever postings actually came back, not a count.
    for job in postings[:5]:
        _assert_valid_posting(job)
    time.sleep(1)  # be polite to the next parametrized case's host


def test_remoteok_aggregator_returns_structurally_valid_postings():
    aggregator = AggregatorEntry(name="RemoteOK", source_type=AggregatorType.REMOTEOK)
    postings = RemoteOKAdapter().fetch_and_parse(aggregator)
    assert len(postings) > 0
    for job in postings[:5]:
        _assert_valid_posting(job)
        assert job.remote is True

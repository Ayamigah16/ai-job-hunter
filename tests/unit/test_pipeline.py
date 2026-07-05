from ai_job_hunter.models import ATSType
from ai_job_hunter.pipeline import RunResult
from ai_job_hunter.pipeline import run as run_pipeline
from ai_job_hunter.registry import CompanyEntry
from ai_job_hunter.scoring.profile import ScoringProfile
from ai_job_hunter.sheets.writer import FakeSheetsWriter


class _StubNotifier:
    def __init__(self):
        self.notified: list = []

    def notify(self, new_jobs):
        self.notified.extend(new_jobs)


def make_profile() -> ScoringProfile:
    return ScoringProfile.model_validate(
        {
            "role_title_keywords": ["platform engineer"],
            "must_have_skills": ["kubernetes"],
            "weights": {"must_have_match": 100, "role_title_match": 100},
        }
    )


def make_company() -> CompanyEntry:
    return CompanyEntry(name="Acme", slug="acme", ats_type=ATSType.GREENHOUSE, board_token="acme")


def _patch_fetch(monkeypatch, scored_jobs):
    """Isolate run() from real network I/O: stub the fetch step (no real HTTP
    calls) and the scoring step (return a fixed, pre-built list) separately,
    since run() composes them itself rather than calling fetch_score_and_dedup."""
    import ai_job_hunter.pipeline as pipeline_module

    monkeypatch.setattr(pipeline_module, "fetch_all_with_summary", lambda *a, **k: ({}, []))
    monkeypatch.setattr(pipeline_module, "_score_relevant_jobs", lambda *a, **k: scored_jobs)


def test_run_notifies_only_newly_appended_jobs_above_notify_threshold(monkeypatch, make_scored_job):
    scored_high = make_scored_job(score=90.0, company="Acme", title="Platform Engineer")
    scored_low = make_scored_job(score=10.0, company="Acme", title="Data Entry")
    _patch_fetch(monkeypatch, [scored_high, scored_low])

    writer = FakeSheetsWriter()
    notifier = _StubNotifier()

    result = run_pipeline(
        companies=[make_company()],
        aggregators=[],
        profile=make_profile(),
        writer=writer,
        score_threshold=0,
        notify_threshold=50,
        notifier=notifier,
    )

    assert isinstance(result, RunResult)
    assert len(result.open_roles.appended) == 2
    assert notifier.notified == [scored_high]
    assert result.fetch_outcomes == []


def test_run_does_not_notify_for_updated_rows_on_rerun(monkeypatch, make_scored_job):
    scored = make_scored_job(score=90.0, company="Acme", title="Platform Engineer")
    _patch_fetch(monkeypatch, [scored])

    writer = FakeSheetsWriter()
    notifier = _StubNotifier()
    company = make_company()

    run_pipeline([company], [], make_profile(), writer, 0, notify_threshold=0, notifier=notifier)
    notifier.notified.clear()
    run_pipeline([company], [], make_profile(), writer, 0, notify_threshold=0, notifier=notifier)

    assert notifier.notified == []

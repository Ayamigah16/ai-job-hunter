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


def test_run_notifies_only_newly_appended_jobs_above_notify_threshold(monkeypatch, make_scored_job):
    import ai_job_hunter.pipeline as pipeline_module

    scored_high = make_scored_job(score=90.0, company="Acme", title="Platform Engineer")
    scored_low = make_scored_job(score=10.0, company="Acme", title="Data Entry")
    monkeypatch.setattr(
        pipeline_module, "fetch_score_and_dedup", lambda *a, **k: [scored_high, scored_low]
    )

    writer = FakeSheetsWriter()
    notifier = _StubNotifier()

    result = pipeline_module.run(
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


def test_run_does_not_notify_for_updated_rows_on_rerun(monkeypatch, make_scored_job):
    import ai_job_hunter.pipeline as pipeline_module

    scored = make_scored_job(score=90.0, company="Acme", title="Platform Engineer")
    monkeypatch.setattr(pipeline_module, "fetch_score_and_dedup", lambda *a, **k: [scored])

    writer = FakeSheetsWriter()
    notifier = _StubNotifier()
    company = make_company()

    run_pipeline([company], [], make_profile(), writer, 0, notify_threshold=0, notifier=notifier)
    notifier.notified.clear()
    run_pipeline([company], [], make_profile(), writer, 0, notify_threshold=0, notifier=notifier)

    assert notifier.notified == []

from dataclasses import replace
from datetime import date

from ai_job_hunter.models import ATSType, HiresInAfrica, Priority, ScoredJob, ScoreResult
from ai_job_hunter.registry import CompanyEntry
from ai_job_hunter.sheets.writer import FakeSheetsWriter, careers_page_url


def test_careers_page_url_known_ats():
    company = CompanyEntry(
        name="Acme", slug="acme", ats_type=ATSType.GREENHOUSE, board_token="acme"
    )
    assert careers_page_url(company) == "https://job-boards.greenhouse.io/acme"


def test_careers_page_url_unsupported_ats_is_blank():
    company = CompanyEntry(name="Acme", slug="acme", ats_type=ATSType.UNSUPPORTED)
    assert careers_page_url(company) == ""


def test_sync_open_roles_appends_new_row_below_threshold_skipped(make_scored_job):
    writer = FakeSheetsWriter()
    high = make_scored_job(score=80.0, company="Acme", title="Platform Engineer")
    low = make_scored_job(score=10.0, company="Acme", title="Sales Rep")

    result = writer.sync_open_roles([high, low], score_threshold=40)

    assert len(result.appended) == 1
    assert result.appended[0] is high
    assert result.skipped == [low]
    assert len(writer.open_roles_rows) == 1
    assert writer.open_roles_rows[0]["Status"] == "New"
    assert writer.open_roles_rows[0]["Notes"] == ""


def test_sync_open_roles_rerun_does_not_duplicate_or_clobber_status(make_scored_job):
    writer = FakeSheetsWriter()
    job = make_scored_job(
        score=80.0, company="Acme", title="Platform Engineer", url="https://acme.com/jobs/1"
    )

    writer.sync_open_roles([job], score_threshold=40)
    # Simulate the user manually updating Status/Notes in the sheet.
    writer.open_roles_rows[0]["Status"] = "Applied"
    writer.open_roles_rows[0]["Notes"] = "Referred by Jane"

    # Re-running with the same job (e.g. metadata refreshed) must not duplicate
    # the row nor touch the user's Status/Notes edits.
    result = writer.sync_open_roles([job], score_threshold=40)

    assert len(writer.open_roles_rows) == 1
    assert len(result.updated) == 1
    assert result.appended == []
    assert writer.open_roles_rows[0]["Status"] == "Applied"
    assert writer.open_roles_rows[0]["Notes"] == "Referred by Jane"


def test_sync_open_roles_dedups_same_job_from_two_sources(make_scored_job):
    writer = FakeSheetsWriter()
    company_board = make_scored_job(
        score=80.0, company="Acme", title="Platform Engineer", url="https://acme.com/jobs/1"
    )
    aggregator = make_scored_job(
        score=75.0,
        company="Acme",
        title="Platform Engineer",
        url="https://acme.com/jobs/1?utm_source=remoteok",
    )

    writer.sync_open_roles([company_board], score_threshold=40)
    result = writer.sync_open_roles([aggregator], score_threshold=40)

    assert len(writer.open_roles_rows) == 1
    assert result.appended == []
    assert len(result.updated) == 1


def test_sync_target_companies_appends_and_never_overwrites_curated_fields():
    writer = FakeSheetsWriter()
    company = CompanyEntry(
        name="Acme",
        slug="acme",
        ats_type=ATSType.GREENHOUSE,
        board_token="acme",
        industry="DevOps",
        hires_in_africa=HiresInAfrica.YES,
        priority=Priority.HIGH,
    )

    first = writer.sync_target_companies([company])
    assert len(first.appended) == 1
    assert writer.target_companies_rows[0]["Hires in Africa?"] == "yes"

    # User hand-edits curated fields in the sheet.
    writer.target_companies_rows[0]["Priority"] = "low"
    writer.target_companies_rows[0]["Referral Needed?"] = "yes"

    updated_company = company.model_copy(update={"industry": "Cloud Infrastructure"})
    second = writer.sync_target_companies([updated_company])

    assert len(second.updated) == 1
    row = writer.target_companies_rows[0]
    assert row["Industry"] == "Cloud Infrastructure"
    assert row["Priority"] == "low"
    assert row["Referral Needed?"] == "yes"


def test_open_roles_row_maps_location_to_country_and_region(make_scored_job):
    writer = FakeSheetsWriter()
    job = make_scored_job(company="Acme", title="Platform Engineer", location_raw="Berlin, Germany")
    writer.sync_open_roles([job], score_threshold=0)
    row = writer.open_roles_rows[0]
    assert row["Country"] == "Germany"
    assert row["Region"] == "Europe"


def test_open_roles_row_formats_salary_range(make_scored_job):
    writer = FakeSheetsWriter()
    job_with_salary = make_scored_job(salary_min=90000, salary_max=130000)
    writer.sync_open_roles([job_with_salary], score_threshold=0)
    assert writer.open_roles_rows[0]["Salary"] == "90,000-130,000"


def test_open_roles_row_formats_dates(make_job):
    job = make_job(company="Acme", title="Platform Engineer")
    job_with_date = replace(job, posted_date=date(2026, 1, 15))
    scored = ScoredJob(job=job_with_date, score=ScoreResult(total_score=80.0), job_id="job-1")

    writer = FakeSheetsWriter()
    writer.sync_open_roles([scored], score_threshold=0)
    assert writer.open_roles_rows[0]["Date Posted"] == "2026-01-15"

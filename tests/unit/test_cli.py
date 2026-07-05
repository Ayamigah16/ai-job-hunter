from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from ai_job_hunter.cli import cli
from ai_job_hunter.pipeline import FetchOutcome, RunResult
from ai_job_hunter.sheets.writer import SyncResult


def test_validate_config_succeeds_against_real_seed():
    result = CliRunner().invoke(cli, ["validate-config"])
    assert result.exit_code == 0
    assert "companies" in result.output


def test_fetch_dry_run_prints_per_source_counts(make_job):
    fake_results = {"Acme": [make_job()]}
    fake_outcomes = [FetchOutcome("Acme", 1, None)]
    with patch(
        "ai_job_hunter.cli.fetch_all_with_summary", return_value=(fake_results, fake_outcomes)
    ):
        result = CliRunner().invoke(cli, ["fetch", "--dry-run"])
    assert result.exit_code == 0
    assert "Acme: 1 jobs" in result.output
    assert "Total: 1 jobs from 1 sources" in result.output


def test_fetch_dry_run_reports_failures(make_job):
    fake_results = {"Acme": []}
    fake_outcomes = [FetchOutcome("Acme", 0, "Connection timed out")]
    with patch(
        "ai_job_hunter.cli.fetch_all_with_summary", return_value=(fake_results, fake_outcomes)
    ):
        result = CliRunner().invoke(cli, ["fetch", "--dry-run"])
    assert result.exit_code == 0
    assert "1 source(s) failed to fetch" in result.output
    assert "Connection timed out" in result.output


def test_fetch_no_dry_run_is_rejected():
    result = CliRunner().invoke(cli, ["fetch", "--no-dry-run"])
    assert result.exit_code != 0
    assert "isn't implemented yet" in result.output


def test_fetch_score_prints_ranked_jobs(make_scored_job):
    scored = make_scored_job(score=90.0, company="Acme", title="Platform Engineer")
    with patch("ai_job_hunter.cli.fetch_score_and_dedup", return_value=[scored]):
        result = CliRunner().invoke(cli, ["fetch", "--dry-run", "--score"])
    assert result.exit_code == 0
    assert "1 relevant jobs after filter + dedup" in result.output
    assert "Acme" in result.output


def test_run_without_sheets_config_fails_clearly(monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_SHEETS_SPREADSHEET_ID", raising=False)
    with patch("ai_job_hunter.cli.get_settings") as get_settings:
        get_settings.return_value = MagicMock(
            google_application_credentials=None, google_sheets_spreadsheet_id=None
        )
        result = CliRunner().invoke(cli, ["run"])
    assert result.exit_code != 0
    assert "Google Sheets isn't configured" in result.output


def test_run_reports_notifier_status_and_fetch_failures():
    settings = MagicMock(
        google_application_credentials="creds.json",
        google_sheets_spreadsheet_id="sheet-id",
        telegram_bot_token=None,
        telegram_chat_id=None,
        smtp_host=None,
    )
    fake_run_result = RunResult(
        open_roles=SyncResult(appended=[1], updated=[], skipped=[]),
        target_companies=SyncResult(appended=[], updated=[], skipped=[]),
        fetch_outcomes=[FetchOutcome("Acme", 0, "boom")],
    )

    with (
        patch("ai_job_hunter.cli.get_settings", return_value=settings),
        patch("ai_job_hunter.cli.get_gspread_client"),
        patch("ai_job_hunter.cli.open_spreadsheet"),
        patch("ai_job_hunter.cli.GoogleSheetsWriter"),
        patch("ai_job_hunter.cli.run_pipeline", return_value=fake_run_result),
    ):
        result = CliRunner().invoke(cli, ["run"])

    assert result.exit_code == 0
    assert "No Telegram/email credentials configured" in result.output
    assert "1 source(s) failed to fetch" in result.output
    assert "boom" in result.output


def test_dashboard_without_sheets_config_fails_clearly():
    with patch("ai_job_hunter.cli.get_settings") as get_settings:
        get_settings.return_value = MagicMock(
            google_application_credentials=None, google_sheets_spreadsheet_id=None
        )
        result = CliRunner().invoke(cli, ["dashboard"])
    assert result.exit_code != 0
    assert "Google Sheets isn't configured" in result.output


def test_dashboard_prints_computed_stats():
    from ai_job_hunter.dashboard import DashboardStats

    settings = MagicMock(
        google_application_credentials="creds.json", google_sheets_spreadsheet_id="sheet-id"
    )
    stats = DashboardStats(
        applications_this_week=2,
        interviews=1,
        response_rate=50.0,
        rejections=0,
        pending=1,
        offers=0,
    )

    with (
        patch("ai_job_hunter.cli.get_settings", return_value=settings),
        patch("ai_job_hunter.cli.get_gspread_client"),
        patch("ai_job_hunter.cli.open_spreadsheet"),
        patch("ai_job_hunter.cli.refresh_dashboard", return_value=stats),
    ):
        result = CliRunner().invoke(cli, ["dashboard"])

    assert result.exit_code == 0
    assert "2 applications this week" in result.output

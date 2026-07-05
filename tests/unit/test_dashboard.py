from datetime import date
from unittest.mock import MagicMock

from ai_job_hunter.dashboard import compute_dashboard_stats, refresh_dashboard, stats_to_rows
from ai_job_hunter.sheets.schema import APPLICATIONS_COLUMNS


def test_compute_dashboard_stats_classifies_by_keywords():
    today = date(2026, 7, 8)  # a Wednesday
    applications = [
        {
            "Date Applied": "2026-07-06",  # Monday this week
            "Interview Stage": "Phone Screen",
            "Feedback": "",
        },
        {
            "Date Applied": "2026-06-01",  # long before this week
            "Interview Stage": "",
            "Feedback": "We received an offer for you!",
        },
        {
            "Date Applied": "2026-07-07",  # Tuesday this week
            "Interview Stage": "",
            "Feedback": "Unfortunately we are rejecting your application.",
        },
        {
            "Date Applied": "2026-06-20",
            "Interview Stage": "",
            "Feedback": "",
        },
    ]

    stats = compute_dashboard_stats(applications, today)

    assert stats.applications_this_week == 2
    assert stats.interviews == 1
    assert stats.offers == 1
    assert stats.rejections == 1
    assert stats.pending == 2  # total(4) - rejections(1) - offers(1)
    assert stats.response_rate == 75.0  # 3 of 4 applications got any response


def test_compute_dashboard_stats_empty_applications():
    stats = compute_dashboard_stats([], date(2026, 7, 8))
    assert stats.applications_this_week == 0
    assert stats.response_rate == 0.0
    assert stats.pending == 0


def test_compute_dashboard_stats_handles_unparseable_dates():
    applications = [{"Date Applied": "not a date", "Interview Stage": "", "Feedback": ""}]
    stats = compute_dashboard_stats(applications, date(2026, 7, 8))
    assert stats.applications_this_week == 0


def test_stats_to_rows_shape():
    stats = compute_dashboard_stats([], date(2026, 7, 8))
    rows = stats_to_rows(stats, "2026-07-08T12:00:00Z")
    assert rows[0] == ["Metric", "Value"]
    assert rows[-1] == ["Last Updated", "2026-07-08T12:00:00Z"]
    assert len(rows) == 8


def test_refresh_dashboard_reads_applications_and_overwrites_dashboard_tab():
    applications_ws = MagicMock()
    applications_ws.row_values.return_value = APPLICATIONS_COLUMNS
    applications_ws.get_all_records.return_value = [
        {"Date Applied": "2026-07-06", "Interview Stage": "Onsite", "Feedback": ""}
    ]
    dashboard_ws = MagicMock()

    spreadsheet = MagicMock()
    spreadsheet.worksheet.side_effect = lambda name: {
        "Applications": applications_ws,
        "Weekly Dashboard": dashboard_ws,
    }[name]

    stats = refresh_dashboard(spreadsheet, date(2026, 7, 8), "2026-07-08T12:00:00Z")

    assert stats.interviews == 1
    dashboard_ws.clear.assert_called_once()
    dashboard_ws.update.assert_called_once()
    written_rows = dashboard_ws.update.call_args[0][0]
    assert written_rows[0] == ["Metric", "Value"]

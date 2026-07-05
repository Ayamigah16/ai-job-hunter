"""Computes Weekly Dashboard aggregates from the read-only Applications tab.

Interview Stage / Feedback are free text the user fills in by hand, so
classification here is intentionally simple keyword matching, not a strict
state machine — tune the *_KEYWORDS constants below as your own note-taking
style settles.

Weekly Dashboard is entirely computed/derived — unlike Open Roles or Target
Companies there's nothing user-owned in it, so a full clear + rewrite each
run is fine; no partial-column non-clobber contract is needed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from ai_job_hunter.sheets.schema import (
    APPLICATIONS_COLUMNS,
    APPLICATIONS_SHEET,
    WEEKLY_DASHBOARD_COLUMNS,
    WEEKLY_DASHBOARD_SHEET,
    validate_headers,
)

if TYPE_CHECKING:
    import gspread

OFFER_KEYWORDS = ("offer",)
REJECTION_KEYWORDS = ("reject", "declined", "no longer moving forward", "position filled")
INTERVIEW_KEYWORDS = ("interview", "screen", "onsite", "phone call", "technical", "panel")

_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y")


@dataclass
class DashboardStats:
    applications_this_week: int
    interviews: int
    response_rate: float
    rejections: int
    pending: int
    offers: int


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text.lower() for keyword in keywords)


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def compute_dashboard_stats(applications: list[dict[str, str]], today: date) -> DashboardStats:
    """Classifies each application into exactly one bucket, by precedence:
    offer > rejection > interview > pending. An application that reached an
    offer clearly also had an interview, but it's more useful on a dashboard
    to see it counted once, in its most-advanced stage, than in both.
    """
    week_start = today - timedelta(days=today.weekday())
    applications_this_week = 0
    interviews = 0
    rejections = 0
    offers = 0
    responded = 0

    for row in applications:
        applied_date = _parse_date(row.get("Date Applied", ""))
        if applied_date is not None and applied_date >= week_start:
            applications_this_week += 1

        combined = f"{row.get('Interview Stage', '')} {row.get('Feedback', '')}"
        if _contains_any(combined, OFFER_KEYWORDS):
            offers += 1
            responded += 1
        elif _contains_any(combined, REJECTION_KEYWORDS):
            rejections += 1
            responded += 1
        elif _contains_any(combined, INTERVIEW_KEYWORDS):
            interviews += 1
            responded += 1

    total = len(applications)
    pending = max(total - rejections - offers, 0)
    response_rate = round((responded / total * 100), 1) if total else 0.0

    return DashboardStats(
        applications_this_week=applications_this_week,
        interviews=interviews,
        response_rate=response_rate,
        rejections=rejections,
        pending=pending,
        offers=offers,
    )


def stats_to_rows(stats: DashboardStats, generated_at: str) -> list[list[str]]:
    return [
        WEEKLY_DASHBOARD_COLUMNS,
        ["Applications This Week", str(stats.applications_this_week)],
        ["Interviews", str(stats.interviews)],
        ["Response Rate", f"{stats.response_rate}%"],
        ["Rejections", str(stats.rejections)],
        ["Pending", str(stats.pending)],
        ["Offers", str(stats.offers)],
        ["Last Updated", generated_at],
    ]


def refresh_dashboard(
    spreadsheet: gspread.Spreadsheet, today: date, generated_at: str
) -> DashboardStats:
    applications_ws = spreadsheet.worksheet(APPLICATIONS_SHEET)
    validate_headers(applications_ws, APPLICATIONS_COLUMNS)
    applications = applications_ws.get_all_records()

    stats = compute_dashboard_stats(applications, today)

    dashboard_ws = spreadsheet.worksheet(WEEKLY_DASHBOARD_SHEET)
    dashboard_ws.clear()
    dashboard_ws.update(stats_to_rows(stats, generated_at), "A1")
    return stats

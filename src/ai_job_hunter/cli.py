"""Command-line entrypoint. `ai-job-hunter --help` for the full command list."""

from __future__ import annotations

import click

from ai_job_hunter.config_settings import get_settings
from ai_job_hunter.pipeline import fetch_all, fetch_score_and_dedup
from ai_job_hunter.pipeline import run as run_pipeline
from ai_job_hunter.registry import (
    DEFAULT_AGGREGATORS_PATH,
    DEFAULT_COMPANIES_PATH,
    RegistryError,
    load_aggregators,
    load_companies,
)
from ai_job_hunter.scoring.profile import DEFAULT_SKILLS_PROFILE_PATH, load_scoring_profile
from ai_job_hunter.sheets.client import SheetsConfigError, get_gspread_client, open_spreadsheet
from ai_job_hunter.sheets.writer import GoogleSheetsWriter, SheetSchemaError


@click.group()
def cli() -> None:
    """AI Job Hunter command-line interface."""


@cli.command("validate-config")
def validate_config() -> None:
    """Load config/companies.yaml and config/aggregators.yaml, report errors."""
    try:
        companies = load_companies(DEFAULT_COMPANIES_PATH)
        aggregators = load_aggregators(DEFAULT_AGGREGATORS_PATH)
    except RegistryError as exc:
        click.secho(f"Config invalid: {exc}", fg="red")
        raise SystemExit(1) from exc

    fetchable = [c for c in companies if c.ats_type.value != "unsupported"]
    click.secho(
        f"OK: {len(companies)} companies ({len(fetchable)} fetchable, "
        f"{len(companies) - len(fetchable)} tracked-only) and "
        f"{len(aggregators)} aggregator sources loaded from "
        f"{DEFAULT_COMPANIES_PATH} and {DEFAULT_AGGREGATORS_PATH}.",
        fg="green",
    )


@cli.command("fetch")
@click.option(
    "--dry-run/--no-dry-run",
    default=True,
    help="Fetch and print results without writing anywhere "
    "(the only mode until Phase 4 adds Google Sheets sync).",
)
@click.option(
    "--score",
    is_flag=True,
    default=False,
    help="Filter to relevant roles, dedup across sources, score, and print ranked "
    "results instead of raw per-source counts.",
)
@click.option("--top", default=20, show_default=True, help="How many ranked jobs to print.")
def fetch(dry_run: bool, score: bool, top: int) -> None:
    """Fetch postings from every configured company and aggregator source."""
    if not dry_run:
        raise click.ClickException(
            "--no-dry-run isn't implemented yet — Sheets sync lands in Phase 4."
        )

    companies = load_companies(DEFAULT_COMPANIES_PATH)
    aggregators = load_aggregators(DEFAULT_AGGREGATORS_PATH)

    if not score:
        results = fetch_all(companies, aggregators)
        total = 0
        for source_name, jobs in results.items():
            click.echo(f"{source_name}: {len(jobs)} jobs")
            total += len(jobs)
        click.secho(f"Total: {total} jobs from {len(results)} sources", fg="green")
        return

    profile = load_scoring_profile(DEFAULT_SKILLS_PROFILE_PATH)
    scored_jobs = fetch_score_and_dedup(companies, aggregators, profile)
    click.secho(f"{len(scored_jobs)} relevant jobs after filter + dedup", fg="green")
    for scored in scored_jobs[:top]:
        job = scored.job
        click.echo(
            f"[{scored.score.total_score:5.1f}] {job.company} — {job.title} "
            f"({job.location_raw or 'n/a'}) "
            f"must={scored.score.matched_must_have} africa={scored.score.africa_friendly_hint}"
        )


@cli.command("run")
def run() -> None:
    """Fetch, score, dedup, and sync results into the configured Google Sheet."""
    settings = get_settings()
    if not settings.google_application_credentials or not settings.google_sheets_spreadsheet_id:
        raise click.ClickException(
            "Google Sheets isn't configured — set GOOGLE_APPLICATION_CREDENTIALS and "
            "GOOGLE_SHEETS_SPREADSHEET_ID in .env. See the README's Google Sheets setup section."
        )

    companies = load_companies(DEFAULT_COMPANIES_PATH)
    aggregators = load_aggregators(DEFAULT_AGGREGATORS_PATH)
    profile = load_scoring_profile(DEFAULT_SKILLS_PROFILE_PATH)

    try:
        client = get_gspread_client(settings.google_application_credentials)
        spreadsheet = open_spreadsheet(client, settings.google_sheets_spreadsheet_id)
        writer = GoogleSheetsWriter(spreadsheet)
        result = run_pipeline(
            companies, aggregators, profile, writer, settings.score_threshold_write
        )
    except (SheetsConfigError, SheetSchemaError) as exc:
        raise click.ClickException(str(exc)) from exc

    click.secho(
        f"Open Roles: {len(result.open_roles.appended)} new, "
        f"{len(result.open_roles.updated)} updated, "
        f"{len(result.open_roles.skipped)} below threshold. "
        f"Target Companies: {len(result.target_companies.appended)} new, "
        f"{len(result.target_companies.updated)} updated.",
        fg="green",
    )


if __name__ == "__main__":
    cli()

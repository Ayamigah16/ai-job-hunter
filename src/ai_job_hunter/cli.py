"""Command-line entrypoint. `ai-job-hunter --help` for the full command list."""

from __future__ import annotations

import click

from ai_job_hunter.pipeline import fetch_all
from ai_job_hunter.registry import (
    DEFAULT_AGGREGATORS_PATH,
    DEFAULT_COMPANIES_PATH,
    RegistryError,
    load_aggregators,
    load_companies,
)


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
    help="Fetch and print per-source counts without writing anywhere "
    "(the only mode until Phase 4 adds Google Sheets sync).",
)
def fetch(dry_run: bool) -> None:
    """Fetch postings from every configured company and aggregator source."""
    if not dry_run:
        raise click.ClickException(
            "--no-dry-run isn't implemented yet — Sheets sync lands in Phase 4."
        )

    companies = load_companies(DEFAULT_COMPANIES_PATH)
    aggregators = load_aggregators(DEFAULT_AGGREGATORS_PATH)
    results = fetch_all(companies, aggregators)

    total = 0
    for source_name, jobs in results.items():
        click.echo(f"{source_name}: {len(jobs)} jobs")
        total += len(jobs)

    click.secho(f"Total: {total} jobs from {len(results)} sources", fg="green")


if __name__ == "__main__":
    cli()

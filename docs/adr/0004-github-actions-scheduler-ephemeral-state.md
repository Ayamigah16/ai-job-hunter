# 0004 — GitHub Actions Scheduler, Not Local Cron

## Status
Accepted

## Context
The pipeline needs to run on a recurring schedule without the user manually invoking it. The
project also doubles as a DevOps-flavored portfolio piece, where a CI/CD-driven scheduling
approach is itself a demonstrable skill, not just plumbing.

## Decision
**GitHub Actions scheduled workflow**, not local cron. `scheduled-run.yml` runs daily
(`0 6 * * *`) plus on manual `workflow_dispatch`; `integration-smoke.yml` runs weekly
(`0 5 * * 1`) plus on manual dispatch, exercising `tests/integration/test_live_adapters.py`
against a handful of real endpoints (one company per representative ATS type, one aggregator) to
catch upstream schema breakage between the four ATS integration examples early, without touching
the network on every regular PR/push (`ci.yml` stays fully offline, `pytest`'s default `addopts`
excludes `@pytest.mark.integration`).

Reasoning over local cron: no dependency on a personal machine being powered on and
network-reachable at the scheduled time; secrets live in GitHub's encrypted secret store instead
of an indefinitely-protected local dotfile; failures surface as GitHub-native run history/logs
and failure-notification emails, none of which needs to be built. `Dockerfile` also exists so the
same image can be run locally (`docker build . && docker run --env-file .env ai-job-hunter run`)
or on any other container platform later, independent of GitHub Actions specifically.

**Critical implication — ephemeral runners.** Every scheduled run starts on a brand-new VM with
nothing persisted from the previous run. This is exactly why dedup/idempotency (ADR-0003) is
designed to recompute job identity from the Google Sheet's own current content on every run
rather than from a local cache file, and why "already notified" is structural (only genuinely
new rows trigger a notification) rather than a persisted log. HTTP-level caching (ETags /
If-Modified-Since) is deliberately skipped for now — it can't reliably persist across ephemeral
runs without `actions/cache`, and a full daily re-fetch across ~26 sources is cheap enough that
the optimization isn't worth the complexity yet. Revisit only if rate limits become a real
problem as the company registry grows toward 100-300 entries.

Local cron is not recommended for production use of this project — it remains useful only for
manual iteration during development (`ai-job-hunter run` invoked by hand, or a personal cron
entry on a dev machine), never as the way this is meant to actually run day to day.

## Consequences
- Secrets (`GCP_SERVICE_ACCOUNT_KEY`, `GOOGLE_SHEETS_SPREADSHEET_ID`, `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_CHAT_ID`, `SMTP_*`) must be configured as GitHub repo secrets before
  `scheduled-run.yml` can succeed — this is a one-time manual setup step in GitHub's UI that
  can't be done from the codebase itself.
- The service account JSON key is written to `$RUNNER_TEMP` at job start, never checked into the
  repo or workspace, and is gone the moment the runner is torn down.
- A stuck/broken adapter degrades gracefully (per ADR-0002's per-record error isolation) rather
  than failing the whole scheduled run, so one bad company doesn't block the sheet from updating
  with everything else that succeeded.

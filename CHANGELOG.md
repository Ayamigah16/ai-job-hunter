# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Project scaffold: packaging (`pyproject.toml`), lint/test config (ruff, pytest, mypy),
  CI workflow running lint + unit tests on every PR, `.env.example`, `.gitignore` with
  credentials excluded, pre-commit hooks, `content_generation` extension-point stub
  (CV/cover-letter generation deferred), ADR-0001 recording the stack/datastore decisions.
- Core data models (`JobPosting`, `ScoreResult`, `ScoredJob`, `ATSType`, `AggregatorType`) and
  a validated company/aggregator registry loader (`registry.py`) backed by `config/companies.yaml`
  and `config/aggregators.yaml` — data files, not code, so growing the registry needs no src/
  changes. Seeded with 26 companies (20 with live-verified ATS board tokens across Greenhouse,
  Ashby, and Workable; 6 tracked with `ats_type: unsupported` pending a future adapter) and 5
  job-aggregator sources. Added a first-draft `config/skills_profile.yaml` scoring profile and
  `config/regions.json` country-to-region lookup. New `ai-job-hunter validate-config` CLI command.
- ATS/aggregator adapters for all 8 planned ATS platforms (Greenhouse, Lever, Ashby, Workable,
  SmartRecruiters, BambooHR, Recruitee, Personio) and all 5 job aggregators (RemoteOK, Arbeitnow,
  Remotive, Himalayas, We Work Remotely), each with a fixture-based unit test (130 tests total).
  New `registry_map.py` (ATSType/AggregatorType -> adapter class, no ATS-specific branching in
  the pipeline), `pipeline.py` (`fetch_all`), and `ai-job-hunter fetch --dry-run` CLI command.
  Live-validated end-to-end: a real run against the full seed registry pulled 2,295 postings
  from 26 sources with zero unhandled exceptions. Corrected Fly.io's registry entry (BambooHR,
  not "no public ATS" as originally researched) based on what adapter construction found live.
  See ADR-0002 for the adapter abstraction and the field-mapping-quality tradeoffs per source.
- Scoring engine (`scoring/profile.py`, `scoring/filters.py`, `scoring/scorer.py`) and
  cross-source dedup (`dedup.py`). `is_relevant()` filters company-wide job boards down to
  target-role postings before scoring (a job must match a target role title or mention a
  must-have skill to survive at all); `score_job()` is a pure function combining must/nice-to-have
  skill matches, role-title match, remote-friendliness, salary disclosure, and sponsorship
  mentions per `config/skills_profile.yaml`'s configurable weights. `compute_job_id()` gives the
  same posting the same id regardless of which source found it (canonicalized URL, or
  company+title when no URL), so `dedup_jobs()` collapses duplicates across a company's own board
  and any aggregator that also indexed it. New `pipeline.fetch_score_and_dedup` and
  `ai-job-hunter fetch --dry-run --score` CLI flag. Live-validated: a real run surfaced 795
  relevant, deduped, ranked jobs from the 2,295 raw postings fetched in Phase 2 — including a
  real DevOps role based in Egypt ranking in the top 15, a direct hit for the Africa-hiring
  use case this project exists for.
- Google Sheets integration (`sheets/schema.py`, `sheets/client.py`, `sheets/writer.py`),
  `regions.py` (best-effort location -> country/region lookup for the Open Roles sheet), and
  `pipeline.run` / `ai-job-hunter run`. `GoogleSheetsWriter` (real, gspread-backed) and
  `FakeSheetsWriter` (in-memory test double) share the same row-building logic, so unit tests
  against the fake are meaningful evidence of the real writer's behavior. Enforces the
  non-clobber contract end-to-end: reruns never duplicate rows (job identity recomputed from
  each existing row's own cells, see ADR-0003) and never overwrite a user-edited Status/Notes or
  a curated Target Companies field. Worksheet headers are validated against `sheets/schema.py`
  at sync time and fail loudly on drift. Code is fully unit-tested (158 tests) but not yet
  live-verified against a real spreadsheet — that requires a one-time Google Cloud service
  account setup documented in the README.
- Notifications (`notifiers/base.py`, `email_notifier.py`, `telegram_notifier.py`,
  `dispatcher.py`): `NotifierDispatcher` fans out to Telegram and/or SMTP email, isolating one
  channel's failure from the other. Wired into `pipeline.run` so a summary fires only for jobs
  newly appended THIS run and scoring at or above `SCORE_THRESHOLD_NOTIFY` — an immediate rerun
  with no new jobs sends nothing, since "already notified" is structural (see ADR-0003). `run`
  works with zero, one, or both channels configured. 168 unit tests total (SMTP/HTTP calls
  mocked); live delivery is pending your Telegram bot token / SMTP credentials, documented in
  the README's Notifications setup section.
- Scheduler and containerization (`v0.2.0`): `.github/workflows/scheduled-run.yml` (daily cron +
  manual dispatch, reads all config from repo secrets, writes the service account key to
  `$RUNNER_TEMP` at job start), `.github/workflows/integration-smoke.yml` (weekly + manual,
  runs `tests/integration/test_live_adapters.py` against real Greenhouse/Ashby/Workable/RemoteOK
  endpoints, asserting structural shape rather than exact content so routine job-posting churn
  doesn't cause flakiness), and a `Dockerfile`. Docker image build and run verified locally
  end-to-end: `validate-config` and a live `fetch --dry-run --score` both succeeded inside the
  container. See ADR-0004 for why GitHub Actions over local cron and the ephemeral-runner
  implications for state design. The daily schedule itself needs GitHub repo secrets configured
  (documented in the README) before it can run for real.
- Weekly Dashboard tab (`dashboard.py`, `ai-job-hunter dashboard` CLI command): reads the
  Applications tab, classifies each row into exactly one bucket (offer > rejection > interview >
  pending, by keyword match on Interview Stage/Feedback — free text, so intentionally simple, see
  the module docstring for tuning), and fully overwrites the Weekly Dashboard tab with
  Applications This Week / Interviews / Response Rate / Rejections / Pending / Offers — this tab
  is entirely computed, so unlike Open Roles/Target Companies there's no partial-column
  non-clobber contract needed. Wired into `scheduled-run.yml` after the main sync. Moved header
  validation (`validate_headers`/`SheetSchemaError`) from `sheets/writer.py` into `sheets/schema.py`
  so both `writer.py` and `dashboard.py` share one implementation. Also fixed a latent bug found
  while building this: `GoogleSheetsWriter`'s two `worksheet.update()` calls had gspread's
  `(values, range_name)` arguments swapped — never caught by the unit suite since
  `FakeSheetsWriter` doesn't touch the real gspread API, only surfaced by checking gspread's
  actual method signature while wiring the new dashboard code the same way.

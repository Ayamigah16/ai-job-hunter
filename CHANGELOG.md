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

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

# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Project scaffold: packaging (`pyproject.toml`), lint/test config (ruff, pytest, mypy),
  CI workflow running lint + unit tests on every PR, `.env.example`, `.gitignore` with
  credentials excluded, pre-commit hooks, `content_generation` extension-point stub
  (CV/cover-letter generation deferred), ADR-0001 recording the stack/datastore decisions.

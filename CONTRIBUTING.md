# Contributing

## Dev setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                      # unit tests only, offline (default)
ruff check .                # lint
mypy src/ai_job_hunter       # type check
pytest -m integration        # hits real endpoints, not run by default
```

CI (`.github/workflows/ci.yml`) runs ruff, mypy, and pytest with an 85% coverage gate on every
PR — run all three locally before pushing.

## Adding a company

Companies are **data, not code** — edit `config/companies.yaml` only, no `src/` changes needed.

1. Find the company's careers page and identify its ATS. Look at the URL: `job-boards.greenhouse.io/{token}`,
   `jobs.lever.co/{token}`, `jobs.ashbyhq.com/{token}`, `apply.workable.com/{token}`,
   `jobs.smartrecruiters.com/{token}`, `{token}.bamboohr.com`, `{token}.recruitee.com`, or
   `{token}.jobs.personio.de` all reveal the ATS type and board token directly.
2. **Verify the token before committing it.** Generic slugs can silently resolve to an unrelated
   company of the same name on the same ATS (this has actually happened during this project's own
   research — `neon`, `render`, `railway`, and `fly` all had collisions). Fetch the board's API
   endpoint directly (see `docs/adr/0002-ats-adapter-abstraction.md` for exact URLs) and confirm
   the returned company name / job content actually matches, not just that you got a 200.
3. Add the entry to `config/companies.yaml` following the existing schema (`name`, `slug`,
   `ats_type`, `board_token`, `industry`, `hires_in_africa`, `priority`, optional `notes`). If the
   company's ATS isn't one of the 8 supported types, use `ats_type: unsupported` and note in
   `notes` what it actually uses (Workday, Teamtailor, in-house, ...) — it'll still show up in the
   Target Companies sheet, just won't be auto-fetched.
4. Run `ai-job-hunter validate-config` — it must exit 0.
5. Run `ai-job-hunter fetch --dry-run` and confirm your new company shows a non-zero (or
   expectedly-zero) job count with no error.

## Adding a new ATS adapter

If a company uses an ATS not yet in `ats_type` (Workday, Teamtailor, an in-house board, etc.):

1. Add the new value to the `ATSType` enum in `models.py`.
2. Create `src/ai_job_hunter/adapters/{name}.py` implementing `BaseATSAdapter`
   (`adapters/base.py`) — see any existing adapter (`greenhouse.py` is the simplest) as a
   template. `fetch_raw()` should return `[]` on 404/empty, never raise; `parse()` should return
   `None` for unmappable records, never raise.
3. Register it in `adapters/registry_map.py`'s `ATS_ADAPTERS` dict.
4. Add a small **synthetic** fixture (2-3 postings, not scraped real data) under
   `tests/fixtures/{name}/sample_response.json`, modeled on the real API shape — verify that
   shape against at least one live company using that ATS before writing the fixture.
5. Add `tests/unit/adapters/test_{name}.py` covering field mapping, especially the `remote` flag.

## Growing to more companies

The registry seed intentionally started small (~40) with real, live-verified integration targets
per ATS type rather than hundreds of unverified guesses. Growing it further is exactly the
"Adding a company" flow above, repeated — a good task to batch across a PR touching only
`config/companies.yaml`.

# 0003 — Dedup and Idempotency via Recomputed Sheet State, Not a Separate Store

## Status
Accepted

## Context
The pipeline runs repeatedly (manually now, on a schedule from Phase 6 onward) against sources
that return the same postings run after run, plus the same posting is often visible from more
than one source (a company's own ATS board and a job aggregator that also indexed it). Re-running
must not create duplicate `Open Roles` rows, and it must never overwrite `Status`/`Notes` a user
has already edited by hand, or `Target Companies` columns (`Hires in Africa?`, `Referral Needed?`,
`Priority`) a user has curated. Phase 6 will also move execution to GitHub Actions, whose runners
are ephemeral — nothing on disk survives between runs.

## Decision
**Identity is a pure function, recomputed every time, never persisted separately.**
`dedup.compute_job_id(company, title, url)` hashes the canonicalized apply URL (query string
stripped of tracking params, trailing slash and case normalized) or, when a source gives no
usable URL, a normalized `company|title` pair. The exact same function is applied to freshly
fetched jobs (`pipeline.fetch_score_and_dedup`, collapsing same-posting duplicates across sources
within one run) **and** to every existing `Open Roles` row read back from the sheet
(`GoogleSheetsWriter.sync_open_roles`, recomputing each row's id from its own Company/Role/Apply
Link cells). Two ids match if and only if the same posting is involved — no lookup table, cache,
or `_NotifyLog` tab is needed, and none would survive an ephemeral GitHub Actions runner anyway.

**Sync is append-or-metadata-update, never delete, never touch curated columns.** For each scored
job at or above the write threshold: if its id already exists in the sheet, only
`OPEN_ROLES_MANAGED_COLUMNS` (Company through Deadline) are overwritten — `Status` and `Notes`
are never touched on an existing row. If the id is new, a full row is appended with
`Status = "New"`. The same pattern applies to `Target Companies`, keyed by company name instead
of a job id: only `Industry`/`Careers Page` refresh on an existing row; `Remote Friendly`,
`Hires in Africa?`, `Referral Needed?`, and `Priority` are set only when the pipeline creates the
row and are never touched again. `GoogleSheetsWriter` simply has no method that writes to
`Networking` or `Applications` at all — those tabs are entirely user-owned.

**Schema drift fails loudly.** Both sync methods read the worksheet's actual header row and
compare it against `sheets/schema.py` before writing anything; a mismatch raises
`SheetSchemaError` with the expected vs. actual columns rather than silently writing values into
the wrong column.

**A future notification gap is accepted, not engineered around.** Since "already notified"
(Phase 5) will also be derived structurally — a job can only be freshly appended once — a crash
between the sheet write and the notify step means that job won't be re-notified on the next run
(it's now an existing row). This is an accepted MVP tradeoff, not a bug to fix now; a `Notified`
timestamp column is a plausible Phase 8 hardening item if it turns out to matter in practice.

## Consequences
- No local cache/state file exists anywhere in this codebase for dedup purposes — correctness
  survives a full ephemeral-runner restart by construction, not by careful cache invalidation.
- `GoogleSheetsWriter` and `FakeSheetsWriter` (the in-memory unit-test double) share the exact
  same row-building functions (`build_open_roles_row`, `build_target_company_row`), so a test
  passing against the fake is meaningful evidence the real writer's row shape is correct — only
  the gspread I/O layer itself (`worksheet.update`/`append_rows`/`get_all_records`) is unverified
  by the unit suite, since it requires a real spreadsheet and service account credentials.
- Recomputing every row's id on every sync is O(existing rows) work per run — fine at the
  hundreds-of-rows scale this project targets; would need a real index if the sheet ever grew to
  many thousands of rows.

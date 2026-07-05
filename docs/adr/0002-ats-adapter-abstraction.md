# 0002 — Per-ATS-Type Adapter Registry, Not Per-Company Code

## Status
Accepted

## Context
Job postings need to be fetched from many companies, but most companies' careers pages are
themselves powered by one of a small number of Applicant Tracking Systems (Greenhouse, Lever,
Ashby, Workable, SmartRecruiters, BambooHR, Recruitee, Personio), each exposing its own public,
unauthenticated JSON or XML job-listing API. Standalone job aggregators (RemoteOK, Arbeitnow,
Remotive, Himalayas, We Work Remotely) add a second category of source that isn't tied to a
single company at all.

## Decision
One adapter class per **ATS platform**, not per **company**. `BaseATSAdapter` (company-scoped:
`fetch_raw(company)` / `parse(raw, company)`) and `BaseAggregatorAdapter` (source-scoped:
`fetch_raw(aggregator)` / `parse(raw, aggregator)`) are the two abstractions; `registry_map.py`
maps `ATSType`/`AggregatorType` enum values to their adapter class, so `pipeline.py` has zero
ATS-specific branching — adding a new company that uses an already-supported ATS is a
config-only change (`config/companies.yaml`), not a code change.

Both base classes fund through a shared `_safe_parse_many` helper so one malformed record from a
source never aborts the whole fetch — it's logged and skipped. A shared `strip_html()` utility
(unescape-then-strip-tags, in that order) normalizes the several sources whose descriptions are
HTML; note the order matters — some Greenhouse boards double-encode their HTML, so unescaping
before stripping is required to actually remove the tags rather than leaving literal `<div>` text
behind.

Field mapping quality varies deliberately by source and is documented per-adapter rather than
forced into a lowest-common-denominator shape: Ashby (`isRemote`), Arbeitnow (`remote`), and
Recruitee (`remote`) expose an explicit remote boolean and are trusted directly; Greenhouse,
Workable, BambooHR, and Personio have no structured remote flag and fall back to a
case-insensitive regex over location/title text; the five aggregators are remote-only by
definition and hardcode `remote=True`. `tech_stack` is left `[]` for company-scoped ATS sources
(extracting skills from free-text descriptions is the scoring engine's job, not an adapter's) but
is populated directly from RemoteOK's/Arbeitnow's/Himalayas' native tags/categories fields, since
those are already clean structured data worth keeping.

## Consequences
- 20 of the 26 seeded companies were live-verified against real endpoints during adapter
  construction (each confirmed by matching the returned company name/job content, not just an
  HTTP 200 — see `config/companies.yaml` history and the research that produced it), catching two
  wrong assumptions in the process: Fly.io was initially marked as having no public ATS but was
  found to use BambooHR; Pulumi's and Wiz's Greenhouse tokens (`pulumicorporation`, `wizinc`)
  differ from the naive lowercase-company-name guess.
- A `cli fetch --dry-run` run against the full seed registry pulled 2,295 real postings from 26
  sources with zero unhandled exceptions, validating the abstraction end-to-end before any
  scoring/sheet-sync logic exists.
- Generic-looking board tokens can silently resolve to an unrelated company of the same name on
  the same ATS (observed for `neon`, `render`, `railway`, `fly` during research) — anyone adding a
  new company to `config/companies.yaml` must verify the returned content actually matches the
  target company, not just that the request returns 200.
- Six companies (DigitalOcean, Red Hat, CrowdStrike, Civo, Automattic, Snyk) use an ATS with no
  adapter yet (Workday, Teamtailor, in-house, or a deactivated board) and are seeded with
  `ats_type: unsupported` — tracked for the Target Companies sheet but silently skipped by
  `pipeline.fetch_all`. Adding Workday/Teamtailor support is a future `feature/*` branch, not a
  blocker for the current phases.

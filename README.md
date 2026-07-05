# AI Job Hunter

An automated pipeline that discovers, filters, scores, and tracks remote
DevOps / Platform / SRE / Cloud / DevSecOps job openings across company career pages and job
aggregators, writing results into a Google Sheet and notifying on high-match new roles.

> Status: early build-out, in progress. See [CHANGELOG.md](CHANGELOG.md) for what's landed and
> the roadmap below for what's next.

## Why this exists

Manually tracking hundreds of company career pages for remote-friendly, internationally-hiring
DevOps/Platform/SRE roles doesn't scale. This project automates the discovery and first-pass
filtering, and gives a single spreadsheet as the source of truth for applications and follow-up.

## How it works (target architecture)

```
company career pages (ATS APIs)  ─┐
job aggregators (APIs / RSS)     ─┼─▶ adapters ─▶ filter + score ─▶ dedup ─▶ Google Sheet ─▶ notify
                                  ─┘                                              │
                                                                        (Email + Telegram)
```

- **Adapters** poll each company's Applicant Tracking System (Greenhouse, Lever, Ashby,
  Workable, SmartRecruiters, BambooHR, Recruitee, Personio) or a job aggregator (RemoteOK,
  Arbeitnow, Remotive, Himalayas, We Work Remotely), using each source's public JSON/XML API or
  RSS feed rather than scraping rendered HTML — far lower maintenance.
- **Scoring** matches each posting against a configurable skills/keyword profile
  (`config/skills_profile.yaml`) and flags remote-friendliness, salary disclosure, and
  sponsorship mentions.
- **Dedup** collapses the same posting seen via multiple sources (e.g. a company's own board and
  an aggregator) using a stable hash of the canonicalized apply URL.
- **The Google Sheet** is the system of record: an `Open Roles` tab the pipeline appends/updates,
  plus `Target Companies`, `Networking`, `Applications`, and a computed `Weekly Dashboard` — the
  last three are user-owned or read-only from the pipeline's perspective (see
  [docs/adr](docs/adr/) for the exact non-clobber contract).
- **Notifications** (Email + Telegram) fire only for genuinely new, high-scoring roles.

CV/cover-letter AI generation is intentionally **not** part of the current build — see Roadmap.

## Quickstart (development)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

Later phases will require a `.env` (copy `.env.example`) with Google Sheets, Telegram, and SMTP
credentials — none of that is needed yet for the current (scaffold) stage.

## Project layout

See `src/ai_job_hunter/` for the package; `config/` holds data (company registry, skills
profile) that grows independently of the code; `docs/adr/` records architectural decisions as
they're made; `tests/unit` runs offline against fixtures, `tests/integration` (excluded by
default) hits real endpoints.

## Roadmap

- [x] Project scaffold, CI, docs structure
- [ ] Core models + config loader + seed company registry
- [ ] ATS adapters (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, BambooHR, Recruitee,
      Personio) + aggregator adapters
- [ ] Scoring engine + cross-source dedup
- [ ] Google Sheets integration (MVP milestone, `v0.1.0`)
- [ ] Email + Telegram notifications
- [ ] GitHub Actions scheduler + Docker (`v0.2.0`)
- [ ] Weekly Dashboard tab
- [ ] Hardening: retries, structured logging, mypy, coverage gate
- [ ] Grow company registry toward 100-300 companies (ongoing, config-only)
- [ ] **Deferred**: AI-generated tailored CVs and cover letters
- [ ] **Deprioritized**: Wellfound/AngelList and LinkedIn (no public API; scraping-only, higher
      maintenance/ToS risk — revisit only if the above sources prove insufficient)

## License

MIT — see [LICENSE](LICENSE).

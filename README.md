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

```text
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

# Validate the company/aggregator registry
ai-job-hunter validate-config

# Fetch real postings from every configured source (no writes anywhere yet)
ai-job-hunter fetch --dry-run

# Filter to relevant roles, dedup across sources, score, and print the top matches
ai-job-hunter fetch --dry-run --score --top 20
```

## Google Sheets setup (required for `ai-job-hunter run`)

`fetch --dry-run` (with or without `--score`) needs no credentials at all. Only the full
`run` command — which syncs results into your spreadsheet — needs the setup below.

1. **Create the spreadsheet.** Make a new Google Sheet with tabs named exactly `Open Roles`,
   `Target Companies`, `Networking`, `Applications`, `Weekly Dashboard`. Give `Open Roles` the
   header row `Company | Role | Country | Remote | Region | Salary | Tech Stack | Apply Link |
   Date Posted | Deadline | Status | Notes`, and `Target Companies` the header row `Company |
   Industry | Careers Page | Remote Friendly | Hires in Africa? | Referral Needed? | Priority`
   (exact spelling/order — the pipeline validates this and fails loudly on drift, see
   `sheets/schema.py`). Copy the spreadsheet id out of its URL
   (`docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`).
2. **Create a GCP service account.** In the [Google Cloud Console](https://console.cloud.google.com/):
   create (or reuse) a project, enable the **Google Sheets API**, then under
   *IAM & Admin → Service Accounts* create a service account, add a JSON key, and download it.
3. **Share the sheet with the service account.** Open the downloaded JSON, copy its
   `client_email` value, and share your spreadsheet with that email as **Editor** — the same way
   you'd share it with a person.
4. **Configure `.env`.** Copy `.env.example` to `.env`, save the JSON key under
   `credentials/service-account.json` (already gitignored), and set
   `GOOGLE_APPLICATION_CREDENTIALS=./credentials/service-account.json` and
   `GOOGLE_SHEETS_SPREADSHEET_ID=<the id from step 1>`.
5. Run `ai-job-hunter run`.

## Notifications setup (optional)

`ai-job-hunter run` sends a summary via Telegram and/or email for newly-appended jobs scoring at
or above `SCORE_THRESHOLD_NOTIFY` (default 70) in `.env`. Both are optional and independent —
configure one, both, or neither (with neither configured, `run` still syncs the sheet, it just
skips notifications and tells you so).

**Telegram**: message [@BotFather](https://t.me/BotFather) with `/newbot` and follow the prompts
to get a bot token. Then message your new bot anything, and fetch
`https://api.telegram.org/bot<token>/getUpdates` in a browser to find your numeric chat id in the
response. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`.

**Email**: uses plain SMTP. For Gmail, create an
[app password](https://myaccount.google.com/apppasswords) (regular passwords won't work with
2FA enabled) and set `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USERNAME` (your Gmail
address), `SMTP_PASSWORD` (the app password), and optionally `NOTIFY_EMAIL_FROM`/
`NOTIFY_EMAIL_TO` if they differ from `SMTP_USERNAME`. Any other SMTP provider (Outlook,
SendGrid's SMTP relay, etc.) works the same way — just change `SMTP_HOST`/`SMTP_PORT`.

## Project layout

See `src/ai_job_hunter/` for the package; `config/` holds data (company registry, skills
profile) that grows independently of the code; `docs/adr/` records architectural decisions as
they're made; `tests/unit` runs offline against fixtures, `tests/integration` (excluded by
default) hits real endpoints.

## Roadmap

- [x] Project scaffold, CI, docs structure
- [x] Core models + config loader + seed company registry
- [x] ATS adapters (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, BambooHR, Recruitee,
      Personio) + aggregator adapters
- [x] Scoring engine + cross-source dedup
- [x] Google Sheets integration (MVP milestone, `v0.1.0`) — code complete, pending your Google
      Cloud setup for a live end-to-end run (see setup section above)
- [x] Email + Telegram notifications — code complete, pending your bot token/SMTP setup for a
      live test (see setup section above)
- [ ] GitHub Actions scheduler + Docker (`v0.2.0`)
- [ ] Weekly Dashboard tab
- [ ] Hardening: retries, structured logging, mypy, coverage gate
- [ ] Grow company registry toward 100-300 companies (ongoing, config-only)
- [ ] **Deferred**: AI-generated tailored CVs and cover letters
- [ ] **Deprioritized**: Wellfound/AngelList and LinkedIn (no public API; scraping-only, higher
      maintenance/ToS risk — revisit only if the above sources prove insufficient)

## License

MIT — see [LICENSE](LICENSE).

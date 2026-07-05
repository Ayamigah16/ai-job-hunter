# 0001 — Stack, Datastore, and Notification Channels

## Status
Accepted

## Context
This project automates discovery, filtering, scoring, and tracking of remote
DevOps/Platform/SRE/Cloud job openings, writing results into a spreadsheet the user already
lives in day-to-day, and notifying on high-match new roles. Several equally valid choices exist
for the implementation language, the system-of-record datastore, and the notification channel(s).

## Decision
- **Language/runtime: Python 3.11+.** Best ecosystem for scraping/HTTP polling (requests),
  structured data handling (pydantic), and cron-style batch jobs. Also aligns with the project's
  secondary goal of being a DevOps-flavored portfolio piece (Python + Docker + GitHub Actions).
- **Datastore: Google Sheets**, not Airtable or a local database. The user already lives in
  Google Drive; Sheets requires no new account, is trivially shareable, and supports ad-hoc
  manual editing (Status, Notes, Priority) alongside automated writes. Access via a GCP service
  account (see ADR-0003 for the write/idempotency contract).
- **Notifications: both Email and Telegram.** Telegram gives instant push at zero cost; email
  gives a durable, searchable record. Both are cheap to support via a single `Notifier` protocol
  with a fan-out dispatcher, so supporting both costs little beyond one extra adapter.
- **CV/cover-letter AI generation: explicitly deferred.** The core discovery/scoring/tracking
  loop is valuable on its own and has enough moving parts (8+ ATS integrations, scoring, sheet
  sync, notifications, scheduling) to be a complete first milestone. Content generation is a
  distinct problem (prompt design, resume templating, tone) that deserves its own phase once the
  job pipeline is proven reliable. A `ContentGenerator` Protocol stub
  (`src/ai_job_hunter/content_generation/base.py`) exists from day one so the extension point is
  visible in the architecture without being built prematurely.

## Consequences
- Google Sheets' API has lower throughput/row-count ceilings than a real database — acceptable
  at the scale of hundreds of tracked postings, would need revisiting if scaled to thousands.
- A GCP project + service account is a one-time manual setup cost for the user (documented in
  the README) since this tool cannot provision Google Cloud resources on its own.
- Adding a third notification channel later (e.g. Slack) is a new `Notifier` implementation, not
  a redesign, because of the protocol-based dispatcher.

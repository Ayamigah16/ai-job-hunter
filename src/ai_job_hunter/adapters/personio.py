"""Adapter for companies whose careers site is powered by Personio.

Unlike every other adapter in this package, Personio's public feed is XML, not
JSON: `GET https://{board_token}.jobs.personio.de/xml?language=en`.

Verified live against `knime.jobs.personio.de/xml` (KNIME is a real,
currently-active Personio customer with open postings at check time), cross-
checked against Personio's own developer docs
(https://developer.personio.de/docs/retrieving-open-job-positions). Both agree
on the shape: a `<workzag-jobs>` root containing repeated `<position>`
elements with direct children `id`, `subcompany`, `office`,
`additionalOffices` (a container of extra `<office>` sub-elements — ignored
here, we only use the primary `office`), `department`, `recruitingCategory`,
`name` (job title), `jobDescriptions` (a container of `<jobDescription>`
blocks, each with its own `name`/`value` pair, `value` holding HTML wrapped in
CDATA), `employmentType`, `seniority`, `schedule`, `keywords`, `occupation`,
`occupationCategory`, and `createdAt` (ISO 8601 with a numeric UTC offset,
e.g. `2026-07-02T15:34:32+00:00`). There is no direct "apply URL" field and no
structured remote flag in either the live example or the docs, matching this
module's fallback design (`_is_remote` regex, constructed job URL). The job
URL pattern (`https://{token}.jobs.personio.de/job/{id}`) was confirmed
separately against a live indexed URL for another tenant
(reddo-it-service.jobs.personio.de/job/1461016).

Caveat: Personio positions its XML schema as fairly stable, but community/
support threads suggest optional fields (e.g. `seniority`, `keywords`) are
sometimes absent depending on tenant configuration and which optional fields a
company has filled in on their end — this adapter only depends on `id`,
`name`, `office`, `department`, `jobDescriptions`, and `createdAt`, all of
which appeared on every position observed live.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from ai_job_hunter.adapters.base import BaseATSAdapter, strip_html
from ai_job_hunter.models import ATSType, JobPosting

if TYPE_CHECKING:
    from ai_job_hunter.registry import CompanyEntry

_REMOTE_RE = re.compile(r"remote", re.IGNORECASE)

# Nested containers whose direct .text is meaningless whitespace between child
# elements; they need bespoke flattening instead of a plain tag->text copy.
_JOB_DESCRIPTIONS_TAG = "jobDescriptions"


def _flatten_job_descriptions(job_descriptions_el: ET.Element) -> str:
    """Join every <jobDescription><name>/<value> pair into one text blob.

    Each block keeps its heading (e.g. "Responsibilities") followed by its
    (still-HTML) value; `parse()` strips HTML from the combined result. This
    is a best-effort flatten, not a faithful re-rendering of the original
    layout.
    """
    parts: list[str] = []
    for block in job_descriptions_el.findall("jobDescription"):
        name_el = block.find("name")
        value_el = block.find("value")
        name = (name_el.text or "").strip() if name_el is not None else ""
        value = (value_el.text or "").strip() if value_el is not None else ""
        if not name and not value:
            continue
        parts.append(f"{name}\n{value}" if name else value)
    return "\n\n".join(parts)


def _positions_from_xml(xml_text: str) -> list[dict]:
    """Parse a Personio `<workzag-jobs>` XML document into plain dicts.

    Only direct children of each `<position>` become dict entries (tag name
    -> stripped text content, "" if the tag has no text), so this naturally
    ignores nested `<office>` entries under `<additionalOffices>` — those
    share a tag name with the primary `<office>` but aren't a direct child of
    `<position>`. The one exception is `jobDescriptions`, whose direct text is
    just inter-element whitespace; it's flattened via
    `_flatten_job_descriptions` instead so `parse()` still gets real content.

    Standalone and reused as-is by tests against the fixture file, so the
    fixture and this function are always exercised through the same path.
    """
    root = ET.fromstring(xml_text)
    positions: list[dict] = []
    for position_el in root.findall("position"):
        record: dict[str, str] = {}
        for child in position_el:
            if child.tag == _JOB_DESCRIPTIONS_TAG:
                record[child.tag] = _flatten_job_descriptions(child)
            else:
                record[child.tag] = (child.text or "").strip()
        positions.append(record)
    return positions


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _is_remote(location_raw: str, title: str) -> bool | None:
    combined = f"{location_raw} {title}"
    return bool(_REMOTE_RE.search(combined))


class PersonioAdapter(BaseATSAdapter):
    """Fetches and normalizes postings from a Personio XML feed."""

    ats_type = ATSType.PERSONIO

    def fetch_raw(self, company: CompanyEntry) -> list[dict]:
        if not company.board_token:
            return []

        url = f"https://{company.board_token}.jobs.personio.de/xml?language=en"
        response = self.session.get(url)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        if not response.content:
            return []

        return _positions_from_xml(response.text)

    def parse(self, raw: dict, company: CompanyEntry) -> JobPosting | None:
        native_id = raw.get("id")
        title = raw.get("name")
        if not native_id or not title:
            return None

        location_raw = raw.get("office") or ""

        return JobPosting(
            company=company.name,
            title=title,
            location_raw=location_raw,
            remote=_is_remote(location_raw, title),
            department=raw.get("department") or None,
            salary_min=None,
            salary_max=None,
            salary_currency=None,
            tech_stack=[],
            url=f"https://{company.board_token}.jobs.personio.de/job/{native_id}",
            posted_date=_parse_date(raw.get("createdAt")),
            deadline=None,
            source_ats=self.ats_type.value,
            raw_native_id=str(native_id),
            description_raw=strip_html(raw.get(_JOB_DESCRIPTIONS_TAG) or ""),
            fetched_at=datetime.now(UTC),
        )

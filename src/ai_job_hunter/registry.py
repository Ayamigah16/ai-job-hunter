"""Loads and validates config/companies.yaml and config/aggregators.yaml.

These files are data, not code — growing the registry never touches src/.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from ai_job_hunter.models import AggregatorType, ATSType, HiresInAfrica, Priority

DEFAULT_COMPANIES_PATH = Path("config/companies.yaml")
DEFAULT_AGGREGATORS_PATH = Path("config/aggregators.yaml")


class RegistryError(Exception):
    """Raised when config/companies.yaml or config/aggregators.yaml fails validation."""


class CompanyEntry(BaseModel):
    name: str
    slug: str
    ats_type: ATSType
    board_token: str | None = None
    industry: str = ""
    hires_in_africa: HiresInAfrica = HiresInAfrica.UNKNOWN
    priority: Priority = Priority.MEDIUM
    notes: str = ""


class AggregatorEntry(BaseModel):
    name: str
    source_type: AggregatorType
    enabled: bool = True
    category: str | None = None
    search_terms: list[str] = []


def _load_yaml_list(path: Path) -> list[dict]:
    if not path.exists():
        raise RegistryError(f"Config file not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        raise RegistryError(f"{path} must contain a YAML list at the top level")
    return data


def load_companies(path: Path = DEFAULT_COMPANIES_PATH) -> list[CompanyEntry]:
    raw_entries = _load_yaml_list(path)
    entries: list[CompanyEntry] = []
    seen_slugs: dict[str, int] = {}

    for index, raw in enumerate(raw_entries):
        try:
            entry = CompanyEntry.model_validate(raw)
        except ValidationError as exc:
            name = _entry_label(raw, index)
            raise RegistryError(f"Invalid company entry '{name}' in {path}: {exc}") from exc

        if entry.slug in seen_slugs:
            first_index = seen_slugs[entry.slug]
            raise RegistryError(
                f"Duplicate slug '{entry.slug}' in {path}: entries #{first_index} and #{index}"
            )
        seen_slugs[entry.slug] = index
        entries.append(entry)

    return entries


def load_aggregators(path: Path = DEFAULT_AGGREGATORS_PATH) -> list[AggregatorEntry]:
    raw_entries = _load_yaml_list(path)
    entries: list[AggregatorEntry] = []

    for index, raw in enumerate(raw_entries):
        try:
            entries.append(AggregatorEntry.model_validate(raw))
        except ValidationError as exc:
            name = _entry_label(raw, index)
            raise RegistryError(f"Invalid aggregator entry '{name}' in {path}: {exc}") from exc

    return entries


def _entry_label(raw: object, index: int) -> str:
    if isinstance(raw, dict) and "name" in raw:
        return str(raw["name"])
    return f"entry #{index}"

from pathlib import Path

import pytest

from ai_job_hunter.models import ATSType
from ai_job_hunter.registry import (
    DEFAULT_AGGREGATORS_PATH,
    DEFAULT_COMPANIES_PATH,
    RegistryError,
    load_aggregators,
    load_companies,
)


def test_load_seed_companies_succeeds():
    companies = load_companies(DEFAULT_COMPANIES_PATH)
    assert len(companies) >= 10
    assert any(c.slug == "gitlab" and c.ats_type == ATSType.GREENHOUSE for c in companies)


def test_load_seed_aggregators_succeeds():
    aggregators = load_aggregators(DEFAULT_AGGREGATORS_PATH)
    assert len(aggregators) == 5


def test_duplicate_slug_raises(tmp_path: Path):
    bad_file = tmp_path / "companies.yaml"
    bad_file.write_text(
        """
- name: Company A
  slug: dupe
  ats_type: greenhouse
  board_token: a
- name: Company B
  slug: dupe
  ats_type: lever
  board_token: b
"""
    )
    with pytest.raises(RegistryError, match="Duplicate slug"):
        load_companies(bad_file)


def test_unknown_ats_type_raises(tmp_path: Path):
    bad_file = tmp_path / "companies.yaml"
    bad_file.write_text(
        """
- name: Company A
  slug: a
  ats_type: not-a-real-ats
"""
    )
    with pytest.raises(RegistryError, match="Invalid company entry"):
        load_companies(bad_file)


def test_missing_file_raises(tmp_path: Path):
    with pytest.raises(RegistryError, match="not found"):
        load_companies(tmp_path / "does-not-exist.yaml")

"""Loads config/skills_profile.yaml — data, not code, tuned without touching src/."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

DEFAULT_SKILLS_PROFILE_PATH = Path("config/skills_profile.yaml")


class ScoringProfile(BaseModel):
    role_title_keywords: list[str] = []
    must_have_skills: list[str] = []
    nice_to_have_skills: list[str] = []
    seniority: str = ""
    sponsorship_keywords: list[str] = []
    remote_positive_keywords: list[str] = []
    africa_friendly_positive_keywords: list[str] = []
    africa_friendly_negative_keywords: list[str] = []
    weights: dict[str, float] = {}


def load_scoring_profile(path: Path = DEFAULT_SKILLS_PROFILE_PATH) -> ScoringProfile:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return ScoringProfile.model_validate(data)

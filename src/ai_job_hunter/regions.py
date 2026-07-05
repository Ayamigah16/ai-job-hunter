"""Country/region lookup for the Open Roles sheet's Country and Region columns.

Best-effort only: location strings are free text from a dozen different
sources, so this is substring matching against config/regions.json, not a
real geocoder.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DEFAULT_REGIONS_PATH = Path("config/regions.json")

_GENERIC_LOCATION_KEYS = {"remote", "worldwide", "global", "anywhere"}


@lru_cache(maxsize=1)
def _regions_map(path_str: str) -> dict[str, str]:
    with Path(path_str).open(encoding="utf-8") as f:
        data = json.load(f)
    return {key: value for key, value in data.items() if not key.startswith("_")}


def lookup_location(location_raw: str, path: Path = DEFAULT_REGIONS_PATH) -> tuple[str, str]:
    """Best-effort (country_label, region) guess from free-text location.

    country_label is "" when the only match is a generic remote-ish keyword
    (e.g. "Remote", "Worldwide") rather than an actual country/region name.
    """
    regions = _regions_map(str(path))
    location_lower = location_raw.lower()
    for key, region in regions.items():
        if key.lower() in location_lower:
            country_label = "" if key.lower() in _GENERIC_LOCATION_KEYS else key
            return country_label, region
    return "", "Unknown"

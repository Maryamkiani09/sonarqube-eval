"""Security hotspots (Person 1, 'basic').

NOTE: SonarQube is phasing hotspots out in 2026 (rules now raise vulnerabilities
instead). On a recent Community Build this list may legitimately be EMPTY - that
is a finding worth documenting, not a bug in this tool.
"""
from __future__ import annotations

from collections import Counter

from .client import SonarClient


def search_hotspots(client: SonarClient, project: str, status: str | None = None) -> list[dict]:
    return list(client.paginate("api/hotspots/search", "hotspots", projectKey=project, status=status))


def review(client: SonarClient, hotspot_key: str, resolution: str = "SAFE") -> None:
    """Mark a hotspot REVIEWED as SAFE | FIXED (| ACKNOWLEDGED on newer versions)."""
    client.post("api/hotspots/change_status", hotspot=hotspot_key, status="REVIEWED", resolution=resolution)


def by_priority(hotspots: list[dict]) -> dict[str, int]:
    return dict(Counter(h.get("vulnerabilityProbability", "?") for h in hotspots))

"""Issues: search, categories, technical debt, workflow (Persons 1 and 4)."""
from __future__ import annotations

import re
from collections import Counter

from .client import SonarClient

# 1 day of effort = 8 hours in SonarQube.
_EFFORT = re.compile(r"(?:(\d+)d)?\s*(?:(\d+)h)?\s*(?:(\d+)min)?")


def parse_effort(effort: str | None) -> int:
    """'1d2h30min' -> minutes (8h days). Missing/blank -> 0."""
    if not effort:
        return 0
    match = _EFFORT.fullmatch(effort.strip())
    if not match:
        return 0
    days, hours, minutes = (int(g) if g else 0 for g in match.groups())
    return days * 8 * 60 + hours * 60 + minutes


def format_minutes(minutes: int) -> str:
    days, rest = divmod(minutes, 8 * 60)
    hours, mins = divmod(rest, 60)
    parts = [f"{days}d" if days else "", f"{hours}h" if hours else "", f"{mins}min" if mins or not minutes else ""]
    return "".join(parts)


def search_issues(client: SonarClient, project: str, **filters) -> list[dict]:
    """All issues of a project; filters: types, severities, statuses, rules, tags..."""
    return list(client.paginate("api/issues/search", "issues", components=project, **filters))


def facet_counts(client: SonarClient, project: str, facet: str, **filters) -> dict[str, int]:
    """Cheap aggregate (one request) e.g. facet='severities' or 'types'."""
    body = client.get("api/issues/search", components=project, facets=facet, ps=1, **filters)
    for item in body.get("facets", []):
        if item.get("property") == facet:
            return {v["val"]: v["count"] for v in item.get("values", [])}
    return {}


def summarize(issues: list[dict]) -> dict:
    """Group issues by type / severity / status / rule and add up technical debt."""
    return {
        "total": len(issues),
        "by_type": dict(Counter(i.get("type", "?") for i in issues)),
        "by_severity": dict(Counter(i.get("severity", "?") for i in issues)),
        "by_status": dict(Counter(i.get("status", "?") for i in issues)),
        "top_rules": Counter(i.get("rule", "?") for i in issues).most_common(5),
        "debt_minutes": sum(parse_effort(i.get("effort")) for i in issues),
    }


def transition(client: SonarClient, issue_key: str, name: str) -> dict:
    """confirm | unconfirm | reopen | resolve | falsepositive | wontfix | accept"""
    return client.post("api/issues/do_transition", issue=issue_key, transition=name)


def assign(client: SonarClient, issue_key: str, assignee: str) -> dict:
    return client.post("api/issues/assign", issue=issue_key, assignee=assignee)


def comment(client: SonarClient, issue_key: str, text: str) -> dict:
    return client.post("api/issues/add_comment", issue=issue_key, text=text)


def set_tags(client: SonarClient, issue_key: str, tags: list[str]) -> dict:
    return client.post("api/issues/set_tags", issue=issue_key, tags=",".join(tags))

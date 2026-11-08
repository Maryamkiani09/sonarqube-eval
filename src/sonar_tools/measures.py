"""Metrics, ratings, history and trends (Persons 1 and 3)."""
from __future__ import annotations

from .client import SonarApiError, SonarClient

DEFAULT_METRICS = [
    "ncloc", "lines", "files", "bugs", "vulnerabilities", "code_smells",
    "coverage", "line_coverage", "branch_coverage",
    "duplicated_lines_density", "duplicated_blocks",
    "complexity", "cognitive_complexity",
    "sqale_index", "sqale_debt_ratio",
    "reliability_rating", "security_rating", "sqale_rating", "alert_status",
]

RATING_LETTERS = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}
RATING_METRICS = {"reliability_rating", "security_rating", "sqale_rating", "security_review_rating"}


def rating_letter(value: float | str) -> str:
    return RATING_LETTERS.get(int(float(value)), "?")


def maintainability_rating(debt_ratio_percent: float) -> str:
    """SonarQube default grid: A<=5%, B<=10%, C<=20%, D<=50%, else E."""
    for limit, letter in ((5, "A"), (10, "B"), (20, "C"), (50, "D")):
        if debt_ratio_percent <= limit:
            return letter
    return "E"


def debt_ratio(debt_minutes: float, ncloc: int, minutes_per_line: int = 30) -> float:
    """Technical-debt ratio (%) = debt / (ncloc * dev cost per line)."""
    if ncloc <= 0:
        return 0.0
    return round(debt_minutes / (ncloc * minutes_per_line) * 100, 2)


def _convert(metric: str, raw: str):
    if metric in RATING_METRICS:
        return rating_letter(raw)
    try:
        return float(raw)
    except ValueError:
        return raw


def get_measures(client: SonarClient, project: str, metrics: list[str] | None = None) -> dict:
    """Current measures. Metrics unknown to this server version are skipped."""
    wanted = list(metrics or DEFAULT_METRICS)
    try:
        body = client.get("api/measures/component", component=project, metricKeys=",".join(wanted))
    except SonarApiError as exc:
        if exc.status not in (400, 404):
            raise
        known = {m["key"] for m in client.paginate("api/metrics/search", "metrics")}
        wanted = [m for m in wanted if m in known]
        body = client.get("api/measures/component", component=project, metricKeys=",".join(wanted))
    out = {}
    for item in body.get("component", {}).get("measures", []):
        raw = item.get("value", item.get("period", {}).get("value"))
        if raw is not None:
            out[item["metric"]] = _convert(item["metric"], raw)
    return out


def history(client: SonarClient, project: str, metrics: list[str], from_date: str | None = None) -> dict[str, list[tuple[str, float]]]:
    """metric -> [(date, value), ...] oldest first."""
    params = {"component": project, "metrics": ",".join(metrics)}
    if from_date:
        params["from"] = from_date
    body = client.get("api/measures/search_history", **params)
    out: dict[str, list[tuple[str, float]]] = {}
    for item in body.get("measures", []):
        points = [(h["date"], float(h["value"])) for h in item.get("history", []) if "value" in h]
        out[item["metric"]] = points
    return out


def trend(points: list[tuple[str, float]]) -> dict:
    """Summarise a time series: first, last, delta, % change, direction."""
    if len(points) < 2:
        return {"first": None, "last": points[-1][1] if points else None, "delta": 0.0, "pct_change": 0.0, "direction": "flat"}
    first, last = points[0][1], points[-1][1]
    delta = round(last - first, 4)
    pct = round(delta / first * 100, 2) if first else 0.0
    direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
    return {"first": first, "last": last, "delta": delta, "pct_change": pct, "direction": direction}

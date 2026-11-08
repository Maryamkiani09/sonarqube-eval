"""Custom reports: CSV, Markdown, HTML, JSON (Persons 3 and 6).

Community Build has no PDF/CSV report button (PDF reports are Enterprise+), so
we build them from the Web API. For a PDF, open the HTML report in a browser
and use "Print -> Save as PDF".
"""
from __future__ import annotations

import csv
import html
import io
import json
from datetime import datetime, timezone
from pathlib import Path

ISSUE_COLUMNS = ["key", "type", "severity", "status", "rule", "component", "line", "message", "effort", "creationDate"]


def build_report(project: str, measures: dict, issue_summary: dict, gate: dict | None = None, now: datetime | None = None) -> dict:
    return {
        "project": project,
        "generated_at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "measures": measures,
        "issues": issue_summary,
        "quality_gate": gate or {},
    }


def issues_to_csv(issues: list[dict]) -> str:
    """Issue-level CSV export (the usual 'export to CSV' people look for)."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=ISSUE_COLUMNS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for issue in issues:
        writer.writerow({c: issue.get(c, "") for c in ISSUE_COLUMNS})
    return buffer.getvalue()


def to_csv(report: dict) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["section", "name", "value"])
    for name, value in report["measures"].items():
        writer.writerow(["measure", name, value])
    for group in ("by_type", "by_severity", "by_status"):
        for name, value in report["issues"].get(group, {}).items():
            writer.writerow([group, name, value])
    writer.writerow(["issues", "debt_minutes", report["issues"].get("debt_minutes", 0)])
    writer.writerow(["quality_gate", "status", report["quality_gate"].get("status", "n/a")])
    return buffer.getvalue()


def to_markdown(report: dict) -> str:
    lines = [f"# SonarQube report - {report['project']}", "", f"Generated: {report['generated_at']}", "",
             f"Quality gate: **{report['quality_gate'].get('status', 'n/a')}**", "", "## Measures", "", "| Metric | Value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in report["measures"].items()]
    lines += ["", "## Issues", "", f"Total: {report['issues'].get('total', 0)}", ""]
    for group in ("by_type", "by_severity"):
        lines.append(f"**{group}**: " + ", ".join(f"{k}={v}" for k, v in report["issues"].get(group, {}).items()))
    return "\n".join(lines) + "\n"


def to_html(report: dict) -> str:
    esc = html.escape
    rows = "".join(f"<tr><td>{esc(str(k))}</td><td>{esc(str(v))}</td></tr>" for k, v in report["measures"].items())
    gate = esc(str(report["quality_gate"].get("status", "n/a")))
    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>SonarQube report - {esc(report['project'])}</title>"
        "<style>body{font-family:sans-serif;margin:2rem}td,th{border:1px solid #ccc;padding:4px 8px}</style></head><body>"
        f"<h1>{esc(report['project'])}</h1><p>Generated {esc(report['generated_at'])} - quality gate <b>{gate}</b></p>"
        f"<table><tr><th>Metric</th><th>Value</th></tr>{rows}</table>"
        f"<p>Issues: {esc(str(report['issues'].get('total', 0)))}</p></body></html>"
    )


def write_report(report: dict, out_dir: str | Path, formats=("csv", "md", "html", "json")) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    renderers = {"csv": to_csv, "md": to_markdown, "html": to_html, "json": lambda r: json.dumps(r, indent=2, default=str)}
    written = []
    for fmt in formats:
        path = out / f"{report['project']}.{fmt}"
        path.write_text(renderers[fmt](report), encoding="utf-8")
        written.append(path)
    return written

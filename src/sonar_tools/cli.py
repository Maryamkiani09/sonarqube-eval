"""Command line front end:  python -m sonar_tools.cli <command> ...

Reads SONAR_URL (default http://localhost:9000) and SONAR_TOKEN from the environment.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import issues as issues_mod
from . import measures as measures_mod
from . import projects as projects_mod
from . import quality_gates, reports, system
from . import hotspots as hotspots_mod
from .client import SonarApiError, SonarClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sonar_tools")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("version", "health", "database", "plugins", "languages", "projects"):
        sub.add_parser(name)
    for name in ("gate-status", "issues-summary", "hotspots"):
        sub.add_parser(name).add_argument("project")
    gate = sub.add_parser("gate-create")
    gate.add_argument("name")
    gate.add_argument("--preset", choices=sorted(quality_gates.PRESETS), default="strict")
    csv_cmd = sub.add_parser("issues-csv")
    csv_cmd.add_argument("project")
    csv_cmd.add_argument("-o", "--output", default="-")
    rep = sub.add_parser("report")
    rep.add_argument("project")
    rep.add_argument("--out", default="reports")
    rep.add_argument("--formats", default="csv,md,html,json")
    tr = sub.add_parser("trend")
    tr.add_argument("project")
    tr.add_argument("--metric", default="coverage")
    return parser


def run(args, client: SonarClient) -> int:
    cmd = args.command
    if cmd == "version":
        print(system.server_version(client))
    elif cmd == "health":
        print(system.health(client))
    elif cmd == "database":
        print(json.dumps(system.database_info(client)))
    elif cmd == "plugins":
        for plugin in system.installed_plugins(client):
            print(f"{plugin['key']}\t{plugin.get('version', '')}\t{plugin.get('name', '')}")
    elif cmd == "languages":
        print(", ".join(lang["key"] for lang in system.supported_languages(client)))
    elif cmd == "projects":
        for project in projects_mod.list_projects(client):
            print(f"{project['key']}\t{project.get('name', '')}")
    elif cmd == "gate-status":
        status = quality_gates.project_status(client, args.project)
        print(status["status"])
        for cond in quality_gates.failed_conditions(status):
            print(f"  {cond['metricKey']} actual={cond.get('actualValue')} threshold={cond.get('errorThreshold')}")
        return 0 if status["status"] in ("OK", "WARN") else 1
    elif cmd == "gate-create":
        quality_gates.create_gate(client, args.name, quality_gates.PRESETS[args.preset])
        print(f"created quality gate {args.name} ({args.preset})")
    elif cmd == "issues-summary":
        print(json.dumps(issues_mod.summarize(issues_mod.search_issues(client, args.project)), indent=2))
    elif cmd == "issues-csv":
        text = reports.issues_to_csv(issues_mod.search_issues(client, args.project))
        if args.output == "-":
            sys.stdout.write(text)
        else:
            Path(args.output).write_text(text, encoding="utf-8")
    elif cmd == "hotspots":
        found = hotspots_mod.search_hotspots(client, args.project)
        print(f"{len(found)} hotspots {hotspots_mod.by_priority(found)}")
    elif cmd == "report":
        summary = issues_mod.summarize(issues_mod.search_issues(client, args.project))
        gate = quality_gates.project_status(client, args.project)
        report = reports.build_report(args.project, measures_mod.get_measures(client, args.project), summary, gate)
        for path in reports.write_report(report, args.out, args.formats.split(",")):
            print(path)
    elif cmd == "trend":
        data = measures_mod.history(client, args.project, [args.metric])
        print(json.dumps(measures_mod.trend(data.get(args.metric, []))))
    return 0


def main(argv=None, client: SonarClient | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args, client or SonarClient.from_env())
    except SonarApiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

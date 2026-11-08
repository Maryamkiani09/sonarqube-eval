"""CI/CD helper: wait for the analysis, check the quality gate, fail the build (Person 5).

Usage in any pipeline, after ``sonar-scanner`` has run:

    python -m sonar_tools.ci --report-task .scannerwork/report-task.txt

Exit codes: 0 = gate passed, 1 = gate failed, 2 = could not determine / error.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Callable

from . import quality_gates
from .client import SonarApiError, SonarClient

EXIT_OK, EXIT_GATE_FAILED, EXIT_ERROR = 0, 1, 2


class CeTaskFailed(Exception):
    """The background (Compute Engine) task ended FAILED or CANCELED."""


def read_report_task(path: str | Path) -> dict[str, str]:
    """Parse the key=value file written by the scanner."""
    data = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            data[key.strip()] = value.strip()
    return data


def wait_for_ce_task(
    client: SonarClient,
    task_id: str,
    timeout: float = 300,
    interval: float = 3,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> dict:
    deadline = now() + timeout
    while now() < deadline:
        task = client.get("api/ce/task", id=task_id)["task"]
        if task["status"] == "SUCCESS":
            return task
        if task["status"] in ("FAILED", "CANCELED"):
            raise CeTaskFailed(f"task {task_id} {task['status']}: {task.get('errorMessage', '')}")
        sleep(interval)
    raise TimeoutError(f"task {task_id} still not finished after {timeout}s")


def exit_code_for(gate_status: str) -> int:
    if gate_status in ("OK", "WARN"):
        return EXIT_OK
    if gate_status == "ERROR":
        return EXIT_GATE_FAILED
    return EXIT_ERROR


def check(client: SonarClient, report_task: str | None, project: str | None, timeout: float, out=print) -> int:
    try:
        if report_task:
            info = read_report_task(report_task)
            task = wait_for_ce_task(client, info["ceTaskId"], timeout=timeout)
            status = quality_gates.project_status(client, analysis_id=task.get("analysisId"))
        else:
            status = quality_gates.project_status(client, project=project)
    except (CeTaskFailed, TimeoutError, SonarApiError, KeyError, OSError) as exc:
        out(f"ERROR: {exc}")
        return EXIT_ERROR
    out(f"Quality gate: {status['status']}")
    for cond in quality_gates.failed_conditions(status):
        out(f"  FAILED {cond['metricKey']}: actual={cond.get('actualValue')} threshold={cond.get('errorThreshold')} ({cond['comparator']})")
    return exit_code_for(status["status"])


def main(argv=None, client: SonarClient | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail the build when the SonarQube quality gate fails")
    parser.add_argument("--report-task", help="path to .scannerwork/report-task.txt")
    parser.add_argument("--project", help="project key (when no report-task file is available)")
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args(argv)
    if not (args.report_task or args.project):
        parser.error("give --report-task or --project")
    return check(client or SonarClient.from_env(), args.report_task, args.project, args.timeout)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

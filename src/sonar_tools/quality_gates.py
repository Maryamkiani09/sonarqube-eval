"""Quality gates: create, enforce, evaluate thresholds (Person 2)."""
from __future__ import annotations

from dataclasses import dataclass

from .client import SonarClient


@dataclass(frozen=True)
class Condition:
    """Gate condition: the gate FAILS when the metric is GT / LT ``error``."""

    metric: str
    op: str  # "GT" or "LT"
    error: float

    def violated(self, value: float) -> bool:
        if self.op == "GT":
            return value > self.error
        if self.op == "LT":
            return value < self.error
        raise ValueError(f"unsupported operator {self.op!r}")


# Rating conditions use 1=A .. 5=E, so "GT 1" means "worse than A".
SONAR_WAY_LIKE = (
    Condition("new_security_rating", "GT", 1),
    Condition("new_reliability_rating", "GT", 1),
    Condition("new_maintainability_rating", "GT", 1),
    Condition("new_coverage", "LT", 80),
    Condition("new_duplicated_lines_density", "GT", 3),
)

# Conditions on OVERALL code: deterministic for a first analysis of this project.
STRICT_OVERALL = (
    Condition("coverage", "LT", 80),
    Condition("duplicated_lines_density", "GT", 3),
    Condition("bugs", "GT", 0),
    Condition("vulnerabilities", "GT", 0),
    Condition("code_smells", "GT", 20),
    Condition("reliability_rating", "GT", 1),
)

PRESETS = {"sonar-way": SONAR_WAY_LIKE, "strict": STRICT_OVERALL}


def evaluate(measures: dict[str, float], conditions) -> list[Condition]:
    """Pure-Python gate evaluation: return the conditions that are violated."""
    return [c for c in conditions if c.metric in measures and c.violated(float(measures[c.metric]))]


def create_gate(client: SonarClient, name: str, conditions=STRICT_OVERALL) -> str:
    client.post("api/qualitygates/create", name=name)
    for cond in conditions:
        client.post("api/qualitygates/create_condition", gateName=name, metric=cond.metric, op=cond.op, error=cond.error)
    return name


def copy_gate(client: SonarClient, source: str, name: str) -> None:
    client.post("api/qualitygates/copy", sourceName=source, name=name)


def list_gates(client: SonarClient) -> list[dict]:
    return client.get("api/qualitygates/list").get("qualitygates", [])


def show_gate(client: SonarClient, name: str) -> dict:
    return client.get("api/qualitygates/show", name=name)


def set_default(client: SonarClient, name: str) -> None:
    client.post("api/qualitygates/set_as_default", name=name)


def associate(client: SonarClient, gate: str, project: str) -> None:
    client.post("api/qualitygates/select", gateName=gate, projectKey=project)


def deselect(client: SonarClient, project: str) -> None:
    """Put the project back on the default quality gate."""
    client.post("api/qualitygates/deselect", projectKey=project)


def delete_gate(client: SonarClient, name: str) -> None:
    client.post("api/qualitygates/destroy", name=name)


def project_status(client: SonarClient, project: str | None = None, analysis_id: str | None = None) -> dict:
    params = {"projectKey": project, "analysisId": analysis_id}
    return client.get("api/qualitygates/project_status", **params)["projectStatus"]


def failed_conditions(status: dict) -> list[dict]:
    return [c for c in status.get("conditions", []) if c.get("status") == "ERROR"]

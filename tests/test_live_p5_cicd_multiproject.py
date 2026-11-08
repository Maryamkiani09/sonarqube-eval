"""LIVE tests - Person 5: CI/CD gate enforcement, multi-project, branches, webhooks."""
import os
import uuid

import pytest

from sonar_tools import ci, projects, quality_gates, webhooks
from sonar_tools.client import SonarApiError

pytestmark = pytest.mark.integration


def test_p5_01_many_projects_in_one_instance(live):
    suffix = uuid.uuid4().hex[:5]
    keys = [(f"eval-svc-{suffix}-{n}", f"Service {n}") for n in "abc"]
    try:
        assert len(projects.create_many(live, keys)) == 3
        listed = {p["key"] for p in projects.list_projects(live, f"eval-svc-{suffix}")}
        assert listed == {k for k, _ in keys}
    finally:
        for key, _ in keys:
            projects.delete_project(live, key)


def test_p5_02_ci_exit_code_matches_gate(live, project_key):
    status = quality_gates.project_status(live, project_key)["status"]
    assert ci.main(["--project", project_key], client=live) == ci.exit_code_for(status)


def test_p5_03_build_breaks_with_strict_gate(live, project_key):
    name = f"eval-ci-{uuid.uuid4().hex[:6]}"
    quality_gates.create_gate(live, name, quality_gates.STRICT_OVERALL)
    quality_gates.associate(live, name, project_key)
    try:
        assert ci.main(["--project", project_key], client=live) == ci.EXIT_GATE_FAILED
    finally:
        quality_gates.deselect(live, project_key)
        quality_gates.delete_gate(live, name)


def test_p5_04_only_main_branch_in_community_build(live, project_key):
    branches = projects.list_branches(live, project_key)
    assert len(branches) == 1 and branches[0]["isMain"]


def test_p5_05_pull_requests_unsupported_or_empty(live, project_key):
    try:
        pulls = live.get("api/project_pull_requests/list", project=project_key).get("pullRequests", [])
    except SonarApiError:
        return  # endpoint refused: pull request analysis is not available
    assert pulls == []


def test_p5_06_webhook_registration(live, project_key):
    host = os.environ.get("SONAR_WEBHOOK_HOST", "host.docker.internal")
    hook = webhooks.create(live, "eval-hook", f"http://{host}:8081/", secret="s3cret", project=project_key)
    try:
        assert hook["name"] == "eval-hook"
        assert any(h["key"] == hook["key"] for h in webhooks.list_webhooks(live, project_key))
    finally:
        webhooks.delete(live, hook["key"])

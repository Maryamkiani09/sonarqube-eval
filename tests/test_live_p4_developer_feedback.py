"""LIVE tests - Person 4: what SonarQube for IDE (SonarLint) relies on.

The IDE itself cannot be automated from Python; see TEST_CASES.md (TC-P4-*) for
the manual connected-mode steps. These tests check the SERVER side of that link.
"""
import uuid

import pytest

from sonar_tools import admin, issues, quality_profiles

pytestmark = pytest.mark.integration


def test_p4_01_user_token_can_be_created_and_revoked(live):
    name = f"ide-{uuid.uuid4().hex[:6]}"
    token = admin.generate_token(live, name, token_type="USER_TOKEN")
    try:
        assert token and token != name
    finally:
        admin.revoke_token(live, name)


def test_p4_02_project_exposes_a_quality_profile_for_ide_sync(live, project_key):
    body = live.get("api/qualityprofiles/search", project=project_key)
    assert any(p["language"] == "py" for p in body["profiles"])
    py = next(p for p in body["profiles"] if p["language"] == "py")
    assert quality_profiles.active_rule_count(live, py["key"]) > 50


def test_p4_03_issue_has_ide_visible_fields(live, project_key):
    first = issues.search_issues(live, project_key, ps=1)[0]
    for field in ("key", "rule", "severity", "type", "status", "component", "message"):
        assert field in first


def test_p4_04_status_change_is_visible_on_server(live, project_key):
    """SonarLint mirrors server-side statuses: confirm an issue, then undo it."""
    target = next(i for i in issues.search_issues(live, project_key, statuses="OPEN"))
    issues.transition(live, target["key"], "confirm")
    try:
        refreshed = next(i for i in issues.search_issues(live, project_key, statuses="CONFIRMED") if i["key"] == target["key"])
        assert refreshed["status"] == "CONFIRMED"
    finally:
        issues.transition(live, target["key"], "unconfirm")

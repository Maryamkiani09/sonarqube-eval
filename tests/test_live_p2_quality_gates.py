"""LIVE tests - Person 2: quality gates, profiles, rules, thresholds."""
import uuid

import pytest

from sonar_tools import quality_gates, quality_profiles
from sonar_tools.quality_gates import Condition

pytestmark = pytest.mark.integration


@pytest.fixture
def temp_gate(live, project_key):
    name = f"eval-gate-{uuid.uuid4().hex[:6]}"
    yield name
    quality_gates.deselect(live, project_key)
    try:
        quality_gates.delete_gate(live, name)
    except Exception:
        pass


def test_p2_01_builtin_gate_exists(live):
    gates = quality_gates.list_gates(live)
    assert any(g.get("isBuiltIn") for g in gates)
    assert sum(1 for g in gates if g.get("isDefault")) == 1


def test_p2_02_strict_gate_fails_flawed_project(live, project_key, temp_gate):
    quality_gates.create_gate(live, temp_gate, quality_gates.STRICT_OVERALL)
    quality_gates.associate(live, temp_gate, project_key)
    status = quality_gates.project_status(live, project_key)
    assert status["status"] == "ERROR"
    failed = {c["metricKey"] for c in quality_gates.failed_conditions(status)}
    assert "bugs" in failed and "coverage" in failed


def test_p2_03_lenient_gate_passes(live, project_key, temp_gate):
    quality_gates.create_gate(live, temp_gate, [Condition("ncloc", "LT", 1)])
    quality_gates.associate(live, temp_gate, project_key)
    assert quality_gates.project_status(live, project_key)["status"] == "OK"


def test_p2_04_local_evaluation_matches_server(live, project_key, temp_gate):
    from sonar_tools import measures
    quality_gates.create_gate(live, temp_gate, quality_gates.STRICT_OVERALL)
    quality_gates.associate(live, temp_gate, project_key)
    server_failed = {c["metricKey"] for c in quality_gates.failed_conditions(quality_gates.project_status(live, project_key))}
    values = measures.get_measures(live, project_key)
    numeric = {k: v for k, v in values.items() if isinstance(v, float)}
    numeric["reliability_rating"] = "ABCDE".index(values["reliability_rating"]) + 1
    assert {c.metric for c in quality_gates.evaluate(numeric, quality_gates.STRICT_OVERALL)} == server_failed


def test_p2_05_custom_profile_activate_deactivate(live, project_key):
    base = quality_profiles.list_profiles(live, "py", defaults=True)[0]
    name = f"eval-profile-{uuid.uuid4().hex[:6]}"
    custom = quality_profiles.copy_profile(live, base["key"], name)
    try:
        before = quality_profiles.active_rule_count(live, custom["key"])
        quality_profiles.deactivate_rule(live, custom["key"], "python:S1481")
        assert quality_profiles.active_rule_count(live, custom["key"]) == before - 1
        quality_profiles.activate_rule(live, custom["key"], "python:S1481", severity="BLOCKER")
        assert quality_profiles.active_rule_count(live, custom["key"]) == before
        quality_profiles.associate_project(live, "py", name, project_key)
        assert "<name>" in quality_profiles.backup(live, "py", name)
    finally:
        quality_profiles.set_default(live, "py", base["name"])
        quality_profiles.associate_project(live, "py", base["name"], project_key)
        quality_profiles.delete_profile(live, "py", name)


def test_p2_06_rule_search_by_severity(live):
    assert quality_profiles.search_rules(live, "py", severities="BLOCKER", ps=5)

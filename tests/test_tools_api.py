"""sonar_tools against the in-memory FakeSonar HTTP server."""
import json

import pytest
import requests

from fake_sonar import FakeSonar
from sonar_tools import admin, ci, cli, hotspots, issues, measures, projects, quality_gates, quality_profiles, system, webhooks
from sonar_tools.client import SonarApiError, SonarClient


# ----------------------------------------------------------------- client
def test_token_is_sent_as_basic_auth_user():
    server = FakeSonar(token="sqa_good").start()
    try:
        assert SonarClient(server.url, "sqa_good").get("api/system/status")["status"] == "UP"
        with pytest.raises(SonarApiError) as err:
            SonarClient(server.url, "wrong").get("api/system/status")
        assert err.value.status == 401 and "Insufficient privileges" in err.value.message
    finally:
        server.stop()


def test_unknown_endpoint_raises_api_error(client):
    with pytest.raises(SonarApiError) as err:
        client.get("api/does/not/exist")
    assert err.value.status == 404


def test_none_params_are_dropped_and_bools_lowercased(client, fake):
    client.get("api/qualityprofiles/search", language=None, defaults=True)
    params = fake.calls[-1][2]
    assert "language" not in params and params["defaults"] == "true"


def test_from_env(monkeypatch):
    monkeypatch.setenv("SONAR_URL", "http://example:9000/")
    monkeypatch.setenv("SONAR_TOKEN", "tok")
    c = SonarClient.from_env()
    assert c.base_url == "http://example:9000" and c.session.auth == ("tok", "")


def test_paginate_walks_all_pages(client, fake):
    for i in range(7):
        fake.projects[f"pg{i}"] = f"P{i}"
    keys = [p["key"] for p in client.paginate("api/projects/search", "components", page_size=3, q="pg")]
    assert len(keys) == 7
    assert sum(1 for c in fake.calls if c[1] == "api/projects/search") == 3


def test_paginate_respects_max_items(client, fake):
    for i in range(10):
        fake.projects[f"q{i}"] = "Q"
    assert len(list(client.paginate("api/projects/search", "components", max_items=4, q="q"))) == 4


# ----------------------------------------------------------------- system
def test_system_info(client):
    assert system.server_version(client).startswith("26.")
    assert system.status(client)["status"] == "UP"
    assert system.health(client) == "GREEN"
    assert system.database_info(client) == {"vendor": "PostgreSQL", "version": "17.2"}
    assert system.installed_plugins(client)[0]["key"] == "python"
    assert system.available_plugins(client) == []
    assert {"py", "java"} <= {lang["key"] for lang in system.supported_languages(client)}


def test_wait_until_up_retries_then_succeeds(client):
    calls = {"n": 0}

    class Flaky:
        def get(self, path, **params):
            calls["n"] += 1
            return {"status": "STARTING"} if calls["n"] < 3 else {"status": "UP"}

    assert system.wait_until_up(Flaky(), timeout=100, interval=1, sleep=lambda s: None)["status"] == "UP"
    assert calls["n"] == 3


def test_wait_until_up_times_out():
    clock = iter(range(0, 1000, 10))
    with pytest.raises(TimeoutError):
        system.wait_until_up(SonarClient("http://127.0.0.1:1"), timeout=25, interval=1, sleep=lambda s: None, now=lambda: next(clock))


# --------------------------------------------------------------- projects
def test_create_many_projects_and_idempotency(client, fake):
    new = projects.create_many(client, [("svc-a", "A"), ("svc-b", "B"), ("svc-a", "A")])
    assert new == ["svc-a", "svc-b"]
    assert {"svc-a", "svc-b"} <= {p["key"] for p in projects.list_projects(client)}
    projects.delete_project(client, "svc-a")
    assert not projects.project_exists(client, "svc-a")


def test_duplicate_project_key_is_an_api_error(client):
    with pytest.raises(SonarApiError):
        projects.create_project(client, "shopflow")


def test_main_branch_only(client):
    branches = projects.list_branches(client, "shopflow")
    assert len(branches) == 1 and branches[0]["isMain"]
    assert projects.analyses(client, "shopflow")[0]["key"] == "A1"


# ----------------------------------------------------------- quality gates
def test_default_gate_fails_on_low_coverage(client):
    status = quality_gates.project_status(client, "shopflow")
    assert status["status"] == "ERROR"
    assert quality_gates.failed_conditions(status)[0]["metricKey"] == "coverage"


def test_custom_gate_create_associate_and_enforce(client, fake):
    quality_gates.create_gate(client, "Strict", quality_gates.STRICT_OVERALL)
    assert len(quality_gates.show_gate(client, "Strict")["conditions"]) == len(quality_gates.STRICT_OVERALL)
    quality_gates.associate(client, "Strict", "shopflow")
    failed = {c["metricKey"] for c in quality_gates.failed_conditions(quality_gates.project_status(client, "shopflow"))}
    assert {"coverage", "bugs", "vulnerabilities", "duplicated_lines_density", "code_smells", "reliability_rating"} == failed


def test_lenient_gate_passes(client):
    quality_gates.create_gate(client, "Lenient", [quality_gates.Condition("coverage", "LT", 10)])
    quality_gates.associate(client, "Lenient", "shopflow")
    assert quality_gates.project_status(client, "shopflow")["status"] == "OK"


def test_gate_default_copy_delete(client, fake):
    quality_gates.copy_gate(client, "Sonar way", "Copy")
    quality_gates.set_default(client, "Copy")
    assert [g["name"] for g in quality_gates.list_gates(client) if g["isDefault"]] == ["Copy"]
    quality_gates.delete_gate(client, "Copy")
    assert "Copy" not in fake.gates


def test_deselect_returns_project_to_default_gate(client, fake):
    quality_gates.create_gate(client, "Temp", [quality_gates.Condition("coverage", "LT", 10)])
    quality_gates.associate(client, "Temp", "shopflow")
    assert quality_gates.project_status(client, "shopflow")["status"] == "OK"
    quality_gates.deselect(client, "shopflow")
    assert quality_gates.project_status(client, "shopflow")["status"] == "ERROR"


def test_duplicate_gate_name_rejected(client):
    with pytest.raises(SonarApiError):
        quality_gates.create_gate(client, "Sonar way")


# ---------------------------------------------------------------- profiles
def test_profile_copy_activate_deactivate(client, fake):
    base = quality_profiles.find_profile(client, "py", "Sonar way")
    assert base["isBuiltIn"]
    custom = quality_profiles.copy_profile(client, base["key"], "ShopFlow way")
    before = quality_profiles.active_rule_count(client, custom["key"])
    quality_profiles.activate_rule(client, custom["key"], "python:S1763", severity="BLOCKER")
    assert quality_profiles.active_rule_count(client, custom["key"]) == before + 1
    quality_profiles.deactivate_rule(client, custom["key"], "python:S125")
    assert quality_profiles.active_rule_count(client, custom["key"]) == before
    quality_profiles.associate_project(client, "py", "ShopFlow way", "shopflow")
    assert fake.profile_projects[("py", "shopflow")] == "ShopFlow way"
    assert "<name>ShopFlow way</name>" in quality_profiles.backup(client, "py", "ShopFlow way")


def test_list_profiles_filters_language(client):
    assert quality_profiles.list_profiles(client, "java") == []
    assert quality_profiles.create_profile(client, "py", "X")["name"] == "X"
    quality_profiles.delete_profile(client, "py", "X")
    assert quality_profiles.find_profile(client, "py", "X") is None


# ------------------------------------------------------------------ issues
def test_issue_search_filters_and_facets(client):
    assert len(issues.search_issues(client, "shopflow")) == 3
    assert [i["key"] for i in issues.search_issues(client, "shopflow", types="BUG")] == ["I1"]
    assert issues.facet_counts(client, "shopflow", "severities") == {"MAJOR": 1, "MINOR": 1, "CRITICAL": 1}
    assert issues.facet_counts(client, "shopflow", "types") == {"BUG": 1, "CODE_SMELL": 1, "VULNERABILITY": 1}


def test_issue_summary_from_server(client):
    summary = issues.summarize(issues.search_issues(client, "shopflow"))
    assert summary["debt_minutes"] == 5 + 60 + 30


def test_issue_workflow(client, fake):
    assert issues.transition(client, "I1", "confirm")["issue"]["status"] == "CONFIRMED"
    assert issues.transition(client, "I1", "falsepositive")["issue"]["status"] == "RESOLVED"
    issues.assign(client, "I2", "ali")
    issues.comment(client, "I2", "will fix")
    issues.set_tags(client, "I2", ["tech-debt", "sprint-5"])
    stored = next(i for i in fake.issues if i["key"] == "I2")
    assert stored["assignee"] == "ali" and stored["comments"] == ["will fix"] and stored["tags"] == ["tech-debt", "sprint-5"]


def test_transition_on_missing_issue(client):
    with pytest.raises(SonarApiError):
        issues.transition(client, "NOPE", "confirm")


# ---------------------------------------------------------------- measures
def test_get_measures_converts_ratings_and_numbers(client):
    result = measures.get_measures(client, "shopflow")
    assert result["coverage"] == 41.2 and result["reliability_rating"] == "C" and result["security_rating"] == "E"
    assert result["alert_status"] == "ERROR"


def test_get_measures_skips_metrics_unknown_to_server(client):
    result = measures.get_measures(client, "shopflow", ["coverage", "not_a_metric"])
    assert result == {"coverage": 41.2}


def test_unknown_project_measures(client):
    with pytest.raises(SonarApiError):
        measures.get_measures(client, "ghost")


def test_history_and_trend(client, fake):
    fake.history["shopflow"] = {"coverage": [{"date": "2026-10-01", "value": "30"}, {"date": "2026-11-01", "value": "45"}]}
    series = measures.history(client, "shopflow", ["coverage"])
    assert series["coverage"] == [("2026-10-01", 30.0), ("2026-11-01", 45.0)]
    assert measures.trend(series["coverage"]) == {"first": 30.0, "last": 45.0, "delta": 15.0, "pct_change": 50.0, "direction": "up"}


# ---------------------------------------------------------------- hotspots
def test_hotspot_search_and_review(client, fake):
    fake.hotspots = [{"key": "H1", "vulnerabilityProbability": "HIGH", "status": "TO_REVIEW"}]
    found = hotspots.search_hotspots(client, "shopflow")
    assert hotspots.by_priority(found) == {"HIGH": 1}
    hotspots.review(client, "H1", "SAFE")
    assert fake.hotspots[0]["status"] == "REVIEWED" and fake.hotspots[0]["resolution"] == "SAFE"


# ---------------------------------------------------------------- webhooks
def test_webhook_registration_api(client, fake):
    hook = webhooks.create(client, "ci", "http://ci.local/hook", secret="s", project="shopflow")
    assert hook["hasSecret"] and webhooks.list_webhooks(client)[0]["name"] == "ci"
    assert webhooks.deliveries(client, hook["key"])[0]["success"]
    webhooks.delete(client, hook["key"])
    assert webhooks.list_webhooks(client) == []


def _post(url, payload, secret=None):
    body = json.dumps(payload).encode()
    headers = {webhooks.SIGNATURE_HEADER: webhooks.sign(body, secret)} if secret else {}
    return requests.post(url, data=body, headers=headers, timeout=5)


def test_receiver_accepts_valid_and_rejects_bad_signature():
    receiver = webhooks.WebhookReceiver(secret="topsecret").start()
    try:
        payload = {"status": "SUCCESS", "project": {"key": "shopflow"}, "qualityGate": {"name": "G", "status": "ERROR", "conditions": [{"metric": "bugs", "status": "ERROR"}]}}
        assert _post(receiver.url, payload, "topsecret").status_code == 200
        assert _post(receiver.url, payload, "wrong").status_code == 401
        assert _post(receiver.url, payload).status_code == 401
        assert len(receiver.events) == 1 and receiver.rejected == 2
        assert receiver.events[0].failed_conditions[0]["metric"] == "bugs"
    finally:
        receiver.stop()


def test_receiver_without_secret_accepts_everything():
    receiver = webhooks.WebhookReceiver().start()
    try:
        assert _post(receiver.url, {"project": {"key": "p"}}).status_code == 200
        assert receiver.events[0].project_key == "p"
    finally:
        receiver.stop()


# ---------------------------------------------------------------------- ci
def test_wait_for_ce_task_polls_until_success(client, fake):
    fake.ce_tasks["T1"] = ["PENDING", "IN_PROGRESS", "SUCCESS"]
    naps = []
    task = ci.wait_for_ce_task(client, "T1", sleep=naps.append)
    assert task["status"] == "SUCCESS" and len(naps) == 2


def test_wait_for_ce_task_failure(client, fake):
    fake.ce_tasks["T2"] = ["FAILED"]
    with pytest.raises(ci.CeTaskFailed, match="boom"):
        ci.wait_for_ce_task(client, "T2", sleep=lambda s: None)


def test_wait_for_ce_task_timeout(client, fake):
    fake.ce_tasks["T3"] = ["IN_PROGRESS"]
    clock = iter(range(0, 100, 5))
    with pytest.raises(TimeoutError):
        ci.wait_for_ce_task(client, "T3", timeout=12, sleep=lambda s: None, now=lambda: next(clock))


def _report_task(tmp_path, task_id="T9"):
    path = tmp_path / "report-task.txt"
    path.write_text(f"projectKey=shopflow\nceTaskId={task_id}\n")
    return str(path)


def test_ci_build_fails_when_gate_fails(client, fake, tmp_path, capsys):
    fake.ce_tasks["T9"] = ["PENDING", "SUCCESS"]
    fake.analysis_project["AN-T9"] = "shopflow"
    assert ci.main(["--report-task", _report_task(tmp_path)], client=client) == 1
    out = capsys.readouterr().out
    assert "Quality gate: ERROR" in out and "FAILED coverage" in out


def test_ci_build_passes_when_gate_passes(client, fake, tmp_path):
    fake.measures["shopflow"]["coverage"] = "95"
    fake.ce_tasks["T9"] = ["SUCCESS"]
    fake.analysis_project["AN-T9"] = "shopflow"
    assert ci.main(["--report-task", _report_task(tmp_path)], client=client) == 0


def test_ci_returns_2_on_broken_task(client, fake, tmp_path, capsys):
    fake.ce_tasks["T9"] = ["FAILED"]
    assert ci.main(["--report-task", _report_task(tmp_path)], client=client) == 2
    assert "ERROR" in capsys.readouterr().out


def test_ci_returns_2_when_report_file_missing(client, tmp_path):
    assert ci.main(["--report-task", str(tmp_path / "nope.txt")], client=client) == 2


def test_ci_by_project_key(client):
    assert ci.main(["--project", "shopflow"], client=client) == 1


def test_ci_requires_an_argument(client):
    with pytest.raises(SystemExit):
        ci.main([], client=client)


# ------------------------------------------------------------------- admin
def test_users_groups_permissions_tokens(client, fake):
    admin.create_user(client, "sara", "Sara", "pw-123456", "sara@example.com")
    admin.create_group(client, "reviewers")
    admin.add_user_to_group(client, "reviewers", "sara")
    admin.grant_permission(client, "codeviewer", project="shopflow", group="reviewers")
    admin.grant_permission(client, "scan", project="shopflow", login="sara")
    assert fake.groups["reviewers"]["members"] == ["sara"]
    assert ("group", "reviewers", "codeviewer", "shopflow") in fake.permissions
    assert ("user", "sara", "scan", "shopflow") in fake.permissions
    assert admin.generate_token(client, "ci-token", project="shopflow") == "sqp_ci-token"
    admin.revoke_token(client, "ci-token")
    assert "ci-token" not in fake.tokens
    admin.deactivate_user(client, "sara")
    assert "sara" not in fake.users


def test_grant_permission_needs_exactly_one_target(client):
    with pytest.raises(ValueError):
        admin.grant_permission(client, "scan", project="shopflow")
    with pytest.raises(ValueError):
        admin.grant_permission(client, "scan", project="shopflow", login="a", group="b")


def test_settings_exclusions_and_new_code(client, fake):
    admin.set_exclusions(client, "shopflow", ["**/generated/**", "**/migrations/**"])
    setting = admin.get_setting(client, "sonar.exclusions", "shopflow")
    assert setting["values"] == ["**/generated/**", "**/migrations/**"]
    admin.set_setting(client, "sonar.core.serverBaseURL", "http://sonar.local")
    assert admin.get_setting(client, "sonar.core.serverBaseURL")["value"] == "http://sonar.local"
    admin.reset_setting(client, "sonar.exclusions", "shopflow")
    assert admin.get_setting(client, "sonar.exclusions", "shopflow") is None
    admin.set_new_code_period(client, "shopflow", "NUMBER_OF_DAYS", "30")
    assert fake.new_code["shopflow"] == ("NUMBER_OF_DAYS", "30")


# --------------------------------------------------------------------- cli
def run_cli(client, *argv):
    return cli.main(list(argv), client=client)


def test_cli_info_commands(client, capsys):
    for command in ("version", "health", "database", "plugins", "languages", "projects"):
        assert run_cli(client, command) == 0
    out = capsys.readouterr().out
    assert "26.10" in out and "GREEN" in out and "PostgreSQL" in out and "python" in out and "shopflow" in out


def test_cli_gate_status_exit_code(client, capsys):
    assert run_cli(client, "gate-status", "shopflow") == 1
    assert "coverage" in capsys.readouterr().out


def test_cli_gate_create_and_issue_exports(client, fake, capsys, tmp_path):
    assert run_cli(client, "gate-create", "Team gate", "--preset", "sonar-way") == 0
    assert len(fake.gates["Team gate"]) == len(quality_gates.SONAR_WAY_LIKE)
    target = tmp_path / "issues.csv"
    run_cli(client, "issues-csv", "shopflow", "-o", str(target))
    assert target.read_text().count("\n") == 4
    run_cli(client, "issues-csv", "shopflow")
    assert "python:S1763" in capsys.readouterr().out
    run_cli(client, "issues-summary", "shopflow")
    assert '"total": 3' in capsys.readouterr().out


def test_cli_report_hotspots_trend(client, fake, tmp_path, capsys):
    fake.history["shopflow"] = {"coverage": [{"date": "d1", "value": "10"}, {"date": "d2", "value": "20"}]}
    assert run_cli(client, "report", "shopflow", "--out", str(tmp_path), "--formats", "csv,html") == 0
    assert (tmp_path / "shopflow.csv").exists() and (tmp_path / "shopflow.html").exists()
    run_cli(client, "hotspots", "shopflow")
    run_cli(client, "trend", "shopflow", "--metric", "coverage")
    out = capsys.readouterr().out
    assert "0 hotspots" in out and '"direction": "up"' in out


def test_cli_reports_api_errors_with_exit_code_2(client, capsys):
    assert run_cli(client, "gate-status", "ghost") == 2
    assert "error:" in capsys.readouterr().err

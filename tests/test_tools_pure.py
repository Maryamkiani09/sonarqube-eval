"""Unit tests for pure logic in sonar_tools (no server needed)."""
import json
from datetime import datetime, timezone

import pytest

from sonar_tools import ci, hotspots, issues, measures, quality_gates, quality_profiles, reports, webhooks
from sonar_tools.quality_gates import Condition


# ---------------------------------------------------------- quality gates
def test_condition_gt_and_lt():
    assert Condition("bugs", "GT", 0).violated(1)
    assert not Condition("bugs", "GT", 0).violated(0)
    assert Condition("coverage", "LT", 80).violated(79.9)
    assert not Condition("coverage", "LT", 80).violated(80)


def test_condition_rejects_unknown_operator():
    with pytest.raises(ValueError):
        Condition("x", "EQ", 1).violated(1)


def test_evaluate_returns_only_violations():
    values = {"coverage": 41.2, "bugs": 0, "duplicated_lines_density": 11.3}
    bad = quality_gates.evaluate(values, quality_gates.STRICT_OVERALL)
    assert {c.metric for c in bad} == {"coverage", "duplicated_lines_density"}


def test_evaluate_ignores_missing_metrics():
    assert quality_gates.evaluate({}, quality_gates.STRICT_OVERALL) == []


def test_presets_exist():
    assert set(quality_gates.PRESETS) == {"sonar-way", "strict"}


def test_failed_conditions_filter():
    status = {"conditions": [{"status": "OK"}, {"status": "ERROR", "metricKey": "bugs"}]}
    assert quality_gates.failed_conditions(status) == [{"status": "ERROR", "metricKey": "bugs"}]


# --------------------------------------------------------------- profiles
def test_diff_rule_sets():
    diff = quality_profiles.diff_rule_sets({"a", "b"}, {"b", "c"})
    assert diff == {"only_a": ["a"], "only_b": ["c"], "common": ["b"]}


# ----------------------------------------------------------------- issues
@pytest.mark.parametrize(
    "text,minutes",
    [("5min", 5), ("1h", 60), ("1h30min", 90), ("1d", 480), ("2d1h5min", 2 * 480 + 65), ("", 0), (None, 0), ("garbage", 0)],
)
def test_parse_effort(text, minutes):
    assert issues.parse_effort(text) == minutes


@pytest.mark.parametrize("minutes,text", [(0, "0min"), (45, "45min"), (90, "1h30min"), (480, "1d"), (545, "1d1h5min")])
def test_format_minutes(minutes, text):
    assert issues.format_minutes(minutes) == text


def test_summarize_issues():
    data = [
        {"type": "BUG", "severity": "MAJOR", "status": "OPEN", "rule": "r1", "effort": "10min"},
        {"type": "BUG", "severity": "MINOR", "status": "OPEN", "rule": "r1", "effort": "1h"},
        {"type": "CODE_SMELL", "severity": "MINOR", "status": "CLOSED", "rule": "r2"},
    ]
    summary = issues.summarize(data)
    assert summary["total"] == 3
    assert summary["by_type"] == {"BUG": 2, "CODE_SMELL": 1}
    assert summary["debt_minutes"] == 70
    assert summary["top_rules"][0] == ("r1", 2)


# --------------------------------------------------------------- measures
def test_rating_letters():
    assert [measures.rating_letter(v) for v in (1, "2.0", 3, 4, 5)] == list("ABCDE")
    assert measures.rating_letter(9) == "?"


@pytest.mark.parametrize("ratio,letter", [(0, "A"), (5, "A"), (5.1, "B"), (10, "B"), (20, "C"), (50, "D"), (50.1, "E")])
def test_maintainability_rating_grid(ratio, letter):
    assert measures.maintainability_rating(ratio) == letter


def test_debt_ratio():
    assert measures.debt_ratio(300, 100) == 10.0  # 300 / (100*30) = 10 %
    assert measures.debt_ratio(300, 0) == 0.0


def test_trend_directions():
    assert measures.trend([("d1", 40.0), ("d2", 50.0)])["direction"] == "up"
    assert measures.trend([("d1", 50.0), ("d2", 40.0)])["pct_change"] == -20.0
    assert measures.trend([("d1", 5.0), ("d2", 5.0)])["direction"] == "flat"
    assert measures.trend([("d1", 5.0)])["delta"] == 0.0
    assert measures.trend([])["last"] is None


# ---------------------------------------------------------------- reports
REPORT = reports.build_report(
    "proj<1>", {"bugs": 3.0, "coverage": 41.2}, {"total": 2, "by_type": {"BUG": 2}, "by_severity": {"MAJOR": 2}, "debt_minutes": 70},
    {"status": "ERROR"}, now=datetime(2026, 11, 7, tzinfo=timezone.utc),
)


def test_csv_report_has_all_sections():
    text = reports.to_csv(REPORT)
    assert "measure,bugs,3.0" in text
    assert "by_type,BUG,2" in text
    assert "quality_gate,status,ERROR" in text


def test_markdown_report():
    text = reports.to_markdown(REPORT)
    assert "| bugs | 3.0 |" in text and "**ERROR**" in text


def test_html_report_escapes_project_name():
    text = reports.to_html(REPORT)
    assert "proj&lt;1&gt;" in text and "<script" not in text


def test_issues_csv_header_and_row():
    text = reports.issues_to_csv([{"key": "K", "type": "BUG", "unexpected": 1}])
    lines = text.strip().splitlines()
    assert lines[0].startswith("key,type,severity")
    assert lines[1].startswith("K,BUG,")


def test_write_report_creates_files(tmp_path):
    paths = reports.write_report(REPORT, tmp_path / "out", formats=("json", "md"))
    assert [p.suffix for p in paths] == [".json", ".md"]
    assert json.loads(paths[0].read_text())["project"] == "proj<1>"


# --------------------------------------------------------------- webhooks
def test_signature_roundtrip():
    body = b'{"a": 1}'
    signature = webhooks.sign(body, "s3cret")
    assert webhooks.verify_signature(body, "s3cret", signature)
    assert webhooks.verify_signature(body, "s3cret", signature.upper())
    assert not webhooks.verify_signature(body, "other", signature)
    assert not webhooks.verify_signature(body, "s3cret", None)


def test_parse_payload_extracts_failed_conditions():
    payload = {
        "status": "SUCCESS", "project": {"key": "shopflow"}, "branch": {"name": "main"},
        "qualityGate": {"name": "Strict", "status": "ERROR", "conditions": [{"metric": "bugs", "status": "ERROR"}, {"metric": "coverage", "status": "OK"}]},
    }
    event = webhooks.parse_payload(payload)
    assert (event.project_key, event.gate_status, event.branch) == ("shopflow", "ERROR", "main")
    assert [c["metric"] for c in event.failed_conditions] == ["bugs"]


def test_parse_payload_tolerates_missing_gate():
    assert webhooks.parse_payload({}).gate_status is None


# ---------------------------------------------------------------- hotspots
def test_hotspots_by_priority():
    assert hotspots.by_priority([{"vulnerabilityProbability": "HIGH"}, {"vulnerabilityProbability": "HIGH"}, {}]) == {"HIGH": 2, "?": 1}


# --------------------------------------------------------------------- ci
def test_read_report_task(tmp_path):
    file = tmp_path / "report-task.txt"
    file.write_text("projectKey=shopflow\nceTaskId=AY123\nserverUrl=http://x:9000\nnoise line\n")
    info = ci.read_report_task(file)
    assert info["ceTaskId"] == "AY123" and info["projectKey"] == "shopflow"


@pytest.mark.parametrize("status,code", [("OK", 0), ("WARN", 0), ("ERROR", 1), ("NONE", 2), ("???", 2)])
def test_exit_code_for(status, code):
    assert ci.exit_code_for(status) == code

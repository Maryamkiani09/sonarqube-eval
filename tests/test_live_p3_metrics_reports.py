"""LIVE tests - Person 3: metrics, dashboards data, trends, exports."""
import csv
import io

import pytest

from sonar_tools import issues, measures, projects, reports

pytestmark = pytest.mark.integration


def test_p3_01_all_core_metrics_available(live, project_key):
    m = measures.get_measures(live, project_key)
    for key in ("ncloc", "coverage", "duplicated_lines_density", "complexity", "sqale_rating", "reliability_rating"):
        assert key in m, key


def test_p3_02_coverage_is_partial(live, project_key):
    coverage = measures.get_measures(live, project_key, ["coverage", "line_coverage"])
    assert 0 < coverage["coverage"] < 100, "sample tests are deliberately incomplete"


def test_p3_03_issue_level_csv_export(live, project_key):
    found = issues.search_issues(live, project_key)
    rows = list(csv.DictReader(io.StringIO(reports.issues_to_csv(found))))
    assert len(rows) == len(found) and rows[0]["rule"]


def test_p3_04_summary_report_in_four_formats(live, project_key, tmp_path):
    summary = issues.summarize(issues.search_issues(live, project_key))
    report = reports.build_report(project_key, measures.get_measures(live, project_key), summary)
    paths = reports.write_report(report, tmp_path)
    assert {p.suffix for p in paths} == {".csv", ".md", ".html", ".json"}
    assert all(p.stat().st_size > 0 for p in paths)


def test_p3_05_history_and_trend(live, project_key):
    if len(projects.analyses(live, project_key)) < 2:
        pytest.skip("run the scanner a second time (after improving the code) to get a trend")
    series = measures.history(live, project_key, ["coverage", "bugs"])
    assert len(series["coverage"]) >= 2
    assert measures.trend(series["bugs"])["direction"] in ("up", "down", "flat")


def test_p3_06_technical_debt_ratio_consistent(live, project_key):
    m = measures.get_measures(live, project_key, ["sqale_index", "ncloc", "sqale_rating"])
    ratio = measures.debt_ratio(m["sqale_index"], int(m["ncloc"]))
    assert measures.maintainability_rating(ratio) == m["sqale_rating"]

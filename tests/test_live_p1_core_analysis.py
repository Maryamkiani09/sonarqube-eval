"""LIVE tests - Person 1: core analysis and code quality.

Run after analysing the project once (README step 5). These tests assert what
the deliberately flawed sample code SHOULD produce. If one fails, check whether
your SonarQube version/rule set behaves differently and document it - that is
an evaluation finding, not necessarily a bug.
"""
import pytest

from sonar_tools import hotspots, issues, measures

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def m(live, project_key):
    return measures.get_measures(live, project_key)


def test_p1_01_code_was_analysed(m):
    assert m["ncloc"] > 100 and m["files"] >= 10


def test_p1_02_bugs_detected(m):
    assert m["bugs"] >= 1


def test_p1_03_code_smells_and_technical_debt(m):
    assert m["code_smells"] >= 5 and m["sqale_index"] > 0


def test_p1_04_duplication_detected(m):
    assert m["duplicated_lines_density"] > 0


def test_p1_05_complexity_metrics(m):
    assert m["complexity"] > 10 and m["cognitive_complexity"] > 10


def test_p1_06_ratings_are_letters(m):
    for rating in ("reliability_rating", "security_rating", "sqale_rating"):
        assert m[rating] in list("ABCDE")


def test_p1_07_multi_language_support(live, project_key):
    distribution = measures.get_measures(live, project_key, ["ncloc_language_distribution"])["ncloc_language_distribution"]
    languages = {part.split("=")[0] for part in distribution.split(";")}
    assert "py" in languages and len(languages) >= 4, languages


def test_p1_08_issue_categories_present(live, project_key):
    all_issues = issues.search_issues(live, project_key)
    assert all_issues
    assert all(i.get("type") and i.get("severity") and i.get("status") for i in all_issues)


def test_p1_09_exclusions_respected(live, project_key):
    assert not [i for i in issues.search_issues(live, project_key) if "generated" in i["component"]]


def test_p1_10_secrets_analyzer(live, project_key):
    found = issues.search_issues(live, project_key, languages="secrets")
    if not found:
        pytest.skip("secrets analyzer reported nothing - record this in your findings")
    assert all(i["component"].endswith(".py") or "." in i["component"] for i in found)


def test_p1_11_hotspots_recorded(live, project_key, capsys):
    found = hotspots.search_hotspots(live, project_key)
    with capsys.disabled():
        print(f"\n[finding] security hotspots on this version: {len(found)} {hotspots.by_priority(found)}")
    assert isinstance(found, list)

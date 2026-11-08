# Test Cases

Two layers:

* **Automated** – `pytest` (unit tests with no server; `integration` tests against your SonarQube).
* **Manual (UI)** – what to click, what to expect, and what to screenshot for the report.

Record for every case: **Pass / Fail / Different-from-expected**, version of SonarQube, and a screenshot.
"Different-from-expected" results are *findings*, not failures of your project.

Prerequisite for all: server running, `scripts/run_analysis.sh` executed once (project `shopflow-eval`).

---

## Person 1 – Core analysis & code quality

| ID | Steps | Expected result |
|----|-------|-----------------|
| P1-1 | Project → Overview | Analysis exists; lines of code, languages shown; Python plus fixture languages |
| P1-2 | Issues → filter Type/Quality = Bug | Findings in `bugs.py` (unreachable code, ignored return value, always-false `len(x) < 0`, duplicate condition, self-assignment, float equality) – exact list depends on version |
| P1-3 | Issues → Code Smell | Findings in `legacy.py` (unused imports, commented-out code, too many parameters, mutable default argument, bare `except`, duplicated literal) and `orders.py` (cognitive complexity) |
| P1-4 | Measures → Duplications | Duplicated blocks in `pricing.py` and between `csv_exporter.py` / `tsv_exporter.py`; `inventory.py` has none |
| P1-5 | Measures → Complexity | `orders.py` highest cyclomatic & cognitive complexity |
| P1-6 | Overview → ratings | Letters A–E for Reliability, Security, Maintainability; note which file drives each |
| P1-7 | Overview → language breakdown / Project Information | Python, JS, Java, Go, PHP, CSS, HTML, Docker, Terraform, Kubernetes, CloudFormation present |
| P1-8 | Issues on `config.py` | Hard-coded secret (the AWS documentation example keys) and insecure http URL / disabled TLS verification |
| P1-9 | Administration → Configuration → *Mode* (if offered) | Compare **MQR** vs **Standard** view of the same issues; screenshot both |
| P1-10 | Open file `generated/gen_models.py` via search | Not analysed (excluded) – proves exclusion works |
| P1-11 | Security Hotspots page | Hotspots (e.g. weak hash, SQL string building in `auth.py`) *or* a note that this version merged them into issues – record which |
| P1-12 | Open an issue → "Why is this an issue?" | Rule description, how to fix, code example |

Automated: `tests/test_live_p1_core_analysis.py` (11), `tests/test_app_shopflow.py`.

## Person 2 – Quality gates & profiles

| ID | Steps | Expected result |
|----|-------|-----------------|
| P2-1 | Quality Gates → *Sonar way* | Built-in, not editable; read its conditions (new-code focused) |
| P2-2 | Copy it → "Strict"; add overall-code conditions (coverage < 80, duplication > 3, bugs > 0) | New gate created |
| P2-3 | Project settings → Quality Gate → select Strict; re-scan | Gate status **Failed**, failing conditions listed |
| P2-4 | Create a lenient gate (all thresholds loose); assign; re-scan | **Passed** |
| P2-5 | Quality Profiles → Python → copy *Sonar way* → "Team" | Custom profile; set as default or assign to project |
| P2-6 | In "Team": deactivate one rule, activate one rule, change a severity | Next scan reflects the change (issue appears/disappears) |
| P2-7 | Rules page: filter by language=Python, severity=Blocker | Count shown; compare with `test_p2_06` output |
| P2-8 | Profile → Compare against Sonar way | Differences listed |
| P2-9 | Profile → Back up / Restore | XML downloaded and re-importable |
| P2-10 | CLI: `python -m sonar_tools.cli gate-create Strict --preset strict` then `gate-status shopflow-eval` (run with `PYTHONPATH=src`) | Same result as UI |

Automated: `tests/test_live_p2_quality_gates.py` (6), `tests/test_tools_pure.py` (gate evaluation logic).

## Person 3 – Metrics, reports & trends

| ID | Steps | Expected result |
|----|-------|-----------------|
| P3-1 | Measures → Coverage | Overall % roughly matches `reports/coverage.xml`; `inventory.py` ≈ 100 %, `orders.py` partial |
| P3-2 | Measures → Tests | Test counts from `reports/junit.xml` |
| P3-3 | Look for a dashboard builder / portfolio menu | Only the fixed project overview exists in Community → record as limitation |
| P3-4 | Run `IMPROVE=1 VERSION=1.1 scripts/run_analysis.sh` after fixing a bug | Project → Activity graph shows two versions; metrics changed |
| P3-5 | CLI: `report shopflow-eval --out reports/out --formats csv,md,html,json`; `issues-csv shopflow-eval -o issues.csv` | Files generated; numbers match UI |
| P3-6 | Search the UI for "Export PDF" / "Download report" | **Absent** (Enterprise+) → screenshot as evidence |
| P3-7 | Look for a CSV download button on Issues/Measures | Absent or limited; the API-based export is the workaround |
| P3-8 | Compare technical debt ratio in UI with `measures.debt_ratio()` | Equal within rounding |

Automated: `tests/test_live_p3_metrics_reports.py` (6), `tests/test_tools_pure.py` (reports/measures).

## Person 4 – Developer feedback & SonarQube for IDE

| ID | Steps | Expected result |
|----|-------|-----------------|
| P4-1 | Install SonarQube for IDE (VS Code or IntelliJ); open `src/shopflow/bugs.py` **without** connecting | Standalone analysis underlines issues live |
| P4-2 | Create a User token; connect IDE to `http://localhost:9000` (connected mode); bind to `shopflow-eval` | Binding succeeds; the IDE uses the project's quality profile |
| P4-3 | Change a rule in the server profile (see P2-6); sync the IDE | IDE behaviour follows the server profile |
| P4-4 | Mark an issue "False positive" in the server UI; refresh the IDE | Suppression visible in the IDE (may need re-sync) |
| P4-5 | Edit code to fix an issue in the IDE | Issue disappears immediately; compare with scan latency on the server |
| P4-6 | Revoke the token (`test_p4_01` does this via API) | IDE reports connection failure |

Automated: `tests/test_live_p4_developer_feedback.py` (4).
Note: the IDE plugin itself cannot be unit-tested from Python; steps P4-1…6 are manual by nature.

## Person 5 – CI/CD & multi-project

| ID | Steps | Expected result |
|----|-------|-----------------|
| P5-1 | Two projects exist after `run_analysis` | `shopflow-eval` and `sonar-tools-eval`; Projects page lists both; create more with `sonar_tools.projects.create_many` |
| P5-2 | `WAIT=1 scripts/run_analysis.sh` with the Strict gate | Scanner exits non-zero → build fails |
| P5-3 | Scan with `-Dsonar.branch.name=feature-x` | **Rejected** by Community Build; record the *exact* message |
| P5-4 | Scan with `-Dsonar.pullrequest.key=1 -Dsonar.pullrequest.branch=x -Dsonar.pullrequest.base=main` | **Rejected**; record message. Project has no Branches/PR tab |
| P5-5 | Run `PYTHONPATH=src python -m sonar_tools.ci --report-task .scannerwork/report-task.txt` | Exit 0 when gate OK, 1 when failed, 2 on error |
| P5-6 | Register webhook (`test_p5_06`) pointing at `WebhookReceiver`; run a scan | Receiver verifies HMAC signature and prints gate status |
| P5-7 | Copy `.github/workflows/sonarqube.yml` into a real GitHub repo with secrets `SONAR_TOKEN`, `SONAR_HOST_URL` | Workflow runs; needs a server reachable from GitHub (self-hosted runner or tunnel) |
| P5-8 | Jenkins / GitLab / Azure DevOps files in `ci/` | Same flow; **action/task version tags in these files are from memory – check current versions** |

Automated: `tests/test_live_p5_cicd_multiproject.py` (6), `tests/test_tools_api.py` (CI helpers, webhooks, against fake server).

## Person 6 – Plugins, API, localization, databases, reporting

| ID | Steps | Expected result |
|----|-------|-----------------|
| P6-1 | `version`, `health`, `database` CLI commands | Version string; health GREEN; DB = PostgreSQL (compose) |
| P6-2 | Start H2 compose; repeat | DB = H2; UI shows "embedded database" warning |
| P6-3 | Administration → Marketplace | Installed plugins include Python analyzer; list of available plugins |
| P6-4 | Marketplace → search "Chinese" / "Spanish" language pack; install; restart | UI language changes (localization is a plugin) – record |
| P6-5 | `plugins`, `languages` CLI | Lists match the UI |
| P6-6 | Create user, group, give group permission on project via API (`test_p6_07`) | Appears in Security UI; test cleans up |
| P6-7 | Browse `http://localhost:9000/web_api` | Compare the parameter names used in `src/sonar_tools/*.py` with the docs; **log differences** |
| P6-8 | Settings round-trip via API (`test_p6_08`) | Set then reset a property |
| P6-9 | Try MySQL JDBC URL in `docker-compose.yml` | Server refuses to start/unsupported – record message (optional) |

Automated: `tests/test_live_p6_api_plugins_admin.py` (8), `tests/test_tools_api.py`.

---

## Automated test map

| File | Count | Needs server? | What it proves |
|------|-------|---------------|----------------|
| `test_app_shopflow.py` | app unit tests | no | The sample app behaves as designed; its coverage is *partial* on purpose |
| `test_app_improvement.py` | 16 | no (`IMPROVE=1`) | Extra coverage for the second analysis / trend demo |
| `test_tools_pure.py` | pure logic | no | Gate evaluation, effort parsing, reports, signatures |
| `test_tools_api.py` | API wrappers | no (fake server) | Request building, pagination, error handling for every module |
| `test_live_p1…p6_*.py` | 41 | **yes** | Each person's features on the real server |

Totals: 115 pass / 57 skipped by default; the 57 = 41 live + 16 improvement tests.

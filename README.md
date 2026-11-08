# SonarQube Community Build – Evaluation Project

A complete, runnable project for exploring and evaluating **SonarQube Community Build**
(group final project, 6 people). It contains:

| Part | Folder | Purpose |
|------|--------|---------|
| **Subject under analysis** (ShopFlow app) | `src/shopflow/` | Small Python app with *deliberate* bugs, smells, duplication, secrets and security hotspots, plus a clean module and partially-tested code, so every SonarQube feature has something to show. |
| **Polyglot fixtures** | `fixtures/polyglot/` | JS, Java, Go, PHP, Docker, Terraform, Kubernetes, CloudFormation, HTML, CSS files – shows multi-language analysis. |
| **Tooling package** (`sonar_tools`) | `src/sonar_tools/` | Python client + CLI for the SonarQube Web API: quality gates, profiles, issues, measures, reports (CSV/MD/HTML/JSON), webhooks, CI wait/exit-code, admin. This is the "Python code" that automates each person's area. |
| **Unit tests** (no server needed) | `tests/test_app_*.py`, `test_tools_*.py` | 115 tests; `tools` tests run against an in-memory fake Sonar server (`tests/fake_sonar.py`). |
| **Live tests** (need a server) | `tests/test_live_p1…p6_*.py` | 41 tests, one file per team member, run against your real SonarQube. Skipped automatically without `SONAR_TOKEN`. |
| **Infrastructure** | `docker-compose*.yml`, `scripts/`, `ci/`, `.github/` | SonarQube + PostgreSQL, scan scripts, and CI examples (GitHub Actions, Jenkins, GitLab, Azure DevOps). |

Companion documents: **`FEATURE_MATRIX.md`** (every feature, Community status, where it is tested) and
**`TEST_CASES.md`** (manual UI test cases + mapping to automated tests).

> ⚠️ **Honest status of this project.** The unit tests (115) pass and the coverage reports were generated and
> checked. The author did **not** have a SonarQube server, so the live tests, Docker files, CI files,
> the PowerShell script, and the expected-findings lists were **written but never executed against a real
> server**. Web API parameter names come from knowledge of the API and should be checked against your own
> server's built-in docs at `http://localhost:9000/web_api`. Treat the first run as part of the evaluation,
> and record any differences you find – that is valuable material for the report.

---

## 1. Prerequisites

* Docker + Docker Compose (for the server)
* Python 3.10+ (3.13 is configured in `sonar-project.properties`; change `sonar.python.version` if yours differs)
* [`sonar-scanner` CLI](https://docs.sonarsource.com/sonarqube-server/latest/analyzing-source-code/scanners/sonarscanner/) on your PATH
* Node.js (only needed so the scanner can analyse the JS file) and a JDK (scanner itself)
* Linux hosts: `sudo sysctl -w vm.max_map_count=524288` (Elasticsearch requirement)

```bash
pip install -r requirements-dev.txt     # requests, pytest, pytest-cov
```

## 2. Quick start

```bash
# 1. Start SonarQube Community + PostgreSQL
docker compose up -d
#    open http://localhost:9000  (login admin / admin, you will be forced to change the password)

# 2. Create a token: My Account → Security → Generate Tokens (a "User" token is fine)
export SONAR_HOST_URL=http://localhost:9000
export SONAR_TOKEN=<your token>

# 3. Run tests + coverage + both scans
scripts/run_analysis.sh                 # Windows: .\scripts\run_analysis.ps1
```

Two projects are created in SonarQube:

* `shopflow-eval` – the app + polyglot fixtures (the main exploration target)
* `sonar-tools-eval` – the tooling package itself (written clean; shows a *passing* project and a *passing* gate)

### Second analysis → trends and "new code"

```bash
IMPROVE=1 VERSION=1.1 scripts/run_analysis.sh
```

`IMPROVE=1` enables `tests/test_app_improvement.py`, which adds extra coverage; use it together with edits
to the code (fix a bug or two) to get a *second* data point, so history graphs, "new code" metrics and
the Clean-as-You-Code gate have something to compare. To see different behaviour, change what gets scanned
using the commented "scope experiments" in `sonar-project.properties`.

### Alternative: H2 (embedded) database

```bash
docker compose -f docker-compose.h2.yml up -d   # port 9001
```
H2 is for evaluation only (no upgrade path, not for production). Useful for Person 6's DB comparison.

## 3. Who uses what (maps to the assignment PDF)

| Person | Focus | Python module(s) | Live tests | CLI commands |
|--------|-------|------------------|------------|--------------|
| 1 | Core analysis & code quality | `issues.py`, `hotspots.py`, `src/shopflow/*`, `fixtures/` | `test_live_p1_core_analysis.py` | `issues-summary`, `hotspots` |
| 2 | Quality gates & profiles | `quality_gates.py`, `quality_profiles.py` | `test_live_p2_quality_gates.py` | `gate-create`, `gate-status` |
| 3 | Metrics, reports, trends | `measures.py`, `reports.py` | `test_live_p3_metrics_reports.py` | `report`, `trend`, `issues-csv` |
| 4 | Developer feedback / IDE | `issues.py` (workflow), `client.py` tokens | `test_live_p4_developer_feedback.py` | `issues-summary` + manual IDE steps |
| 5 | CI/CD & multi-project | `ci.py`, `projects.py`, `webhooks.py`, `ci/*`, `.github/*` | `test_live_p5_cicd_multiproject.py` | `projects`, `gate-status` |
| 6 | Plugins, API, DB, localization | `admin.py`, `system.py`, `client.py` | `test_live_p6_api_plugins_admin.py` | `version`, `health`, `database`, `plugins`, `languages` |

Run the CLI with `PYTHONPATH=src python -m sonar_tools.cli --help`.

## 4. Running the tests

```bash
python -m pytest                          # 115 pass, 57 skipped (live tests skip with no token)
IMPROVE=1 python -m pytest                # also runs the 16 "after improvement" tests

# Live tests against your server:
export SONAR_URL=http://localhost:9000
export SONAR_TOKEN=<token>
export SONAR_PROJECT_KEY=shopflow-eval      # default
python -m pytest -m integration -v
# Webhook test: if the server runs in Docker, it must be able to reach this machine:
export SONAR_WEBHOOK_HOST=host.docker.internal
```

Expect **some live tests to fail the first time** – version differences (e.g. hotspot handling, profile names,
MQR-vs-Standard metric names) are exactly what an evaluation should discover. Read the assertion message, check
the UI, then either fix the test or write the difference down as a finding.

## 5. Troubleshooting

| Problem | Fix |
|---------|-----|
| SonarQube container exits immediately | `vm.max_map_count` too low (see prerequisites) |
| Scanner can't reach server from Docker | use `host.docker.internal`, or `SONAR_HOST_URL=http://sonarqube:9000` inside the compose network |
| Coverage shows 0% / "file not found" | `reports/coverage.xml` paths must be relative to the project root – always use the provided `.coveragerc` (`source = .`) |
| Java fixture reports "binaries missing" | `sonar.java.binaries` points at `fixtures/polyglot`; for a quick demo this is acceptable |
| 401 from the API | use the token as the *username* with empty password (the client does this); a *project analysis token* cannot call most admin endpoints – use a *User* token |
| Branch / PR analysis rejected | **expected** – not in Community Build; see `TEST_CASES.md` (negative tests) and record the exact message |

## 6. The ShopFlow app is intentionally flawed

`auth.py`, `config.py`, `legacy.py`, `bugs.py` contain bad code **on purpose** (hard-coded fake credentials from
vendor documentation, SQL string building, weak hashing, etc.). Do not deploy or reuse it.

## 7. Layout

```
src/shopflow/        subject of analysis (inventory.py is clean; others are flawed)
src/sonar_tools/     Web API toolkit + CLI
fixtures/polyglot/   multi-language samples
tests/               unit tests, fake Sonar server, live tests (p1–p6)
scripts/             run_analysis.sh / .ps1
ci/ .github/         CI pipeline examples (Jenkins, GitLab, Azure DevOps, GitHub Actions)
docker-compose*.yml  SonarQube + PostgreSQL / H2
```

Note: the coverage config for the tooling project is `coveragerc_tools.ini` (a leading-dot name such as
`.coveragerc.tools` is not reliably read by coverage.py).

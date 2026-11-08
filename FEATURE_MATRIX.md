# Feature Matrix – SonarQube Community Build

Answers two questions: **(1)** what does the team's assignment document cover and is each item really in
Community, and **(2)** what else exists in Community that the document does not mention.

**Evidence labels** (be honest about these in your report):

* **[Docs]** – stated in Sonar's official documentation when this was researched (Nov 2026, Community Build ≈ 26.x).
* **[Mem]** – from general knowledge of the product; *not* re-checked against the docs.
* **[2nd]** – seen only in a secondary source (blog/news); treat as unconfirmed.
* **[Verify]** – you must confirm on your own instance; UI/names change between releases.

Product names move around (Community *Edition* → Community *Build*; SonarLint → SonarQube for IDE; "Sonar way"
profile names changed). Always compare with the version you installed (`sonar_tools.cli version`).

---

## A. Features from the assignment document

| # | Person | Feature in the document | In Community? | Evidence | Exercised by |
|---|--------|-------------------------|---------------|----------|--------------|
| 1 | P1 | Static code analysis | Yes | Docs | `test_p1_01`, `shopflow/*` |
| 1 | P1 | Bugs, vulnerabilities, code smells | Yes (rule set smaller than paid editions, e.g. no taint analysis) | Docs | `test_p1_02/03/08`, `bugs.py`, `legacy.py` |
| 1 | P1 | Security hotspots (basic) | **Verify** – reported as being phased out/reworked in newer releases | 2nd | `test_p1_11` (tolerant), `auth.py`, `config.py` |
| 1 | P1 | Technical debt (effort estimate) | Yes | Docs | `test_p1_03`, `issues.parse_effort` |
| 1 | P1 | Multi-language support | Yes (≈ 20 languages; several IaC) | Docs | `test_p1_07`, `fixtures/polyglot/*` |
| 1 | P1 | Code duplication | Yes | Docs | `test_p1_04`, `pricing.py`, `exporters/*` |
| 1 | P1 | Cyclomatic / cognitive complexity | Yes (both metrics) | Docs | `test_p1_05`, `orders.py` |
| 1 | P1 | Reliability / security / maintainability ratings | Yes | Docs | `test_p1_06` |
| 2 | P2 | Quality gates, built-in "Sonar way" | Yes | Docs | `test_p2_01` |
| 2 | P2 | Custom quality gates | Yes | Docs | `test_p2_02/03`, `quality_gates.py` |
| 2 | P2 | Quality profiles per language, rule (de)activation | Yes (copy/inherit, backup/restore) | Docs | `test_p2_05/06`, `quality_profiles.py` |
| 2 | P2 | Severity / coverage / duplication thresholds | Yes (gate conditions on overall or new code) | Docs | `test_p2_02/04`, `PRESETS` |
| 3 | P3 | Coverage & duplication metrics | Yes (coverage is *imported* from your test tool – SonarQube does not run tests) | Docs | `test_p3_01/02`, `.coveragerc` |
| 3 | P3 | Dashboards | **Partly** – per-project overview and Issues/Measures pages only. Portfolios & custom dashboards are paid | Docs | manual (TEST_CASES P3-3) |
| 3 | P3 | Historical trends | Yes (project activity graph; needs ≥ 2 analyses) | Docs | `test_p3_05`, `IMPROVE=1` run |
| 3 | P3 | **PDF export** | **No** – PDF reports are Enterprise+ | Docs | negative check P3-6 |
| 3 | P3 | **CSV export** | **No built-in button** in the UI; use Web API → our `reports.py` / `issues_to_csv` | Mem/Verify | `test_p3_03/04` |
| 4 | P4 | SonarQube for IDE (ex-SonarLint) plugin | Yes, free in VS Code, IntelliJ-family, Visual Studio, Eclipse | Docs | manual (P4-1…4) |
| 4 | P4 | Live feedback in the editor (standalone) | Yes | Docs | manual |
| 4 | P4 | Connected mode to Community server | Yes (token, shared profile & suppressions) | Docs | `test_p4_01/02` |
| 4 | P4 | "Linking to CI/CD" | Imprecise – connected mode links the IDE to the *server*; CI just shares the same project. | Docs | `test_p4_02/03`, P5 tests |
| 4 | P4 | Issue categories (bug/vuln/smell) | Yes (MQR mode shows "software qualities" instead) | Docs | `test_p1_08`, `test_p4_03` |
| 5 | P5 | Jenkins / GitHub Actions / GitLab CI / Azure DevOps | Scanner integration works in all | Docs | `ci/*`, `.github/*`, `test_p5_02/03` |
| 5 | P5 | PR decoration / PR analysis | **No** – Developer Edition+ | Docs | negative check P5-4, `test_p5_05` |
| 5 | P5 | **Branch analysis** | **No** – Community analyses the *main branch only* | Docs | `test_p5_04`, negative check P5-3 |
| 5 | P5 | Multi-project | Yes (any number of projects, unlimited users) | Docs | `test_p5_01` |
| 5 | P5 | Automated gate enforcement / build failure | Yes – `sonar.qualitygate.wait=true` or poll CE task | Docs | `ci.py`, `test_p5_02/03` |
| 6 | P6 | Plugins / marketplace | Yes (marketplace + manual jar install; admin only) | Docs | `test_p6_03/04` |
| 6 | P6 | Web API | Yes (full REST API, per-instance docs at `/web_api`) | Docs | `client.py`, `test_tools_api.py`, `test_p6_*` |
| 6 | P6 | Localization | Yes, via language-pack plugins (marketplace) | Mem/Verify | `test_p6_05` |
| 6 | P6 | **MySQL** | **No** – unsupported. Supported: PostgreSQL, SQL Server, Oracle. H2 = evaluation only | Docs | `test_p6_02`, `docker-compose*.yml` |
| 6 | P6 | Automated reporting | Yes (API + webhooks; no built-in scheduled report) | Docs | `reports.py`, `webhooks.py` |

---

## B. Community features **not** in the assignment document (answer to question 1)

| Feature | Notes | Evidence | Exercised by |
|---------|-------|----------|--------------|
| **Secrets detection** | Finds hard-coded tokens/keys in any file | Docs | `config.py`, `test_p1_10` |
| **Infrastructure-as-code analysis** | Docker, Terraform, Kubernetes, CloudFormation, Ansible etc. | Docs | `fixtures/polyglot/*` |
| **Clean as You Code / New Code Period** | "new code" definitions (previous version, number of days, reference branch) drive "new code" gate conditions | Docs | `test_p2_04`, `IMPROVE=1` |
| **MQR vs Standard experience** | Multi-Quality Rule mode (software qualities & impact severity) vs classic bug/vuln/smell | Docs | `test_p1_08`, TEST_CASES P1-9 |
| **Issue workflow** | Assign, comment, tag, change severity, *false positive / accept* | Docs | `issues.py`, `test_p4_04` |
| **Issue suppression** | `# NOSONAR`, UI resolution | Docs | `legacy.py`, `test_p1_09` |
| **Analysis scope** | Inclusions/exclusions, test-file patterns, generated-code exclusion | Docs | `sonar-project.properties`, `test_p1_09` |
| **SCM integration** | Blame data → issue author / assignee, new-code detection | Docs | manual (needs git) |
| **Webhooks** | HMAC-signed POST after each analysis | Docs | `webhooks.py`, `test_p5_06` |
| **Authentication & authorization** | Users, groups, global/project permissions, permission templates, tokens (user / project / global analysis) | Docs | `test_p6_07`, `test_p4_01` |
| **Delegated auth (LDAP/SAML/GitHub/GitLab/Bitbucket)** | Free; some configuration only in paid editions | Mem/Verify | manual |
| **External issue import** | Generic issue import format for third-party tools | Mem/Verify | manual |
| **Rules database** | Search/filter all rules, per-rule docs, tags, clean-code attributes | Docs | `test_p2_06` |
| **Quality profile inheritance, backup/restore, compare** | | Docs | `quality_profiles.py`, `test_p2_05` |
| **Project badges** | Embeddable SVG status badges | Mem/Verify | manual |
| **Project administration** | Tags, links, key renaming, deletion, background tasks view | Docs | `projects.py`, `test_p5_01` |
| **Compute Engine / background tasks** | Queue visibility, failed task logs | Docs | `ci.read_report_task`, `wait_for_ce_task` |
| **System info & health check** | `/api/system/health`, `/api/system/status`, logs | Docs | `system.py`, `test_p6_01` |
| **Housekeeping / data retention** | Admin settings for history cleanup | Mem/Verify | manual |
| **E-mail notifications** | Gate changes, issue assignment (needs SMTP) | Mem/Verify | manual |
| **Dependency / SCA, AI Code Assurance, MCP server** | Newer Sonar features – availability per edition **unknown**; check docs | none | not tested |

---

## C. Paid-only features (use for the "limitations" slide)

| Feature | Edition | Evidence |
|---------|---------|----------|
| Branch analysis, pull-request analysis & decoration | Developer+ | Docs |
| Taint analysis, advanced Java/C#/etc. security rules | Developer+ | Docs |
| C, C++, Objective-C, Swift (some), Apex, PL/SQL, COBOL, ABAP… analyzers | Developer / Enterprise (varies) | Mem/Verify |
| Portfolios, executive/security reports, **PDF reports** | Enterprise+ | Docs |
| Audit logs, advanced governance, scalability (Data Center) | Enterprise / Data Center | Mem |
| Regulatory reports (OWASP, CWE, PCI) | Enterprise+ | Mem/Verify |

---

## D. Corrections to the assignment document (list these in your report)

1. **Branch analysis (Person 5)** – not available in Community; only the main branch is analysed.
2. **PDF export (Person 3)** – Enterprise+ only.
3. **CSV export (Person 3)** – no built-in measures/project CSV export; obtained through the Web API.
4. **Dashboards (Person 3)** – only the fixed project overview; no custom dashboards or portfolios.
5. **MySQL (Person 6)** – not supported by modern SonarQube; use PostgreSQL (or H2 for evaluation).
6. **SonarLint** – renamed *SonarQube for IDE*.
7. **Security hotspots** – verify whether your version still lists them as a separate feature.
8. **Coverage** – SonarQube does not measure coverage itself; it imports reports from `coverage.py`, JaCoCo, etc.

"""A small in-memory imitation of the SonarQube Web API, served over real HTTP.

It lets the unit tests exercise sonar_tools end to end WITHOUT a SonarQube
server. It only implements the endpoints sonar_tools uses and is NOT a
substitute for the live tests in tests/integration.
"""
from __future__ import annotations

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class FakeSonar:
    def __init__(self, token: str | None = None) -> None:
        self.token = token
        self.calls: list[tuple[str, str, dict]] = []
        self.projects: dict[str, str] = {}
        self.gates: dict[str, list[dict]] = {"Sonar way": [{"metric": "coverage", "op": "LT", "error": "80"}]}
        self.default_gate = "Sonar way"
        self.project_gate: dict[str, str] = {}
        self.profiles = [{"key": "py-way", "name": "Sonar way", "language": "py", "isBuiltIn": True, "isDefault": True}]
        self.active_rules: dict[str, set[str]] = {"py-way": {"python:S1481", "python:S125"}}
        self.profile_projects: dict[tuple[str, str], str] = {}
        self.issues = [
            {"key": "I1", "type": "BUG", "severity": "MAJOR", "status": "OPEN", "rule": "python:S1763", "component": "shopflow:src/a.py", "line": 3, "message": "unreachable", "effort": "5min", "creationDate": "2026-11-01"},
            {"key": "I2", "type": "CODE_SMELL", "severity": "MINOR", "status": "OPEN", "rule": "python:S1481", "component": "shopflow:src/b.py", "line": 9, "message": "unused", "effort": "1h", "creationDate": "2026-11-01"},
            {"key": "I3", "type": "VULNERABILITY", "severity": "CRITICAL", "status": "OPEN", "rule": "python:S2068", "component": "shopflow:src/c.py", "line": 1, "message": "password", "effort": "30min", "creationDate": "2026-11-01"},
        ]
        self.measures: dict[str, dict[str, str]] = {}
        self.history: dict[str, dict[str, list[dict]]] = {}
        self.known_metrics = ["coverage", "bugs", "vulnerabilities", "code_smells", "ncloc", "duplicated_lines_density", "reliability_rating", "security_rating", "sqale_rating", "alert_status", "complexity"]
        self.hotspots: list[dict] = []
        self.webhooks: dict[str, dict] = {}
        self.ce_tasks: dict[str, list[str]] = {}
        self.analysis_project: dict[str, str] = {}
        self.settings: dict[tuple[str, str | None], dict] = {}
        self.users: dict[str, dict] = {}
        self.groups: dict[str, dict] = {}
        self.permissions: list[tuple] = []
        self.tokens: dict[str, str] = {}
        self.new_code: dict[str, tuple] = {}
        self._server: ThreadingHTTPServer | None = None

    # ------------------------------------------------------------ plumbing
    def start(self) -> "FakeSonar":
        state = self

        class Handler(BaseHTTPRequestHandler):
            def _serve(self, method: str) -> None:
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query, keep_blank_values=True)
                if method == "POST":
                    body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
                    params.update(parse_qs(body, keep_blank_values=True))
                path = parsed.path.strip("/")
                state.calls.append((method, path, {k: v[0] if len(v) == 1 else v for k, v in params.items()}))
                if state.token and not state._authorized(self.headers.get("Authorization", "")):
                    return self._send(401, {"errors": [{"msg": "Insufficient privileges"}]})
                handler = getattr(state, "h_" + path.replace("/", "_"), None)
                if handler is None:
                    return self._send(404, {"errors": [{"msg": f"Unknown url : /{path}"}]})
                status, payload = handler(params)
                self._send(status, payload)

            def _send(self, status: int, payload) -> None:
                if isinstance(payload, str):
                    data, ctype = payload.encode(), "text/plain"
                else:
                    data, ctype = json.dumps(payload).encode(), "application/json"
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):  # noqa: N802
                self._serve("GET")

            def do_POST(self):  # noqa: N802
                self._serve("POST")

            def log_message(self, *args):
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
        return self

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def _authorized(self, header: str) -> bool:
        if not header.startswith("Basic "):
            return False
        user = base64.b64decode(header[6:]).decode().partition(":")[0]
        return user == self.token

    def paths(self) -> list[str]:
        return [c[1] for c in self.calls]

    @staticmethod
    def _p(params: dict, key: str, default=None):
        return params.get(key, [default])[0]

    @staticmethod
    def _error(status: int, msg: str):
        return status, {"errors": [{"msg": msg}]}

    def _page(self, items: list, params: dict, key: str, flat_total: bool = False):
        page, size = int(self._p(params, "p", 1)), int(self._p(params, "ps", 100))
        chunk = items[(page - 1) * size: page * size]
        body = {key: chunk, "paging": {"pageIndex": page, "pageSize": size, "total": len(items)}}
        if flat_total:
            body.update({"total": len(items), "p": page, "ps": size})
        return 200, body

    # -------------------------------------------------------------- system
    def h_api_system_status(self, params):
        return 200, {"id": "fake", "version": "26.10.0.0", "status": "UP"}

    def h_api_server_version(self, params):
        return 200, "26.10.0.133078"

    def h_api_system_health(self, params):
        return 200, {"health": "GREEN"}

    def h_api_system_info(self, params):
        return 200, {"Database": {"Database": "PostgreSQL", "Database Version": "17.2"}}

    def h_api_plugins_installed(self, params):
        return 200, {"plugins": [{"key": "python", "name": "Python Code Quality and Security", "version": "5.0"}]}

    def h_api_plugins_available(self, params):
        return 200, {"plugins": []}

    def h_api_languages_list(self, params):
        return 200, {"languages": [{"key": "py", "name": "Python"}, {"key": "java", "name": "Java"}, {"key": "js", "name": "JavaScript"}]}

    # ------------------------------------------------------------ projects
    def h_api_projects_create(self, params):
        key, name = self._p(params, "project"), self._p(params, "name")
        if not key or not name:
            return self._error(400, "project and name are required")
        if key in self.projects:
            return self._error(400, f"Could not create Project, key already exists: {key}")
        self.projects[key] = name
        return 200, {"project": {"key": key, "name": name}}

    def h_api_projects_search(self, params):
        q = (self._p(params, "q") or "").lower()
        items = [{"key": k, "name": n} for k, n in self.projects.items() if q in k.lower()]
        return self._page(items, params, "components")

    def h_api_projects_delete(self, params):
        self.projects.pop(self._p(params, "project"), None)
        return 204, ""

    def h_api_project_branches_list(self, params):
        return 200, {"branches": [{"name": "main", "isMain": True, "type": "LONG"}]}

    def h_api_project_analyses_search(self, params):
        return self._page([{"key": "A1", "date": "2026-11-01"}], params, "analyses")

    # -------------------------------------------------------- quality gates
    def h_api_qualitygates_create(self, params):
        name = self._p(params, "name")
        if name in self.gates:
            return self._error(400, "Name has already been taken")
        self.gates[name] = []
        return 200, {"name": name}

    def h_api_qualitygates_create_condition(self, params):
        gate = self._p(params, "gateName")
        if gate not in self.gates:
            return self._error(404, "Quality gate not found")
        self.gates[gate].append({"metric": self._p(params, "metric"), "op": self._p(params, "op"), "error": self._p(params, "error")})
        return 200, {"id": str(len(self.gates[gate]))}

    def h_api_qualitygates_list(self, params):
        return 200, {"qualitygates": [{"name": n, "isDefault": n == self.default_gate} for n in self.gates]}

    def h_api_qualitygates_show(self, params):
        name = self._p(params, "name")
        if name not in self.gates:
            return self._error(404, "Quality gate not found")
        return 200, {"name": name, "conditions": self.gates[name]}

    def h_api_qualitygates_select(self, params):
        self.project_gate[self._p(params, "projectKey")] = self._p(params, "gateName")
        return 204, ""

    def h_api_qualitygates_set_as_default(self, params):
        self.default_gate = self._p(params, "name")
        return 204, ""

    def h_api_qualitygates_deselect(self, params):
        self.project_gate.pop(self._p(params, "projectKey"), None)
        return 204, ""

    def h_api_qualitygates_destroy(self, params):
        self.gates.pop(self._p(params, "name"), None)
        return 204, ""

    def h_api_qualitygates_copy(self, params):
        self.gates[self._p(params, "name")] = list(self.gates[self._p(params, "sourceName")])
        return 204, ""

    def h_api_qualitygates_project_status(self, params):
        project = self._p(params, "projectKey") or self.analysis_project.get(self._p(params, "analysisId"))
        if project not in self.measures:
            return self._error(404, "Project not found")
        measures = self.measures[project]
        conditions, failed = [], False
        for cond in self.gates[self.project_gate.get(project, self.default_gate)]:
            if cond["metric"] not in measures:
                continue
            actual, limit = float(measures[cond["metric"]]), float(cond["error"])
            bad = actual > limit if cond["op"] == "GT" else actual < limit
            failed = failed or bad
            conditions.append({"status": "ERROR" if bad else "OK", "metricKey": cond["metric"], "comparator": cond["op"], "errorThreshold": cond["error"], "actualValue": measures[cond["metric"]]})
        return 200, {"projectStatus": {"status": "ERROR" if failed else "OK", "conditions": conditions}}

    # ------------------------------------------------------ quality profiles
    def h_api_qualityprofiles_search(self, params):
        lang = self._p(params, "language")
        return 200, {"profiles": [p for p in self.profiles if not lang or p["language"] == lang]}

    def h_api_qualityprofiles_create(self, params):
        profile = {"key": "new-" + self._p(params, "name"), "name": self._p(params, "name"), "language": self._p(params, "language"), "isBuiltIn": False}
        self.profiles.append(profile)
        self.active_rules[profile["key"]] = set()
        return 200, {"profile": profile}

    def h_api_qualityprofiles_copy(self, params):
        source = self._p(params, "fromKey")
        new = {"key": "copy-" + self._p(params, "toName"), "name": self._p(params, "toName"), "language": "py", "isBuiltIn": False}
        self.profiles.append(new)
        self.active_rules[new["key"]] = set(self.active_rules[source])
        return 200, new

    def h_api_qualityprofiles_activate_rule(self, params):
        self.active_rules[self._p(params, "key")].add(self._p(params, "rule"))
        return 204, ""

    def h_api_qualityprofiles_deactivate_rule(self, params):
        self.active_rules[self._p(params, "key")].discard(self._p(params, "rule"))
        return 204, ""

    def h_api_qualityprofiles_delete(self, params):
        name = self._p(params, "qualityProfile")
        self.profiles = [p for p in self.profiles if p["name"] != name]
        return 204, ""

    def h_api_qualityprofiles_add_project(self, params):
        self.profile_projects[(self._p(params, "language"), self._p(params, "project"))] = self._p(params, "qualityProfile")
        return 204, ""

    def h_api_qualityprofiles_set_default(self, params):
        return 204, ""

    def h_api_qualityprofiles_backup(self, params):
        return 200, "<?xml version='1.0'?><profile><name>" + self._p(params, "qualityProfile") + "</name></profile>"

    def h_api_rules_search(self, params):
        profile = self._p(params, "qprofile")
        total = len(self.active_rules.get(profile, set()))
        return 200, {"total": total, "p": 1, "ps": 1, "rules": []}

    # --------------------------------------------------------------- issues
    def h_api_issues_search(self, params):
        items = list(self.issues)
        for field, key in (("types", "type"), ("severities", "severity"), ("statuses", "status")):
            wanted = self._p(params, field)
            if wanted:
                items = [i for i in items if i[key] in wanted.split(",")]
        status, body = self._page(items, params, "issues", flat_total=True)
        facet = self._p(params, "facets")
        if facet:
            field = {"severities": "severity", "types": "type"}[facet]
            counts: dict[str, int] = {}
            for i in items:
                counts[i[field]] = counts.get(i[field], 0) + 1
            body["facets"] = [{"property": facet, "values": [{"val": k, "count": v} for k, v in counts.items()]}]
        return status, body

    def _issue(self, params):
        return next((i for i in self.issues if i["key"] == self._p(params, "issue")), None)

    def h_api_issues_do_transition(self, params):
        issue = self._issue(params)
        if issue is None:
            return self._error(404, "Issue not found")
        issue["status"] = {"confirm": "CONFIRMED", "falsepositive": "RESOLVED", "accept": "RESOLVED", "reopen": "REOPENED"}.get(self._p(params, "transition"), issue["status"])
        return 200, {"issue": issue}

    def h_api_issues_assign(self, params):
        issue = self._issue(params)
        issue["assignee"] = self._p(params, "assignee")
        return 200, {"issue": issue}

    def h_api_issues_add_comment(self, params):
        issue = self._issue(params)
        issue.setdefault("comments", []).append(self._p(params, "text"))
        return 200, {"issue": issue}

    def h_api_issues_set_tags(self, params):
        issue = self._issue(params)
        issue["tags"] = (self._p(params, "tags") or "").split(",")
        return 200, {"issue": issue}

    # ------------------------------------------------------------- measures
    def h_api_measures_component(self, params):
        component = self._p(params, "component")
        if component not in self.measures:
            return self._error(404, f"Component '{component}' not found")
        wanted = self._p(params, "metricKeys", "").split(",")
        unknown = [m for m in wanted if m not in self.known_metrics]
        if unknown:
            return self._error(400, "The following metric keys are not found: " + ", ".join(unknown))
        items = [{"metric": m, "value": v} for m, v in self.measures[component].items() if m in wanted]
        return 200, {"component": {"key": component, "measures": items}}

    def h_api_metrics_search(self, params):
        return self._page([{"key": k} for k in self.known_metrics], params, "metrics")

    def h_api_measures_search_history(self, params):
        data = self.history.get(self._p(params, "component"), {})
        items = [{"metric": m, "history": data.get(m, [])} for m in self._p(params, "metrics", "").split(",")]
        return self._page(items, params, "measures")

    # ------------------------------------------------------------- hotspots
    def h_api_hotspots_search(self, params):
        return self._page(self.hotspots, params, "hotspots")

    def h_api_hotspots_change_status(self, params):
        for h in self.hotspots:
            if h["key"] == self._p(params, "hotspot"):
                h["status"], h["resolution"] = self._p(params, "status"), self._p(params, "resolution")
        return 204, ""

    # ------------------------------------------------------------- webhooks
    def h_api_webhooks_create(self, params):
        key = f"wh{len(self.webhooks) + 1}"
        self.webhooks[key] = {"key": key, "name": self._p(params, "name"), "url": self._p(params, "url"), "hasSecret": bool(self._p(params, "secret"))}
        return 200, {"webhook": self.webhooks[key]}

    def h_api_webhooks_list(self, params):
        return 200, {"webhooks": list(self.webhooks.values())}

    def h_api_webhooks_delete(self, params):
        self.webhooks.pop(self._p(params, "webhook"), None)
        return 204, ""

    def h_api_webhooks_deliveries(self, params):
        return 200, {"deliveries": [{"id": "d1", "success": True}]}

    # ------------------------------------------------------------------- ce
    def h_api_ce_task(self, params):
        task_id = self._p(params, "id")
        states = self.ce_tasks.get(task_id)
        if not states:
            return self._error(404, "Task not found")
        status = states.pop(0) if len(states) > 1 else states[0]
        task = {"id": task_id, "status": status, "analysisId": "AN-" + task_id}
        if status == "FAILED":
            task["errorMessage"] = "boom"
        return 200, {"task": task}

    # ---------------------------------------------------------------- admin
    def h_api_users_create(self, params):
        login = self._p(params, "login")
        self.users[login] = {"login": login, "name": self._p(params, "name")}
        return 200, {"user": self.users[login]}

    def h_api_users_deactivate(self, params):
        self.users.pop(self._p(params, "login"), None)
        return 200, {"user": {}}

    def h_api_user_groups_create(self, params):
        self.groups[self._p(params, "name")] = {"name": self._p(params, "name"), "members": []}
        return 200, {"group": {"name": self._p(params, "name")}}

    def h_api_user_groups_add_user(self, params):
        self.groups[self._p(params, "name")]["members"].append(self._p(params, "login"))
        return 204, ""

    def h_api_permissions_add_user(self, params):
        self.permissions.append(("user", self._p(params, "login"), self._p(params, "permission"), self._p(params, "projectKey")))
        return 204, ""

    def h_api_permissions_add_group(self, params):
        self.permissions.append(("group", self._p(params, "groupName"), self._p(params, "permission"), self._p(params, "projectKey")))
        return 204, ""

    def h_api_user_tokens_generate(self, params):
        name = self._p(params, "name")
        self.tokens[name] = "sqp_" + name
        return 200, {"name": name, "token": self.tokens[name], "type": self._p(params, "type")}

    def h_api_user_tokens_revoke(self, params):
        self.tokens.pop(self._p(params, "name"), None)
        return 204, ""

    def h_api_settings_set(self, params):
        key, comp = self._p(params, "key"), self._p(params, "component")
        self.settings[(key, comp)] = {"key": key, "values": params.get("values"), "value": self._p(params, "value")}
        return 204, ""

    def h_api_settings_values(self, params):
        found = self.settings.get((self._p(params, "keys"), self._p(params, "component")))
        return 200, {"settings": [found] if found else []}

    def h_api_settings_reset(self, params):
        self.settings.pop((self._p(params, "keys"), self._p(params, "component")), None)
        return 204, ""

    def h_api_new_code_periods_set(self, params):
        self.new_code[self._p(params, "project")] = (self._p(params, "type"), self._p(params, "value"))
        return 204, ""

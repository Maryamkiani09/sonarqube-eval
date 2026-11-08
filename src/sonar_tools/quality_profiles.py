"""Quality profiles and rules: activate / deactivate / severity (Person 2)."""
from __future__ import annotations

from .client import SonarClient


def list_profiles(client: SonarClient, language: str | None = None, defaults: bool = False) -> list[dict]:
    return client.get("api/qualityprofiles/search", language=language, defaults=defaults).get("profiles", [])


def find_profile(client: SonarClient, language: str, name: str) -> dict | None:
    return next((p for p in list_profiles(client, language) if p["name"] == name), None)


def create_profile(client: SonarClient, language: str, name: str) -> dict:
    return client.post("api/qualityprofiles/create", language=language, name=name)["profile"]


def delete_profile(client: SonarClient, language: str, name: str) -> None:
    client.post("api/qualityprofiles/delete", language=language, qualityProfile=name)


def copy_profile(client: SonarClient, from_key: str, new_name: str) -> dict:
    """Copy (e.g. the built-in 'Sonar way', which is read-only) into an editable profile."""
    return client.post("api/qualityprofiles/copy", fromKey=from_key, toName=new_name)


def activate_rule(client: SonarClient, profile_key: str, rule_key: str, severity: str | None = None) -> None:
    """Activate a rule such as 'python:S1481'; ``severity`` overrides the default."""
    client.post("api/qualityprofiles/activate_rule", key=profile_key, rule=rule_key, severity=severity)


def deactivate_rule(client: SonarClient, profile_key: str, rule_key: str) -> None:
    client.post("api/qualityprofiles/deactivate_rule", key=profile_key, rule=rule_key)


def associate_project(client: SonarClient, language: str, profile_name: str, project: str) -> None:
    client.post("api/qualityprofiles/add_project", language=language, qualityProfile=profile_name, project=project)


def set_default(client: SonarClient, language: str, profile_name: str) -> None:
    client.post("api/qualityprofiles/set_default", language=language, qualityProfile=profile_name)


def active_rule_count(client: SonarClient, profile_key: str) -> int:
    body = client.get("api/rules/search", qprofile=profile_key, activation=True, ps=1)
    return int(body.get("total", 0))


def search_rules(client: SonarClient, language: str, **filters) -> list[dict]:
    return list(client.paginate("api/rules/search", "rules", languages=language, **filters))


def backup(client: SonarClient, language: str, name: str) -> str:
    """Profile as XML, e.g. to version-control it or import it elsewhere."""
    return client.get_text("api/qualityprofiles/backup", language=language, qualityProfile=name)


def diff_rule_sets(a: set[str], b: set[str]) -> dict[str, list[str]]:
    """Compare two profiles' active rule keys (pure helper)."""
    return {"only_a": sorted(a - b), "only_b": sorted(b - a), "common": sorted(a & b)}

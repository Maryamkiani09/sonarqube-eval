"""Users, groups, permissions, tokens and settings (Persons 4, 5, 6)."""
from __future__ import annotations

from .client import SonarClient


# ------------------------------------------------------------------ users
def create_user(client: SonarClient, login: str, name: str, password: str, email: str | None = None) -> dict:
    return client.post("api/users/create", login=login, name=name, password=password, email=email)["user"]


def deactivate_user(client: SonarClient, login: str) -> None:
    client.post("api/users/deactivate", login=login)


def create_group(client: SonarClient, name: str, description: str | None = None) -> dict:
    return client.post("api/user_groups/create", name=name, description=description)["group"]


def add_user_to_group(client: SonarClient, group: str, login: str) -> None:
    client.post("api/user_groups/add_user", name=group, login=login)


def grant_permission(client: SonarClient, permission: str, project: str | None = None, login: str | None = None, group: str | None = None) -> None:
    """permission: admin | codeviewer | issueadmin | securityhotspotadmin | scan | user"""
    if bool(login) == bool(group):
        raise ValueError("give exactly one of login / group")
    endpoint = "api/permissions/add_user" if login else "api/permissions/add_group"
    client.post(endpoint, permission=permission, projectKey=project, login=login, groupName=group)


# ----------------------------------------------------------------- tokens
def generate_token(client: SonarClient, name: str, token_type: str = "PROJECT_ANALYSIS_TOKEN", project: str | None = None) -> str:
    """USER_TOKEN | GLOBAL_ANALYSIS_TOKEN | PROJECT_ANALYSIS_TOKEN (needs ``project``)."""
    return client.post("api/user_tokens/generate", name=name, type=token_type, projectKey=project)["token"]


def revoke_token(client: SonarClient, name: str) -> None:
    client.post("api/user_tokens/revoke", name=name)


# --------------------------------------------------------------- settings
def set_setting(client: SonarClient, key: str, value: str | list[str], project: str | None = None) -> None:
    field = "values" if isinstance(value, list) else "value"
    client.post("api/settings/set", key=key, component=project, **{field: value})


def get_setting(client: SonarClient, key: str, project: str | None = None) -> dict | None:
    settings = client.get("api/settings/values", keys=key, component=project).get("settings", [])
    return settings[0] if settings else None


def reset_setting(client: SonarClient, key: str, project: str | None = None) -> None:
    client.post("api/settings/reset", keys=key, component=project)


def set_exclusions(client: SonarClient, project: str, patterns: list[str]) -> None:
    """Analysis-scope exclusions, e.g. ['**/generated/**']."""
    set_setting(client, "sonar.exclusions", patterns, project)


def set_new_code_period(client: SonarClient, project: str, kind: str = "PREVIOUS_VERSION", value: str | None = None) -> None:
    """kind: PREVIOUS_VERSION | NUMBER_OF_DAYS | SPECIFIC_ANALYSIS (REFERENCE_BRANCH needs branches)."""
    client.post("api/new_code_periods/set", project=project, type=kind, value=value)

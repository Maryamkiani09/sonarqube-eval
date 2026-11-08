"""Project and branch management - multi-project support (Person 5)."""
from __future__ import annotations

from .client import SonarClient


def create_project(client: SonarClient, key: str, name: str | None = None, visibility: str = "private") -> dict:
    return client.post("api/projects/create", project=key, name=name or key, visibility=visibility)["project"]


def delete_project(client: SonarClient, key: str) -> None:
    client.post("api/projects/delete", project=key)


def list_projects(client: SonarClient, query: str | None = None) -> list[dict]:
    return list(client.paginate("api/projects/search", "components", q=query))


def project_exists(client: SonarClient, key: str) -> bool:
    return any(p["key"] == key for p in list_projects(client, key))


def ensure_project(client: SonarClient, key: str, name: str | None = None) -> dict:
    """Create the project unless it already exists."""
    if project_exists(client, key):
        return {"key": key, "name": name or key, "created": False}
    created = create_project(client, key, name)
    created["created"] = True
    return created


def create_many(client: SonarClient, specs: list[tuple[str, str]]) -> list[str]:
    """Create several projects in one instance; returns the keys that were new."""
    new_keys = []
    for key, name in specs:
        if ensure_project(client, key, name).get("created"):
            new_keys.append(key)
    return new_keys


def list_branches(client: SonarClient, project: str) -> list[dict]:
    """Community Build analyses the MAIN branch only: expect exactly one entry."""
    return client.get("api/project_branches/list", project=project).get("branches", [])


def analyses(client: SonarClient, project: str) -> list[dict]:
    return list(client.paginate("api/project_analyses/search", "analyses", project=project))

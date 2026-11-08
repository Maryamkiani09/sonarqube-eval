"""Server, database, plugin and language information (Person 6)."""
from __future__ import annotations

import time
from typing import Callable

from .client import SonarApiError, SonarClient


def server_version(client: SonarClient) -> str:
    return client.get_text("api/server/version").strip()


def status(client: SonarClient) -> dict:
    """{'id': ..., 'version': ..., 'status': 'UP'|'STARTING'|'DB_MIGRATION_NEEDED'...}"""
    return client.get("api/system/status")


def health(client: SonarClient) -> str:
    """GREEN / YELLOW / RED (requires admin or system passcode)."""
    return client.get("api/system/health").get("health", "UNKNOWN")


def wait_until_up(
    client: SonarClient,
    timeout: float = 300,
    interval: float = 5,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> dict:
    """Poll /api/system/status until the server reports UP."""
    deadline = now() + timeout
    last = "no response"
    while now() < deadline:
        try:
            info = status(client)
            last = info.get("status", "?")
            if last == "UP":
                return info
        except Exception as exc:  # server still booting
            last = type(exc).__name__
        sleep(interval)
    raise TimeoutError(f"SonarQube not UP after {timeout}s (last: {last})")


def database_info(client: SonarClient) -> dict:
    """Which database engine the instance runs on (admin only)."""
    db = client.get("api/system/info").get("Database", {})
    return {"vendor": db.get("Database"), "version": db.get("Database Version")}


def installed_plugins(client: SonarClient) -> list[dict]:
    return client.get("api/plugins/installed").get("plugins", [])


def available_plugins(client: SonarClient) -> list[dict]:
    """Marketplace plugins (requires the update center to be reachable)."""
    try:
        return client.get("api/plugins/available").get("plugins", [])
    except SonarApiError:
        return []


def supported_languages(client: SonarClient) -> list[dict]:
    return client.get("api/languages/list").get("languages", [])

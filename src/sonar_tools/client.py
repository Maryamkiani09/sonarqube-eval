"""Minimal SonarQube Web API client (token auth, pagination, error handling)."""
from __future__ import annotations

import os
from typing import Any, Iterator

import requests


class SonarApiError(Exception):
    """Raised for any HTTP status >= 400 returned by the server."""

    def __init__(self, status: int, message: str, url: str = "") -> None:
        super().__init__(f"HTTP {status} from {url}: {message}")
        self.status = status
        self.message = message
        self.url = url


def _clean(params: dict[str, Any] | None) -> dict[str, Any]:
    """Drop None values and turn bools into 'true'/'false' as SonarQube expects."""
    cleaned: dict[str, Any] = {}
    for key, value in (params or {}).items():
        if value is None:
            continue
        cleaned[key] = str(value).lower() if isinstance(value, bool) else value
    return cleaned


class SonarClient:
    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        if token:
            # SonarQube tokens are sent as the basic-auth user name, empty password.
            self.session.auth = (token, "")

    @classmethod
    def from_env(cls) -> "SonarClient":
        url = os.environ.get("SONAR_URL") or os.environ.get("SONAR_HOST_URL") or "http://localhost:9000"
        return cls(url, os.environ.get("SONAR_TOKEN"))

    # ------------------------------------------------------------------ core
    def _request(self, method: str, path: str, params=None, data=None) -> requests.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        response = self.session.request(
            method, url, params=_clean(params), data=_clean(data), timeout=self.timeout
        )
        if response.status_code >= 400:
            raise SonarApiError(response.status_code, self._error_message(response), url)
        return response

    @staticmethod
    def _error_message(response: requests.Response) -> str:
        try:
            errors = response.json().get("errors", [])
            if errors:
                return "; ".join(e.get("msg", "") for e in errors)
        except ValueError:
            pass
        return response.text.strip()[:200] or response.reason or "error"

    def get(self, path: str, **params: Any) -> dict:
        response = self._request("GET", path, params=params)
        return response.json() if response.content else {}

    def post(self, path: str, **data: Any) -> dict:
        response = self._request("POST", path, data=data)
        return response.json() if response.content else {}

    def get_text(self, path: str, **params: Any) -> str:
        return self._request("GET", path, params=params).text

    def paginate(
        self, path: str, key: str, page_size: int = 100, max_items: int = 10000, **params: Any
    ) -> Iterator[dict]:
        """Yield every item of a paged endpoint (SonarQube caps results at 10,000)."""
        page, seen = 1, 0
        while seen < max_items:
            body = self.get(path, p=page, ps=page_size, **params)
            items = body.get(key, [])
            for item in items:
                yield item
                seen += 1
                if seen >= max_items:
                    return
            total = body.get("paging", {}).get("total", body.get("total", seen))
            if not items or seen >= total:
                return
            page += 1

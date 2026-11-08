"""Webhooks: register them, receive them, verify the HMAC signature (Persons 5 and 6).

SonarQube POSTs a JSON payload when a background task finishes and signs the
body with HMAC-SHA256 using the webhook secret (header
``X-Sonar-Webhook-HMAC-SHA256``).
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .client import SonarClient

SIGNATURE_HEADER = "X-Sonar-Webhook-HMAC-SHA256"


def create(client: SonarClient, name: str, url: str, secret: str | None = None, project: str | None = None) -> dict:
    return client.post("api/webhooks/create", name=name, url=url, secret=secret, project=project)["webhook"]


def list_webhooks(client: SonarClient, project: str | None = None) -> list[dict]:
    return client.get("api/webhooks/list", project=project).get("webhooks", [])


def delete(client: SonarClient, key: str) -> None:
    client.post("api/webhooks/delete", webhook=key)


def deliveries(client: SonarClient, webhook: str) -> list[dict]:
    return client.get("api/webhooks/deliveries", webhook=webhook).get("deliveries", [])


def sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify_signature(body: bytes, secret: str, header_value: str | None) -> bool:
    if not header_value:
        return False
    return hmac.compare_digest(sign(body, secret), header_value.strip().lower())


@dataclass
class WebhookEvent:
    project_key: str
    task_status: str
    gate_name: str | None
    gate_status: str | None
    branch: str | None
    failed_conditions: list[dict] = field(default_factory=list)


def parse_payload(payload: dict) -> WebhookEvent:
    gate = payload.get("qualityGate") or {}
    failed = [c for c in gate.get("conditions", []) if c.get("status") == "ERROR"]
    return WebhookEvent(
        project_key=payload.get("project", {}).get("key", ""),
        task_status=payload.get("status", ""),
        gate_name=gate.get("name"),
        gate_status=gate.get("status"),
        branch=(payload.get("branch") or {}).get("name"),
        failed_conditions=failed,
    )


class WebhookReceiver:
    """Tiny HTTP server that stores verified webhook events (for demos/tests)."""

    def __init__(self, secret: str | None = None, host: str = "127.0.0.1", port: int = 0) -> None:
        self.secret = secret
        self.events: list[WebhookEvent] = []
        self.rejected = 0
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802 - http.server API
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                if receiver.secret and not verify_signature(body, receiver.secret, self.headers.get(SIGNATURE_HEADER)):
                    receiver.rejected += 1
                    self.send_response(401)
                    self.end_headers()
                    return
                receiver.events.append(parse_payload(json.loads(body)))
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):  # silence request logging
                pass

        self._server = ThreadingHTTPServer((host, port), Handler)
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}/"

    def start(self) -> "WebhookReceiver":
        self._thread = threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        if self._thread:
            self._thread.join(timeout=5)


def main(argv=None) -> None:  # pragma: no cover - manual demo entry point
    parser = argparse.ArgumentParser(description="Run a SonarQube webhook receiver")
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--secret")
    args = parser.parse_args(argv)
    receiver = WebhookReceiver(args.secret, host="0.0.0.0", port=args.port).start()
    print(f"Listening on {receiver.url} - register it in Administration > Webhooks")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        receiver.stop()


if __name__ == "__main__":  # pragma: no cover
    main()

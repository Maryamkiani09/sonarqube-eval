"""Shared fixtures. Unit tests use FakeSonar; integration tests need a live server."""
from __future__ import annotations

import os

import pytest

from fake_sonar import FakeSonar
from sonar_tools import system
from sonar_tools.client import SonarClient


# ------------------------------------------------------------ unit tests
@pytest.fixture
def fake():
    server = FakeSonar().start()
    server.measures["shopflow"] = {
        "coverage": "41.2", "bugs": "9", "vulnerabilities": "5", "code_smells": "44",
        "ncloc": "700", "duplicated_lines_density": "11.3", "reliability_rating": "3.0",
        "security_rating": "5.0", "sqale_rating": "1.0", "alert_status": "ERROR", "complexity": "120",
    }
    server.projects["shopflow"] = "ShopFlow"
    yield server
    server.stop()


@pytest.fixture
def client(fake):
    return SonarClient(fake.url)


# ----------------------------------------------------- integration tests
@pytest.fixture(scope="session")
def live() -> SonarClient:
    """Client for the real server named by SONAR_URL / SONAR_TOKEN (admin token)."""
    c = SonarClient.from_env()
    system.wait_until_up(c, timeout=60)
    return c


@pytest.fixture(scope="session")
def project_key() -> str:
    """Project that has already been analysed with sonar-scanner (see README step 5)."""
    return os.environ.get("SONAR_PROJECT_KEY", "shopflow-eval")


def pytest_collection_modifyitems(config, items):
    """Skip tests marked 'integration' unless a live SonarQube token is configured."""
    if os.environ.get("SONAR_TOKEN"):
        return
    skip = pytest.mark.skip(reason="needs a live SonarQube: set SONAR_URL and SONAR_TOKEN")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)

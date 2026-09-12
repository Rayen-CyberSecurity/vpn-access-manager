"""Shared fixtures.

init.sql is replayed before EVERY test, so the suite is order-independent and
the seed state (gw-eu-1 full, gw-us-1 empty) is guaranteed each time. That is
what lets the capacity tests assume a full gateway without setting one up.
"""

import os
import pathlib

# Tests run on the host machine, outside the Docker Compose network.
# Therefore PostgreSQL is reached through localhost instead of the Docker
# service hostname "db".
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://vpnadmin:vpnpass123@localhost:5432/vpnmanager",
)

import psycopg
import pytest
from fastapi.testclient import TestClient

from api.config import settings
from api.main import app

INIT_SQL = pathlib.Path(__file__).resolve().parents[1] / "db" / "init.sql"


@pytest.fixture(autouse=True)
def reset_db():
    # init.sql begins with DROP TABLE IF EXISTS ... CASCADE, so replaying it
    # is a full reset. autocommit because it contains DDL.
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        conn.execute(INIT_SQL.read_text())
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth():
    return {"X-API-Key": settings.api_key}

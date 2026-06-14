import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """App instance with the password gate enabled."""
    monkeypatch.setenv("APP_PASSWORD", "letmein")
    # Re-import config and dependents so the env var is picked up.
    import app.config

    importlib.reload(app.config)
    import app.security

    importlib.reload(app.security)
    import app.main

    importlib.reload(app.main)
    return TestClient(app.main.app)


def test_health_is_open(client):
    assert client.get("/api/health").status_code == 200


def test_gated_without_password(client):
    assert client.get("/api/games").status_code == 401
    assert client.get("/api/chesscom/foo/recent").status_code == 401


def test_gated_with_wrong_password(client):
    assert client.get("/api/games", headers={"X-App-Password": "wrong"}).status_code == 401


def test_gated_with_correct_password(client):
    r = client.get("/api/games", headers={"X-App-Password": "letmein"})
    assert r.status_code == 200

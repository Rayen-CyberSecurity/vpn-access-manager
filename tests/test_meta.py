
"""Tests for API metadata and route scope."""


def test_openapi_title(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "VPN Access Manager"
    assert response.json()["info"]["version"] == "0.1.0"


def test_exact_project_routes(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = set(response.json()["paths"])

    assert paths == {
        "/gateways",
        "/sessions",
        "/sessions/{session_id}",
        "/sessions/{session_id}/close",
    }


def test_exact_five_operations(client):
    response = client.get("/openapi.json")
    paths = response.json()["paths"]

    operations = {
        (method.upper(), path)
        for path, methods in paths.items()
        for method in methods
        if method.lower() in {"get", "post", "put", "patch", "delete"}
    }

    assert operations == {
        ("GET", "/gateways"),
        ("GET", "/sessions"),
        ("GET", "/sessions/{session_id}"),
        ("POST", "/sessions"),
        ("POST", "/sessions/{session_id}/close"),
    }

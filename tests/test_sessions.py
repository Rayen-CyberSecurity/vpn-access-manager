def test_list_all_sessions(client):
    r = client.get("/sessions")
    assert r.status_code == 200
    assert len(r.json()) == 7


def test_filter_by_status(client):
    rows = client.get("/sessions?status=active").json()
    assert len(rows) == 4
    assert all(s["status"] == "active" for s in rows)


def test_filter_by_gateway(client):
    rows = client.get("/sessions?gateway=gw-eu-1").json()
    assert all(s["gateway_name"] == "gw-eu-1" for s in rows)


def test_filter_by_user(client):
    rows = client.get("/sessions?user=amuller").json()
    assert all(s["username"] == "amuller" for s in rows)


def test_get_single_session(client):
    r = client.get("/sessions/1")
    assert r.status_code == 200
    assert r.json()["id"] == 1


def test_client_ip_has_no_netmask(client):
    """inet carries a /32 that IPv4Address rejects; host() strips it."""
    assert "/" not in client.get("/sessions/1").json()["client_ip"]


def test_get_unknown_session_is_404(client):
    assert client.get("/sessions/9999").status_code == 404


def test_open_session_returns_201_and_body(client, auth):
    r = client.post(
        "/sessions",
        json={"user_id": 8, "gateway_id": 2, "client_ip": "192.168.20.99"},
        headers=auth,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "active"
    assert body["gateway_name"] == "gw-eu-2"
    assert body["disconnected_at"] is None
    assert body["bytes_transferred"] == 0


def test_open_increments_the_gateway_count(client, auth):
    client.post(
        "/sessions",
        json={"user_id": 8, "gateway_id": 2, "client_ip": "192.168.20.99"},
        headers=auth,
    )
    g = {r["name"]: r for r in client.get("/gateways").json()}
    assert g["gw-eu-2"]["active_sessions"] == 2


def test_open_on_unknown_gateway_is_404(client, auth):
    r = client.post(
        "/sessions",
        json={"user_id": 1, "gateway_id": 99, "client_ip": "10.0.0.1"},
        headers=auth,
    )
    assert r.status_code == 404


def test_open_for_unknown_user_is_404(client, auth):
    r = client.post(
        "/sessions",
        json={"user_id": 999, "gateway_id": 3, "client_ip": "10.0.0.1"},
        headers=auth,
    )
    assert r.status_code == 404


def test_malformed_ip_is_422(client, auth):
    r = client.post(
        "/sessions",
        json={"user_id": 1, "gateway_id": 3, "client_ip": "not-an-ip"},
        headers=auth,
    )
    assert r.status_code == 422


def test_negative_bytes_is_422(client, auth):
    r = client.post(
        "/sessions/4/close", json={"bytes_transferred": -1}, headers=auth
    )
    assert r.status_code == 422


def test_duplicate_active_session_is_409(client, auth):
    """User 1 already holds an active session on gw-eu-1 (session_one_active)."""
    r = client.post(
        "/sessions",
        json={"user_id": 1, "gateway_id": 1, "client_ip": "10.0.0.1"},
        headers=auth,
    )
    assert r.status_code == 409


def test_close_sets_status_time_and_bytes(client, auth):
    r = client.post(
        "/sessions/4/close", json={"bytes_transferred": 5242880}, headers=auth
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "closed"
    assert body["disconnected_at"] is not None
    assert body["bytes_transferred"] == 5242880


def test_close_is_idempotent(client, auth):
    """Closing twice returns the identical record, byte count included."""
    first = client.post(
        "/sessions/4/close", json={"bytes_transferred": 5242880}, headers=auth
    ).json()
    second = client.post(
        "/sessions/4/close", json={"bytes_transferred": 999999}, headers=auth
    ).json()
    assert first == second


def test_close_unknown_session_is_404(client, auth):
    r = client.post(
        "/sessions/9999/close", json={"bytes_transferred": 0}, headers=auth
    )
    assert r.status_code == 404

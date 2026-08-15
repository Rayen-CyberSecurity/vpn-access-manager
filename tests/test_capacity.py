from concurrent.futures import ThreadPoolExecutor

FULL_GATEWAY = 1          # gw-eu-1, seeded at 3/3


def active_count(client, name):
    return {r["name"]: r for r in client.get("/gateways").json()}[name][
        "active_sessions"
    ]


def test_full_gateway_refuses_with_409(client, auth):
    r = client.post(
        "/sessions",
        json={"user_id": 7, "gateway_id": FULL_GATEWAY, "client_ip": "10.0.0.7"},
        headers=auth,
    )
    assert r.status_code == 409


def test_refusal_message_names_the_gateway_and_numbers(client, auth):
    r = client.post(
        "/sessions",
        json={"user_id": 7, "gateway_id": FULL_GATEWAY, "client_ip": "10.0.0.7"},
        headers=auth,
    )
    detail = r.json()["detail"]
    assert "gw-eu-1" in detail
    assert "3/3" in detail


def test_refusal_creates_no_row(client, auth):
    before = len(client.get("/sessions").json())
    client.post(
        "/sessions",
        json={"user_id": 7, "gateway_id": FULL_GATEWAY, "client_ip": "10.0.0.7"},
        headers=auth,
    )
    assert len(client.get("/sessions").json()) == before


def test_capacity_frees_up_after_a_close(client, auth):
    client.post("/sessions/1/close", json={"bytes_transferred": 100}, headers=auth)
    r = client.post(
        "/sessions",
        json={"user_id": 7, "gateway_id": FULL_GATEWAY, "client_ip": "10.0.0.7"},
        headers=auth,
    )
    assert r.status_code == 201
    assert active_count(client, "gw-eu-1") == 3


def test_concurrent_opens_never_exceed_capacity(client, auth):
    """One free slot, two simultaneous requests: exactly one may win.

    Without SELECT ... FOR UPDATE in open_session both transactions read the
    same count, both pass the check, and the gateway ends up at 4.
    """
    client.post("/sessions/1/close", json={"bytes_transferred": 100}, headers=auth)
    assert active_count(client, "gw-eu-1") == 2

    def attempt(user_id):
        return client.post(
            "/sessions",
            json={
                "user_id": user_id,
                "gateway_id": FULL_GATEWAY,
                "client_ip": f"10.0.0.{user_id}",
            },
            headers=auth,
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = sorted(pool.map(attempt, [6, 7]))

    assert codes == [201, 409]
    assert active_count(client, "gw-eu-1") == 3


def test_different_gateways_do_not_block_each_other(client, auth):
    def attempt(gateway_id):
        return client.post(
            "/sessions",
            json={
                "user_id": 8,
                "gateway_id": gateway_id,
                "client_ip": "10.0.1.8",
            },
            headers=auth,
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = sorted(pool.map(attempt, [2, 3]))

    assert codes == [201, 201]

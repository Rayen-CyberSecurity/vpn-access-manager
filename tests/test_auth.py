NEW = {"user_id": 8, "gateway_id": 2, "client_ip": "192.168.20.99"}


def test_reads_need_no_key(client):
    assert client.get("/gateways").status_code == 200
    assert client.get("/sessions").status_code == 200


def test_open_without_key_is_401(client):
    assert client.post("/sessions", json=NEW).status_code == 401


def test_open_with_wrong_key_is_401(client):
    r = client.post("/sessions", json=NEW, headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_close_without_key_is_401(client):
    r = client.post("/sessions/4/close", json={"bytes_transferred": 1})
    assert r.status_code == 401

def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_users_seeded(client):
    r = client.get("/users")
    assert r.status_code == 200
    assert len(r.json()) == 8


def test_users_carry_department_name(client):
    users = client.get("/users").json()
    assert {u["department"] for u in users} == {"Engineering", "Sales", "Support"}

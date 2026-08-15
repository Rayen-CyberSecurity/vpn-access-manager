def by_name(rows):
    return {r["name"]: r for r in rows}


def test_gateway_list_returns_all_three(client):
    r = client.get("/gateways")
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_active_counts_match_seed(client):
    g = by_name(client.get("/gateways").json())
    assert g["gw-eu-1"]["active_sessions"] == 3
    assert g["gw-eu-2"]["active_sessions"] == 1


def test_active_count_includes_empty_gateway(client):
    """gw-us-1 has zero active sessions and must still appear.

    This is the test that fails if LEFT JOIN is changed to JOIN.
    """
    g = by_name(client.get("/gateways").json())
    assert "gw-us-1" in g
    assert g["gw-us-1"]["active_sessions"] == 0


def test_gateways_sorted_by_name(client):
    names = [r["name"] for r in client.get("/gateways").json()]
    assert names == sorted(names)

import pytest
from fastapi.testclient import TestClient

from sentinel.data import seed_demo
from sentinel.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = tmp_path / "demo.sqlite"
    monkeypatch.setenv("SENTINEL_DB", str(path))
    seed_demo(path)
    with TestClient(app) as api:
        yield api


@pytest.mark.parametrize(("field", "count"), [("creator", 19), ("offer", 99), ("link", 0)])
def test_related_twin_orders_share_the_selected_record(client, field, count):
    base = "/api/orders/"
    original = client.get(base + "sim-00176").json()
    result = client.get(base + "sim-00176/related", params={"field": field}).json()
    assert result["value"] == original["attribution"][field]
    rows = result["orders"]
    assert len(rows) == len({row["order"] for row in rows}) == count
    assert [row["date"] for row in rows] == sorted((row["date"] for row in rows), reverse=True)
    for row in rows:
        assert row["order"] != original["order_id"]
        other = client.get(base + row["order"]).json()
        assert other["attribution"][field] == result["value"]
        assert row["date"] == other["events"][0]["occurred_at_utc"][:10]


def test_reference_cases_and_missing_attribution(client):
    base = "/api/orders/"
    result = client.get(base + "lab-comissao-normal/related").json()
    ids = {row["order"] for row in result["orders"]}
    assert "lab-atribuicao-divergente" in ids
    assert all(order.startswith("lab-") for order in ids)
    assert "lab-comissao-normal" not in ids
    for order in ("demo-order-1", "lab-venda"):
        assert client.get(base + order + "/related").json() == {"value": None, "orders": []}
    assert client.get(base + "sim-10000/related").status_code == 404
    assert client.get(base + "sim-00176/related?field=invalid").status_code == 422

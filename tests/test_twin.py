from fastapi.testclient import TestClient
from sentinel.main import app
from sentinel import twin


def test_population():
    creators, products, dates = set(), set(), set()
    for i in range(twin.SIZE):
        events, journey, expiry = twin.fixture(i)
        creators.add(journey.creator)
        products.add(journey.product)
        dates.add(events[0]["occurred_at_utc"][:10])
    assert (len(creators), len(products), len(dates)) == (500, 100, 90)
    assert sum(twin.summary()["counts"].values()) == 10000


def test_plan_and_creator_scope(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DB", str(tmp_path / "lab.sqlite"))
    monkeypatch.delenv("SENTINEL_LOCAL_AI", raising=False)
    with TestClient(app) as api:
        run = api.post("/api/twin/plan").json()
        assert any(len(row["signals"]) > 1 for row in run["cases"])
        assert any(row["expected"] != row["baseline"] for row in run["cases"])
        rows = api.get("/api/twin/creators/500").json()
        assert len(rows) == 20
        for row in rows:
            detail = api.get("/api/orders/" + row["order"]).json()
            assert detail["attribution"]["creator"] == "creator-500"
        assert api.get("/api/twin/creators/501").status_code == 422
        assert api.get("/api/orders/sim-10000").status_code == 404


def test_approval_replay(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DB", str(tmp_path / "lab.sqlite"))
    with TestClient(app) as api:
        url = "/api/twin/proposals"
        before = api.get(url).json()
        assert len(before["checks"]) == 2
        assert before["replay"] is None
        assert before["baseline"]["fn"] > 0
        body = dict(revision=before["revision"], reviewer="Teste", note="Experimento", decision="confirmado")
        after = api.post(url + "/review", json=body).json()
        assert after["replay"]["fn"] == after["replay"]["fp"] == 0
        assert api.post(url + "/review", json=body).json() == after
        assert api.post(url + "/review", json=dict(body, decision="descartado")).status_code == 409


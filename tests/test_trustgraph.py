import sqlite3
import io
import json
from unittest.mock import Mock
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from sentinel.data import seed_demo
from sentinel.main import app
from sentinel.trustgraph import evaluate, reconcile, scenarios


@pytest.fixture
def local(tmp_path, monkeypatch):
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("SENTINEL_DB", str(path))
    monkeypatch.delenv("SENTINEL_LOCAL_AI", raising=False)
    seed_demo(path)
    with TestClient(app) as client:
        yield client, path


@pytest.mark.parametrize("name,events,journey,expected", list(scenarios()))
def test_expected_decisions(name, events, journey, expected):
    result = reconcile(events, journey)
    assert (result["status"] == "revisar") is expected
    assert result == reconcile(list(reversed(events)), journey)
    assert len(result["events"]) == len(events)


def test_evaluation_and_legacy_ledger(local):
    client, _ = local
    case = client.get("/api/orders/demo-order-1").json()
    assert (case["paid_minor"], case["refunded_minor"], case["net_minor"]) == (10000, 10000, 0)
    assert case["attribution"] is None
    assert client.get("/api/orders/missing").status_code == 404
    assert client.get("/api/validation").json() == evaluate()
    assert evaluate()["counts"] == {"tn": 4, "tp": 9, "fp": 0, "fn": 0}
    timings = {r["name"]: r["simulated_seconds_to_alert"] for r in evaluate()["cases"]}
    assert timings["reembolso-excedente"] == 1
    assert timings["reembolso-integral"] is None
    assert client.get("/static/console.js").status_code == 200


def test_commission_fixture(local):
    client, _ = local
    case = client.get("/api/orders/lab-comissao-apos-reembolso").json()
    assert case["attribution"]["expected_minor"] == 0
    assert case["attribution"]["posted_minor"] == 1000
    assert case["reasons"] == ["comissao_divergente"]


def test_review_conflicts_and_audit(local):
    client, path = local
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("DELETE FROM synthetic_events WHERE event_type='order_paid'")
    url = "/api/orders/demo-order-1"
    body = dict(revision=client.get(url).json()["revision"], reviewer="Operações",
                decision="confirmado", note="Falta o pagamento.")
    received = client.post(url + "/review", json=body)
    assert received.status_code == 200
    assert client.post(url + "/review", json=body).json() == received.json()
    assert client.post(url + "/review", json=dict(body, note="Outro")).status_code == 409
    seed_demo(path)
    assert client.post(url + "/review", json=body).status_code == 409
    assert client.get(url).json()["review"] is None
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("SELECT COUNT(*) FROM case_reviews").fetchone() == (1,)


def test_citations_and_abstention(local):
    client, _ = local
    url = "/api/orders/demo-order-1/explanation"
    answer = client.post(url, json={"question": "Como funciona uma oferta?"}).json()
    assert answer["sources"][0]["id"] == "YS-CREATORS-01"
    assert answer["event_ids"] == ["demo-paid-1", "demo-refund-1"]
    missing = client.post(url, json={"question": "Qual o prazo de saque?"}).json()
    assert missing["mode"] == "evidencia_insuficiente"
    assert not missing["sources"]


def test_unavailable_generation_reports_failure(local, monkeypatch):
    client, _ = local
    monkeypatch.setenv("SENTINEL_LOCAL_AI", "1")

    def unavailable(*args, **kwargs):
        raise ConnectionRefusedError

    monkeypatch.setattr("sentinel.evidence.HTTPConnection", unavailable)
    response = client.post("/api/orders/demo-order-1/explanation", json={"question":"evento pago"})
    assert response.status_code == 503


@pytest.mark.parametrize("ids,status,mode", [
    (["demo-paid-1", "YS-WEBHOOK-01"], 200, "rascunho_ia"),
    ([], 200, "evidencia_insuficiente"),
    (["YS-UNKNOWN"], 503, None),
])
def test_generated_citations_are_checked(local, monkeypatch, ids, status, mode):
    client, _ = local
    monkeypatch.setenv("SENTINEL_LOCAL_AI", "1")
    payload = {"choices":[{"message":{"content": json.dumps({"ids": ids})}}]}
    response = io.BytesIO(json.dumps(payload).encode())
    response.status = 200
    transport = Mock()
    transport.return_value.getresponse.return_value = response
    monkeypatch.setattr("sentinel.evidence.HTTPConnection", transport)
    received = client.post("/api/orders/demo-order-1/explanation", json={"question":"Qual evento de pagamento?"})
    assert received.status_code == status
    transport.assert_called_once_with("127.0.0.1", 11434, timeout=90)
    if mode:
        assert received.json()["mode"] == mode
    if mode == "rascunho_ia":
        assert "[demo-paid-1]" in received.json()["draft"]


@pytest.mark.parametrize("decision", ["confirmado", "descartado"])
def test_rule_replay_requires_approval(local, decision):
    client, _ = local
    before = client.get("/api/experiment").json()
    assert before["baseline"]["counts"]["fn"] == 1
    assert before["replay"] is None
    body = dict(revision=before["revision"], reviewer="Teste", note="Cenários fixos.", decision=decision)
    result = client.post("/api/experiment/review", json=body)
    assert result.status_code == 200
    replay = result.json()["replay"]
    if decision == "confirmado":
        assert replay == {"counts": {"tp": 10, "tn": 4, "fp": 0, "fn": 0}, "missed_commission_minor": 0}
    else:
        assert replay is None
    assert client.get("/api/experiment").json() == result.json()
    assert client.post("/api/experiment/review", json=dict(body, note="revisado")).status_code == 409

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
    assert response.status_code == 200
    assert response.json()["generation_status"] == "error"
    assert response.json()["citation_ids"] == ["demo-paid-1"]


def mock_generation(monkeypatch, ids):
    monkeypatch.setenv("SENTINEL_LOCAL_AI", "1")
    payload = {"choices": [{"message": {"content": json.dumps({"ids": ids})}}]}
    response = io.BytesIO(json.dumps(payload).encode())
    response.status = 200
    transport = Mock()
    transport.return_value.getresponse.return_value = response
    monkeypatch.setattr("sentinel.evidence.HTTPConnection", transport)
    return transport


@pytest.mark.parametrize("ids,mode,status", [
    (["demo-paid-1"], "rascunho_ia", "selected"),
    ([], "evidencia_local", "empty"),
    (["YS-UNKNOWN"], "evidencia_local", "error"),
    (["YS-WEBHOOK-01"], "evidencia_local", "error"),
    (["demo-refund-1"], "evidencia_local", "error"),
])
def test_generated_citations_are_checked(local, monkeypatch, ids, mode, status):
    client, _ = local
    monkeypatch.delenv("SENTINEL_OLLAMA_MODEL", raising=False)
    transport = mock_generation(monkeypatch, ids)
    received = client.post("/api/orders/demo-order-1/explanation", json={"question": "Qual evento de pagamento?"})
    assert received.status_code == 200
    transport.assert_called_once_with("127.0.0.1", 11434, timeout=90)
    answer = received.json()
    assert answer["mode"] == mode
    assert answer["generation_status"] == status
    assert answer["citation_ids"] == ["demo-paid-1"]
    assert "[demo-paid-1]" in answer["message"]
    request = json.loads(transport.return_value.request.call_args.args[2])
    assert request["model"] == "sentinel-qwen-local"
    assert request["max_tokens"] == 180
    assert request["stream"] is False
    assert request["reasoning_effort"] == "none"


COMMISSION_ORDER = "lab-comissao-apos-reembolso"


@pytest.mark.parametrize("ids", [None, [], ["lab-comissao-apos-reembolso-1"], ["demo-refund-1"]])
def test_commission_explanation_retains_ledger_finding(local, monkeypatch, ids):
    client, _ = local
    if ids is not None:
        transport = mock_generation(monkeypatch, ids)
        monkeypatch.setenv("SENTINEL_OLLAMA_MODEL", "qwen3:4b")
    answer = client.post(f"/api/orders/{COMMISSION_ORDER}/explanation",
                         json={"question": "Por que a comissão ficou em revisão após o reembolso do pedido?"}).json()
    assert "prevê 0 centavos" in answer["case_finding"]
    assert "registrou 1000 centavos" in answer["case_finding"]
    assert answer["citation_ids"] == ["synthetic-offer-v1", "lab-comissao-apos-reembolso-1"]
    assert answer["sources"] == []
    if ids is not None:
        request = json.loads(transport.return_value.request.call_args.args[2])
        assert request["model"] == "qwen3:4b"


@pytest.mark.parametrize("order_id,event_id", [
    ("demo-order-1", "demo-refund-1"),
    (COMMISSION_ORDER, "lab-comissao-apos-reembolso-1"),
])
def test_refund_cites_only_selected_orders_event(local, order_id, event_id):
    client, _ = local
    url = f"/api/orders/{order_id}"
    case = client.get(url).json()
    event = next(event for event in case["events"] if event["event_type"] == "order_refunded")
    answer = client.post(url + "/explanation", json={"question": "Qual evento comprova o reembolso do pedido?"}).json()
    assert answer["citation_ids"] == [event_id]
    assert answer["revision"] == case["revision"]
    assert answer["sources"] == []
    assert event_id in answer["message"]
    assert event["occurred_at_utc"] in answer["message"]
    assert f"{event['amount_minor']} centavos" in answer["message"]


@pytest.mark.parametrize(("order_id", "expected"), [
    ("sim-03501", "2713 centavos"),
    ("lab-reembolso-sem-venda", "Nenhum pagamento"),
    ("lab-venda", "A regra atual não sinalizou divergências"),
])
def test_plain_language_order_diagnosis(local, order_id, expected):
    client, _ = local
    response = client.post(f"/api/orders/{order_id}/explanation",
                           json={"question": "o que ha de errado com o pedido?"})
    assert response.status_code == 200
    answer = response.json()
    assert answer["mode"] == "evidencia_local"
    assert expected in answer["message"]
    assert answer["citation_ids"]


def test_withdrawal_date_abstains_before_generation(local, monkeypatch):
    client, _ = local
    transport = mock_generation(monkeypatch, ["demo-paid-1"])
    answer = client.post(f"/api/orders/{COMMISSION_ORDER}/explanation",
                         json={"question": "Qual é a data do próximo saque deste pedido?"}).json()
    assert answer["mode"] == "evidencia_insuficiente"
    assert answer["citation_ids"] == answer["sources"] == []
    assert "Não há evidência local para determinar a data do próximo saque." == answer["message"]
    transport.assert_not_called()


def test_order_without_refund_explains_missing_event(local):
    client, _ = local
    answer = client.post("/api/orders/sim-00004/explanation",
                         json={"question": "Qual evento comprova o reembolso?"}).json()
    assert answer["mode"] == "evidencia_local"
    assert "Nenhum evento de reembolso" in answer["message"]
    assert "sim-00004-0" not in answer["citation_ids"]


def test_order_questions_use_selected_order_and_recorded_review(local):
    client, _ = local
    simulated = client.post("/api/orders/sim-03501/explanation",
                            json={"question": "Quem recebeu o crédito pelo link?"}).json()
    assert "creator-002" in simulated["message"]
    assert "criador-demo" not in simulated["message"]

    url = "/api/orders/lab-comissao-apos-reembolso"
    case = client.get(url).json()
    saved = client.post(url + "/review", json=dict(revision=case["revision"], reviewer="Pessoa revisora",
                        decision="confirmado", note="Reembolso conferido."))
    assert saved.status_code == 200
    answer = client.post(url + "/explanation", json={"question": "Quem confirmou o alerta?"}).json()
    assert "Pessoa revisora" in answer["message"]
    assert "Reembolso conferido" in answer["message"]


def test_local_model_can_match_an_unrecognized_phrase_to_order_facts(local, monkeypatch):
    client, _ = local
    mock_generation(monkeypatch, ["resumo"])
    response = client.post("/api/orders/sim-03501/explanation",
                           json={"question": "Me dá um panorama dessa transação?"})
    answer = response.json()
    assert answer["generation_status"] == "selected"
    assert "2713 centavos" in answer["message"]
    assert "sim-03501-1" in answer["citation_ids"]



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

import pytest
from fastapi.testclient import TestClient

from sentinel.main import app


@pytest.mark.parametrize(("name", "last", "fragment", "amount"), [
    ("retido", "Comissão retida", "não há data", 1000),
    ("agendado", "Repasse agendado", "previsto para 08/01/2026", 1000),
    ("concluido", "Repasse concluído", "confirma o repasse", 1000),
    ("cancelado", "Pedido cancelado", "comissão foi revertida", 0),
])
def test_payout_visible_and_cited(tmp_path, monkeypatch, name, last, fragment, amount):
    monkeypatch.setenv("SENTINEL_DB", str(tmp_path / "payout.sqlite"))
    order_id = "lab-repasse-" + name
    with TestClient(app) as client:
        assert order_id in client.get("/api/orders").json()
        url = "/api/orders/" + order_id
        order = client.get(url).json()
        records = order["payout"]
        assert [r["date"] for r in records] == sorted(r["date"] for r in records)
        assert records[-1]["label"] == last
        assert records[-1]["amount_minor"] == order["attribution"]["posted_minor"] == amount
        assert order["refunded_minor"] == (10000 if name == "cancelado" else 0)
        answer = client.post(url + "/explanation", json={"question": "Qual é a situação do repasse?"}).json()
        assert fragment in answer["message"]
        assert answer["citation_ids"] == [records[-1]["id"]]


@pytest.mark.parametrize("order_id", ["lab-comissao-apos-reembolso", "lab-repasse-cancelado"])
def test_refund_after_cancellation_cites_refund_not_payout(tmp_path, monkeypatch, order_id):
    monkeypatch.setenv("SENTINEL_DB", str(tmp_path / "refund.sqlite"))
    with TestClient(app) as client:
        answer = client.post(f"/api/orders/{order_id}/explanation", json={
            "question": "Quanto foi reembolsado após o cancelamento?"}).json()
    assert "10000 centavos" in answer["message"]
    assert f"{order_id}-1" in answer["citation_ids"]

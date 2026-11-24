"""Compare two local methods on four labeled synthetic orders. Run at repo root."""
import json
from http.client import HTTPConnection
from time import perf_counter

from sentinel.trustgraph import reconcile, scenarios

GOLD = {
    "venda": (10000, False),
    "reembolso-integral": (0, False),
    "reembolso-sem-venda": (-3000, True),
    "reembolso-excedente": (-100, True),
}


def model_answer(events):
    prompt = ("Use os eventos sintéticos abaixo. Some pagamentos e subtraia reembolsos "
              "em centavos. Revise quando não houver exatamente um pagamento ou o total "
              "reembolsado exceder o total pago. Retorne net_minor inteiro e review booleano.\n"
              + json.dumps(events))
    connection = HTTPConnection("127.0.0.1", 11434, timeout=120)
    try:
        connection.request("POST", "/api/generate", json.dumps({
            "model":"sentinel-qwen-local", "prompt":prompt, "stream":False,
            "format":{"type":"object","properties":{"net_minor":{"type":"integer"},
                      "review":{"type":"boolean"}},"required":["net_minor","review"]},
            "options":{"temperature":0, "num_predict":120},
        }), {"Content-Type":"application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError(f"Local model returned HTTP {response.status}")
        payload = json.load(response)
        return json.loads(payload["response"])
    finally:
        connection.close()


def run():
    rows = []
    for name, events, journey, _ in scenarios():
        if name not in GOLD:
            continue
        expected_net, expected_review = GOLD[name]
        for method in ("trustgraph", "local_model"):
            start = perf_counter()
            error = None
            try:
                if method == "trustgraph":
                    case = reconcile(events, journey)
                    net, review = case["net_minor"], case["status"] == "revisar"
                else:
                    result = model_answer(events)
                    net, review = result["net_minor"], result["review"]
            except (KeyError, ValueError, TypeError) as exc:
                net, review, error = None, None, type(exc).__name__
            rows.append(dict(case=name, method=method, net_minor=net, review=review,
                             correct=(type(net) is int and net == expected_net and review is expected_review),
                             seconds=round(perf_counter()-start, 4), error=error))
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()

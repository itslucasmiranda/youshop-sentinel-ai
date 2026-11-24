# YouShop Sentinel AI

Investigate synthetic creator commissions from a promotion link through a
payment, refund and ledger entry. FastAPI serves a Brazilian Portuguese React
console. SQLite records human decisions against versioned evidence.

## Run on Windows

Open this folder in VS Code. In its PowerShell terminal, run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn sentinel.main:app --host 127.0.0.1
```

Select `.venv\Scripts\python.exe` as the Python interpreter in VS Code.
Open [the local interface](http://127.0.0.1:8000/) or check
[`GET /health`](http://127.0.0.1:8000/health) for HTTP 200 and
`{"status":"ok"}`. The health endpoint checks API liveness.

## Load local sample events

In a second terminal, run:

```powershell
.\.venv\Scripts\python.exe -m sentinel.data
```

The command loads two synthetic events into `sentinel-demo.sqlite3` on the
first run against a fresh file. Running it again inserts zero events. No
credentials or platform connections are required.

See [data provenance](docs/provenance.md) and the [delivery roadmap](docs/delivery.md).

The [TrustGraph operator guide](docs/trustgraph.md) covers the React console,
synthetic commission cases, human review, defensive evaluation and local AI.

## Walk through one order

Select `lab-comissao-apos-reembolso`. Its fictional offer has a BRL 100
payment, a full refund, and BRL 10 in booked commission. Compare the expected
amount, inspect the event identifiers and ask which commission remained after
the refund. Open the rule experiment to review a separate fixed scenario and
inspect the effect of a proposed check. All decisions apply to the local lab.

See [research and evaluation](docs/discovery.md) for the experiments and
[source provenance](docs/provenance.md) for the official material used.

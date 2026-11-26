# TrustGraph operator guide

Start the demo with the Windows commands in the README. The Portuguese console
at the root lists SQLite orders and 13 fixed synthetic cases. Select
`lab-comissao-apos-reembolso` to trace an offer through its creator, promotion
link, payment, refund and booked commission. Sums use integer BRL centavos.
The training offer pays 10% of the remaining positive order balance, rounded
down. This versioned contract and all signal thresholds are invented for the
exercise. The source registry describes the limits of official evidence.

The ledger expects a single payment. Missing or multiple payments, excessive
refunds, inconsistent fixture versions and ambiguous chronology trigger review.
Affiliate cases cover self-purchase, linked accounts, conflicting attribution,
unusual traffic and an unreversed commission. Each alert is a lead for a human.
The validation panel computes its confusion matrix from the evaluator output
and independent fixture labels. These cases do not measure field accuracy.
Each scenario also reports the first alert's event ID and seconds since its
first synthetic timestamp. Prefixes are evaluated in ledger order. The
affiliate snapshot is available at the final event. This is simulated event
time; the separate model benchmark measures elapsed wall-clock time.

The rule experiment adds a fourteenth case with a booked commission and
missing independent sale confirmation. The panel reports the attributed
amount for missed commission cases in fictional BRL. A named operator can
accept or reject one versioned check for the lab. Acceptance replays all
14 fixed cases and displays the resulting false positives, false negatives
and uncovered commission. A rejected check stays inactive. The test suite
exercises both choices in temporary databases.

The local review form stores the operator's self-reported name, explanation,
decision, UTC time and evidence digest. A repeated identical submission is
idempotent. A changed case requires a new review. Older reviews are retained
in SQLite. This is a single-user, loopback demo. Limit input to fictional
identifiers. Only code review and a new version can change the rules.

## Local retrieval and generation

The explanation endpoint resolves the requested order and returns its revision.
`event_ids` lists the order's events for existing API clients. `citation_ids`
lists the specific facts and references that support the answer. Commission
review shows expected and booked centavos from the synthetic ledger. Refund
questions identify the matching event, amount and UTC timestamp. A request for
the next withdrawal date receives an explicit insufficient-evidence response.

Optional Ollama generation runs on 127.0.0.1:11434. The default model is
`sentinel-qwen-local`. Set `SENTINEL_OLLAMA_MODEL` to use another locally
installed model. The model selects up to three verified candidate IDs.
Generation requests [no model thinking](https://docs.ollama.com/api/openai-compatibility)
and caps the input at 12 candidates, the output at 180 tokens and the
HTTP read at 16 KiB, with a 90-second socket timeout. Empty, invalid or failed
model output falls back to the deterministic answer. Case findings and event
evidence are rendered independently of the model, and reviews still require
a named human decision.

Run the fixed retrieval suite from the repository root after installing the
project. The optional live run checks Ollama's installed tags, skips missing
models, and reports final-answer scores, model selections, generation errors
and per-question latency. Precision and recall are null when their respective
denominators are zero. The unit tests use mocked model responses.

```powershell
.\.venv\Scripts\python.exe -m evaluation.retrieval
.\.venv\Scripts\python.exe -m evaluation.retrieval --live
$env:SENTINEL_LOCAL_AI = "1"
$env:SENTINEL_OLLAMA_MODEL = "qwen3:4b"
.\.venv\Scripts\python.exe -m uvicorn sentinel.main:app --host 127.0.0.1
```


## Build and validate

The repository includes the compiled UI so a Python-only install can serve it.
After editing the React/TypeScript source, run `npm ci` and `npm run build`
inside `frontend`. From the repository root run `python -m pytest -q`.
Set `SENTINEL_DB` to choose an isolated database for API tests or demos.

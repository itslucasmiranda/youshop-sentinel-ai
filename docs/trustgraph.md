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

The question endpoint retrieves project-written summaries in Portuguese by
accent-insensitive keyword matching. It returns source identifiers, links,
sections, access dates, case revision and event identifiers. Unmatched questions
produce an insufficient-evidence response. Official references describe the
platform vocabulary. Case decisions come from synthetic ledger arithmetic.

Optional generation uses a local llama.cpp server with a previously downloaded
instruct GGUF. Run this from the folder containing the server, substituting the
local model path:

```powershell
.\llama-server.exe -m "C:\models\model.gguf" --host 127.0.0.1 --port 18765 -c 4096
```

In the project terminal set `$env:SENTINEL_LOCAL_AI = "1"` before starting
Uvicorn. Questions with retrieved evidence now request a Portuguese draft.
Generation errors surface as HTTP 503. Treat generated text as a draft to
check against the displayed source summaries and event evidence. The model
has no tools or authority to write reviews, update rules or move money.

## Build and validate

The repository includes the compiled UI so a Python-only install can serve it.
After editing the React/TypeScript source, run `npm ci` and `npm run build`
inside `frontend`. From the repository root run `python -m pytest -q`.
Set `SENTINEL_DB` to choose an isolated database for API tests or demos.

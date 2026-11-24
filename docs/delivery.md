# Delivery roadmap

## Project Foundation

Branch `feat/project-foundation`. Acceptance: Windows with Python 3.12,
FastAPI liveness and Portuguese landing page, pytest, and GitHub Actions.
Open the PR against `main`.

## Data Foundation

Branch `feat/data-foundation`. Acceptance: source catalogue, isolated SQLite
fixture, and repeatability and rollback checks. Open a stacked PR against
`feat/project-foundation` or target `main` after the foundation merges.

## TrustGraph

Implement deterministic reconciliation of a versioned local event ledger.
Define expected results for each approved fixture, including missing records
and incomplete histories. Preserve event identifiers, evidence and rule versions
in each decision. Route ambiguous cases to human review.

## Evidence and defensive validation

Ground RAG explanations in reviewed references and reconciliation evidence.
Include citations and surface insufficient evidence. Human reviewers own rule
approval and any resulting action. Run defensive checks against approved,
fixed synthetic fixtures in an isolated environment with no production access.
Evaluate expected alerts and false positives using the fixture labels.

After both foundation PRs pass remote CI and are reviewed and merged, tag
`v0.1.0` from `main` and publish the release notes with verified scope.

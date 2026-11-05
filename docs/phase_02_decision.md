# Phase 2 candidate decision — review pending

The implementation proposes a candidate from primary validation AP/F2 only. See phase_02_results.md for measured results and artifacts/phase_02/candidate_proposal.json for the exact decision SHA, fitted model SHA, split SHA and operating point.

## Required independent sign-off

| Reviewer | Decision hash reviewed | Decision |
|---|---|---|
| Source/split reviewer (N2) | Pending | Pending |
| Model/evaluation reviewer (N3/N4; different person) | Pending | Pending |

No reviewer identity, gold label, approval or signature is fabricated. The local/CI script never changes this table and always keeps the proposal pending. The held-out test remains sealed. There is no final test score and no production-readiness claim.

Review source provenance and Public-license limitations, duplicate/feature-conflict audit, Time drift, train-only fit evidence, SMOTE class counts, validation AP and false-alert trade-offs, stable-tie top-K limitation, bounded-search selection bias, independent-reference differences, notebook execution and the hosted CI run at the PR head. Capture the exact candidate decision hash in both reviews before freezing a research champion. Do not reinterpret a later rerun as approval of a different hash.

P3/P4 backlog: Spark scale benchmarks; persistence/serving of reviewed models; formal test-opening protocol after a reviewed candidate freeze; external/longitudinal data; operational cost assumptions and calibration; final demo/report. Replicated data is never independent ML evidence.

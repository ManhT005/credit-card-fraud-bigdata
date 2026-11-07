# Phase 2 candidate decision

## Proposal for independent review

- Candidate: `xgboost_06`
- Run ID: `chronological-xgboost_06-1f4d95e0f797`
- Decision SHA-256: `1602082a03abe686b8c828bc3bbac9711163461fcec65e459f51e6da4dafe00a`
- Fitted model SHA-256: `94dfe90f1c08d1e0933d6c5366c897c8b3a5e0d5c2e6778272ef2982df83c31f`
- Primary split SHA-256: `25d7a9daf496855757b2c1b8e05bbe26f015c8aac43758cee25e4f56c168a690`
- Selection: highest chronological validation AP, then F2, then model name. The reference protocol does not influence selection.
- Operating point: threshold `0.08604497462511063`, validation AP 0.839861, F2 0.809859, 14 false alerts and 10 missed fraud cases.
- Evidence: [locked GitHub Actions run 42364868665](https://github.com/ManhT005/credit-card-fraud-bigdata/actions/runs/42364868665), artifact `13570879627`. See [the results report](phase_02_results.md) for its verified digest and complete comparison.

## Required independent sign-offs

| Role | GitHub reviewer | Decision SHA-256 reviewed | Review |
|---|---|---|---|
| Source/split (N2) | Pending | Pending | Pending |
| Model/evaluation (N3 or N4) | Pending | Pending | Pending |

The two reviewers must be distinct and independent of the change owner. Each records their approval of the exact decision SHA-256 above on [PR #3](https://github.com/ManhT005/credit-card-fraud-bigdata/pull/3). The source/split review covers source provenance, license metadata, duplicate isolation, class prevalence and Time drift. The model/evaluation review covers train-only preprocessing and SMOTE, validation-only AP/F2, the alert trade-off, reference protocol separation, notebook evidence and bounded-search limitations.

Freeze the candidate after both approvals and a successful full CI run on the final PR head. Verify that its artifact reproduces the decision SHA-256 above. If the hash changes, require both reviewers to review the new proposal. The automated evidence records technical completion separately from human sign-off. The held-out test remains sealed.

P3/P4 backlog: Spark scale benchmarks, persistence and serving of reviewed models, formal test-opening protocol after candidate freeze, external or longitudinal data, operational cost assumptions and calibration, and the final demo and report. Replicated data is for ETL benchmarking.

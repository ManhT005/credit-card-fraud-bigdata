# Phase 1 dataset card — review pending

Source: [OpenML ID 1597](https://www.openml.org/d/1597), credit-card fraud. Expected reference: 284807 transactions, 492 fraud rows, 31 fields.

**Original-data execution evidence: see the `phase-1-acceptance` CI job and its `phase-1-acceptance` artifact. Acceptance requires a successful run for the PR revision.** The repository does not contain the original CSV.

| Fields | Meaning | Caution |
|---|---|---|
| Time | Relative seconds | Not calendar time |
| Amount | Transaction amount | Skew and outliers require analysis |
| V1–V28 | Anonymized PCA features | Original feature meanings unavailable |
| Class | 0 legitimate, 1 fraud | Severe target imbalance |

Review `artifacts/phase_01/profile.json`, `column_profile.csv`, and `dataset_manifest.json` locally. Do not publish raw transactions. Exact duplicates do not prove errors without transaction IDs; do not delete them in Phase 1.

Phase 2 risks: splitting before learned preprocessing, train-only SMOTE, duplicate overlap across splits, validation-only threshold tuning, protected held-out test. Two-day relative time range limits longitudinal claims. The source PCA fit cannot be audited from anonymized features.

Teaching sources: [Preprocessing PDF](https://drive.google.com/file/d/1MBpTMxfbYDSN5IV0C_ByVTRj0Xq8zKvG/view), [P1 statistics notebook](https://colab.research.google.com/drive/1AoJppTqDXNFVGL78ikPbBGkvmHqhlZfJ), [PySpark notebook](https://colab.research.google.com/drive/1ei0RUNHC-XznQQAXhDD5inDqA1dVC4kt).


## Verified source identity and license review

The [OpenML metadata API](https://www.openml.org/api/v1/json/data/1597) identifies dataset 1597, version 1, version label `V1_250615`, file ID `1673544`, ARFF MD5 `178bcf9bb1f31a3dfe12d0e577884add`. The acceptance script checks these against the live source and computes SHA-256 for both downloaded ARFF and exported CSV. `Time` is tagged as a row identifier: it must be retained in the 31-column export, rather than dropped by a default feature-only loader. Conversion changes serialization only; no row deletion or learned preprocessing occurs.

The source-declared license field is **`Public`**, not a named SPDX license. This is recorded as supplied by OpenML; it does not establish MIT licensing of the dataset or grant commercial redistribution rights. The repository code license applies to code. Raw transactions are downloaded locally or in CI and excluded from commits and uploaded evidence. Further redistribution requires separate clarification of terms.

## Reproduce acceptance

```bash
python -m pip install -e ".[data,notebook,dev]"
python scripts/phase_01_acceptance.py
```

A failed check exits nonzero. `acceptance.json` is written only after checksum, schema, reference counts, quality checks and every notebook code cell pass. Unexpected quality findings require review; exact duplicates remain unchanged and are reported by class. CI uploads aggregate statistics, provenance, the executed notebook without raw-row previews, and the acceptance marker. No synthetic data can satisfy this original-source check.

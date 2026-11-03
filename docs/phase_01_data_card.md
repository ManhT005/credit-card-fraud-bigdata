# Phase 1 dataset card — review pending

Source: [OpenML ID 1597](https://www.openml.org/d/1597), credit-card fraud. Expected reference: 284807 transactions, 492 fraud rows, 31 fields.

**Actual local rows / checksum / license verification: PENDING source run.** The repository does not contain the original CSV.

| Fields | Meaning | Caution |
|---|---|---|
| Time | Relative seconds | Not calendar time |
| Amount | Transaction amount | Skew and outliers require analysis |
| V1–V28 | Anonymized PCA features | Original feature meanings unavailable |
| Class | 0 legitimate, 1 fraud | Severe target imbalance |

Review `artifacts/phase_01/profile.json`, `column_profile.csv`, and `dataset_manifest.json` locally. Do not publish raw transactions. Exact duplicates do not prove errors without transaction IDs; do not delete them in Phase 1.

Phase 2 risks: splitting before learned preprocessing, train-only SMOTE, duplicate overlap across splits, validation-only threshold tuning, protected held-out test. Two-day relative time range limits longitudinal claims. The source PCA fit cannot be audited from anonymized features.

Teaching sources: [Preprocessing PDF](https://drive.google.com/file/d/1MBpTMxfbYDSN5IV0C_ByVTRj0Xq8zKvG/view), [P1 statistics notebook](https://colab.research.google.com/drive/1AoJppTqDXNFVGL78ikPbBGkvmHqhlZfJ), [PySpark notebook](https://colab.research.google.com/drive/1ei0RUNHC-XznQQAXhDD5inDqA1dVC4kt).

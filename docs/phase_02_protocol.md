# Phase 2 experiment protocol — implementation baseline

Base: origin/develop 24f6c4330d0890e9e133de6cbe004afd7326e0e5 (Phase 1 merged).
Scope follows PHASE_02_IMPLEMENTATION_PLAN.md; this branch implements P2-00 through P2-09 as one integrated research pipeline. Independent peer reviews remain pending; code execution never manufactures sign-off.

## Decisions fixed before experiments

| Decision | Implementation default | Governance |
|---|---|---|
| D0 duplicates | Retain every row. Primary Time groups never split. SHA-256 exact-record overlap is a hard error. | Proposed baseline for peer review |
| D1 reference | Separate stratified split of full-record groups, approximately 60/20/20 rows; group-size deviations reported. | Never merged with primary results |
| D2 features | Time, V1–V28, Amount; allowlisted ColumnTransformer; train-fitted StandardScaler. No extra PCA or default imputation. | Class/row_id excluded |
| D3 resources | Seed 42; two CPU threads; six XGBoost settings in phase_02_models.yaml; SMOTE ratio 0.1, k=5. IsolationForest included. | No adaptive/test-based grid expansion |
| D4 selection | Highest validation AP; then validation F2; then name. Threshold = exact maximum validation F2, equal maxima choose highest threshold. | Candidate proposed; requires two independent reviewers |

## Source gate

Require Phase 1 acceptance.json, source_provenance.json and dataset_manifest.json. Compare actual CSV SHA with all three records; pin OpenML ID/version/file ID and original ARFF MD5; recompute row/class counts, schema and data-quality checks. Mismatch, missing evidence, or unexpected quality findings stop before fitting. The Public source-declared license is recorded by Phase 1; source data is not redistributed and code MIT does not extend to transactions.

## Partition semantics

Source row position is an audit identity, never a feature. Stable Time/position sort selects nearest group boundaries to 70/15/15. Every split covers both classes and every original row exactly once. Strict Time inequalities separate partitions. Full-record fingerprints hash numeric canonical little-endian float64 values, including Time and Class, with signed zeros normalized. Feature-only conflicting-label groups are reported. Split identity depends on source bytes, config and actual partitions; it is independent of execution timestamps and Phase 1 run URL.

Reference stratification keeps exact-record duplicates together and stratifies the group label. Ratios are approximate at row level because groups have different sizes. It remains a secondary protocol; feature-conflict groups and temporal limitations must be considered during review. It cannot select the primary proposal.

## Fit and evaluation boundaries

All learned preprocessing lives inside the estimator pipeline. fit sees train only. SMOTE lives in an imblearn Pipeline after the scaler; it cannot resample predict_proba inputs. Its input and output class counts are recorded. class_weight=balanced and XGBoost scale_pos_weight derive from training labels. Validation keeps original counts and prevalence. No cross-validation is claimed; if CV is added, the entire pipeline must be fitted inside each training fold.

Metrics use sklearn average_precision_score (AP, not trapezoidal PR area), ROC-AUC, precision, recall, F1/F2, fixed binary confusion matrix, alert volume and precision@K (K=100, clipped to validation length). Undefined single-class evaluation, non-finite scores and non-validation selection fail closed. Precision with no predicted positives is zero. Ranking ties preserve validation row order, so Dummy top-K is not a meaningful discrimination claim.

The held-out partition permits only integrity checks and class-count auditing. Its features and labels are never passed to training, threshold selection or model evaluation. No test metric or prediction output is produced. Source anonymized PCA fit cannot be audited; Time spans only two days.

## Artifacts and acceptance

artifacts/phase_02 contains intake, both split manifests, per-run manifests/metrics/threshold policies, primary and independent reference comparisons, candidate proposal and executed notebooks. Run manifests include source/split/config/code/model hashes, feature order, train/validation class counts, parameters, fit/evaluation sources, versions, runtime, git dirty flag and test_opened=false. Curve coordinates are thinned to at most 150 points; no raw score/label pairs, transaction previews, predictions or model binaries are uploaded.

`python scripts/phase_02_acceptance.py --execute-notebooks` executes 11 candidates per protocol and four notebooks from both supported working directories. Hosted CI retains P1 acceptance, then downloads the successful P1 artifact and reacquires checksum-pinned source for the P2 job. The P2 job passes technical execution; acceptance.json still records accepted=false and research_acceptance=pending_two_independent_reviewers. A machine PASS does not open test or approve the proposal.

Official methods: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html ; https://imbalanced-learn.org/stable/references/generated/imblearn.pipeline.Pipeline.html ; https://xgboost.readthedocs.io/en/stable/parameter.html

# Experiment protocol — planned, not executed

## Dataset integrity

Load OpenML data ID 1597 and record version, schema, row count, class balance,
source and download date. Inspect duplicates and missingness. Preserve dataset
provenance and never silently mix synthetic repetitions into ML datasets.

## Splitting and leakage prevention

1. Sort by relative `Time` and perform chronological train/validation/test split.
2. Fit scalers and any learned transforms on training data only.
3. Apply SMOTE only within training folds, never before splitting.
4. Select hyperparameters and thresholds using training/validation only.
5. Keep held-out test untouched until final evaluation.
6. Run a separate stratified-random reference experiment.

## Methods

Dummy majority baseline; logistic regression; class-weighted logistic regression;
SMOTE with a leakage-safe pipeline; XGBoost with and without class weights;
and Isolation Forest as an unsupervised anomaly-detection comparison.

## Metrics

Report average precision (AP) as the primary summary of the PR curve,
plus recall, precision, F1/F2, ROC-AUC, confusion matrix, precision@K,
false alerts and missed fraud. Optimize the alert threshold on validation data.

## Big Data evaluation

Compare equivalent pandas and PySpark ETL transformations on original, 10x and
100x input scales. Track replicated-source IDs. Scaled rows are for processing
benchmarks only, never for independent training/test samples.

Capture elapsed time, CPU/RAM, dataset bytes, output bytes, Spark mode,
partition count, and repeat-run variation.

## Reporting

Every measured result must have a config, code revision, random seed,
input provenance and execution hardware. Do not claim measurements before running.

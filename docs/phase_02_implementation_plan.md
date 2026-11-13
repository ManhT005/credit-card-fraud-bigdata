# PHASE 02 — LEAKAGE-SAFE MODELING & EVALUATION

**Dự án:** Credit Card Fraud Detection — Big Data Analytics  
**Repo:** https://github.com/ManhT005/credit-card-fraud-bigdata  
**Base:** `develop` tại merge commit `24f6c4330d0890e9e133de6cbe004afd7326e0e5` (xác minh ngày 05/11/2026).  
**Trạng thái:** Kế hoạch triển khai, chưa có metric Phase 2.  
**Thời lượng đề xuất:** 12 ngày làm việc / khoảng 2,5–3 tuần, nhóm 5 người.  
**Quy tắc:** Logic tái sử dụng đặt tại `src/fraud_detection/`; notebook chỉ là lớp diễn giải/thực nghiệm, không sao chép nguyên pipeline. Test là bộ dữ liệu giữ kín, không được dùng chọn threshold.

## 0. Cơ sở thực tế và định hướng

### 0.1. Hiện trạng đã kiểm tra

- PR #2 Phase 1 đã merge vào `develop`; hai GitHub checks `tests` và `phase-1-acceptance` **PASS** trên merge commit.
- Đã có `scripts/phase_01_acceptance.py`, profiling package, `src/fraud_detection/paths.py`, `notebooks/01_data_profiling.ipynb`, unit tests, config và tài liệu nguồn.
- `configs/experiment.yaml`: seed 42; primary split chronological 70/15/15; reference stratified test 20%; SMOTE train-only; threshold validation-only; metric chính average precision (AP).
- `docs/experiment_protocol.md` đã ghi rõ split trước fitting, train-only transformations, giữ prevalence tự nhiên của validation/test, không tự chế dữ liệu để train.
- **Theo README hiện tại, Phase 2 = ML baselines & evaluation, Phase 3 = Spark ETL + benchmark, Phase 4 = demo/report.** Đây là phạm vi chính thức của kế hoạch này (khác cách phân pha phác thảo ở buổi trao đổi trước).
- Dataset OpenML 1597: dự kiến 284.807 giao dịch, 492 gian lận, 31 trường. Các số trên là metadata nguồn; kết quả chạy phải gắn với artifact SHA thực tế của Phase 1. License do OpenML khai báo `Public`, **không tự suy diễn** giấy phép thương mại/redistribution.

### 0.2. Mục tiêu nghiệm thu

1. Khóa dữ liệu đầu vào và chiến lược train/validation/test; xử lý rủi ro duplicate leakage.
2. Xây dựng preprocessing có thể chứng minh **không fit trên validation/test**.
3. Huấn luyện và đánh giá ít nhất **Dummy majority, Logistic Regression, Logistic Regression class-weighted**, thêm **SMOTE và XGBoost** theo độ ưu tiên; Isolation Forest có nhánh so sánh nếu đủ nguồn lực.
4. Đánh giá thống nhất bằng **AP (average_precision_score), Precision, Recall, F1/F2, ROC-AUC, confusion matrix, alert rate**, chọn threshold **chỉ trên validation**.
5. Có notebook, script, tests, manifest thí nghiệm, CI và báo cáo trung thực; 5 thành viên đều sở hữu đầu ra kỹ thuật.

### 0.3. Ngoài phạm vi

- Spark 1x/10x/100x performance benchmark, Parquet scale, cluster Docker (Phase 3).
- Streamlit production, API phục vụ dự đoán, slide bảo vệ cuối kỳ (Phase 4).
- Fine-tuning DL, full SHAP, tuning hàng trăm cấu hình, MLflow server bắt buộc.
- Bất cứ phương pháp nào dùng test set làm validation/tuning hay dùng dữ liệu nhân bản làm quan sát ML độc lập.

## 1. Sơ đồ pipeline mục tiêu

```text
Verified original OpenML source + Phase 1 SHA
          |
     DATA GATE (P2-00)
          |
   deterministic row identity / duplicate audit
          |
          +---- primary chronological train/val/sealed-test (70/15/15)
          |        group by Time at cut boundaries
          |
          +---- reference stratified random (separate protocol)
          |
       split manifest + fingerprint overlap guards
          |
   train only -> sklearn / imblearn Pipeline
          |       imputer (if needed) -> scaling -> estimator
          |       SMOTE, if used, only on training folds
          |
  models: Dummy -> Logistic -> weighted Logistic -> SMOTE -> XGB
                                             \-> Isolation Forest (optional)
          |
  validation scores -> AP, PR curve, confusion, F2, alert volume
          |
  validation-only threshold selection & candidate choice
          |
  run manifest + aggregate report + experiment decision
          |
  CI + reproducibility review -> candidate FROZEN; TEST SEALED
```

**Nguyên tắc khoa học:** Bộ dữ liệu V1–V28 đã qua PCA ẩn danh từ nguồn; nhóm không có cơ sở tuyên bố kiểm chứng được toàn bộ quá trình fit PCA ban đầu. Chỉ đảm bảo không phát sinh thêm leakage trong code của mình. Duplicate có thể là những giao dịch khác nhau khi thiếu transaction ID, nên không tự xóa dữ liệu.

## 2. Protocol và quyết định phải khóa trước khi train

| Hạng mục | Giá trị khuyến nghị | Cần lưu evidence |
|---|---|---|
| Input | Original CSV SHA-256 từ Phase 1, đúng 31 cột | `source_sha256`, metadata OpenML |
| Features | Time, V1–V28, Amount; **không dùng Class** | ordered feature list |
| Target | `Class` binary; positive=1 fraud | label contract |
| Seed | 42 | random_state/config SHA |
| Primary | Chronological 70/15/15 | actual counts; Time boundaries |
| Tie handling | Không chia các dòng có **Time bằng nhau** qua hai split | group boundary audit |
| Reference | Stratified random có test 20%; đề xuất tách train-val 60/20/20 bằng 80/20 rồi 75/25 trên phần 80% | independent split ID |
| Model selection | Chỉ dùng validation; giữ sealed test | run config / training manifest |
| Primary metric | AP (`average_precision_score`), **khác** trapezoidal PR-AUC | unit tests |
| Threshold | F2 validation-only, report alert rate và FP/FN | policy JSON |
| Advanced | XGB bounded grid; Isolation Forest optional | runtime / version / config |

### 2.1. Chi tiết split chính: chronological

1. Đọc dữ liệu gốc đã kiểm tra P1; tạo `row_id` theo **vị trí bản ghi ban đầu** (chỉ để audit, không làm feature).
2. Sort ổn định theo `Time` rồi `row_id`; không bỏ/làm tròn `Time` tùy tiện.
3. Chọn cutpoints **gần** 70/15/15 nhưng không cắt nhóm có cùng `Time`; report sai lệch thực tế với tỷ lệ mong muốn.
4. Kiểm tra toàn vẹn: `n_train+n_val+n_test=n_original`, không giao row ID, Time có thứ tự, mỗi split có 2 lớp; nếu không đủ positive **fail closed**, review protocol thay vì tự sửa âm thầm.
5. Tạo fingerprint trên **toàn bộ trường gốc** để kiểm tra exact-record overlap qua split; **hard fail** nếu có overlap. Ghi thêm khả năng những hàng có cùng features nhưng khác nhãn.
6. Xuất `split_manifest.json` (dataset SHA, git/config SHA, group-cut boundaries, counts, prevalence, positive counts, split index digest, duplicate audit); row-level split files lưu `data/processed/` bị gitignore.
7. Reference stratified split phải chạy riêng, không gộp score như thể cùng một protocol. Nếu duplicate fingerprint chéo split: đánh dấu rủi ro và dùng grouped-aware solution/secondary exploratory, không công bố như test đáng tin cậy.

**Điểm cần thống nhất (decision D0):** primary mặc định giữ duplicate; vì exact duplicate chứa `Time` giống nhau, group-by-Time tại ranh giới sẽ giữ cùng nhóm, nhưng vẫn phải kiểm tra fingerprint thực tế. Không drop duplicates mặc định và không giả định chúng đều là lỗi.

### 2.2. Train-only preprocessing

- Trường features là allowlist; `Class`, `row_id`, split metadata **không** nằm trong X.
- `StandardScaler` đặt trong `sklearn.Pipeline` dành cho logistic; nếu xem xét RobustScaler hoặc biến đổi Amount cần chạy ablation riêng.
- Chỉ dùng `SimpleImputer` nếu source có missing hoặc experiment giả lập; học thống kê từ train-fold, không điền thiếu toàn tập trước split.
- `SMOTE` dùng **imblearn Pipeline**, sau split, trong từng training fold; không gọi `fit_resample` trên full dataset.
- Cân lớp qua `class_weight` hoặc `scale_pos_weight` tính từ **train fold**, không tự kết hợp bừa với SMOTE.
- Validation/test phải giữ **nguyên số lượng** và prevalence ban đầu.
- Không fit PCA mới trên dữ liệu train+val+test; PCA nguồn đã được áp dụng, và hạn chế về provenance phải ghi nhận.

## 3. Thiết kế notebook (bắt buộc)

| File | Vai trò | Cell/block tối thiểu | Output |
|---|---|---|---|
| `02_split_and_leakage_audit.ipynb` | Split & data integrity | provenance, label theo Time, group-aware split, positive counts, overlap audit | split summary + plot |
| `03_baseline_models.ipynb` | Baseline supervised | Dummy, Logistic, weighted Logistic, PR curves, validation comparison | model comparison |
| `04_imbalance_experiments.ipynb` | Balancing & advanced | SMOTE train-only, XGB weighted, optional IsolationForest | run table + lessons |
| `05_threshold_and_errors.ipynb` | Decision-making | threshold–precision/recall/F2, alert rate, FP/FN, confusion matrix | threshold policy |

**Cần chỉnh README notebook:** trên `develop` đang dự kiến `02_model_baselines.ipynb`, `03_threshold_analysis.ipynb`, `04_spark_benchmark.ipynb`. Khi implement phải chọn **một** numbering convention, update `notebooks/README.md` đồng bộ; Spark benchmark chuyển Phase 3, không tạo các notebook trùng chức năng.

Notebook: dùng `fraud_detection.paths.find_project_root`, chạy từ cả root và thư mục notebooks; Markdown giải thích mục tiêu và kết quả, có config+seed+SHA; không hardcode ổ `D:`; không lưu raw preview, row-level prediction hay token trong artifact CI; không viết số đo giả. Code đào tạo, splitting và metrics **đặt trong module**, notebook chỉ gọi hàm.

## 4. WBS — 10 task triển khai có Owner/Acceptance

### P2-00 — Source intake & frozen protocol (N1 owner, N2/N3 review)

**Kiến thức:** data versioning, experiment reproducibility, train/val/test governance.  
**Công việc:** kiểm tra Phase 1 source SHA/`acceptance.json`; verify original CSV khớp nguồn; chốt exact duplicate policy, reference split ratio, numbering convention và metric names; điều chỉnh `configs/experiment.yaml` bằng PR có review.  
**Deliverables:** `docs/phase_02_protocol.md`, frozen config + SHA, `dataset_intake.json` aggregate.  
**AC:** source bất đồng SHA → STOP; PR có cả N2/N3 review, không còn thông số split mơ hồ.

### P2-01 — Deterministic split + audit (N2 owner, N1 reviewer)

**Kiến thức:** stable sort, group-aware boundaries, fingerprinting, leakage, reproducible seeds.  
**File:** `src/fraud_detection/preprocessing/split.py`, `manifest.py`, `tests/test_split.py`; notebook `02_split_and_leakage_audit.ipynb`.  
**AC:** train/val/test đầy đủ, no-row-loss, disjoint IDs/fingerprints, same-Time group không bị tách; Time monotonic; positive coverage; manifest có counts+hash; all-negative split fail closed.

### P2-02 — Leakage-safe preprocessors (N2 owner, N3 reviewer)

**Kiến thức:** `fit` vs `transform`, StandardScaler, missing data, `sklearn.Pipeline`, `imblearn.Pipeline`.  
**File:** `src/fraud_detection/preprocessing/pipeline.py`, `tests/test_preprocessing.py`.  
**AC:** có test giá trị cực trị ở validation **không làm đổi** mean/std scaler đã fit train; Class không lọt X; transformations không sửa raw; val/test giữ original counts.

### P2-03 — Evaluation core (N4 owner, N3 reviewer)

**Kiến thức:** probability score, TP/FP/TN/FN, precision, recall, F1/F2, AP, ROC-AUC, PR curve, alert@K.  
**File:** `src/fraud_detection/evaluation/metrics.py`, `thresholds.py`, `tests/test_evaluation.py`.  
**AC:** unit test tiny fixtures với kết quả tính tay; `zero_division` policy; AP không gọi nhầm PR-AUC hình thang; hard fail khi metric không định nghĩa; tie handling; evaluator không truy cập test khi tuning.

### P2-04 — Basic supervised models (N3 owner, N4 reviewer)

**Kiến thức:** prior baseline, sigmoid, logistic loss, class_weight, regularization, score-vs-label.  
**File:** `src/fraud_detection/models/baselines.py`, `src/fraud_detection/pipelines/train.py`, `tests/test_baselines.py`, `03_baseline_models.ipynb`.  
**Thí nghiệm bắt buộc:** Dummy (`strategy='prior'`), Logistic plain, Logistic balanced; trên **cùng primary train/val split**.  
**AC:** AP, PR/ROC, precision/recall/F1/F2, confusion matrix, alert volume, runtime, seed và config tracked; không công bố winner bằng accuracy; test sealed.

### P2-05 — Imbalance experiments (N3 owner, N2 reviewer)

**Kiến thức:** resampling priors, SMOTE, fold-specific k-neighbors, class weighting, CV leakage.  
**Thí nghiệm:** no balancing vs class weight vs train-fold SMOTE (undersampling chỉ optional).  
**File:** `tests/test_imbalance.py`, phần `04_imbalance_experiments.ipynb`.  
**AC:** chứng minh SMOTE chỉ tăng rows ở training folds; val/test distribution không đổi; grid nhỏ và seed cố định; ghi before/after class counts.

### P2-06 — Advanced candidates (N4 owner, N3 reviewer)

**Kiến thức:** XGBoost GBT, scale_pos_weight, unsupervised anomaly scores.  
**Bắt buộc:** XGBoost với `scale_pos_weight` tính từ train, bounded search 6–12 config; kết quả validation.  
**Khuyến khích:** Isolation Forest như *unsupervised* so sánh; thống nhất chiều anomaly score (điểm cao = nguy cơ cao).  
**AC:** mỗi run có split+source+git SHA, hyperparameters, runtime; không dùng val/test để fit; nếu dời IsolationForest phải ghi deferred rõ ràng.

### P2-07 — Threshold & error analysis (N4 owner, N5 phối hợp)

**Kiến thức:** F2 ưu tiên recall, precision/recall vs threshold, false alarms, business trade-off.  
**File:** `05_threshold_and_errors.ipynb`, `threshold_policy.json` aggregate.  
**AC:** threshold chọn trên validation; ghi precision@K, alerts/1000, FP/FN; phân tích slice `Amount` và `Time` (không gán tên nghiệp vụ cho PCA); không tự tuyên bố production-ready.

### P2-08 — Reproducible notebooks & reports (N5 owner, N1 reviewer)

**Kiến thức:** scientific reporting, plotting, clean-room execution, artifact privacy.  
**File:** `docs/phase_02_results.md`, cập nhật `README.md`, `notebooks/README.md`, reports figures; notebook execution test.  
**AC:** toàn bộ notebook chạy từ clean environment; source pinned; biểu đồ/metric dẫn run ID; không commit raw rows, split CSV, prediction rows hoặc model binary tùy tiện.

### P2-09 — Phase 2 acceptance & candidate freeze (N1 owner, cả nhóm review)

**File:** `scripts/phase_02_acceptance.py`, `docs/phase_02_decision.md`, CI workflow cập nhật.  
**AC:** verified source → split checks → baseline → validation scores → threshold → aggregate evidence, fail closed; hosted CI PASS; champion khóa dựa trên validation, **held-out test chưa xem**; các scope deferred ghi thành backlog Phase 3/4.

## 5. Phân vai 5 người

| Người | Role | Tasks sở hữu | Review chéo | Kết quả phải chứng minh |
|---|---|---|---|---|
| **N1** | Tech Lead / Experiment Engineer | P2-00, P2-09; CI/integration | P2-01, P2-08 | Có code acceptance/CI, không chỉ PM |
| **N2** | Data Engineer | P2-01, P2-02 | P2-05 | Split, fingerprint audit, train-only preprocessor |
| **N3** | Supervised ML Engineer | P2-04, P2-05 | P2-00, P2-03, P2-06 | Các baseline công bằng, no leakage, AP/PR |
| **N4** | Data Scientist / Evaluation | P2-03, P2-06, P2-07 | P2-04 | Evaluation đúng, threshold validation-only |
| **N5** | Visualization / Research QA | P2-08, hỗ trợ P2-07 | Các notebook và evidence | Notebook execution, báo cáo truy vết được |

N5 không chỉ làm slide: chịu trách nhiệm notebook/QA/report có thể chạy; N1 không chỉ quản lý: chịu trách nhiệm script acceptance và CI. PR bắt buộc reviewer khác owner.

## 6. Timeline / Critical Path (12 ngày)

| Thời gian | Công việc chính | Song song | Gate |
|---|---|---|---|
| **D1** | Source & config freeze (N1, N2) | Contract metrics (N4), notebook plan (N5) | **G0** source+protocol |
| **D2–D3** | Time-group split + manifest (N2) | Metrics tests (N4), baseline API (N3) | **G1** split no-leakage |
| **D4** | Preprocessors/pipeline (N2) | Eval core done (N4), split notebook (N5) | **G2** pipeline freeze |
| **D5–D6** | Dummy/logistic/balanced (N3) | XGB skeleton (N4), PR reviews (N1) | **G3** baseline reproducible |
| **D7–D8** | SMOTE study (N3) | XGB / IsolationForest (N4), charts (N5) | **G4** model comparison |
| **D9** | Candidate/threshold (N4) | Audit manifest (N2), notebook (N5) | **G5** validation-only choice |
| **D10–D11** | Acceptance/e2e CI (N1), report (N5) | Fix tests/experiment logs (N2–N4) | **G6** hosted evidence |
| **D12** | Whole-team sign-off / freeze | README, backlog | **G7** phase closure |

**Critical path:** G0 → G1 → G2 → G3 → G5 → G6 → G7. Không cho model training bypass split gate để 'chạy cho kịp'.

## 7. Chiến lược Git/PR khuyến nghị

| PR | Branch khuyến nghị | Owner | Dependency | Nội dung |
|---|---|---|---|---|
| P2-A | `feature/p2-01-split-contract` | N2 | G0 | split, manifest, no-leakage tests, split notebook |
| P2-B | `feature/p2-02-evaluation-core` | N4 | G0 | metrics, threshold API skeleton |
| P2-C | `feature/p2-03-preprocessing-pipeline` | N2 | PR A | train-only transformation tests |
| P2-D | `feature/p2-04-supervised-baselines` | N3 | PR A/B/C | model baseline, notebook, evaluation |
| P2-E | `feature/p2-05-imbalanced-candidates` | N3+N4 | PR D | SMOTE, XGB, optional IsolationForest |
| P2-F | `feature/p2-06-acceptance-report` | N1+N5 | PR A–E | notebook checks, evidence and review |

Mỗi PR từ `develop` mới nhất, rebase/fetch sau PR dependency, CI chạy trên PR HEAD. Không force-push nhánh của người khác, không merge khi hosted CI fail dù local PASS. Có thể chia further PR nếu một PR đổi quá nhiều file. Không phải tạo các nhánh này ngay khi viết kế hoạch.

## 8. Folder / artifact contracts đề xuất

```text
configs/
  experiment.yaml                    # update with review
  phase_02_models.yaml               # model grid + seeds
src/fraud_detection/
  preprocessing/
    split.py
    manifest.py
    pipeline.py
  evaluation/
    metrics.py
    thresholds.py
  models/
    baselines.py
    candidates.py
  pipelines/
    train.py
notebooks/
  01_data_profiling.ipynb            # P1 existing
  02_split_and_leakage_audit.ipynb
  03_baseline_models.ipynb
  04_imbalance_experiments.ipynb
  05_threshold_and_errors.ipynb
scripts/
  phase_02_acceptance.py
reports/phase_02/
  model_comparison.md
  decision_log.md
docs/
  phase_02_protocol.md
  phase_02_results.md
  phase_02_decision.md
tests/
  test_split.py
  test_preprocessing.py
  test_evaluation.py
  test_baselines.py
  test_imbalance.py
  test_phase_02_execution.py
artifacts/phase_02/                 # gitignored
  split_manifest.json
  runs/<run_id>/
    run_manifest.json
    validation_metrics.json
    threshold_policy.json
  acceptance.json
```

### 8.1. Mandatory experiment manifest

Tối thiểu: `run_id`, `original_csv_sha256`, `split_sha256`, `config_sha256`, `git_sha`, `python/package_versions`, `seed`, `feature_order`, `train/val counts`, `model_name`, `hyperparameters`, `fit_source=train`, `evaluation_source=validation`, `test_opened=false`, `runtime_seconds`, `validation_metrics`. Đây là schema **đề xuất**, không phải kết quả đã đo.

`model_comparison.csv` cần có: `run_id`, `split_strategy`, `split_sha`, `model`, `balance_strategy`, `ap_val`, `roc_auc_val`, `precision_val`, `recall_val`, `f1_val`, `f2_val`, `threshold_val`, `alerts_val`, `fp_val`, `fn_val`, `runtime_seconds`, `seed`, `git_sha`. Giá trị chưa đo phải là null/N/A, không phải 0 giả.

## 9. Quality gates / test matrix

| Test | Nội dung bắt buộc | Mức |
|---|---|---|
| Split integrity | deterministic, no-row-loss, no-ID-overlap, Time-ties grouped | BLOCKER |
| Cross-split duplicates | không exact full-record fingerprint overlap | BLOCKER |
| Leakage | validation extremes không đổi fitted scaler/imputer | BLOCKER |
| Labels | Class không lọt features, positive class=1 | BLOCKER |
| SMOTE | chỉ fit train/fold, val/test giữ count & class rate | BLOCKER |
| Metrics | AP, F1/F2, confusion, zero-positive corner cases | BLOCKER |
| Threshold | select validation only, tie/NaN handling | BLOCKER |
| Replay | same input+seed+code → same split & metrics tolerance | BLOCKER |
| Notebook | all cells execute root/notebooks, no raw previews in CI artifact | BLOCKER |
| Hosted CI | pytest+ruff pass at PR head; P1 source check retained | BLOCKER |

### 9.1. Definition of Done

- [ ] Source SHA/metadata khớp nguồn Phase 1, verified on current revision.
- [ ] Chronological split deterministic; cùng `Time` không bị tách; train/val/test có 2 lớp; không giao mẫu.
- [ ] Stratified protocol riêng, rõ random state, không trộn với chronological.
- [ ] Model pipeline train-only: scaler/imputer/SMOTE không fit validation/test.
- [ ] Dummy + Logistic + weighted Logistic có kết quả validation và manifest.
- [ ] SMOTE và XGBoost được so sánh trên cùng split, trong giới hạn tài nguyên; Isolation Forest chạy hoặc defer minh bạch.
- [ ] AP, Precision, Recall, F1/F2, ROC-AUC, confusion, alert volume đầy đủ; threshold validation-only.
- [ ] Notebook chạy xuyên suốt và tái lập được từ root và `notebooks/`.
- [ ] Có data/split/model hash, hardware/runtime, package versions, git SHA cho experiment.
- [ ] CI hosted PASS; original-data acceptance có artifact aggregate không chứa raw data.
- [ ] Có 2 reviewer ký candidate; test không được dùng cho tuning; documented limitations.
- [ ] README, notebook index, result report phản ánh đúng việc đã hoàn thành, không ghi số giả.

**Trạng thái:** `DONE` chỉ khi các BLOCKER đạt; `PARTIAL` nếu secondary models bỏ dở nhưng core gate đạt; `BLOCKED` nếu thiếu source validation/hosted CI. Merge PR không đồng nghĩa research acceptance.

## 10. Rủi ro và quyết định quan trọng

| Rủi ro | Ảnh hưởng | Hành động |
|---|---|---|
| Duplicate leakage | AP ảo | group Time + fingerprint overlap hard fail |
| Nhiều score tuning trên val hiếm fraud | Selection bias | freeze grid, giới hạn 6–12 XGB runs, báo cáo uncertainty |
| SMOTE trước split | Leak kinh điển | imblearn Pipeline + automated tests |
| Lẫn AP và trapezoid PR-AUC | Metric không so sánh được | tên metric rõ, unit tests |
| Threshold dựa test | Test trở thành validation | sealed test gating và signature trước khi mở |
| IsolationForest score direction sai | đảo nhãn gian lận | test convention (risk high = score high) |
| Data source offline / job fail | Không reproducible | fail closed, không ghi PASS từ local mặc định |
| Artifact leak transaction rows | Privacy / source terms | whitelist aggregate, sanitize notebooks |
| Spark premature scope | Chậm mô hình | Phase 3 benchmark tách rõ |
| PCA components không diễn giải | Phán đoán nghiệp vụ quá mức | không đặt business labels V1–V28 |

**5 quyết định cần ký trước training:** D0 duplicate policy; D1 stratified reference validation ratio; D2 feature/scaler configuration; D3 bounded model grid/runtime budget; D4 champion selection criteria. Không mở test trước D4.

## 11. Liên kết kiến thức học phần

- **Đề tài #9:** fraud detection mất cân bằng, gợi ý SMOTE, class weight, Isolation Forest, XGBoost, PR-AUC; quy trình thu thập → EDA → làm sạch → features → modeling → evaluation → demo. Yêu cầu benchmark Spark vs đơn máy áp dụng ở Phase 3.
- **Bài giảng `bigdata_analytics_model_regression.pdf`:** Logistic Regression, `train_test_split`, `stratify`, cross-validation; gắn P2-01/P2-04.
- **Bài giảng `bigdata_analytics_preprocess_data.pdf`:** missing values, scaling, PCA, leakage; gắn P2-02 và split gate.
- **Bài giảng/Notebook PySpark:** chuẩn bị cho Phase 3; Phase 2 không lấy tốc độ Spark làm tiêu chí winner model.

Tài liệu tham chiếu:

- [Develop repository](https://github.com/ManhT005/credit-card-fraud-bigdata/tree/develop)
- [Phase 1 merged PR](https://github.com/ManhT005/credit-card-fraud-bigdata/pull/2)
- [Experiment protocol](https://github.com/ManhT005/credit-card-fraud-bigdata/blob/develop/docs/experiment_protocol.md)
- [Experiment config](https://github.com/ManhT005/credit-card-fraud-bigdata/blob/develop/configs/experiment.yaml)
- [Phase 1 acceptance script](https://github.com/ManhT005/credit-card-fraud-bigdata/blob/develop/scripts/phase_01_acceptance.py)
- [Đề tài môn học](https://drive.google.com/file/d/1bHKkSoT1uwLvbT70im-9z-k-TtMjlNgu/view)
- [Bài giảng mô hình](https://drive.google.com/file/d/1p1T5c9S6c747fHPMSvxL2qgCd_8BL4-K/view)
- [Bài giảng tiền xử lý](https://drive.google.com/file/d/1MBpTMxfbYDSN5IV0C_ByVTRj0Xq8zKvG/view)

## 12. Task nên triển khai đầu tiên

**Task:** P2-01 — deterministic split & leakage audit (chỉ bắt đầu sau khi D0/D1 chốt).  
**Owner:** N2; **Reviewers:** N1, N3.  
**Branch đề xuất:** `feature/p2-01-split-contract` từ `develop` mới nhất.  
**PR title:** `feat(phase2): deterministic chronological split and leakage audit`.

1. Thêm `src/fraud_detection/preprocessing/split.py`, `manifest.py` với Time-group handling.
2. Viết tests: tie boundary, duplicate cross-split, no-row-loss, rare/zero-positive cases, seed replay.
3. Tạo notebook `02_split_and_leakage_audit.ipynb` + artifact aggregate và class balance plot.
4. Chạy source gốc đã pin từ Phase 1, lưu manifest với SHA, không commit row-level split.
5. Kiểm tra `pytest`, `ruff`, notebook clean execution và 2 code reviews trước khi merge.

**Exit criteria:** split immutable/reproducible; chronological invariant; class coverage; no duplicate overlap; feature allowlist; full unit tests PASS; chưa sử dụng test data để học/tuning.

> **Mục tiêu cuối Phase 2:** Có một quy trình huấn luyện, đánh giá và chọn ứng viên có thể tái lập, ngăn leakage theo test thực tế — không chỉ vài notebook chứa `.fit()` và `.predict()`.

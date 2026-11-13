# Hướng dẫn tái lập và kiểm chứng

Chạy lệnh từ thư mục gốc của repo. Dùng một virtual environment cho demo và một môi trường riêng cho thực nghiệm. [Cài và chạy demo](../README.md#chạy-demo-từ-bản-clone-sạch)

## 1. Kiểm tra số liệu công bố

Từ bản clone sạch, chạy lệnh sau với Python 3.11. Lệnh chỉ dùng thư viện chuẩn.

```bash
python scripts/phase_05_verify.py
```

Trình kiểm tra đối chiếu số dòng, số ca gian lận, quy tắc chọn candidate, ma trận nhầm lẫn, checksum nguồn và decision hash đã ghi. Với ETL, nó tính lại median từ các lượt chạy và kiểm tra số dòng, số ca gian lận, phân bố giờ/lớp giữa các quy mô.

Để kiểm chứng nguồn gốc của số liệu, đăng nhập GitHub, tải hai ZIP dưới đây và giữ nguyên tệp nén. Artifact Actions có thời hạn lưu giữ. Nếu ZIP đã hết hạn, dùng bản sao có cùng checksum hoặc chạy lại bước 2–3 và kiểm tra kết quả mới.

| ZIP | Nguồn và SHA-256 |
| --- | --- |
| `phase-2-acceptance.zip` | [Run 42364868665 · Artifact 13570879627](https://github.com/ManhT005/credit-card-fraud-bigdata/actions/runs/42364868665/artifacts/13570879627) · `77fde42ecdc3ff1cf11790e535840aea7126f051f9d5c221959c451527b6edc9` |
| `phase-3-acceptance.zip` | [Run 42947881498 · Artifact 13824471016](https://github.com/ManhT005/credit-card-fraud-bigdata/actions/runs/42947881498/artifacts/13824471016) · `80a647efed0065983f1dad286c863b1077c6efc07e5a693df7cf24570fdbdca8` |

```bash
python scripts/phase_05_verify.py --phase2-archive phase-2-acceptance.zip --phase3-archive phase-3-acceptance.zip
```

Kết quả cần có `phase2_archive_verified: true` và `phase3_archive_verified: true`. Script dựng lại nội dung snapshot Phase 2 từ ZIP và so khớp từng byte của hai báo cáo ETL CI. Để dựng lại tệp dashboard trên đĩa, dùng `python scripts/phase_04_snapshot.py phase-2-acceptance.zip`.

## 2. Chạy lại profiling và mô hình

Để khớp với CI, dùng Ubuntu 26.04 x86_64 và CPython 3.11.18. Máy Windows có thể dùng WSL với môi trường Linux tương ứng. Cần truy cập OpenML, ổ đĩa có quyền ghi và Jupyter kernel hoạt động. Dùng bash.

```bash
python3.11 --version
python3.11 -m venv .venv-research
source .venv-research/bin/activate
python -m pip install -r requirements/phase-02-linux-py311.txt
python -m pip install --no-build-isolation --no-deps -e ".[data,ml,notebook,dev]"
python -m pip check
export MPLBACKEND=Agg OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
python scripts/phase_01_acceptance.py
python scripts/phase_02_acceptance.py
cp artifacts/phase_02/candidate_proposal.json artifacts/phase_02-first-proposal.json
python scripts/phase_02_acceptance.py --execute-notebooks
cmp artifacts/phase_02-first-proposal.json artifacts/phase_02/candidate_proposal.json
python scripts/phase_05_verify.py --phase2-dir artifacts/phase_02
```

Phase 1 tự tải ARFF từ OpenML và xác minh nguồn trước khi ghi `data/raw/creditcard.csv`. CSV gốc có SHA-256 `f2de838bd0ef569a700976922711e2955fe057f806822a95a721ca55bdaa8080`. Kết quả chính nằm trong `artifacts/phase_02/`. Chờ `phase2_rerun_verified: true`, candidate `xgboost_06`, decision hash `1602082a03abe686b8c828bc3bbac9711163461fcec65e459f51e6da4dafe00a` và `test_opened: false` trong proposal.

Khi có sai khác, so phiên bản thư viện, hash nguồn, hash split và fingerprint mã với [báo cáo Phase 2](phase_02_results.md). Nếu Jupyter kernel gặp hạn chế socket, `python -m pytest -q -m "not notebook"` chạy nhóm kiểm thử còn lại. CI cung cấp kết quả chạy kernel đầy đủ.

## 3. Chạy lại Spark và pandas

Tiếp tục trong môi trường nghiên cứu đã có CSV và acceptance Phase 1. Cài Java 17, đặt `JAVA_HOME` nếu cần và kiểm tra `java -version`. Bắt đầu ở 1×.

```bash
python -m pip install -r infra/docker/requirements.txt
python -m pip install --no-build-isolation --no-deps -e ".[data,ml,notebook,dev,spark]"
python -m pip check
export SPARK_LOCAL_IP=127.0.0.1
python scripts/phase_03_benchmark.py --scales 1 --repeats 2
python scripts/phase_05_verify.py --benchmark artifacts/phase_03/benchmark.json
```

Để đo cả ba quy mô như báo cáo, chuẩn bị ít nhất 30 GiB trống và chạy `python scripts/phase_03_benchmark.py --scales 1 10 100 --repeats 2`. So kết quả mới với [môi trường và số đo đã công bố](phase_03_results.md). Phép kiểm tái lập yêu cầu khớp dữ liệu, số dòng và phân bố giờ/lớp, đồng thời tính lại median của từng lượt chạy. Thời gian tính bằng giây phụ thuộc vào phần cứng, runtime và cache.

Chạy [Spark standalone với Docker Compose](../infra/docker/README.md) nếu cần tái lập cấu hình hai worker. Kiểm tra đầu ra bằng `python scripts/phase_05_verify.py --benchmark artifacts/phase_03/standalone.json`. Có thể mở `notebooks/06_spark_etl_benchmark.ipynb` để đọc số liệu local vừa tạo.

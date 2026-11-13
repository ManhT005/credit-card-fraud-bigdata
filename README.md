# Credit Card Fraud Detection · Big Data Analytics

Đồ án phát hiện gian lận thẻ tín dụng trên OpenML 1597 và so sánh hiệu năng ETL giữa pandas và Apache Spark. Dashboard Streamlit hiển thị kết quả nghiên cứu từ các tệp tổng hợp đi kèm repo.

**Kết quả hiện tại.** Trên validation theo thời gian, candidate `xgboost_06` đạt average precision **0,839861** và phát hiện **46/56** ca gian lận, với **14** cảnh báo sai. Trong benchmark local, Spark có median ETL thấp hơn pandas ở 10× và 100×. Candidate đang chờ hai reviewer độc lập, held-out test vẫn giữ kín và bản `v1.0.0` đang chờ nghiệm thu.

## Chạy demo từ bản clone sạch

Cần Git, Python 3.11 (CI dùng 3.11.18) và Internet để cài dependency. Demo dùng JSON có sẵn và chạy trên máy cá nhân sau khi cài. Lệnh dưới đây lấy bản đang nghiệm thu. Sau khi phát hành, có thể dùng `--branch v1.0.0` để lấy đúng bản release.

```bash
git clone --branch feature/phase-05-final-acceptance-release https://github.com/ManhT005/credit-card-fraud-bigdata.git
cd credit-card-fraud-bigdata
python -m venv .venv
```

Kích hoạt môi trường bằng lệnh phù hợp với terminal.

| Terminal | Lệnh |
| --- | --- |
| Windows PowerShell | `.\.venv\Scripts\Activate.ps1` |
| Windows Git Bash | `source .venv/Scripts/activate` |
| Linux/macOS | `source .venv/bin/activate` |

```bash
python -m pip install -c requirements/dashboard-constraints.txt -e ".[dashboard]"
python -m pip check
python -m streamlit run dashboard/app.py --server.address 127.0.0.1
```

Mở [http://127.0.0.1:8501](http://127.0.0.1:8501). Nếu cổng đang bận, thêm `--server.port 8502` và mở cổng tương ứng. Nếu PowerShell chặn kích hoạt, dùng `.\.venv\Scripts\python.exe` thay cho `python` ở ba lệnh trên.

| Tab | Điểm kiểm tra khi demo |
| --- | --- |
| **Dataset** | 284.807 giao dịch, 492 ca gian lận và cách chia theo `Time` |
| **Fraud detection** | Đường precision–recall, 11 cấu hình validation, ma trận nhầm lẫn tại ngưỡng F₂ |
| **ETL benchmark** | Số đo local ở 1×, 10×, 100× và số đo CI ở 1× cho Spark local và Docker hai worker |

## Tài liệu và minh chứng

| Tài liệu | Nội dung |
| --- | --- |
| [Kiến trúc](docs/architecture.md) | Luồng dữ liệu, mô hình, ETL, dashboard và CI |
| [Báo cáo thực nghiệm](docs/phase_04_final_report.md) | Kết quả validation, benchmark và giới hạn kết luận |
| [Hướng dẫn tái lập](docs/reproducibility.md) | Đối chiếu artifact CI, chạy lại ML và Spark |
| [Nghiệm thu và phát hành](docs/release_acceptance.md) | CI evidence, điều kiện đóng Phase 5 và tạo tag |
| [Data card](docs/phase_01_data_card.md) | Nguồn, checksum, trường dữ liệu và thông tin quyền sử dụng |
| [Quyết định candidate](docs/phase_02_decision.md) | Decision SHA-256 và hồ sơ review |

## Bố cục repo

| Đường dẫn | Vai trò |
| --- | --- |
| `dashboard/`, `reports/phase_03/` | Ứng dụng Streamlit và JSON tổng hợp |
| `src/fraud_detection/`, `configs/` | Nạp dữ liệu, chia tập, huấn luyện và đánh giá |
| `src/fraud_benchmarks/`, `infra/docker/` | ETL pandas/Spark và Spark standalone |
| `scripts/`, `notebooks/` | Lệnh chạy lại, kiểm chứng và phân tích |
| `tests/`, `.github/workflows/` | Kiểm thử, lint và minh chứng CI |
| `data/`, `artifacts/` | Dữ liệu tải về và đầu ra tái lập, được Git bỏ qua |

Phần mềm dùng [giấy phép MIT](LICENSE). Điều khoản sử dụng dữ liệu nguồn được ghi trong [data card](docs/phase_01_data_card.md).

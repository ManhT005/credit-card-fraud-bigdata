# Lệnh chạy từ thư mục gốc

| Lệnh | Công việc |
| --- | --- |
| `python scripts/phase_01_acceptance.py` | Tải và xác minh OpenML 1597, profile CSV, chạy notebook Phase 1 |
| `python scripts/phase_02_acceptance.py --execute-notebooks` | Chạy hai protocol validation và bốn notebook ở hai thư mục |
| `python scripts/phase_03_benchmark.py --scales 1 --repeats 2` | Chạy pandas và Spark trên dữ liệu gốc |
| `python scripts/phase_04_snapshot.py PATH_TO_ZIP` | Tạo lại JSON dashboard từ artifact Phase 2 đã pin |
| `python scripts/phase_05_verify.py --help` | Kiểm chứng artifact và kết quả tái lập với số liệu đã công bố |
| `python scripts/spark_inspection.py` | Kiểm tra nhanh môi trường Spark |

[Hướng dẫn cài đặt và tái lập](../docs/reproducibility.md)

# Báo cáo tổng kết · Phát hiện gian lận thẻ tín dụng

## Mục tiêu và dữ liệu

Đồ án trả lời hai câu hỏi. Mô hình xếp hạng giao dịch gian lận hiệu quả đến
mức nào khi số ca gian lận rất ít? Thời gian ETL thay đổi ra sao khi chuyển
từ pandas sang Spark ở các quy mô đầu vào khác nhau?

OpenML 1597 có **284.807 giao dịch**, trong đó **492** giao dịch gian lận
(**0,173%**). Nhóm giữ 1.081 bản ghi trùng và không để bản ghi trùng xuất hiện
ở nhiều tập. Quy trình chính chia theo `Time` thành train, validation và test.
Các phép biến đổi có học tham số và SMOTE chỉ dùng dữ liệu train.
[Data card](phase_01_data_card.md) · [Quy trình đánh giá](phase_02_protocol.md)

## Kết quả mô hình trên validation

Nhóm so sánh 11 cấu hình từ Dummy, Logistic Regression, XGBoost và Isolation
Forest. Quy tắc chọn candidate ưu tiên average precision, dùng F₂ để phá hòa,
sau đó dùng tên cấu hình. Mỗi mô hình chọn ngưỡng tối đa F₂ trên validation.

Candidate **`xgboost_06`** có AP **0,839861**, precision **0,766667**,
recall **0,821429** và F₂ **0,809859**. Ở ngưỡng **0,086045**, mô hình phát
hiện **46/56** ca gian lận trong tập validation, bỏ sót **10** ca và phát
**14** cảnh báo sai trên **42.722** giao dịch.

Decision SHA-256
`1602082a03abe686b8c828bc3bbac9711163461fcec65e459f51e6da4dafe00a`
vẫn chờ hai reviewer độc lập. Test set giữ kín. Tập validation chỉ có
56 ca gian lận và dữ liệu nguồn bao phủ một cửa sổ thời gian ngắn, nên
kết quả chưa xác lập hiệu quả trên giao dịch tương lai.
[Bảng kết quả](phase_02_results.md) · [Hồ sơ quyết định](phase_02_decision.md)

## Kết quả ETL

| Quy mô | Số giao dịch | pandas (giây) | Spark local[2] (giây) |
|---|---:|---:|---:|
| 1× | 284.807 | 2,526 | 2,987 |
| 10× | 2.848.070 | 22,813 | 15,096 |
| 100× | 28.480.700 | 235,817 | 129,417 |

Bảng ghi median của hai lượt chạy mỗi engine tại từng quy mô trên cùng máy.
Spark có thời gian thấp hơn ở 10× và 100× trong thí nghiệm này. Timer đo phần
đọc CSV, tạo đặc trưng giờ và ghi Snappy Parquet. Đầu ra đã qua kiểm tra
schema, danh tính giao dịch, tổng số ca gian lận và phân bố giờ/lớp.
Dữ liệu nhân bản chỉ dùng để đo ETL. CI kiểm tra Docker với hai worker ở 1×.
[Báo cáo Phase 3](phase_03_results.md)

## Chạy và trình bày demo

Từ thư mục gốc, cài dashboard và chạy ứng dụng.

```bash
python -m pip install -e ".[dashboard]"
python -m streamlit run dashboard/app.py
```

1. Mở **Dataset**, chỉ ra tỷ lệ gian lận 0,173% và cách chia theo thời gian.
2. Mở **Fraud detection**, đọc đường precision–recall và giải thích 14 cảnh
   báo sai, 10 ca bỏ sót tại ngưỡng validation.
3. Mở **ETL benchmark**, so sánh 1×, 10× và 100× ở chế độ local. Chuyển sang
   **CI · Docker two workers · 1×** để trình bày phạm vi xác minh cluster.

Dashboard đọc JSON tổng hợp đã đưa vào repo, nên bản clone sạch có thể demo
ngay sau khi cài dependency. Để tái tạo snapshot Phase 2, tải artifact
`13570879627` từ [Actions run 42364868665](https://github.com/ManhT005/credit-card-fraud-bigdata/actions/runs/42364868665)
và chạy `python scripts/phase_04_snapshot.py path/to/artifact.zip`.
Script xác minh SHA-256 và trích các số liệu, đường PR tổng hợp từ validation.
`reports/phase_03/` chứa các báo cáo benchmark mà dashboard đọc trực tiếp.

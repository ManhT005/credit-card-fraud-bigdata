# Nghiệm thu và phát hành v1.0.0

Trạng thái **chờ nghiệm thu**. Gói P5-05 gồm tài liệu, demo và công cụ kiểm chứng kết quả đã công bố. Điều kiện nghiên cứu nằm trong [hồ sơ quyết định candidate](phase_02_decision.md).

## Evidence CI

| Phạm vi | Revision và kết quả xác minh | Evidence |
| --- | --- | --- |
| Phase 2 · Validation theo thời gian và tham chiếu | PR head `62f5108b511857fd96ac30ab53cb96a7c8090333`, checkout `d615be88b585fc2bbf6a64881dee643f32a77386`. Hai lần chạy tạo cùng proposal, tám lần chạy notebook đạt. | [Run 42364868665](https://github.com/ManhT005/credit-card-fraud-bigdata/actions/runs/42364868665) · [Artifact 13570879627](https://github.com/ManhT005/credit-card-fraud-bigdata/actions/runs/42364868665/artifacts/13570879627) |
| Phase 3 · ETL 1× | Revision `3bec3b0c689973b3b2b8b54bce0a5f08d64322be`. Local và Docker hai worker đều đạt parity trên dữ liệu gốc. | [Run 42947881498](https://github.com/ManhT005/credit-card-fraud-bigdata/actions/runs/42947881498) · [Artifact 13824471016](https://github.com/ManhT005/credit-card-fraud-bigdata/actions/runs/42947881498/artifacts/13824471016) |
| Phase 4 · Dashboard và 5 job nền | PR #5 head `ed45efaf43811dbbf35d1aa38f9d02cd772e2db3` và merge commit `bd3aa42fe4665e39d1c736324708269ab67ff0a2`. | [PR run 43442035772](https://github.com/ManhT005/credit-card-fraud-bigdata/actions/runs/43442035772) · [develop run 43446305514](https://github.com/ManhT005/credit-card-fraud-bigdata/actions/runs/43446305514) |

Bảng trên ghi các mốc nguồn. CI của gói P5-05 chạy trên [nhánh nghiệm thu](https://github.com/ManhT005/credit-card-fraud-bigdata/actions/workflows/ci.yml?query=branch%3Afeature%2Fphase-05-final-acceptance-release). Mở run trên SHA cần nghiệm thu và kiểm tra đủ 5 job.

| Job | Evidence cần kiểm tra |
| --- | --- |
| `tests` | Pytest và Ruff đạt |
| `phase-1-acceptance` | `phase-1-acceptance/acceptance.json`, provenance OpenML và notebook đã chạy |
| `phase-2-acceptance` | `phase-2-acceptance/`, hai proposal trùng nhau, đối chiếu kết quả validation và tám notebook |
| `phase-3-acceptance` | `phase-3-acceptance/`, `benchmark.json` và `standalone.json` ở 1×, đối chiếu parity |
| `phase-4-dashboard` | `release-demo-acceptance/`, thông tin run và checkout, kết quả đối chiếu JSON, Streamlit health check và kiểm thử ba tab |

[Hướng dẫn tải và đối chiếu checksum các ZIP nguồn](reproducibility.md#1-kiểm-tra-số-liệu-công-bố)

## Điều kiện tạo tag

1. Hai reviewer độc lập ký duyệt decision SHA-256 và khóa candidate cùng ngưỡng đã chọn trên validation. [Decision record](phase_02_decision.md)
2. Chạy đánh giá held-out theo protocol đã khóa sau khi đủ sign-off. Cập nhật kết quả tổng hợp, báo cáo và dashboard theo kết quả được duyệt.
3. Tái lập từ bản clone sạch và đối chiếu số liệu công bố. Xác minh cả 5 job thành công trên đúng commit đã merge vào `develop`.
4. Ghi SHA đầy đủ và URL run thành công của commit đó vào release notes. Tạo annotated tag trên chính SHA này, rồi đẩy tag lên GitHub.

```bash
git fetch origin develop --tags
RELEASE_SHA=REPLACE_WITH_FULL_ACCEPTED_DEVELOP_SHA
git merge-base --is-ancestor "$RELEASE_SHA" origin/develop &&
  git tag -a v1.0.0 "$RELEASE_SHA" -m "Credit Card Fraud Big Data Analytics v1.0.0" &&
  git push origin refs/tags/v1.0.0
git ls-remote --tags origin 'refs/tags/v1.0.0*'
```

Dòng `refs/tags/v1.0.0^{}` phải trỏ đến SHA đã nghiệm thu. Ghi phạm vi kết quả, link báo cáo, hướng dẫn demo và CI trong release notes. Bản phát hành gồm mã, tài liệu và JSON tổng hợp. Dữ liệu giao dịch, dự đoán theo từng dòng và model binaries nằm ngoài gói phát hành.

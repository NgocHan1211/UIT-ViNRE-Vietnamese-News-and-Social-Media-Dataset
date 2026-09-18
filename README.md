# DS107 - Nhóm 12: Code Submission

**Tên đề tài:** Xây dựng bộ dữ liệu, mô hình phân loại chủ đề và phân tích phản ứng người dùng đối với bài đăng có liên quan đến tin tức trên mạng xã hội Việt Nam.  
**Môn học:** DS107 - Tư duy tính toán cho khoa học dữ liệu.  
**GVHD:** TS Nguyễn Văn Kiệt, CN. Trần Quốc Khánh.  
**Nhóm thực hiện:** Nhóm 12.

## 1. Mục tiêu gói nộp

Gói `DS107_Nhom12_Code.zip` cung cấp mã nguồn và các dữ liệu/artifact nhẹ để giảng viên có thể kiểm tra, cài đặt môi trường và chạy lại demo Streamlit của dự án.

Các phần chính trong gói nộp:

- Mã nguồn crawl bài đăng Facebook công khai.
- Mã nguồn xây dựng master dataset, tạo dữ liệu cuối, chia train/validation/test.
- Mã nguồn kiểm tra độ đồng thuận gán nhãn (IAA).
- Mã nguồn huấn luyện và tổng hợp kết quả traditional ML.
- Dashboard Streamlit mới tại `src/dashboard/`.
- Các báo cáo, bảng kết quả và dữ liệu đầu ra đã chọn trong `data_outputs/` và `docs/`.

Các trọng số mô hình lớn (`*.joblib`, `*.safetensors`, `*.pt`, `*.bin`) không được đóng gói trong file code zip. Nếu cần chạy đầy đủ phần dự đoán mô hình ở dashboard, vui lòng dùng thêm file model artifact nộp riêng.

## 2. Cấu trúc thư mục

```text
DS107_Nhom12_Code/
├── README.md
├── requirements.txt
├── requirements_modeling.txt
├── CHECKLIST_STATUS.md
├── configs/
│   └── crawl_config.example.json
├── data_outputs/
│   ├── 02_master_dataset/
│   ├── 06_final_master_data/
│   ├── 07_cleaned_splits/
│   └── 08_modeling_results/
├── data_samples/
├── docs/
├── logs/
└── src/
    ├── crawl/
    ├── dataset/
    ├── iaa/
    ├── training/
    │   └── traditional_ml/
    └── dashboard/
        ├── app.py
        ├── components/
        ├── data_loader.py
        ├── visolex_normalizer.py
        ├── viz_theme.py
        ├── config.json
        ├── Public_Response_Streamlit_Enriched.csv
        ├── taxonomy_mapping_used.csv
        ├── data/
        │   └── visolex_dictionary.json
        └── 08_Modeling_Results/
```

## 3. Cài đặt môi trường

Khuyến nghị dùng Python 3.9 trở lên.

```bash
cd DS107_Nhom12_Code
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Trên Windows:

```bash
cd DS107_Nhom12_Code
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Nếu cần chạy crawler bằng Playwright:

```bash
python -m playwright install chromium
```

## 4. Chạy demo dashboard

Dashboard Streamlit mới nằm trong `src/dashboard/`.

```bash
cd src/dashboard
streamlit run app.py
```

Sau khi khởi chạy, Streamlit sẽ in ra địa chỉ local, thường là:

```text
http://localhost:8501
```

Dashboard đã có sẵn các file dữ liệu cần thiết để chạy phần trực quan hóa:

```text
src/dashboard/Public_Response_Streamlit_Enriched.csv
src/dashboard/taxonomy_mapping_used.csv
src/dashboard/data/visolex_dictionary.json
```

Các tab tổng quan, phân tích rủi ro, phân tích phản ứng người dùng và các biểu đồ dữ liệu có thể chạy ngay sau khi cài đặt requirements.

Quy trình tái lập demo nhanh cho giảng viên:

1. Giải nén `DS107_Nhom12_Code.zip`.
2. Tạo môi trường ảo và cài `requirements.txt`.
3. Nếu cần demo đầy đủ mô hình dự đoán, giải nén thêm model artifact nộp riêng vào project root.
4. Chạy dashboard bằng lệnh `streamlit run app.py` trong thư mục `src/dashboard/`.

## 5. Khôi phục model artifact để chạy đầy đủ Tab AI Content Simulator

Do dung lượng lớn, code zip không kèm trọng số traditional ML và checkpoint Transformer. Để chạy đầy đủ phần dự đoán mô hình trong dashboard, giải nén file model artifact nộp riêng vào đúng thư mục gốc của project sao cho tồn tại đường dẫn:

```text
src/dashboard/08_Modeling_Results/
```

Cấu trúc model artifact kỳ vọng:

```text
src/dashboard/08_Modeling_Results/traditional_ml_hpo_deep/
src/dashboard/08_Modeling_Results/phobert_kb4_best_model/
src/dashboard/08_Modeling_Results/xlmr_best_model_kb5/
src/dashboard/08_Modeling_Results/mbert_best_model_kb4/
```

Nếu chưa khôi phục model artifact, dashboard vẫn chạy được các phần phân tích dữ liệu. Riêng thao tác dự đoán bằng mô hình sẽ hiện thông báo thiếu trọng số/checkpoint và hướng dẫn vị trí đặt file.

## 6. Chạy lại một số bước xử lý dữ liệu và mô hình

Tạo lại các split train/validation/test:

```bash
python src/dataset/create_train_val_test_splits.py
```

Kiểm tra IAA:

```bash
python src/iaa/verify_iaa.py
```

Kiểm tra dữ liệu đầu vào cho traditional ML:

```bash
python src/training/traditional_ml/train_traditional_models.py --validate_only
```

Train nhanh traditional ML baseline:

```bash
python src/training/traditional_ml/train_traditional_models.py --tuning_mode fast
```

Kết quả, báo cáo và log đã chọn được lưu sẵn trong:

```text
data_outputs/
docs/
logs/
```

Gói nộp không bao gồm môi trường ảo, cookie, token, browser profile, raw crawl folder đầy đủ hoặc trọng số mô hình lớn trong code zip.

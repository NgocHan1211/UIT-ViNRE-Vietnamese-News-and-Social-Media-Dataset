# Hướng dẫn chạy Dashboard Streamlit

Dashboard này là giao diện demo trực quan hóa dữ liệu và mô phỏng phân loại chủ đề cho đề tài DS107 của Nhóm 12.

## 1. Cài đặt

Từ thư mục gốc của gói nộp:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Hoặc chỉ cài requirements riêng của dashboard:

```bash
cd src/dashboard
pip install -r requirements.txt
```

## 2. Chạy dashboard

```bash
cd src/dashboard
streamlit run app.py
```

Địa chỉ mặc định:

```text
http://localhost:8501
```

## 3. Dữ liệu đi kèm

Dashboard sử dụng các file có sẵn trong thư mục này:

```text
Public_Response_Streamlit_Enriched.csv
taxonomy_mapping_used.csv
data/visolex_dictionary.json
config.json
```

Nếu cần tái tạo file dữ liệu đã làm giàu từ dữ liệu thô, chạy:

```bash
python data_loader.py
```

Lưu ý: lệnh này cần file dữ liệu thô đúng theo đường dẫn cấu hình trong `config.json`.

## 4. Model artifacts cho Tab AI Content Simulator

Gói code không kèm trọng số mô hình lớn. Để chạy đầy đủ phần dự đoán, giải nén model artifact nộp riêng sao cho có cấu trúc:

```text
src/dashboard/08_Modeling_Results/traditional_ml_hpo_deep/
src/dashboard/08_Modeling_Results/phobert_kb4_best_model/
src/dashboard/08_Modeling_Results/xlmr_best_model_kb5/
src/dashboard/08_Modeling_Results/mbert_best_model_kb4/
```

Nếu chưa có model artifact, các tab phân tích dữ liệu vẫn chạy bình thường. Khi bấm dự đoán trong Tab AI Content Simulator, dashboard sẽ báo rõ model/checkpoint nào còn thiếu.

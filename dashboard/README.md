# 📊 Hướng dẫn Cài đặt & Vận hành: Social Media Insights Dashboard

Tài liệu này hướng dẫn chi tiết cách thiết lập môi trường Python, cài đặt thư viện phụ thuộc, chuẩn bị dữ liệu và khởi chạy ứng dụng Dashboard Phân tích Chủ đề Mạng Xã hội.

---

## 🗂️ Cấu trúc thư mục mã nguồn
Trước khi bắt đầu, hãy đảm bảo thư mục của bạn chứa các tệp mã nguồn cốt lõi sau:
*   `app.py`: Mã nguồn chính của ứng dụng Streamlit (chứa cấu trúc các Tab phân tích và bộ lọc).
*   `viz_theme.py`: Module cấu hình giao diện biểu đồ (NYT/Editorial paper-theme) cho Plotly.
*   `requirements.txt`: Danh sách các thư viện Python cần cài đặt.

---

## 🛠️ Bước 1: Cài đặt Môi trường Python

Ứng dụng yêu cầu **Python phiên bản từ 3.8 trở lên**.

### 1. Tạo môi trường ảo (Khuyến nghị)
Tạo môi trường ảo độc lập giúp tránh xung đột phiên bản thư viện giữa các dự án trên máy tính của bạn:

*   **Trên macOS/Linux:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
*   **Trên Windows:**
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

### 2. Cài đặt các thư viện cần thiết
Chạy lệnh sau để tự động tải và cài đặt toàn bộ các thư viện phụ thuộc (Streamlit, Pandas, Plotly, Joblib, v.v.):
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 💾 Bước 2: Chuẩn bị Dữ liệu & Trọng số Mô hình

Để ứng dụng đọc dữ liệu và tải các mô hình phân loại chính xác, cấu trúc tệp cần được sắp xếp đúng như sau:

1. **Tệp Dữ liệu Phân tích (Bắt buộc)**:
   * Đặt tệp dữ liệu đã làm sạch và làm giàu **`Public_Response_Streamlit_Enriched.csv`** nằm chung thư mục với tệp `app.py`.
   * Đặt tệp ánh xạ nhãn chủ đề **`taxonomy_mapping_used.csv`** ở cùng thư mục để hệ thống dịch tên chủ đề sang tiếng Anh chuẩn hóa trên giao diện.

2. **Thư mục Mô hình máy học (Model Zoo - Bắt buộc cho Tab 4)**:
   * Bản phân tích tích hợp **7 mô hình** đã huấn luyện bao gồm 4 mô hình truyền thống (Logistic Regression, Random Forest, XGBoost, Linear SVC) và 3 mô hình Deep Learning (mBERT, PhoBERT, XLM-R).
   * **Mô hình truyền thống**: Nằm tại `08_Modeling_Results/traditional_ml_hpo_deep/model_zoo/` (chứa tệp `model_registry.json` và các thư mục con chứa các tệp `.joblib` tương ứng).
   * **Mô hình Deep Learning (Transformers)**: Nằm tại các thư mục con tương ứng trong `08_Modeling_Results/` (ví dụ: `xlmr_best_model_kb5/`, `phobert_kb4_best_model/`, `mbert_best_model_kb4/`). Thư viện `torch` và `transformers` phục vụ chạy suy luận các mô hình này đã được thêm sẵn vào `requirements.txt`.
   * **⚠️ Lưu ý quan trọng cho macOS:** Mô hình XGBoost yêu cầu thư viện OpenMP. Nếu bạn chạy trên máy Mac và gặp lỗi load XGBoost, hãy mở Terminal và cài đặt thư viện hệ thống qua lệnh:
     ```bash
     brew install libomp
     ```

---

## 🚀 Bước 3: Vận hành ứng dụng

Sau khi đã hoàn thành Bước 1 và Bước 2, hãy mở Terminal (Command Prompt) tại thư mục chứa tệp `app.py` và chạy lệnh sau:

```bash
streamlit run app.py
```

### 🌍 Truy cập Giao diện
Sau khi lệnh chạy thành công, Streamlit sẽ khởi chạy máy chủ cục bộ và tự động mở trình duyệt web của bạn. Nếu không tự động mở, bạn có thể truy cập thủ công qua địa chỉ:
👉 **`http://localhost:8501`**

---

## 📖 Hướng dẫn nhanh về các Tab chức năng trên Giao diện

Ứng dụng bao gồm 4 tab chức năng được thiết kế theo phong cách Báo chí học thuật (Editorial UI):

1. **🗞️ 1. The Front Page (Tổng quan)**:
   * Cung cấp các chỉ số KPI vĩ mô về bài đăng và tương tác.
   * Bản tin tóm tắt biến động thảo luận hàng ngày và điểm sáng/rủi ro nổi bật của dữ liệu.
   * Biểu đồ phân bổ chủ đề thảo luận tổng quan.
2. **🚨 2. Threat Radar (Rủi ro & Khủng hoảng)**:
   * **Phân tích Châm biếm (Sarcasm Alert)**: Nhận diện phản hồi mỉa mai, chế giễu hoặc hoài nghi trên các chủ đề nghiêm túc.
   * **Chỉ số Tranh cãi (Controversy Index)**: Bản đồ bong bóng dư luận tương quan Polarity và Tranh cãi cùng danh sách top bài viết gây tranh luận nhất.
   * **Phân tích Bias & Spam**: Phát hiện dấu hiệu tập trung bài viết đột biến/spam từ một số lượng nhỏ Page (Concentration Ratio).
3. **📊 3. Audience Pulse (Hành vi & Tương tác)**:
   * **Phân tích Phản ứng**: Cơ cấu cảm xúc chi tiết (Tích cực, Tiêu cực, Phân cực) cho từng chủ đề.
   * **Hiệu suất Lan truyền (Virality Ledger)**: Xếp hạng bài viết có tương tác cao nhất, hỗ trợ chuẩn hóa tương tác trên 100k Followers.
   * **Phân tích Thời gian & Tra cứu (Temporal Trends & Archives)**: Biểu đồ nhiệt (Heatmap) nhận diện khung giờ có tương tác trung vị cao nhất theo dữ liệu, xu hướng ngày thường vs cuối tuần, và tra cứu dữ liệu bài viết.
4. **✨ 4. AI Content Simulator (Dự báo ML)**:
   * Nhập nội dung bài đăng dự thảo để hệ thống sử dụng đồng thời 7 mô hình máy học (4 truyền thống và 3 học sâu) dự báo chủ đề.
   * Kết quả từ mô hình ngôn ngữ tốt nhất (XLM-R) được trình bày đặc cách trong Spotlight Card nổi bật ở đầu trang và được ưu tiên làm tham chiếu đối chiếu thống kê lịch sử (mức độ tranh cãi & tỷ lệ châm biếm).


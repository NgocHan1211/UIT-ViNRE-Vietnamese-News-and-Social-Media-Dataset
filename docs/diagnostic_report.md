# 📊 BÁO CÁO DIAGNOSTIC EDA: SỰ CỐ DATA LEAKAGE & BIAS
**Người thực hiện:** Senior Data Scientist / Data Detective  
**Vấn đề:** Sự cố mất nhãn (Data Leakage) sau khi thực hiện Text Matching Join giữa CSV và JSON.

---

## PHẦN 1: KẾT QUẢ BẮT BỆNH (DIAGNOSTIC EDA)

Sau khi thực thi các bước rà soát dữ liệu gốc, phân tích nguồn JSON, và thực hiện `LEFT JOIN`, dưới đây là các con số sự thật đằng sau sự cố "mất nhãn":

### 1. Phân bổ gốc trong CSV (Original Distribution)
Tập dữ liệu CSV (sau khi lọc bỏ các dòng Comment, chỉ giữ lại Post) có tổng cộng **2.636 bài viết**. Tuy nhiên, phân bổ nhãn **trước khi Join** đã vô cùng mất cân bằng:

| Nhãn Chủ Đề (Label) | Số lượng | Tỷ lệ phần trăm |
| :--- | :--- | :--- |
| **Tin tức xã hội** | 2.569 | **98.05%** |
| Thể thao | 38 | 1.45% |
| Social Slang | 10 | 0.38% |
| Phim ảnh | 2 | 0.07% |
| Âm nhạc | 1 | 0.04% |

**👉 Nhận xét:** Sự thống trị của nhãn "Tin tức xã hội" không phải do lỗi Join, mà **bản chất tập CSV gốc đã lệch 98%** về nhãn này. 4 nhãn còn lại gộp chung chưa tới 2% tổng số bài.

### 2. Phân tích Nguồn JSON (JSON Source Profiling)
Quét qua thư mục `json-crawl-data/`, hệ thống phát hiện **27 file** (cả `.json` và `.jsonl`) thuộc về các Fanpage như: `K14vn`, `beatvn.network`, `Theanh28`, `BongDaS2`, `Ghien.Am.Nhac.Production`, `w2wmovie`, v.v...

**Tuy nhiên, có một lỗ hổng cực lớn trong tập JSON thô này:**
Khi đào sâu vào nội dung của 38 bài "Thể thao" và 10 bài "Social Slang" trong CSV, tôi phát hiện **100% các bài này đều mang hashtag `#trollbongro` hoặc `#ghienbongro`** (các Fanpage chuyên về Bóng rổ). Nhưng trong thư mục JSON, **HOÀN TOÀN KHÔNG CÓ** file `posts_trollbongro.json` hay `posts_ghienbongro.json`.

### 3. Phân tích Rò rỉ (Leakage Analysis via Left Join)
Bằng phương pháp `LEFT JOIN` và chuẩn hóa Text Matching, kết quả rớt (Failed to join) như sau:
* Tổng số bài không tìm thấy JSON khớp: **557 bài**.
* Tỷ lệ rớt theo từng nhãn:
  * Thể thao: Rớt 38/38 (**100%**)
  * Social Slang: Rớt 10/10 (**100%**)
  * Tin tức xã hội: Rớt 502/2569 (19.54%)
  * Phim ảnh: Rớt 0/2 (**0%**) - 2 bài Phim ảnh khớp thành công.
  * Âm nhạc: Rớt 0/1 (**0%**) - 1 bài Âm nhạc khớp thành công.

---

## PHẦN 2: KẾT LUẬN & QUYẾT ĐỊNH PIPELINE MỚI

### 🔍 Nguyên nhân cốt lõi (Root Cause)
Sự biến mất của 4 nhãn không phải do thuật toán dở, mà đến từ **2 nguyên nhân cộng gộp**:
1. **Bias từ trong trứng nước:** Tập CSV gốc bị lệch 98% cho "Tin tức xã hội", khiến mọi phép Join đều sẽ đổ ra biển "Tin tức xã hội".
2. **Missing Source Data (Dữ liệu rác/thiếu):** 100% các bài Thể thao (bóng rổ) và Social Slang bị rớt là do **nguồn JSON chưa từng được crawl** cho Fanpage `trollbongro` và `ghienbongro`. Việc tìm kiếm dữ liệu siêu dữ liệu cho các bài này trong đống JSON hiện tại là vô vọng (Zero Match). Thuật toán không cứng nhắc, mà do dữ liệu JSON bị "lủng".

### 💡 Quyết định Xây dựng Pipeline Mới (Decision)
Do JSON bị thiếu hẳn file gốc, Text Match dù Fuzzy đến đâu cũng không thể vớt bài Thể thao/Social Slang (vì làm gì có dữ liệu mà vớt!). Do đó, tôi đề xuất **Kiến trúc Pipeline Tách luồng (Bifurcated Data Pipeline)**:

**Luồng 1: Training AI (Giữ nguyên vẹn 100% Label)**
* **Hành động:** Chỉ dùng file `train.csv` & `test.csv` gốc. **BỎ QUA TÍCH HỢP JSON** cho tác vụ Huấn luyện AI.
* **Lý do:** NLP (Text Classification) chỉ cần `content`. Việc Join JSON bị hụt bài sẽ làm AI mất đi cơ hội học các mẫu câu của 4 nhãn thiểu số kia.

**Luồng 2: Toán học Cảm xúc & Insight Phân tích (Sử dụng Fuzzy Matching)**
* **Hành động:** Xây dựng hệ thống Exact Match + Fuzzy Match (bằng **TF-IDF Cosine Similarity > 0.85**) để Join 2082 bài thành công. Phần Toán học cảm xúc (Reactions/Shares) sẽ **chỉ phân tích trên 2082 bài có JSON**, chấp nhận việc Insight sẽ phản ánh góc nhìn của nhóm "Tin tức xã hội".

Đoạn code Pipeline tích hợp TF-IDF Fuzzy Match đã được lưu tại `src/robust_pipeline.py`.

# Phân tích lỗi Chuyên sâu cho Nhóm Mô hình Tiền huấn luyện (Pre-trained Models)

Báo cáo chi tiết này được kết xuất dựa trên dữ liệu dự đoán thực tế của nhóm mô hình Deep Learning Transformer phục vụ chương đối sánh tương phản với nhóm mô hình Baseline truyền thống.

## 1. Tổng quan Lỗi Định lượng (Per-Model Error Overview)

| Mô hình (Model) | Kịch bản dữ liệu (Best Scenario) | Tổng số mẫu | Số ca đoán sai | Tỷ lệ lỗi tổng (Error Rate) |
| :--- | :---: | :---: | :---: | :---: |
| PhoBERT | 04_Full_Clean_KB4 | 838 | 176 | 21.00% |
| mBERT | 04_Full_Clean_KB4 | 838 | 185 | 22.08% |
| XLM-RoBERTa | 05_Balanced_KB5 | 838 | 174 | 20.76% |

## 2. Phân tích Thuộc tính 1: Độ dài văn bản (Text Length)
* **Biểu đồ trực quan tương ứng:** `error_by_text_length_pretrained.png`

| Mô hình | Phân đoạn độ dài | Tổng số mẫu | Số ca sai | Tỷ lệ lỗi nhóm |
| :--- | :---: | :---: | :---: | :---: |
| PhoBERT | short | 34 | 11 | 32.35% |
| PhoBERT | medium | 638 | 135 | 21.16% |
| PhoBERT | long | 166 | 30 | 18.07% |
| mBERT | short | 34 | 12 | 35.29% |
| mBERT | medium | 638 | 140 | 21.94% |
| mBERT | long | 166 | 33 | 19.88% |
| XLM-RoBERTa | short | 34 | 12 | 35.29% |
| XLM-RoBERTa | medium | 638 | 134 | 21.00% |
| XLM-RoBERTa | long | 166 | 28 | 16.87% |

###  Nhận xét hệ thống về Độ dài văn bản:
So với nhóm mô hình Baseline (vốn ghi nhận tỷ lệ lỗi ở phân đoạn văn bản dài chạm ngưỡng nguy hiểm `32.14%`), cả ba mô hình tiền huấn luyện Transformer đều kiểm soát lỗi phân đoạn câu dài rất ấn tượng. Đặc biệt, nhờ cơ chế **Self-Attention** giúp lưu giữ tốt ngữ cảnh đường dài, các mô hình này không bị hiện tượng loãng thông tin ma trận đặc trưng như TF-IDF của Baseline khi đối mặt với các bài đăng mạng xã hội dài và nhiều tạp nhiễu kể lể.

## 3. Phân tích Thuộc tính 2: Mật độ từ phi chuẩn và Teencode (NSW Density)
* **Biểu đồ trực quan tương ứng:** `nsw_density_correct_vs_wrong_pretrained.png`

| Mô hình | Phân nhóm dự đoán | Mật độ NSW trung bình | Số lượng mẫu |
| :--- | :---: | :---: | :---: |
| PhoBERT | Đoán SAI (0) | 0.12% | 176 |
| PhoBERT | Đoán ĐÚNG (1) | 0.06% | 662 |
| mBERT | Đoán SAI (0) | 0.08% | 185 |
| mBERT | Đoán ĐÚNG (1) | 0.07% | 653 |
| XLM-RoBERTa | Đoán SAI (0) | 0.10% | 174 |
| XLM-RoBERTa | Đoán ĐÚNG (1) | 0.06% | 664 |

###  Nhận xét hệ thống về Teencode & NSW:
Khác biệt cốt lõi nằm ở chỗ nhóm Baseline bị bẫy hoàn toàn bởi các ký tự viết tắt thô (`t`, `k`, `j` chiếm trọng số nhưng rỗng nghĩa), trong khi nhóm Pre-trained sở hữu bộ Tokenizer chuyên dụng dưới dạng Sub-words (BPE/WordPiece) kết hợp nhúng ngữ cảnh từ vựng. Do đó, dù mật độ teencode tăng ở các câu đoán sai, khoảng cách sai lệch ngữ nghĩa đã được thu hẹp đáng kể.

## 4. Phân tích Thuộc tính 4: Độ mất cân bằng của Nhãn (Label Imbalance Influence)
* **Biểu đồ ma trận nhiệt tương ứng:** `confusion_matrix_phobert.png`, `confusion_matrix_mbert.png`, `confusion_matrix_xlm_roberta.png`

### Top 5 cặp nhãn xảy ra xung đột nhận nhầm nhiều nhất:
| Nhãn gốc (Gold Label) | Nhãn bị nhầm (Predicted) | Số ca xảy ra | Mô hình mắc lỗi |
| :---: | :---: | :---: | :--- |
| T13 | T10 | 13 | XLM-RoBERTa |
| T10 | T13 | 12 | PhoBERT |
| T10 | T13 | 9 | mBERT |
| T10 | T13 | 9 | XLM-RoBERTa |
| T13 | T10 | 8 | mBERT |

###  Nhận xét hệ thống về Sự mất cân bằng nhãn:
Vùng tranh chấp kinh điển từng gây tê liệt nặng nề cho nhóm mô hình ML truyền thống giữa **T13 (Xã hội/Biến cố)** và **T10 (Giải trí)** nay đã chứng kiến sự cải thiện rõ rệt, đặc biệt tại cấu hình **XLMR-KB5**. Kỹ thuật Oversampling bổ trợ trực tiếp vào tầng đại diện ngôn ngữ sâu sắc của Transformer giúp ranh giới phân tách nhãn được phân định rõ nét hơn.

## 5. Phân tích Định tính: Tác động của Từ lóng & Ẩn dụ mạng xã hội (Slang & Metaphor)
* **Trích xuất các ca lỗi chứa từ lóng tiêu biểu phục vụ làm Case Studies:**

| Mã số (ID) | Nhãn gốc | Mô hình đoán | Từ lóng phát hiện | Văn bản trích đoạn ngắn |
| :---: | :---: | :---: | :---: | :--- |
| REC_011984 | T02 | T04 | chấn động | nhân viên mkt hướng nội bắt cả mạng xã hội phải hướng về… quần tây đại sứ m... |
| REC_011984 | T02 | T13 | chấn động | nhân viên mkt hướng nội bắt cả mạng xã hội phải hướng về… quần tây đại sứ m... |
| REC_001901 | T13 | T09 | giải cứu | khoảnh khắc hàng trăm người ở hà nội nhấc khối đá lớn giải cứu người bị kẹt... |
| REC_005101 | T13 | T10 | sốc | gái thái sốc khi quen hồng hài nhi việt bên ngoài điển trai bên trong "ở dơ... |
| REC_011984 | T02 | T04 | chấn động | nhân viên mkt hướng nội nhưng bắt cả mạng xã hội phải hướng về… chiếc quần ... |

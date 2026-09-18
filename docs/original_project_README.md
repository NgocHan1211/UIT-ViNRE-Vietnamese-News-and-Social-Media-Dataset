**TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN - ĐHQG-HCM (UIT)**  
**Môn học:** DS107 - Tư duy tính toán cho khoa học dữ liệu  

**Đề tài:** PHÂN LOẠI TIN TỨC VÀ PHÂN TÍCH CẢM XÚC CỦA NGƯỜI DÙNG FACEBOOK VIỆT NAM: TIẾP CẬN DỰA TRÊN SIÊU DỮ LIỆU TƯƠNG TÁC  
**Lĩnh vực:** Khai thác dữ liệu mạng xã hội & Xử lý ngôn ngữ tự nhiên (NLP)  

---

## Công Nghệ Sử Dụng (Tech Stack)
Dự án được xây dựng trên nền tảng Python với sự kết hợp của các công cụ hiện đại:
- **Xử lý dữ liệu:** `Pandas`, `NumPy`
- **Mô hình hóa ngôn ngữ:** `PyTorch`, `PhoBERT` (Pre-trained language model dành riêng cho tiếng Việt)
- **Giao diện trực quan:** `Streamlit` (Dashboard tương tác thời gian thực)

---

## 1. Tổng Quan (Overview)

Tài liệu này mô tả chi tiết cấu trúc, khối lượng và lược đồ của tập dữ liệu được sử dụng trong dự án phân tích xu hướng truyền thông. 

Dự án áp dụng chiến lược **Tiếp cận lấy bài đăng làm trung tâm (Post-Centric)** kết hợp với cơ chế **Nguồn chân lý duy nhất (Single Source of Truth - SSOT)**. Toàn bộ dữ liệu bình luận (comments) được loại bỏ hoàn toàn nhằm triệt tiêu nhiễu ngữ nghĩa trong quá trình huấn luyện trí tuệ nhân tạo, đồng thời ngăn chặn các sai số toán học (ZeroDivisionError) khi tính toán động lực học cảm xúc. Kết quả trích xuất cuối cùng là một "Tập dữ liệu Vàng" (Golden Dataset) đảm bảo tính toàn vẹn 100% về cả văn bản, nhãn chủ đề và siêu dữ liệu tương tác.

---

## 2. Cấu Trúc Dự Án & Cây Thư Mục (Project Directory Structure)

Mã nguồn và dữ liệu của dự án được tổ chức một cách phân tán, tuân thủ các thực hành tốt nhất trong kỹ nghệ phần mềm và khoa học dữ liệu nhằm tối ưu hóa hiệu suất của kho lưu trữ Git:

```text
DS107_Repo/
├── data/                              (1) Chứa toàn bộ dữ liệu 
│   ├── csv-data(labeled)/             - Thư mục chứa dữ liệu có nhãn chủ đề (train.csv, test.csv)
│   ├── json-crawl-data/               - Thư mục chứa siêu dữ liệu thô từ Facebook (*.json)
│   ├── Processed_Data/                - Chứa tệp Master_Data_Raw.csv (2.077 bản ghi Vàng)
│   └── .gitkeep
├── notebooks/                         (2) Thư mục chứa file thử nghiệm Jupyter (.ipynb)
├── src/                               (3) Thư mục chứa mã nguồn chính thức đóng gói (.py)
├── dashboard/                         (4) Giao diện trực quan hóa dữ liệu Streamlit (.py)
├── .gitignore                         (5) Quản lý bỏ qua các tệp dữ liệu lớn/bộ nhớ đệm
├── CONTRIBUTING.md                    (6) Hướng dẫn đóng góp mã nguồn và Git Workflow của nhóm
├── requirements.txt                   (7) Danh sách các thư viện phụ thuộc của dự án
└── README.md                          (8) Tài liệu báo cáo tập dữ liệu vàng (File này)
```

## 3. Thống Kê & Khối Lượng Dữ Liệu (Data Volume & Statistics)

Khối lượng dữ liệu được tinh chế thông qua một quy trình sàng lọc khắt khe (Data Funnel) nhằm loại bỏ các bản ghi nhiễu, trùng lặp và không trọn vẹn.

| Giai đoạn xử lý (Data Funnel) | Số lượng bản ghi | Ghi chú / Nguyên nhân |
| :--- | :--- | :--- |
| Tổng dữ liệu ban đầu | 2.796 | Dữ liệu gốc bao gồm cả Bài đăng và Bình luận. |
| Sau khi xóa trùng lặp | 2.794 | Loại bỏ 2 nội dung bị lặp lại (chiếm 4 dòng). |
| Sau khi lọc loại đối tượng | 2.634 | Loại bỏ hoàn toàn 160 dòng Bình luận (Nhận diện qua trường `comment_ids` rỗng). Chỉ giữ Bài đăng gốc. |
| Golden Dataset (Mapping) | 2.077 | Số lượng Bài đăng gốc khớp nối thành công 100% với siêu dữ liệu JSON. |

Tập dữ liệu Vàng (2.077 bản ghi) được phân loại thành 05 nhãn chủ đề (Thematic Labels) thực tế:
- Tin tức xã hội (Social News - Chiếm đa số)
- Thể thao (Sports)
- Social Slang (Slang & Memes)
- Phim ảnh (Movies)
- Âm nhạc (Music)

## 4. Lược Đồ & Cấu Trúc Dữ Liệu (Data Schema)

Để kiến tạo tập dữ liệu hoàn chỉnh, các trường dữ liệu (Fields/Keys) trọng yếu được bóc tách từ hai nguồn định dạng khác biệt:

### 4.1. Dữ liệu CSV (Chứa Nhãn phân loại)
- **content**: Văn bản thô của bài đăng. Đóng vai trò là khóa chính (Primary Key) trong quá trình khớp chuỗi.
- **label_from_content**: Nhãn phân loại chủ đề do con người gán (Ground Truth).
- **comment_ids**: Trường dữ liệu lưu trữ danh sách mã định danh bình luận. Được sử dụng như một cờ hiệu (Flag) để phân biệt Bài đăng gốc (có dữ liệu) và Bình luận (rỗng).

### 4.2. Dữ liệu JSON (Chứa Siêu dữ liệu tương tác)
- **post_content**: Nội dung văn bản của bài đăng, được sử dụng làm khóa ngoại (Foreign Key) để đối chiếu với tệp CSV.
- **creation_time**: Thời gian bài đăng được xuất bản (Yêu cầu chuẩn hóa về định dạng Datetime, múi giờ UTC+7).
- **share_count**: Lượt chia sẻ của bài đăng (Yêu cầu ép kiểu số nguyên Numeric).
- **reactions_detail**: Đối tượng (Dictionary) chứa chi tiết các trạng thái cảm xúc. Được giải nén thành các trường độc lập phục vụ tính toán Toán học cảm xúc: `like`, `love`, `haha`, `wow`, `sad`, `angry`, `care`.

## 5. Cơ Chế Liên Kết Dữ Liệu (Data Mapping Mechanism)

Do sự bất đồng bộ về mã định danh (ID) giữa hệ thống lưu trữ CSV và hệ thống cào dữ liệu JSON, quá trình hợp nhất dữ liệu không thể sử dụng cơ chế nối bảng truyền thống bằng ID.

Dự án áp dụng thuật toán Khớp chuỗi văn bản chính xác (Exact Text Matching). Cơ chế hoạt động như sau:
1. Trích xuất văn bản thô từ trường `content` (CSV) và trường `post_content` (JSON).
2. Xóa bỏ toàn bộ các ký tự ẩn gây nhiễu định dạng (dấu cách thừa, tab, ký tự xuống dòng `\n`, `\r`) và chuyển văn bản về định dạng chữ thường (lowercase) để tạo ra một Khóa nối chuẩn hóa (Normalized Join Key).
3. Thực hiện thuật toán `Inner Join` dựa trên khóa chuẩn hóa này. Những văn bản vượt qua giới hạn cắt xén của nền tảng (Facebook Truncation) hoặc có sự sai lệch về ký tự mã hóa (Encoding) sẽ bị loại bỏ nhằm đảm bảo tính toàn vẹn tuyệt đối cho 2.077 bản ghi cuối cùng.
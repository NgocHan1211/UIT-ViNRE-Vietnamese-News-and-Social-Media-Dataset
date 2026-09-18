# HƯỚNG DẪN ĐÓNG GÓP MÃ NGUỒN (CONTRIBUTING GUIDELINES)

Tài liệu này quy định các tiêu chuẩn kỹ thuật và quy trình phối hợp dành cho các thành viên tham gia phát triển dự án. Việc tuân thủ nghiêm ngặt các quy định dưới đây nhằm đảm bảo tính đồng nhất của mã nguồn, ngăn chặn xung đột (Merge Conflict) và duy trì sự ổn định của hệ thống trên các môi trường hệ điều hành khác biệt.

---

## 1. Tiêu Chuẩn Lập Trình (Coding Standards)

Mã nguồn của dự án được phát triển chủ yếu bằng ngôn ngữ Python (sử dụng Pandas, PyTorch/PhoBERT, Streamlit). Yêu cầu tuân thủ các quy chuẩn sau:

- **Tính độc lập hệ điều hành (OS-Agnostic):** Không sử dụng đường dẫn tĩnh chứa dấu gạch chéo cụ thể của Windows (`\`) hoặc macOS (`/`). Mọi thao tác đọc/ghi tệp tin bắt buộc phải sử dụng thư viện hệ thống: `os.path.join()`.
- **Bảng mã văn bản (Encoding):** Đặc thù xử lý dữ liệu tiếng Việt yêu cầu sự đồng nhất về bảng mã. Mọi lệnh `open()` hoặc `pd.read_csv()`, `pd.to_csv()` bắt buộc phải khai báo tham số `encoding='utf-8'` hoặc `encoding='utf-8-sig'`.
- **Môi trường ảo (Virtual Environment):** Mọi gói thư viện (packages) cài đặt mới phải được kiểm thử tính tương thích và cập nhật vào tệp `requirements.txt`.

---

## 2. Quản Lý Dữ Liệu và Kho Lưu Trữ (Data Storage Management)

Dự án áp dụng cơ chế phân tách nghiêm ngặt giữa Mã nguồn (Source Code) và Dữ liệu (Data) để tránh làm quá tải kho lưu trữ GitHub:

- **Lưu trữ Tập trung trên Google Drive (Dành cho Data & Model Weights):** Đây là nơi duy nhất để lưu các tệp tin nặng với cấu trúc sau:
  - `01_Raw_Data`: Để lưu bản gốc các file CSV và JSON thô tải từ mạng về.
  - `02_Processed_Data`: Để lưu file `Master_Data_Raw.csv` (và các dữ liệu sau xử lý khác). Mọi người tải data từ đây để code.
  - `03_Model_Weights`: Nơi lưu trữ các file trọng số AI (`.pt`, `.bin`) nặng hàng GB sau khi huấn luyện.

- **Kho lưu trữ GitHub (Chỉ dành cho Source Code):**
  - Mọi người tải data từ Drive về và thả vào thư mục `data/` trên máy tính cục bộ. Thư mục này trên GitHub chỉ chứa `.gitkeep`.
  - Tận dụng `.gitignore`: Tuyệt đối **KHÔNG** push các định dạng file dữ liệu/bộ nhớ đệm như: `*.csv`, `*.json`, `*.pt`, `*.bin`, `__pycache__/`, `.ipynb_checkpoints/`.
  - Cấu trúc thư mục bắt buộc tuân thủ: `data/` (TRỐNG), `notebooks/` (Nháp/EDA), `src/` (Mã nguồn lõi), `dashboard/` (Giao diện).

---

## 3. Quy Trình Cập Nhật Mã Nguồn (Git Workflow)

Nhằm triệt tiêu rủi ro xung đột mã nguồn (Merge Conflict), đặc biệt khi thao tác trên các tệp Jupyter Notebook (`.ipynb`), quy trình làm việc chuẩn được thiết lập như sau:

- **Nghiêm cấm push trực tiếp lên nhánh `main`:** Mọi thành viên tuyệt đối **KHÔNG** được phép push code trực tiếp lên nhánh `main`. Mọi tính năng hoặc sửa lỗi bắt buộc phải thực hiện trên một nhánh phụ (Branch) riêng, sau đó tạo Pull Request (PR) để merge vào `main`.
- **Quy ước đặt tên nhánh (Branch Naming Conventions):** Tên nhánh phải được đặt bằng chữ thường, không dấu, kết nối bằng dấu gạch ngang `-` và tuân theo cấu trúc: `<loai-nhanh>/<mo-ta-ngan>`. Các loại nhánh chính gồm:
  - `feat/`: Nhánh phát triển tính năng mới (ví dụ: `feat/exact-text-matching`, `feat/sentiment-analysis`).
  - `fix/`: Nhánh sửa lỗi (ví dụ: `fix/nan-division-error`, `fix/data-encoding`).
  - `docs/`: Nhánh viết tài liệu (ví dụ: `docs/update-readme`, `docs/contributing-guidelines`).
  - `refactor/`: Nhánh tối ưu hóa, tái cấu trúc mã nguồn (ví dụ: `refactor/clean-data-funnel`).
- **Đồng bộ hóa (Pull):** Luôn khởi chạy lệnh `git pull origin main` trước khi tạo nhánh mới hoặc bắt đầu phiên làm việc mới để cập nhật mã nguồn mới nhất từ hệ thống.
- **Quản lý ký tự kết thúc dòng (CRLF/LF):** Để đồng bộ giữa máy tính Windows và macOS, yêu cầu cấu hình Git toàn cầu trước khi sao chép (clone) kho lưu trữ:
  - **Môi trường Windows:** Chạy lệnh `git config --global core.autocrlf true`
  - **Môi trường macOS/Linux:** Chạy lệnh `git config --global core.autocrlf input`
- **Phân tách mô-đun (Modularity):** Mã nguồn được chia thành các tệp độc lập (`data_processing.py`, `train.py`, `app.py`). Các thành viên chỉ thao tác trên tệp tin thuộc phạm vi trách nhiệm của mình. Hạn chế tối đa việc chỉnh sửa chéo tệp của thành viên khác.
- **Quy trình Đánh giá chéo (Code Review):** Sau khi đẩy nhánh phụ lên GitHub/GitLab và tạo Pull Request (PR), thành viên bắt buộc phải chỉ định (assign) ít nhất một thành viên khác trong nhóm để kiểm tra mã nguồn (Review) nhằm phát hiện lỗi logic trước khi merge vào nhánh `main`.
- **Đóng gói mã nguồn:** Tệp Jupyter Notebook (`.ipynb`) chỉ được sử dụng cho mục đích chạy thử nghiệm (EDA, Testing). Mã nguồn chính thức triển khai vào hệ thống phải được đóng gói dưới định dạng tệp `.py`.

---

## 4. Quy Ước Thông Điệp Cập Nhật (Commit Message Conventions)

Các thông điệp cập nhật (Commit messages) cần ngắn gọn, khách quan và mô tả rõ ràng sự thay đổi kỹ thuật, sử dụng các tiền tố chuẩn sau:

- **`feat:`** Bổ sung tính năng hoặc luồng xử lý mới (ví dụ: `feat: add exact text matching function`).
- **`fix:`** Xử lý lỗi hệ thống hoặc dữ liệu (ví dụ: `fix: resolve NaN division in sentiment formula`).
- **`docs:`** Cập nhật tài liệu kỹ thuật, README (ví dụ: `docs: update data funnel statistics`).
- **`refactor:`** Tối ưu hóa mã nguồn mà không thay đổi chức năng.

# Hướng dẫn thu thập dữ liệu Facebook (Facebook Crawler Guide)

Tài liệu này hướng dẫn các bước chi tiết để cấu hình và chạy script `final_fb_crawl.py` bằng giao thức **CDP (Chrome DevTools Protocol)** trên cả hệ điều hành **macOS** và **Windows**.

---

## 📌 Các bước chuẩn bị trước khi chạy

### Bước 1: Khởi chạy Google Chrome ở chế độ Debug (Cổng `9222`)
Để Playwright có thể điều khiển trình duyệt của bạn (đã đăng nhập sẵn Facebook) mà không bị chặn, bạn cần khởi chạy Chrome ở chế độ debug từ terminal/command prompt.

#### 🍏 Dành cho macOS:
Mở **Terminal** và chạy lệnh sau (Profile đăng nhập sẽ được lưu cố định tại thư mục Home của bạn để tránh phải đăng nhập lại mỗi lần tắt máy):
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/chrome_dev_profile"
```

#### 🪟 Dành cho Windows:
Mở **Command Prompt (cmd)** hoặc **PowerShell** và chạy lệnh:
```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_dev_profile"
```
*(Nếu Chrome của bạn được cài đặt ở thư mục khác, vui lòng thay đổi đường dẫn `"C:\Program Files\Google\Chrome\Application\chrome.exe"` cho đúng).*

---

### Bước 2: Đăng nhập Facebook trên trình duyệt Debug
1. Sau khi chạy lệnh ở Bước 1, một cửa sổ Chrome mới (phiên bản Debug) sẽ tự động mở ra.
2. Truy cập vào [facebook.com](https://facebook.com) và **Đăng nhập** vào tài khoản của bạn (nên sử dụng tài khoản clone hoặc tài khoản phụ để an toàn).
3. **Giữ nguyên cửa sổ Chrome này** trong suốt quá trình chạy crawler. Không tắt đi.

---

### Bước 3: Cấu hình danh sách Fanpage cần cào
Mở file `src/final_fb_crawl.py` bằng IDE của bạn (VS Code, PyCharm,...) và điều chỉnh các cấu hình ở đầu file nếu cần:
- `TARGET_PAGES`: Danh sách URL Fanpage bạn muốn cào (bỏ dấu `#` ở trước URL để kích hoạt, thêm `#` để tắt).
- `TARGET_POSTS`: Số lượng bài viết muốn lấy từ mỗi page (mặc định là `3000`).
- `MIN_REACTIONS`: Số lượng tương tác tối thiểu để lấy bài viết (mặc định là `50`).

---

### Bước 4: Chạy Script thu thập dữ liệu

1. Mở một tab **Terminal mới** (không tắt Terminal đang chạy Chrome ở Bước 1).
2. Di chuyển vào thư mục dự án của bạn:
   ```bash
   cd <đường-dẫn-đến-thư-mục-DS107_Repo-trên-máy-bạn>
   ```
   *(Ví dụ trên Mac: `cd ~/Documents/DS107_Repo` | Trên Windows: `cd D:\DS107_Repo`)*
3. Kích hoạt môi trường ảo (virtual environment):
   - **macOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```
   - **Windows**:
     ```cmd
     .venv\Scripts\activate
     ```
4. Cài đặt các thư viện bắt buộc (chỉ cần chạy một lần duy nhất khi setup dự án):
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
5. Chạy file script từ thư mục gốc của dự án:
   ```bash
   python src/final_fb_crawl.py
   ```

---

## ⚙️ Cơ chế hoạt động của `final_fb_crawl.py`
* **Tự động chuyển trang:** Script sẽ tự động điều khiển tab Chrome điều hướng lần lượt qua các Fanpage trong danh sách `TARGET_PAGES` để cào, không cần bạn phải mở thủ công các tab đó.
* **Lưu dữ liệu real-time:** Dữ liệu cào được sẽ lưu theo thời gian thực dưới định dạng JSON trong thư mục: `data/json-targeted-crawl/posts_{tên_fanpage}.json`.
* **Lọc thông minh:** Tự động loại bỏ các bài Shared (chia sẻ lại), bài viết Video, Reel và các bài viết có tương tác thấp hơn `MIN_REACTIONS`.
* **Chống chặn (Anti-block):** Tự động mô phỏng thao tác lướt của người dùng (`human_scroll`) và tự động nghỉ (Batch Sleep) sau mỗi số lượng bài nhất định để tránh bị Facebook quét checkpoint tài khoản.

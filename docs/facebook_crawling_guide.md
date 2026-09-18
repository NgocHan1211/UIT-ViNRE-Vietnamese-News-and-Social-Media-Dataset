# Hướng dẫn thu thập dữ liệu Facebook (Facebook Crawler Guide)

Tài liệu này cung cấp các bước để chạy script `facebook_crawler.py` và lấy dữ liệu Facebook thông qua giao thức kết nối CDP (Chrome DevTools Protocol).

## Bước 1: Mở trình duyệt ở chế độ Debugging

Để Playwright có thể tự động điều khiển trình duyệt hiện tại mà không bị chặn, bạn cần khởi chạy Google Chrome ở chế độ Debug với port `9222`.

**Dành cho macOS:**
Mở Terminal của macOS và chạy lệnh sau (bạn có thể copy và dán trực tiếp):

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_dev_test"
```

> **💡 Mẹo nhỏ (Quan trọng) cho Mac:**
> Lệnh trên sử dụng thư mục `/tmp/chrome_dev_test` để lưu cấu hình. Thư mục `/tmp` sẽ **tự động bị xóa** mỗi khi bạn khởi động lại máy Mac. Điều này có nghĩa là bạn sẽ phải đăng nhập lại Facebook mỗi lần muốn cào dữ liệu sau khi khởi động máy.
> 
> Nếu bạn muốn máy **nhớ luôn phiên đăng nhập**, bạn có thể đổi đường dẫn lưu trữ sang một thư mục cố định (ví dụ ở thư mục gốc của bạn), bằng cách sử dụng lệnh này thay thế:
> ```bash
> /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/chrome_dev_profile"
> ```

**Dành cho Windows:**
Mở Command Prompt (cmd) hoặc PowerShell và chạy lệnh sau (đường dẫn `C:\chrome_dev_test` sẽ là nơi lưu phiên đăng nhập, không bị mất khi tắt máy):

```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_dev_test"
```

## Bước 2: Chuẩn bị trang Facebook cần cào

1. Sau khi chạy lệnh ở Bước 1, một cửa sổ Chrome mới (phiên bản dev) sẽ hiện ra.
2. Bạn truy cập vào [facebook.com](https://facebook.com) và **Đăng nhập** vào tài khoản của bạn (tài khoản phụ/clone càng tốt).
3. Truy cập vào trang Fanpage mà bạn muốn thu thập dữ liệu (Ví dụ: `facebook.com/K14vn`).
4. **Giữ nguyên tab Fanpage đó** làm tab đang mở (active tab). Đừng thu nhỏ hay tắt nó đi.

## Bước 3: Cài đặt thư viện và Chạy Script

1. Mở một cửa sổ/tab Terminal **MỚI** (để giữ nguyên cửa sổ Terminal đang chạy lệnh Chrome kia).
2. Di chuyển vào thư mục dự án của bạn:
   ```bash
   cd /Users/phucndq/Documents/UIT/HK6/DS107.Q21/DA/DS107_Repo
   ```
3. Kích hoạt môi trường ảo (virtual environment) tùy theo hệ điều hành:

   **Trên macOS/Linux:**
   ```bash
   source .venv/bin/activate
   ```
   **Trên Windows:**
   ```cmd
   .venv\Scripts\activate
   ```

4. Cài đặt các thư viện bắt buộc (chỉ cần chạy 1 lần):
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

5. Chạy file script từ thư mục `src`:
   ```bash
   python src/facebook_crawler.py
   ```

## Hoạt động của hệ thống:
- Script sẽ tự động nhận diện tab Facebook đang mở, và bắt đầu lướt xuống dưới.
- Thông tin trích xuất sẽ được lưu theo thời gian thực tại: `data/json-targeted-crawl/posts_{tên_fanpage}.json`.
- Script sẽ tự động bỏ qua các bài Shared, Video/Reel.
- Nếu lướt trúng 3 bài viết liên tiếp nằm ngoài vùng thời gian (cũ hơn 01/01/2026), script sẽ tự động dừng vòng lặp.
- Các chỉ số Like, Share, Comment được bóc tách chính xác đến hàng đơn vị (hệ thống có thể tự click mở Modal Tương tác để lấy số chuẩn).

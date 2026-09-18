# HDSD crawl Facebook V9.3.2 cho nhóm

## 0. Bản này dùng làm gì?

Bản V9.3.2 dựa trên V9.3 ổn định, chỉ thêm danh sách page theo từng bạn và cơ chế chọn người chạy bằng `CRAWL_OWNER`.

Không dùng V9.4 để chạy nhóm.

## 1. Phân công page

| Người chạy | Mã `CRAWL_OWNER` | Page |
|---|---:|---|
| Phúc | `phuc` | YAN News, VnExpress.net, Dân trí, Tin tức VTV24 |
| Hân | `han` | Kenh14.vn, Theanh28 Entertainment, Người Lao Động, daiphatthanh.sound |
| Nhung | `nhung` | Thông tin Chính phủ, Tuổi Trẻ, Tin tức CAND, Đại biểu Nhân dân |
| Yến | `yen` | Schannel, Vietnamnet.vn, CafeBiz, Weibo Việt Nam |

Mỗi page đặt target mặc định là **1000 post hợp lệ**.

## 2. Chuẩn bị file

Đặt file Python vào thư mục `src/` của project:

```bash
src/facebook_crawler_multipage_v9_3_2_team_pages.py
```

Đặt file supervisor vào thư mục gốc project:

```bash
run_facebook_multipage_v9_3_2.sh
```

Tạo thư mục log nếu chưa có:

```bash
mkdir -p logs
```

## 3. Chạy trên macOS

Mở Terminal tại thư mục project:

```bash
cd "/duong/dan/toi/DS107_Repo"
source .venv/bin/activate
```

Compile kiểm tra trước:

```bash
python -m py_compile src/facebook_crawler_multipage_v9_3_2_team_pages.py
```

Chạy theo từng bạn:

### Phúc

```bash
CRAWL_OWNER=phuc caffeinate -dimsu ./run_facebook_multipage_v9_3_2.sh
```

### Hân

```bash
CRAWL_OWNER=han caffeinate -dimsu ./run_facebook_multipage_v9_3_2.sh
```

### Nhung

```bash
CRAWL_OWNER=nhung caffeinate -dimsu ./run_facebook_multipage_v9_3_2.sh
```

### Yến

```bash
CRAWL_OWNER=yen caffeinate -dimsu ./run_facebook_multipage_v9_3_2.sh
```

Dừng crawler bằng `Ctrl + C`.

## 4. Chạy trên Windows PowerShell

Mở PowerShell tại thư mục project:

```powershell
cd "C:\duong\dan\toi\DS107_Repo"
.\.venv\Scripts\Activate.ps1
mkdir logs -Force
```

Mở Chrome Debug:

```powershell
$chrome = "$Env:ProgramFiles\Google\Chrome\Application\chrome.exe"
Start-Process $chrome -ArgumentList "--remote-debugging-port=9222", "--user-data-dir=$Env:USERPROFILE\chrome-cdp-fb", "--disable-background-timer-throttling", "--disable-renderer-backgrounding"
```

Compile kiểm tra:

```powershell
python -m py_compile .\src\facebook_crawler_multipage_v9_3_2_team_pages.py
```

Chạy theo từng bạn:

### Phúc

```powershell
$env:CRAWL_OWNER="phuc"
python -u .\src\facebook_crawler_multipage_v9_3_2_team_pages.py 2>&1 | Tee-Object -FilePath ("logs\fb_multipage_v9_3_2_phuc_{0}.txt" -f (Get-Date -Format yyyyMMdd_HHmmss))
```

### Hân

```powershell
$env:CRAWL_OWNER="han"
python -u .\src\facebook_crawler_multipage_v9_3_2_team_pages.py 2>&1 | Tee-Object -FilePath ("logs\fb_multipage_v9_3_2_han_{0}.txt" -f (Get-Date -Format yyyyMMdd_HHmmss))
```

### Nhung

```powershell
$env:CRAWL_OWNER="nhung"
python -u .\src\facebook_crawler_multipage_v9_3_2_team_pages.py 2>&1 | Tee-Object -FilePath ("logs\fb_multipage_v9_3_2_nhung_{0}.txt" -f (Get-Date -Format yyyyMMdd_HHmmss))
```

### Yến

```powershell
$env:CRAWL_OWNER="yen"
python -u .\src\facebook_crawler_multipage_v9_3_2_team_pages.py 2>&1 | Tee-Object -FilePath ("logs\fb_multipage_v9_3_2_yen_{0}.txt" -f (Get-Date -Format yyyyMMdd_HHmmss))
```

Trên Windows, nếu muốn chạy nhiều vòng qua đêm giống file `.sh`, chạy lại lệnh Python sau mỗi cycle hoặc dùng Task/loop riêng. Cách an toàn nhất là chạy một cycle trước, gửi log kiểm tra rồi mới chạy lâu.

## 5. Kiểm tra nhanh số lượng post đã thu

macOS/Linux:

```bash
python - <<'PY'
import json, os, glob
for f in sorted(glob.glob("data/**/posts_*.json", recursive=True)):
    try:
        data = json.load(open(f, encoding="utf-8"))
        if isinstance(data, list):
            print(f"{len(data):4d}  {f}")
    except Exception:
        pass
PY
```

Windows PowerShell:

```powershell
python - <<'PY'
import json, os, glob
for f in sorted(glob.glob("data/**/posts_*.json", recursive=True)):
    try:
        data = json.load(open(f, encoding="utf-8"))
        if isinstance(data, list):
            print(f"{len(data):4d}  {f}")
    except Exception:
        pass
PY
```

## 6. Khi nào xem là chạy ổn?

Log nên có các dòng như:

```text
[THÀNH CÔNG new=... total=...]
timestamp_status=ok
[CHECKPOINT] reason=success
```

Các dòng này bình thường, không phải lỗi nghiêm trọng:

```text
[Bỏ qua nhanh] total < 50
[POST ĐÃ THU RỒI - URL]
[TRÙNG CONTENT - FAST SKIP]
[SCAN_NO_ACTION]
```

Dừng và gửi log kiểm tra nếu thấy:

```text
Traceback
ReferenceError
DIALOG_CLOSE_FAIL lặp quá nhiều
Không có [THÀNH CÔNG] trong 15-20 phút
```

## 7. Output nằm ở đâu?

Các file JSON nằm trong thư mục `data/`.

Ví dụ:

```text
data/json-han-nguoilaodong-v9-3-2/posts_Nguoi_Lao_Dong.json
data/json-nhung-tuoitre-v9-3-2/posts_Tuoi_Tre.json
data/json-yen-cafebiz-v9-3-2/posts_CafeBiz.json
```

Mỗi lần gửi kết quả về nhóm thì gửi:

```text
1. file logs/fb_*.txt
2. thư mục data/json-... tương ứng hoặc file posts_*.json
```

## 8. Ghi chú quan trọng

- Không tự sửa code nếu đang chạy ổn.
- Nếu page bị đổi layout hoặc đứng lâu, gửi log + ảnh/video màn hình cho Phúc kiểm tra.
- Chrome phải đăng nhập Facebook trước trong profile debug.

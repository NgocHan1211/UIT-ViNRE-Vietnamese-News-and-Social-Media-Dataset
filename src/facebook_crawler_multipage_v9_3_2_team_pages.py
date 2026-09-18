# ============================================================
# FACEBOOK MULTIPAGE CRAWLER V9.3.2.2 - TEAM PAGES
# ============================================================
# Mục tiêu:
# - Kiểm thử và crawl riêng YAN News theo chunk để tránh Chrome/Facebook bị nặng
#   khi chạy nhiều giờ liên tục trên máy RAM thấp.
# - Có thể resume từ dữ liệu cũ, không thu lại từ đầu nếu đã có JSON seed.
# - Fast-skip các URL đã thu: chỉ resolve URL/timestamp, không mở reaction modal.
# - Tự log health, phát hiện feed đứng, đóng modal kẹt, reload/new-tab recovery.
#
# Gợi ý chạy thực tế:
# - TARGET_POSTS = 1000       : tổng số bài muốn có trong file cuối.
# - SESSION_POST_LIMIT = 100  : mỗi lần chạy chỉ thu thêm tối đa 250 bài rồi tự dừng.
# - Chạy xong 1 session nên tắt Chrome Debug và mở lại để sạch RAM/DOM.
#
# OUTPUT:
# - Mặc định lưu vào: data/json-yannews-chunk-v1/posts_YAN_News.json
# - Nếu file output chưa có, code sẽ thử seed từ:
#     data/json-final-v2-yannews-vnexpress/posts_YAN_News.json
#   để tránh thu lại từ đầu.
#
# YÊU CẦU:
# - Mở Chrome Debug port 9222 và đăng nhập Facebook trước.
# - Không thao tác tay vào tab crawler trong lúc chạy.
# - Mac Air 8GB nên chạy theo chunk 200-300 bài/session, không nên cố 2K/session.
#
# macOS mở Chrome Debug:
# /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
#   --remote-debugging-port=9222 \
#   --user-data-dir="$HOME/chrome-cdp-fb"
#
# Windows PowerShell mở Chrome Debug:
# & "C:\Program Files\Google\Chrome\Application\chrome.exe" `
#   --remote-debugging-port=9222 `
#   --user-data-dir="$env:USERPROFILE\chrome-cdp-fb"
# ============================================================


import os
import json
import time
import random
import re
import hashlib
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ===================== REAL-CLOCK LOG PREFIX =====================
# Tất cả print() phía dưới sẽ tự thêm prefix kiểu:
# [22/05/2026 - 01:50:13] [00:00:03] ...
import builtins as _builtins

_ORIGINAL_PRINT = _builtins.print

def print(*args, **kwargs):
    sep = kwargs.pop("sep", " ")
    end = kwargs.pop("end", "\n")
    flush = kwargs.pop("flush", True)
    text = sep.join(str(a) for a in args)
    prefix = datetime.now().strftime("[%d/%m/%Y - %H:%M:%S] ")

    if text:
        # Nếu text nhiều dòng, prefix từng dòng để log file dễ đọc.
        text = "\n".join((prefix + line) if line.strip() else line for line in text.splitlines())
    else:
        text = prefix.rstrip()

    _ORIGINAL_PRINT(text, sep=sep, end=end, flush=flush, **kwargs)
# ================================================================

# ===================== CONFIG =====================
# Tổng mục tiêu trong file cuối.
TARGET_POSTS = 2000

# Mỗi lần chạy chỉ thu thêm tối đa từng này bài mới.
# Sau đó script tự dừng để bạn restart Chrome Debug, giúp tránh nặng RAM/DOM.
SESSION_POST_LIMIT = 100

MIN_REACTIONS = 50

# Folder output mới, không đè file tối qua.
SAVE_DIR_NAME = 'json-yannews-chunk-v1'

# Checkpoint để lần sau nhảy gần về vùng đã dừng.
CHECKPOINT_FILE_NAME = 'checkpoint_YAN_News_v6.json'
ENABLE_WARM_JUMP_FROM_CHECKPOINT = True
WARM_JUMP_SCROLL_FACTOR = 0.92

# Nếu chưa có checkpoint, ước lượng scroll_y theo số record đã có.
# Với YAN trong log test, 333 records tương ứng khoảng 290k scroll_y.
BOOTSTRAP_SCROLL_PER_RECORD = 850
BOOTSTRAP_MAX_SCROLL_Y = 1200000

# Timestamp metadata luôn bật ở bản chunk/stress.
CAPTURE_POST_TIMESTAMP = True

# External link không phải trường bắt buộc cho bài toán hiện tại, nhưng giữ biến để tránh lỗi runtime.
CAPTURE_EXTERNAL_URL = True

# Nếu output chưa có, copy dữ liệu cũ từ file này để resume/fast-skip.
SEED_JSON_PATH = os.path.join('data', 'json-final-v2-yannews-vnexpress', 'posts_YAN_News.json')
COPY_SEED_ON_EMPTY = True

# V6: cố định identity/output để không tạo nhầm posts_YAN_News_Verified_account.json / posts_yannews.json.
FORCE_PAGE_NAME = "YAN News"
FORCE_PAGE_HANDLE = "yannews"
FORCE_OUTPUT_JSON_NAME = "posts_YAN_News.json"
STRICT_PAGE_IDENTITY = True

# V6: chống hovercard/profile popup che timestamp/reaction.
DISMISS_HOVERCARD_BEFORE_TIMESTAMP = True
DISMISS_HOVERCARD_BEFORE_REACTION = True
HOVERCARD_DISMISS_VERBOSE = False

# V6.2 debug/safety
VISUAL_DEBUG_CURSOR = True
URL_RESOLVE_MAX_SECONDS = 35
END_SESSION_ON_DIALOG_STUCK_AFTER_SAVE = True
AVOID_RELOAD_RECOVERY = True

# V9.3.2: chống hover nhầm hashtag / đứng quá lâu.
HOVER_CANDIDATE_MAX_SECONDS = 6.0
HASHTAG_HOVER_SKIP = True
PRINT_SCAN_SKIP_REASON = True
SCAN_SKIP_LOG_EVERY = 12
PRINT_TIMESTAMP_HOVER_REASON = True

# V9.3.2: Minimal patch trên nền V7 ổn định.
# Nếu timestamp text parse được nhưng hover timestamp không hiện tooltip,
# lấy timestamp text làm mốc chính; probe icon đồng hồ bên phải chỉ để debug.
CLOCK_RIGHT_EDGE_PROBE = True
CLOCK_RIGHT_EDGE_OFFSETS = [(16, 0), (22, 0), (22, -3), (22, 3), (30, 0), (40, 0)]
CLOCK_RIGHT_EDGE_HOVER_MS = 650
CLOCK_RIGHT_EDGE_VERBOSE = False

# V6: điều khiển warm-jump sâu.
WARM_JUMP_MAX_SECONDS = 180
WARM_JUMP_MIN_ACCEPT_RATIO = 0.18

MAX_SCROLLS = 120000

# Không chờ 500 vòng nữa. Nếu feed đứng, recovery sớm.
MAX_EMPTY_ROUNDS = 80
STAGNATION_ROUNDS_BEFORE_RECOVERY = 120
MAX_RECOVERY_ATTEMPTS_PER_PAGE = 2

# Reset nhẹ trong cùng session. Không reset quá thường xuyên để khỏi phải nhảy lại từ đầu nhiều lần.
TAB_RESET_EVERY_NEW_POSTS = 999999
HEALTH_EVERY_NEW_POSTS = 10

# Khi đang đi qua vùng URL đã thu, scroll nhanh hơn để vượt qua vùng cũ.
FAST_SKIP_EXISTING = True
FAST_SKIP_AFTER_DUPLICATES = 1
FAST_SKIP_SCROLL_MULTIPLIER = 4.0

# In log rõ nguyên nhân không thu bài mới.
PRINT_DUPLICATE_POST_LOG = True
PRINT_NO_CANDIDATE_LOG = True
NO_CANDIDATE_LOG_EVERY = 10
DUPLICATE_NO_NEW_RECOVERY_ROUNDS = 220

BATCH_SIZE = 100
BATCH_SLEEP = (5, 15)
PAGE_SLEEP = (5, 10)

KEEP_DEBUG_FIELDS = False
FLATTEN_REACTIONS = True

DEBUG_URL_DIAGNOSTICS = False
DEBUG_SCROLL_SUMMARY = True
DEDUP_BY_CONTENT = True
PREFILTER_LOW_REACTION_BEFORE_MODAL = True
URL_RESOLVE_RETRIES = 3
POST_CONTAINER_MAX_ANCESTOR_LEVELS = 28

# ===================== MULTI-PAGE CONFIG =====================
# Mỗi lần chạy script sẽ chạy lần lượt từng page trong PAGE_CONFIGS.
# Mỗi page thu tối đa SESSION_POST_LIMIT bài mới rồi chuyển sang page tiếp theo.
# Supervisor .sh sẽ restart Chrome và lặp lại cho đến khi tất cả page đủ target_posts.
#
# LƯU Ý:
# - 4 page đã được set sẵn: YAN, VnExpress, Dân trí, Tin tức VTV24.
# - YAN giữ lại folder cũ để resume từ dữ liệu đã crawl.
# - VnExpress có seed cũ nếu tồn tại, các page khác bắt đầu file mới.
# Chọn người chạy bằng biến môi trường CRAWL_OWNER:
#   phuc  -> 4 page của Phúc
#   han   -> 4 page của Hân
#   nhung -> 4 page của Nhung
#   yen   -> 4 page của Yến
#   all   -> chạy tất cả page
#
# Có thể lọc thêm từng page bằng CRAWL_PAGE_KEYS, ví dụ:
#   CRAWL_OWNER=han CRAWL_PAGE_KEYS=nguoilaodong,k14vn python ...
CRAWL_OWNER = os.environ.get("CRAWL_OWNER", "all").strip().lower()
CRAWL_PAGE_KEYS = {
    x.strip().lower()
    for x in os.environ.get("CRAWL_PAGE_KEYS", "").split(",")
    if x.strip()
}

PAGE_CONFIGS = [
    # ==================== PHÚC ====================
    {
        "owner_key": "phuc",
        "owner_name": "Phúc",
        "key": "yannews",
        "url": "https://www.facebook.com/yannews",
        "page_name": "YAN News",
        "page_handle": "yannews",
        "save_dir_name": "json-yannews-chunk-v1",
        "output_json_name": "posts_YAN_News.json",
        "checkpoint_file_name": "checkpoint_YAN_News_v7.json",
        "seed_json_path": None,
        "target_posts": 1000,
        "enabled": True,
    },
    {
        "owner_key": "phuc",
        "owner_name": "Phúc",
        "key": "vnexpress",
        "url": "https://www.facebook.com/congdongvnexpress",
        "page_name": "VnExpress.net",
        "page_handle": "congdongvnexpress",
        "save_dir_name": "json-vnexpress-multipage-v7",
        "output_json_name": "posts_VnExpress_net.json",
        "checkpoint_file_name": "checkpoint_VnExpress_v7.json",
        "seed_json_path": os.path.join("data", "json-final-v2-yannews-vnexpress", "posts_VnExpress_net.json"),
        "target_posts": 1000,
        "enabled": True,
    },
    {
        "owner_key": "phuc",
        "owner_name": "Phúc",
        "key": "dantri",
        "url": "https://www.facebook.com/baodantridientu",
        "page_name": "Dân trí",
        "page_handle": "baodantridientu",
        "save_dir_name": "json-dantri-multipage-v7",
        "output_json_name": "posts_Dantri.json",
        "checkpoint_file_name": "checkpoint_Dantri_v7.json",
        "seed_json_path": None,
        "target_posts": 1000,
        "enabled": True,
    },
    {
        "owner_key": "phuc",
        "owner_name": "Phúc",
        "key": "vtv24",
        "url": "https://www.facebook.com/tintucvtv24",
        "page_name": "Tin tức VTV24",
        "page_handle": "tintucvtv24",
        "save_dir_name": "json-vtv24-multipage-v7",
        "output_json_name": "posts_Tin_tuc_VTV24.json",
        "checkpoint_file_name": "checkpoint_VTV24_v7.json",
        "seed_json_path": None,
        "target_posts": 1000,
        "enabled": True,
    },

    # ==================== HÂN ====================
    {
        "owner_key": "han",
        "owner_name": "Hân",
        "key": "k14vn",
        "url": "https://www.facebook.com/K14vn/",
        "page_name": "Kenh14.vn",
        "page_handle": "K14vn",
        "save_dir_name": "json-han-kenh14-v9-3-2",
        "output_json_name": "posts_Kenh14_vn.json",
        "checkpoint_file_name": "checkpoint_Kenh14_v9_3_2.json",
        "seed_json_path": None,
        "target_posts": 1000,
        "enabled": True,
    },
    {
        "owner_key": "han",
        "owner_name": "Hân",
        "key": "theanh28",
        "url": "https://www.facebook.com/Theanh28",
        "page_name": "Theanh28 Entertainment",
        "page_handle": "Theanh28",
        "save_dir_name": "json-han-theanh28-v9-3-2",
        "output_json_name": "posts_Theanh28_Entertainment.json",
        "checkpoint_file_name": "checkpoint_Theanh28_v9_3_2.json",
        "seed_json_path": None,
        "target_posts": 1000,
        "enabled": True,
    },
    {
        "owner_key": "han",
        "owner_name": "Hân",
        "key": "nguoilaodong",
        "url": "https://www.facebook.com/nguoilaodong",
        "page_name": "Người Lao Động",
        "page_handle": "nguoilaodong",
        "save_dir_name": "json-han-nguoilaodong-v9-3-2",
        "output_json_name": "posts_Nguoi_Lao_Dong.json",
        "checkpoint_file_name": "checkpoint_Nguoi_Lao_Dong_v9_3_2.json",
        "seed_json_path": None,
        "target_posts": 1000,
        "enabled": True,
    },
    {
        "owner_key": "han",
        "owner_name": "Hân",
        "key": "daiphatthanh_sound",
        "url": "https://www.facebook.com/daiphatthanh.sound",
        "page_name": "Đài Phát Thanh Sound",
        "page_handle": "daiphatthanh.sound",
        "save_dir_name": "json-han-daiphatthanh-sound-v9-3-2",
        "output_json_name": "posts_Dai_Phat_Thanh_Sound.json",
        "checkpoint_file_name": "checkpoint_Dai_Phat_Thanh_Sound_v9_3_2.json",
        "seed_json_path": None,
        "target_posts": 1000,
        "enabled": True,
    },

    # ==================== NHUNG ====================
    {
        "owner_key": "nhung",
        "owner_name": "Nhung",
        "key": "thongtinchinhphu",
        "url": "https://www.facebook.com/thongtinchinhphu",
        "page_name": "Thông tin Chính phủ",
        "page_handle": "thongtinchinhphu",
        "save_dir_name": "json-nhung-thongtinchinhphu-v9-3-2",
        "output_json_name": "posts_Thong_tin_Chinh_phu.json",
        "checkpoint_file_name": "checkpoint_Thong_tin_Chinh_phu_v9_3_2.json",
        "seed_json_path": None,
        "target_posts": 1000,
        "enabled": True,
    },
    {
        "owner_key": "nhung",
        "owner_name": "Nhung",
        "key": "tuoitre",
        "url": "https://www.facebook.com/baotuoitre",
        "page_name": "Tuổi Trẻ",
        "page_handle": "baotuoitre",
        "save_dir_name": "json-nhung-tuoitre-v9-3-2",
        "output_json_name": "posts_Tuoi_Tre.json",
        "checkpoint_file_name": "checkpoint_Tuoi_Tre_v9_3_2.json",
        "seed_json_path": None,
        "target_posts": 1000,
        "enabled": True,
    },
    {
        "owner_key": "nhung",
        "owner_name": "Nhung",
        "key": "tintuccand",
        "url": "https://www.facebook.com/tintuccand",
        "page_name": "Tin tức CAND",
        "page_handle": "tintuccand",
        "save_dir_name": "json-nhung-tintuccand-v9-3-2",
        "output_json_name": "posts_Tin_tuc_CAND.json",
        "checkpoint_file_name": "checkpoint_Tin_tuc_CAND_v9_3_2.json",
        "seed_json_path": None,
        "target_posts": 1000,
        "enabled": True,
    },
    {
        "owner_key": "nhung",
        "owner_name": "Nhung",
        "key": "daibieunhandan",
        "url": "https://www.facebook.com/daibieunhandan.vn",
        "page_name": "Đại biểu Nhân dân",
        "page_handle": "daibieunhandan.vn",
        "save_dir_name": "json-nhung-daibieunhandan-v9-3-2",
        "output_json_name": "posts_Dai_bieu_Nhan_dan.json",
        "checkpoint_file_name": "checkpoint_Dai_bieu_Nhan_dan_v9_3_2.json",
        "seed_json_path": None,
        "target_posts": 1000,
        "enabled": True,
    },

    # ==================== YẾN ====================
    {
        "owner_key": "yen",
        "owner_name": "Yến",
        "key": "schannel",
        "url": "https://www.facebook.com/schannel.vn",
        "page_name": "Schannel",
        "page_handle": "schannel.vn",
        "save_dir_name": "json-yen-schannel-v9-3-2",
        "output_json_name": "posts_Schannel.json",
        "checkpoint_file_name": "checkpoint_Schannel_v9_3_2.json",
        "seed_json_path": None,
        "target_posts": 1000,
        "enabled": True,
    },
    {
        "owner_key": "yen",
        "owner_name": "Yến",
        "key": "vietnamnet",
        "url": "https://www.facebook.com/vietnamnet.vn",
        "page_name": "Vietnamnet.vn",
        "page_handle": "vietnamnet.vn",
        "save_dir_name": "json-yen-vietnamnet-v9-3-2",
        "output_json_name": "posts_Vietnamnet_vn.json",
        "checkpoint_file_name": "checkpoint_Vietnamnet_v9_3_2.json",
        "seed_json_path": None,
        "target_posts": 1000,
        "enabled": True,
    },
    {
        "owner_key": "yen",
        "owner_name": "Yến",
        "key": "cafebiz",
        "url": "https://www.facebook.com/cafebiz.vn",
        "page_name": "CafeBiz",
        "page_handle": "cafebiz.vn",
        "save_dir_name": "json-yen-cafebiz-v9-3-2",
        "output_json_name": "posts_CafeBiz.json",
        "checkpoint_file_name": "checkpoint_CafeBiz_v9_3_2.json",
        "seed_json_path": None,
        "target_posts": 1000,
        "enabled": True,
    },
    {
        "owner_key": "yen",
        "owner_name": "Yến",
        "key": "weibovietnam",
        "url": "https://www.facebook.com/weibovietnam",
        "page_name": "Weibo Việt Nam",
        "page_handle": "weibovietnam",
        "save_dir_name": "json-yen-weibovietnam-v9-3-2",
        "output_json_name": "posts_Weibo_Vietnam.json",
        "checkpoint_file_name": "checkpoint_Weibo_Vietnam_v9_3_2.json",
        "seed_json_path": None,
        "target_posts": 1000,
        "enabled": True,
    },
]
# ==============================================================
# ==============================================================


# Không gán nhãn trong crawler; gán nhãn sau bằng script/notebook riêng.

def clean_caption_text(text: str) -> str:
    """Loại các nút UI dính vào caption, không đụng nội dung thật."""
    text = str(text or "").replace("\u200b", "")
    remove_tail = [
        "See less", "Ẩn bớt", "See translation", "Xem bản dịch",
        "See original", "Xem bản gốc"
    ]
    for phrase in remove_tail:
        text = re.sub(rf"\s*{re.escape(phrase)}\s*$", "", text, flags=re.IGNORECASE)
    lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join([line for line in lines if line]).strip()


def save_json_atomic(json_file: str, data: list):
    """Tránh hỏng file nếu process bị ngắt giữa lúc ghi."""
    tmp_file = json_file + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    os.replace(tmp_file, json_file)


def parse_comment_share_from_text(raw_text: str) -> dict:
    """Parse comment/share count từ text/aria của post container.

    Fix v3-minimal:
    - Giữ comment_count theo keyword/aria như v2.
    - Share count lấy từ action row theo cụm số hiển thị:
          reactions, comments, shares
      Trong DOM của bạn mỗi số thường bị lặp 2 lần:
          4.2K, 4.2K, 453, 453, 29, 29
      nên phải collapse duplicate trước, không lấy 453 làm share.
    - Không parse token thời gian 1m/2h.
    """
    text = str(raw_text or "").replace("\xa0", " ")

    patterns = {
        "comment": [
            r"([\d.,]+\s*(?:K|M|B|k|m|b|N|T|nghìn|ngàn|triệu|tỷ)?)\s*(?:lượt\s+)?(?:comments?|bình luận)\b",
            r"(?:comments?|bình luận|lượt bình luận|Leave a comment)\D{0,35}([\d.,]+\s*(?:K|M|B|k|m|b|N|T|nghìn|ngàn|triệu|tỷ)?)",
        ],
        "share": [
            r"([\d.,]+\s*(?:K|M|B|k|m|b|N|T|nghìn|ngàn|triệu|tỷ)?)\s*(?:lượt\s+)?(?:shares?|chia sẻ)\b",
            r"(?:shares?|chia sẻ|lượt chia sẻ|Send this to friends)\D{0,35}([\d.,]+\s*(?:K|M|B|k|m|b|N|T|nghìn|ngàn|triệu|tỷ)?)",
        ],
    }
    out = {"comment": 0, "share": 0}
    debug = {
        "numbers": [],
        "collapsed_action_numbers": [],
        "method": "keyword_only",
        "lines_tail": [],
    }

    for key, pats in patterns.items():
        vals = []
        for pat in pats:
            for m in re.finditer(pat, text, flags=re.IGNORECASE):
                v = parse_count(m.group(1))
                if 0 <= v < 5_000_000:
                    vals.append(v)
        if vals:
            out[key] = max(vals)

    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    debug["lines_tail"] = lines[-80:]

    # Dòng số compact độc lập.
    # Không nhận 1m/2h vì parse_count đã trả 0 với token time lowercase.
    num_re = re.compile(r"^[\d.,]+\s*(?:K|M|B|N|T)?$", re.IGNORECASE)

    numeric = []
    for i, line in enumerate(lines):
        if num_re.fullmatch(line):
            v = parse_count(line)
            if 0 < v < 5_000_000:
                numeric.append({"i": i, "text": line, "value": v})

    debug["numbers"] = numeric[-50:]

    # Tập trung vào vùng action row của post, không lấy số trong comment preview.
    # Trong log của bạn, vùng chuẩn có dạng:
    #   Like
    #   4.2K
    #   4.2K
    #   React
    #   Leave a comment
    #   453
    #   453
    #   Send this to friends...
    #   29
    #   29
    #   See who reacted to this
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        low = line.lower()
        if start_idx is None and (low == "like" or low == "thích"):
            start_idx = i
        if start_idx is not None and (
            "see who reacted" in low
            or "view more comments" in low
            or "write a comment" in low
            or "comment by " in low
            or "xem thêm bình luận" in low
            or "viết bình luận" in low
        ):
            end_idx = i
            break

    action_numeric = []
    if start_idx is not None:
        region_end = end_idx if end_idx is not None else min(len(lines), start_idx + 35)
        for item in numeric:
            if start_idx <= item["i"] < region_end:
                action_numeric.append(item)

    # Nếu không xác định được vùng action row, fallback lấy vùng trước View more comments.
    if not action_numeric:
        cutoff = None
        for i, line in enumerate(lines):
            low = line.lower()
            if "view more comments" in low or "write a comment" in low or "comment by " in low:
                cutoff = i
                break
        if cutoff is not None:
            action_numeric = [x for x in numeric if x["i"] < cutoff]

    # Collapse duplicate liên tiếp do Facebook render cùng số 2 lần.
    collapsed = []
    for item in action_numeric:
        if collapsed and item["value"] == collapsed[-1]["value"] and (item["i"] - collapsed[-1]["i"]) <= 3:
            continue
        collapsed.append(item)

    debug["collapsed_action_numbers"] = collapsed[-20:]

    # Rule chính:
    # sau collapse, cụm chuẩn thường là [total_reactions_display, comment_count, share_count].
    # Ví dụ: [4200, 453, 29].
    if len(collapsed) >= 3:
        # Ưu tiên cụm có số đầu gần total reaction, số thứ 2 bằng comment_count nếu keyword đã có.
        best = None
        best_score = -10**9
        for a, b, c in zip(collapsed, collapsed[1:], collapsed[2:]):
            score = 0
            # Các số action row thường gần nhau.
            if (b["i"] - a["i"]) <= 8 and (c["i"] - b["i"]) <= 8:
                score += 50
            # Số đầu thường là total reactions, thường >= comment.
            if a["value"] >= b["value"]:
                score += 20
            if out["comment"] and b["value"] == out["comment"]:
                score += 100
            # Share thường nhỏ hơn hoặc tương đương comment, không bắt buộc.
            if c["value"] <= max(b["value"] * 5, 50):
                score += 10
            if score > best_score:
                best_score = score
                best = (a, b, c)

        if best and best_score >= 40:
            a, b, c = best
            if out["comment"] == 0:
                out["comment"] = b["value"]
            # Chỉ set share theo số thứ 3 sau collapse, không lấy duplicate của comment.
            out["share"] = c["value"]
            debug["method"] = "collapsed_action_row_reactions_comments_shares"

    # Nếu vẫn không có share nhưng có keyword share thì giữ keyword.
    # Nếu vẫn không có share, để 0 thay vì đoán bừa.
    out["_debug"] = debug
    return out


def parse_count(text: str) -> int:
    """Convert Facebook compact counts to integer.

    Hỗ trợ: 1.8K, 1,8K, 2M, 3,456, 3.456, 4 nghìn, 2 triệu.
    Fix quan trọng: không parse token thời gian lowercase như 19m/41m/2h thành count.
    """
    if not text:
        return 0
    original = str(text).strip()
    s_lower = original.lower().strip()

    # Token thời gian ngắn của Facebook: 19m, 2h, 1d, 30s.
    # Chỉ chặn lowercase; "2M" vẫn là 2 million.
    if re.fullmatch(r"\d+\s*[smhdw]", original) and original[-1].islower():
        return 0

    s = original.strip().upper()
    m = re.search(r"([\d.,]+)\s*(K|M|B|N|T|NGHÌN|NGÀN|TRIỆU|TỶ)?", s, flags=re.IGNORECASE)
    if not m:
        return 0

    raw_num = m.group(1).strip()
    suffix = (m.group(2) or "").upper()

    try:
        if suffix:
            # Có suffix: dấu phẩy/chấm thường là decimal separator.
            num = float(raw_num.replace(",", "."))
        else:
            # Không suffix: xử lý số nguyên theo locale (1,234 | 1.234 | 1234)
            num = float(raw_num.replace(",", "").replace(".", ""))
    except ValueError:
        return 0

    if suffix in {"K", "N", "NGHÌN", "NGÀN"}:
        num *= 1_000
    elif suffix in {"M", "T", "TRIỆU"}:
        num *= 1_000_000
    elif suffix in {"B", "TỶ"}:
        num *= 1_000_000_000
    return int(num)

def parse_facebook_time(time_str) -> int:
    """Convert Facebook time strings to UNIX timestamp.
    Handles:
    - Full date from tooltip: 'Friday, May 16, 2026 at 12:30 AM'
    - UNIX timestamp string: '1747321800'
    - Relative: '1h', '26 phút', 'hôm qua'
    """
    if not time_str:
        return int(time.time())
    s = str(time_str).strip()
    if s.isdigit() and len(s) > 6:
        return int(s)

    # Try full date formats (from tooltip hover and other sources)
    FULL_FORMATS = [
        "%A, %B %d, %Y at %I:%M %p",    # Friday, May 16, 2026 at 12:30 AM  (en-US)
        "%A %d %B %Y at %H:%M",          # Friday 15 May 2026 at 23:55       (en-GB / FB tooltip)
        "%A %d %B %Y at %I:%M %p",       # Friday 15 May 2026 at 11:55 PM
        "%B %d, %Y at %I:%M %p",         # May 16, 2026 at 12:30 AM
        "%d %B %Y at %H:%M",             # 15 May 2026 at 23:55
        "%A, %B %d, %Y",                 # Friday, May 16, 2026
        "%d tháng %m, %Y lúc %H:%M",     # 16 tháng 5, 2026 lúc 00:30
        "%d tháng %m năm %Y lúc %H:%M",  # 16 tháng 5 năm 2026 lúc 00:30
        "%d tháng %m",                   # 16 tháng 5 (năm hiện tại)
        "%d %B at %H:%M",                # 7 May at 9:53 (năm hiện tại)
        "%d %b at %H:%M",                # 7 May at 9:53 (short month)
        "%B %d at %I:%M %p",             # May 16 at 12:30 AM
        "%b %d at %I:%M %p",             # May 16 at 12:30 AM
    ]
    for fmt in FULL_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.year == 1900: # Nếu format không có năm, dùng năm hiện tại
                dt = dt.replace(year=datetime.now().year)
            return int(dt.timestamp())
        except ValueError:
            continue

    sl = s.lower()
    now = datetime.now()
    try:
        # Xử lý dạng "8 tháng 5 lúc 20:15" hoặc "8 tháng 5"
        m_vn_date = re.search(r'(\d+)\s+tháng\s+(\d+)(?:\s+lúc\s+(\d+):(\d+))?', sl)
        if m_vn_date:
            day, month = int(m_vn_date.group(1)), int(m_vn_date.group(2))
            hour = int(m_vn_date.group(3)) if m_vn_date.group(3) else 0
            minute = int(m_vn_date.group(4)) if m_vn_date.group(4) else 0
            dt = datetime(now.year, month, day, hour, minute)
            if dt > now: dt = dt.replace(year=now.year - 1)
            return int(dt.timestamp())

        # Xử lý dạng tiếng Anh: "7 May at 9:53" hoặc "May 7 at 9:53"
        m_en_date = re.search(r'(\d+)\s+([a-z]+)\s+at\s+(\d+):(\d+)', sl)
        if not m_en_date: # Thử format "May 7 at 9:53"
            m_en_date = re.search(r'([a-z]+)\s+(\d+)\s+at\s+(\d+):(\d+)', sl)
            if m_en_date:
                month_str, day = m_en_date.group(1), int(m_en_date.group(2))
            else:
                day, month_str = 0, ""
        else:
            day, month_str = int(m_en_date.group(1)), m_en_date.group(2)

        if m_en_date:
            hour, minute = int(m_en_date.group(3)), int(m_en_date.group(4))
            # Map tháng tiếng Anh
            months = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
            month_idx = -1
            for i, m in enumerate(months):
                if month_str.startswith(m):
                    month_idx = i + 1; break
            if month_idx > 0:
                dt = datetime(now.year, month_idx, day, hour, minute)
                if dt > now: dt = dt.replace(year=now.year - 1)
                return int(dt.timestamp())

        # Short-form: '30s', '48m', '10h', '2d', '3w' (Facebook link text)
        short = re.match(r'^(\d+)\s*([smhdw])$', sl)
        if short:
            n, unit = int(short.group(1)), short.group(2)
            delta = {'s': timedelta(seconds=n), 'm': timedelta(minutes=n),
                     'h': timedelta(hours=n),   'd': timedelta(days=n),
                     'w': timedelta(weeks=n)}[unit]
            return int((now - delta).timestamp())

        if any(k in sl for k in ['vừa xong', 'just now']):
            return int(now.timestamp())
        
        m_re = re.search(r'(\d+)', sl)
        n = int(m_re.group(1)) if m_re else 1
        
        if any(k in sl for k in ['phút', 'min']):
            return int((now - timedelta(minutes=n)).timestamp())
        if any(k in sl for k in ['giờ', 'hour', 'hr']):
            return int((now - timedelta(hours=n)).timestamp())
        if any(k in sl for k in ['hôm qua', 'yesterday']):
            return int((now - timedelta(days=1)).timestamp())
        if any(k in sl for k in ['ngày', 'day']):
            return int((now - timedelta(days=n)).timestamp())
        if any(k in sl for k in ['tuần', 'week']):
            return int((now - timedelta(weeks=n)).timestamp())
        if any(k in sl for k in ['tháng', 'month']) and 'tháng' not in s: # 'X month ago' but not 'Day tháng Month'
            return int((now - timedelta(days=n * 30)).timestamp())
        if any(k in sl for k in ['năm', 'year']):
            return int((now - timedelta(days=n * 365)).timestamp())
    except Exception:
        pass
    return int(now.timestamp())


def human_scroll(page):
    """Simulate smooth human-like scrolling."""
    page.evaluate("""() => new Promise(resolve => {
        let total = 0;
        const target = 1800 + Math.random() * 600;
        const step   = 80  + Math.random() * 50;
        const delay  = 28  + Math.random() * 20;
        const t = setInterval(() => {
            window.scrollBy(0, step);
            total += step;
            if (total >= target) { clearInterval(t); resolve(); }
        }, delay);
    })""")
    time.sleep(random.uniform(2.5, 4.0))



def normalize_facebook_post_url(href: str) -> str:
    """Chuẩn hóa các dạng URL post/photo/permalink của Facebook."""
    if not href:
        return None
    try:
        from urllib.parse import urlparse, parse_qs
        u = urlparse(href)
        qs = parse_qs(u.query)

        # permalink.php?story_fbid=...&id=...
        if "permalink.php" in u.path:
            story = (qs.get("story_fbid") or [None])[0]
            page_id = (qs.get("id") or [None])[0]
            if story and page_id:
                return f"{u.scheme}://{u.netloc}/{page_id}/posts/{story}"

        # photo/?fbid=...&set=pcb.POST_ID...
        set_val = (qs.get("set") or [""])[0]
        m = re.search(r"pcb\.([0-9]+)", set_val or "")
        if m:
            return f"{u.scheme}://{u.netloc}/posts/{m.group(1)}"

        # photo only: giữ fbid nếu không có pcb, nhưng chỉ dùng trong post container.
        fbid = (qs.get("fbid") or [None])[0]
        if fbid and ("photo" in u.path):
            return f"{u.scheme}://{u.netloc}/photo/?fbid={fbid}"

        return href.split("?")[0].rstrip("/")
    except Exception:
        return str(href).split("?")[0].rstrip("/")


def warm_post_for_permalink(page, post_el, max_points=5):
    """Kích hoạt permalink/action row bên trong đúng post container.

    Chỉ rê chuột trong post_el lấy từ share_button, không quét link toàn trang.
    Mục tiêu là thay thao tác hover timestamp thủ công, nhưng không dùng timestamp để lọc ngày.
    """
    moved = 0
    try:
        targets = post_el.evaluate("""(el, maxPoints) => {
            const TIME_RE = /^(\\d+\\s*[smhdw]|\\d+\\s*(phút|giờ|ngày|tuần|tháng|năm)|vừa xong|just now|hôm qua|yesterday)$/i;
            const POST_SEL = [
                'a[href*="/posts/"]',
                'a[href*="pfbid"]',
                'a[href*="story_fbid"]',
                'a[href*="permalink.php"]',
                'a[href*="photo/?fbid"]',
                'a[href*="/photo/"]',
                'a[href*="set=pcb"]',
                'a[href*="/reel/"]',
                'a[href*="/videos/"]',
                'a[href*="/watch/"]',
                'a[href*="/share/"]'
            ].join(',');

            const visible = (n) => {
                const r = n.getBoundingClientRect();
                return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight;
            };
            const point = (n, kind) => {
                const r = n.getBoundingClientRect();
                return {
                    x: Math.round(r.left + Math.max(8, Math.min(r.width / 2, r.width - 8))),
                    y: Math.round(r.top + Math.max(8, Math.min(r.height / 2, r.height - 8))),
                    kind
                };
            };

            const out = [];
            const er = el.getBoundingClientRect();

            // 1) Ưu tiên timestamp trong phần đầu của post.
            const times = [...el.querySelectorAll('a, span')]
                .filter(n => {
                    const txt = (n.innerText || n.getAttribute('aria-label') || '').trim();
                    if (!TIME_RE.test(txt)) return false;
                    const r = n.getBoundingClientRect();
                    return visible(n) && r.top >= er.top - 5 && r.top <= er.top + Math.min(220, er.height * 0.40);
                })
                .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
            for (const n of times.slice(0, 2)) out.push(point(n, 'timestamp'));

            // 2) Link post/photo nằm trong chính post container.
            const links = [...el.querySelectorAll(POST_SEL)]
                .filter(visible)
                .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
            for (const n of links.slice(0, 2)) out.push(point(n, 'post_link'));

            // 3) Caption/story message trong chính post.
            const msg = el.querySelector('[data-ad-rendering-role="story_message"], [data-ad-comet-preview="message"], [data-ad-preview="message"]');
            if (msg && visible(msg)) out.push(point(msg, 'story_message'));

            // 4) Ảnh lớn trong chính post, không phải sidebar vì el là container theo share_button.
            const img = [...el.querySelectorAll('img')]
                .filter(n => {
                    const r = n.getBoundingClientRect();
                    return r.width > 160 && r.height > 100 && visible(n);
                })
                .sort((a, b) => {
                    const ar = a.getBoundingClientRect(), br = b.getBoundingClientRect();
                    return (br.width * br.height) - (ar.width * ar.height);
                })[0];
            if (img) out.push(point(img, 'image'));

            // 5) Vùng header/body fallback.
            out.push({
                x: Math.round(er.left + Math.min(Math.max(er.width * 0.45, 100), er.width - 20)),
                y: Math.round(er.top + Math.min(90, Math.max(er.height - 20, 30))),
                kind: 'post_header'
            });
            out.push({
                x: Math.round(er.left + Math.min(Math.max(er.width * 0.50, 100), er.width - 20)),
                y: Math.round(er.top + Math.min(Math.max(er.height * 0.35, 140), er.height - 20)),
                kind: 'post_body'
            });

            return out.slice(0, maxPoints);
        }""", max_points)

        vp = page.viewport_size or {"width": 1200, "height": 800}
        w = vp.get("width", 1200)
        h = vp.get("height", 800)

        for t in targets:
            x = max(8, min(int(t["x"]), w - 8))
            y = max(8, min(int(t["y"]), h - 8))
            debug_mouse_move(page, x, y, 'scatter_hover')
            page.wait_for_timeout(120)
            moved += 1

        if moved:
            page.wait_for_timeout(350)
        return moved
    except Exception:
        return moved


def extract_quick_url_from_post(post_el):
    """Lấy URL post trong đúng container post, hỗ trợ pfbid/post/photo/permalink."""
    try:
        href = post_el.evaluate("""(el) => {
            if (el.__crawl_quick_url) return el.__crawl_quick_url;
            const patterns = ['/posts/', 'pfbid', 'story_fbid', 'permalink.php', 'photo/?fbid', '/photo/', 'set=pcb', '/reel/', '/videos/', '/watch/', '/share/'];
            const links = [...el.querySelectorAll('a[href]')];

            // Ưu tiên URL post/permalink hơn photo.
            for (const pat of ['/posts/', 'pfbid', 'story_fbid', 'permalink.php']) {
                const a = links.find(a => (a.href || '').includes(pat));
                if (a) return a.href;
            }
            for (const pat of ['set=pcb', 'photo/?fbid', '/photo/']) {
                const a = links.find(a => (a.href || '').includes(pat));
                if (a) return a.href;
            }
            return null;
        }""")
        return normalize_facebook_post_url(href)
    except Exception:
        return None


def check_valid_post(post_el) -> str:
    """Return 'OK' or a skip-reason string.

    V4: không bỏ Reels/Video nữa, vì đây là dạng bài cần thu.
    Vẫn bỏ shared post phức tạp nếu có nhiều story_message để tránh lấy nhầm caption bài được share.
    """
    try:
        return post_el.evaluate("""(el) => {
            if (el.querySelectorAll('[data-ad-rendering-role="story_message"]').length > 1)
                return 'Bài Chia sẻ';
            return 'OK';
        }""") or 'OK'
    except Exception:
        return 'OK'


# Fix reaction mapping: Facebook tiếng Việt 'Thương thương' = Care, không phải Love.

# ===================== V6 HOVERCARD / POPUP HELPERS =====================

def _safe_viewport_size(page):
    try:
        vp = page.viewport_size
        if vp and vp.get("width") and vp.get("height"):
            return int(vp["width"]), int(vp["height"])
    except Exception:
        pass
    try:
        return page.evaluate("() => [window.innerWidth || 1280, window.innerHeight || 720]")
    except Exception:
        return 1280, 720



# ===================== V6.2 VISUAL CURSOR HELPERS =====================

def ensure_visual_cursor(page):
    if not VISUAL_DEBUG_CURSOR:
        return
    try:
        page.evaluate("""() => {
            let dot = document.getElementById('__crawler_cursor_dot__');
            if (!dot) {
                dot = document.createElement('div');
                dot.id = '__crawler_cursor_dot__';
                dot.style.position = 'fixed';
                dot.style.left = '0px';
                dot.style.top = '0px';
                dot.style.width = '22px';
                dot.style.height = '22px';
                dot.style.marginLeft = '-11px';
                dot.style.marginTop = '-11px';
                dot.style.borderRadius = '50%';
                dot.style.background = 'rgba(0, 180, 255, 0.78)';
                dot.style.border = '3px solid white';
                dot.style.boxShadow = '0 0 0 3px rgba(0, 80, 255, 0.75)';
                dot.style.zIndex = '2147483647';
                dot.style.pointerEvents = 'none';
                dot.style.transition = 'left 80ms linear, top 80ms linear';
                document.documentElement.appendChild(dot);
            }
            let label = document.getElementById('__crawler_cursor_label__');
            if (!label) {
                label = document.createElement('div');
                label.id = '__crawler_cursor_label__';
                label.style.position = 'fixed';
                label.style.left = '0px';
                label.style.top = '0px';
                label.style.padding = '3px 7px';
                label.style.borderRadius = '8px';
                label.style.background = 'rgba(0,0,0,0.72)';
                label.style.color = 'white';
                label.style.fontSize = '12px';
                label.style.fontFamily = 'monospace';
                label.style.zIndex = '2147483647';
                label.style.pointerEvents = 'none';
                document.documentElement.appendChild(label);
            }
        }""")
    except Exception:
        pass


def mark_visual_cursor(page, x, y, label=""):
    if not VISUAL_DEBUG_CURSOR:
        return
    try:
        ensure_visual_cursor(page)
        page.evaluate("""({x, y, label}) => {
            const dot = document.getElementById('__crawler_cursor_dot__');
            const lab = document.getElementById('__crawler_cursor_label__');
            if (dot) {
                dot.style.left = Math.round(x) + 'px';
                dot.style.top = Math.round(y) + 'px';
            }
            if (lab) {
                lab.style.left = Math.round(x + 16) + 'px';
                lab.style.top = Math.round(y - 16) + 'px';
                lab.textContent = label || '';
            }
        }""", {"x": x, "y": y, "label": label})
    except Exception:
        pass


def debug_mouse_move(page, x, y, label="move"):
    try:
        mark_visual_cursor(page, x, y, label)
    except Exception:
        pass
    return page.mouse.move(x, y)


def debug_mouse_click(page, x, y, label="click"):
    try:
        mark_visual_cursor(page, x, y, label)
    except Exception:
        pass
    return page.mouse.click(x, y)

# =================== END V6.2 VISUAL CURSOR HELPERS ===================

def overlay_debug_counts(page):
    try:
        return page.evaluate("""() => {
            const visible = (el) => {
                const r = el.getBoundingClientRect();
                const st = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && st.visibility !== 'hidden' && st.display !== 'none';
            };
            const tooltips = [...document.querySelectorAll('[role="tooltip"]')].filter(visible).length;
            const dialogs = [...document.querySelectorAll('[role="dialog"]')].filter(visible).length;
            const cards = [...document.querySelectorAll('[data-testid*="hover"], [aria-label*="Preview"], [aria-label*="preview"]')].filter(visible).length;
            return {tooltips, dialogs, hovercards: cards};
        }""") or {}
    except Exception:
        return {}


def dismiss_hover_popups(page, reason="", click_blank=True, verbose=False):
    """Ẩn hovercard/profile popup do rê nhầm vào tên page/tên người bình luận.

    Facebook thường mở một hovercard khi chuột đi qua page name/commenter.
    Hovercard này có thể che timestamp và reaction row. Cách ổn nhất là:
    - Escape
    - rê chuột ra vùng trắng bên phải
    - click nhẹ vùng trắng
    """
    before = overlay_debug_counts(page)
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(120)
    except Exception:
        pass

    try:
        w, h = _safe_viewport_size(page)
        points = [
            (max(20, w - 36), max(120, min(h - 80, h // 2))),
            (max(20, w - 50), max(100, min(h - 120, 180))),
            (max(20, w - 60), max(100, min(h - 80, h - 120))),
            (12, 12),
        ]
        for x, y in points[:3 if click_blank else 1]:
            debug_mouse_move(page, x, y, 'blank')
            page.wait_for_timeout(80)
            if click_blank:
                debug_mouse_click(page, x, y, 'blank_click')
                page.wait_for_timeout(120)
    except Exception:
        pass

    try:
        # Nếu còn tooltip/hovercard dạng non-modal thì dispatch mouseleave/mouseout để nó tự biến mất.
        page.evaluate("""() => {
            for (const el of document.querySelectorAll('[role="tooltip"], [data-testid*="hover"]')) {
                try {
                    el.dispatchEvent(new MouseEvent('mouseleave', {bubbles:true}));
                    el.dispatchEvent(new MouseEvent('mouseout', {bubbles:true}));
                } catch(e) {}
            }
            if (document.activeElement && document.activeElement.blur) {
                try { document.activeElement.blur(); } catch(e) {}
            }
        }""")
        page.wait_for_timeout(180)
    except Exception:
        pass

    after = overlay_debug_counts(page)
    if verbose or HOVERCARD_DISMISS_VERBOSE:
        print(f"[HOVERCARD_DISMISS] reason={reason} before={before} after={after}", flush=True)
    return after


def wait_for_reaction_dialog(page, timeout_ms=5500):
    """Đợi đúng reaction modal, không lấy nhầm Notifications dialog."""
    deadline = time.time() + timeout_ms / 1000.0
    while time.time() < deadline:
        try:
            ok = page.evaluate("""() => {
                const dialogs = [...document.querySelectorAll('[role="dialog"]')];
                return dialogs.some(d => d.querySelector('[role="tab"]'));
            }""")
            if ok:
                return True
        except Exception:
            pass
        page.wait_for_timeout(180)
    return False

# =================== END V6 HOVERCARD / POPUP HELPERS ===================

def get_reactions_detail(page, post_el) -> dict:
    """Get exact per-reaction counts via modal click.

    Fallback layers (per type):
    1. aria-label count → exact (works for < 1K)
    2. tab innerText ('1.7K') → approximate (for K/M)
    3. Total_All - sum(others) → best-effort (only when exactly 1 type is approximate)
    """
    KNOWN = ["Like", "Love", "Haha", "Wow", "Sad", "Angry", "Care"]
    ZERO  = {k: 0 for k in KNOWN}

    def _parse_k(text):
        t = (text or '').strip().replace(',', '')
        m = re.match(r'([\d.]+)\s*([KkMmBb]?)', t)
        if not m:
            return 0
        n = float(m.group(1))
        suffix = m.group(2).upper()
        if suffix == 'K': return int(n * 1000)
        if suffix == 'M': return int(n * 1_000_000)
        return int(n)

    def _normalize_reaction_name(name: str):
        if not name:
            return None
        n = name.strip().lower()
        mapping = {
            "all": "All", "tất cả": "All",
            "like": "Like", "thích": "Like",
            "love": "Love", "yêu thích": "Love",
            "care": "Care", "thương thương": "Care", "thương": "Care",
            "haha": "Haha", "cười": "Haha",
            "wow": "Wow", "ngạc nhiên": "Wow",
            "sad": "Sad", "buồn": "Sad",
            "angry": "Angry", "phẫn nộ": "Angry",
        }
        return mapping.get(n)

    def _read_tabs():
        return page.evaluate("""() => {
            const dialogs = [...document.querySelectorAll('[role="dialog"]')];
            const modal = dialogs.reverse().find(d => d.querySelector('[role="tab"]'));
            if (!modal) return {};
            const out = {};
            for (const tab of modal.querySelectorAll('[role="tab"]')) {
                const aria = tab.getAttribute('aria-label') || '';
                const text = (tab.innerText || '').trim();
                let key = null;
                let count = 0;

                const m_en = aria.match(/Show\\s+([\\d,]+)\\s+people.*?with\\s+(\\w+)/i);
                if (m_en) {
                    key = m_en[2];
                    count = parseInt(m_en[1].replace(/,/g,'')) || 0;
                } else {
                    const m_any = aria.match(/([\\d.,]+)\\s+(people|ng\\u01b0\\u1eddi).*?(with|v\\u1edbi)?\\s*([^,]*)/i);
                    if (m_any) {
                        key = (m_any[4] || '').trim();
                        count = 0; // fallback parse ở Python
                    }
                }

                if (!key && text) {
                    key = text.split('\\n')[0].trim();
                }
                if (key) out[key] = { count, text };
            }
            return out;
        }""") or {}

    try:
        if DISMISS_HOVERCARD_BEFORE_REACTION:
            dismiss_hover_popups(page, reason="before_reaction_click", click_blank=True, verbose=False)
        try:
            post_el.evaluate("(el) => el.scrollIntoView({block: 'center', inline: 'nearest'})")
            page.wait_for_timeout(180)
        except Exception:
            pass

        clicked = post_el.evaluate("""(el) => {
            const btns = [...el.querySelectorAll('[role="button"]')];
            const btn = btns.find(b =>
                /reaction|people|ng\u01b0\u1eddi/i.test(b.getAttribute('aria-label') || '') &&
                b.querySelector('img')
            );
            if (btn) { btn.click(); return true; }
            const btn2 = btns.find(b => /reaction|people|ng\u01b0\u1eddi/i.test(b.getAttribute('aria-label') || ''));
            if (btn2) { btn2.click(); return true; }
            return false;
        }""")
        if not clicked:
            return ZERO

        if not wait_for_reaction_dialog(page, timeout_ms=5500):
            dismiss_hover_popups(page, reason="reaction_dialog_not_found", click_blank=True, verbose=True)
            return ZERO
        time.sleep(0.8)
        raw = _read_tabs()
        if not raw:
            page.keyboard.press("Escape")
            dismiss_hover_popups(page, reason="reaction_dialog_empty_tabs", click_blank=True, verbose=True)
            return ZERO

        normalized = {}
        for rk, rv in raw.items():
            nk = _normalize_reaction_name(rk)
            if nk:
                normalized[nk] = rv

        total_all = normalized.get('All', {}).get('count', 0)

        # Layer 1 & 2: aria-label exact, fallback to tab text
        resolved = {}
        for k in KNOWN:
            entry = normalized.get(k, {})
            c = entry.get('count', 0)
            t = entry.get('text', '')
            resolved[k] = c if c > 0 else _parse_k(t)

        # Layer 3: if exactly ONE type is approximate, derive from Total - others
        approx = [k for k in KNOWN
                  if normalized.get(k, {}).get('count', 0) == 0
                  and normalized.get(k, {}).get('text', '')]
        if len(approx) == 1 and total_all > 0:
            others = sum(resolved[k] for k in KNOWN if k not in approx)
            resolved[approx[0]] = max(0, total_all - others)

        page.keyboard.press("Escape")
        dismiss_hover_popups(page, reason="after_reaction_modal", click_blank=True, verbose=False)
        time.sleep(0.35)
        return {k: resolved.get(k, 0) for k in KNOWN}

    except Exception as e:
        print(f"      [!] reactions modal error: {e}")
        try:
            dismiss_hover_popups(page, reason="reaction_exception", click_blank=True, verbose=True)
        except Exception:
            pass
        return ZERO


def _extract_caption(post_el, page_name: str) -> str:
    """
    Trích xuất caption bằng chiến thuật 'Mưa dầm thấm lâu':
    1. Ưu tiên semantic roles.
    2. Fallback: Quét toàn bộ cây DOM, lọc nhiễu và lấy khối văn bản thực sự.
    """
    return post_el.evaluate("""(el, pageName) => {
        const SEMANTIC_SELS = [
            '[data-ad-rendering-role="story_message"]',
            '[data-ad-comet-preview="message"]',
            '[data-ad-preview="message"]',
            '[data-ad-rendering-role="message"]',
            '[role="presentation"] [dir="auto"]'
        ];
        for (const sel of SEMANTIC_SELS) {
            const c = el.querySelector(sel);
            if (c && c.innerText.trim().length > 2) return c.innerText.trim();
        }

        // Fallback: Quét tất cả các thẻ có chứa text
        const isNoise = t => {
            const noise = [
                /^[\d.,]+[KMB]?$/i,
                /^(Like|Comment|Share|Chia sẻ|Bình luận|Thích|Yêu thích|Haha|Wow|Buồn|Phẫn nộ)$/i,
                /^\d+\s*(phút|giờ|ngày|m|h|d|w|s)/i,
                /^(See more|Xem thêm|See translation|Xem bản dịch)$/i,
                new RegExp('^' + pageName + '$', 'i')
            ];
            return noise.some(p => p.test(t.trim()));
        };

        // Lấy tất cả các đoạn text "sạch"
        const nodes = [...el.querySelectorAll('div[dir="auto"], span[dir="auto"], div[role="none"]')];
        let candidates = nodes
            .map(n => {
                // Loại bỏ các thẻ ẩn (Facebook dùng để chống crawl)
                const clone = n.cloneNode(true);
                clone.querySelectorAll('[style*="display:none"], [style*="position:absolute"]').forEach(e => e.remove());
                return clone.innerText.trim();
            })
            .filter(t => t.length > 2 && !isNoise(t));

        if (candidates.length > 0) {
            // Sắp xếp theo độ dài giảm dần, lấy cái dài nhất (thường là caption)
            candidates.sort((a, b) => b.length - a.length);
            return candidates[0];
        }

        return '';
    }""", page_name)


def canonicalize_facebook_post_url(raw_url: str, page_handle: str = "") -> str:
    if not raw_url:
        return None
    raw_url = str(raw_url).strip()
    try:
        from urllib.parse import urlparse, parse_qs
        p = urlparse(raw_url)
        host = p.netloc or "www.facebook.com"
        path = p.path or ""
        qs = parse_qs(p.query or "")

        m = re.search(r"/([^/?#]+)/posts/(pfbid[^/?#]+|[0-9]+)", path)
        if m:
            handle, post_id = m.group(1), m.group(2)
            if handle.lower() in {"posts", "photo", "permalink.php"} and page_handle:
                handle = page_handle
            return f"https://{host}/{handle}/posts/{post_id}"

        story = (qs.get("story_fbid") or [None])[0]
        if story and page_handle:
            return f"https://{host}/{page_handle}/posts/{story}"

        set_val = (qs.get("set") or [""])[0]
        m_pcb = re.search(r"pcb\.([0-9]+)", set_val or "")
        if m_pcb and page_handle:
            return f"https://{host}/{page_handle}/posts/{m_pcb.group(1)}"

        fbid = (qs.get("fbid") or [None])[0]
        if fbid and page_handle:
            return f"https://{host}/{page_handle}/posts/{fbid}"

        m2 = re.search(r"/posts/(pfbid[^/?#]+|[0-9]+)", path)
        if m2 and page_handle:
            return f"https://{host}/{page_handle}/posts/{m2.group(1)}"

        return raw_url.split("?")[0].rstrip("/")
    except Exception:
        return raw_url.split("?")[0].rstrip("/")




def strip_tracking_and_comment_from_url(raw_url: str) -> str:
    """Bỏ query tracking/comment_id; giữ lại path chính của bài."""
    if not raw_url:
        return None
    try:
        from urllib.parse import urlparse, urlencode
        p = urlparse(str(raw_url).strip())
        # Giữ một số query cần thiết cho /watch/?v=...
        keep = {}
        from urllib.parse import parse_qs
        qs = parse_qs(p.query or "")
        if "v" in qs:
            keep["v"] = qs["v"][0]
        query = urlencode(keep)
        base = p._replace(query=query, fragment="")
        return base.geturl()
    except Exception:
        return str(raw_url).split("#")[0]




def looks_like_valid_timestamp_raw(raw: str) -> bool:
    """Chỉ xem là timestamp hợp lệ nếu là raw date/time thật."""
    raw = str(raw or "").strip()
    if not raw:
        return False
    if raw in {"Reels", "Photos", "Videos"}:
        return False

    toks = raw.split()
    if len(toks) >= 20 and sum(1 for t in toks if len(t) == 1) / max(len(toks), 1) > 0.7:
        return False

    patterns = [
        r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b.*\bat\s+\d{1,2}:\d{1,2}\b",
        r"\bToday\s+at\s+\d{1,2}:\d{1,2}\b",
        r"\bYesterday\s+at\s+\d{1,2}:\d{1,2}\b",
        r"\b(Added|Updated|Posted)\s+(Today|Yesterday)\s+at\s+\d{1,2}:\d{1,2}\b",
        r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\s+at\s+\d{1,2}:\d{1,2}\b",
        r"\bHôm qua\s+lúc\s+\d{1,2}:\d{1,2}\b",
        r"\b\d{1,2}\s+tháng\s+\d{1,2},?\s+\d{4}\s+lúc\s+\d{1,2}:\d{1,2}\b",
        r"\bThứ\s+\w+,?\s+\d{1,2}\s+tháng\s+\d{1,2},?\s+\d{4}\s+lúc\s+\d{1,2}:\d{1,2}\b",
    ]
    return any(re.search(p, raw, flags=re.I) for p in patterns)


def parse_fb_timestamp_tooltip(raw: str):
    """Parse timestamp raw từ Facebook.

    Hỗ trợ:
    - Thursday 21 May 2026 at 22:23
    - 28 July 2025 at 19:30
    - Yesterday at 20:17
    - Added Yesterday at 20:27
    - Hôm qua lúc 20:17
    - 28 tháng 7, 2025 lúc 19:30
    """
    raw = str(raw or "").strip()
    if not raw:
        return None, None

    raw2 = re.sub(r"\s+", " ", raw).strip()
    raw2 = re.sub(r"^(Added|Updated|Posted)\s+", "", raw2, flags=re.I).strip()

    m = re.search(r"\bToday\s+at\s+(\d{1,2}):(\d{1,2})\b", raw2, flags=re.I)
    if m:
        hour, minute = map(int, m.groups())
        dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        return int(dt.timestamp()), dt.strftime("%Y-%m-%d %H:%M:%S")

    m = re.search(r"\bYesterday\s+at\s+(\d{1,2}):(\d{1,2})\b", raw2, flags=re.I)
    if m:
        hour, minute = map(int, m.groups())
        dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0) - timedelta(days=1)
        return int(dt.timestamp()), dt.strftime("%Y-%m-%d %H:%M:%S")

    m = re.search(r"\bHôm qua\s+lúc\s+(\d{1,2}):(\d{2})\b", raw2, flags=re.I)
    if m:
        hour, minute = map(int, m.groups())
        dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0) - timedelta(days=1)
        return int(dt.timestamp()), dt.strftime("%Y-%m-%d %H:%M:%S")

    formats = [
        "%A %d %B %Y at %H:%M",
        "%A, %d %B %Y at %H:%M",
        "%d %B %Y at %H:%M",
        "%A %d %b %Y at %H:%M",
        "%d %b %Y at %H:%M",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(raw2, fmt)
            return int(dt.timestamp()), dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s+at\s+(\d{1,2}):(\d{2})", raw2)
    if m:
        day, mon, year, hour, minute = m.groups()
        for fmt_mon in ("%B", "%b"):
            try:
                mon_num = datetime.strptime(mon, fmt_mon).month
                dt = datetime(int(year), mon_num, int(day), int(hour), int(minute))
                return int(dt.timestamp()), dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

    m = re.search(r"(?:Thứ\s+\w+,?\s+)?(\d{1,2})\s+tháng\s+(\d{1,2}),?\s+(\d{4})\s+lúc\s+(\d{1,2}):(\d{2})", raw2, flags=re.I)
    if m:
        day, month, year, hour, minute = map(int, m.groups())
        try:
            dt = datetime(year, month, day, hour, minute)
            return int(dt.timestamp()), dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    return None, None

def normalize_post_like_url_from_timestamp(raw_url: str, page_handle: str = "") -> str:
    """Chuẩn hóa URL lấy từ timestamp/header/comment permalink.

    Nếu lỡ hover trúng time của comment nhưng URL có dạng:
        /reel/<id>/?comment_id=...
        /posts/<id>?comment_id=...
    thì strip comment_id để vẫn lấy URL bài gốc.
    """
    if not raw_url:
        return None
    raw_url = strip_tracking_and_comment_from_url(str(raw_url).strip())
    try:
        from urllib.parse import urlparse, parse_qs
        p = urlparse(raw_url)
        host = p.netloc or "www.facebook.com"
        path = p.path or ""
        qs = parse_qs(p.query or "")

        # Reels
        m_reel = re.search(r"/reel/([0-9]+)", path)
        if m_reel:
            return f"https://{host}/reel/{m_reel.group(1)}"

        # Share reels/video/post links
        m_share_r = re.search(r"/share/r/([^/?#]+)", path)
        if m_share_r:
            return f"https://{host}/share/r/{m_share_r.group(1)}"
        m_share_v = re.search(r"/share/v/([^/?#]+)", path)
        if m_share_v:
            return f"https://{host}/share/v/{m_share_v.group(1)}"
        m_share_p = re.search(r"/share/p/([^/?#]+)", path)
        if m_share_p:
            return f"https://{host}/share/p/{m_share_p.group(1)}"

        # Video/watch
        v = (qs.get("v") or [None])[0]
        if v and ("/watch" in path or "/watch/" in path):
            return f"https://{host}/watch/?v={v}"
        m_vid = re.search(r"/videos/([0-9]+)", path)
        if m_vid:
            handle = page_handle.strip("/") if page_handle else ""
            if handle:
                return f"https://{host}/{handle}/videos/{m_vid.group(1)}"
            return f"https://{host}/videos/{m_vid.group(1)}"

        return canonicalize_facebook_post_url(raw_url, page_handle)
    except Exception:
        return canonicalize_facebook_post_url(raw_url, page_handle)


def get_header_timestamp_permalink(page, post_el, page_handle: str = "", do_hover: bool = True):
    """Lấy URL từ timestamp/header anchor của post.

    V7:
    - Không phụ thuộc innerText '2h/9m' vì Facebook có thể render text bị obfuscate.
    - Chọn anchor nhỏ ngay dưới page name, nằm trong header, phía trên nút share/action row.
    - Hover để lấy href/tooltip nếu anchor được hydrate khi rê chuột.
    - Loại URL comment_id để tránh hover nhầm comment time.
    """
    debug = {
        "found": False,
        "raw_href": None,
        "normalized": None,
        "time_text": None,
        "tooltip": None,
        "timestamp_unix": None,
        "timestamp_human": None,
        "reason": "",
        "candidates": [],
        "source": "geometry_header_anchor",
    }

    try:
        info = post_el.evaluate("""(el, args) => {
            const maxRelTop = args.maxRelTop || 105;
            const minGap = args.minGap || 20;

            const visible = (n) => {
                const r = n.getBoundingClientRect();
                return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight;
            };
            const rect = (n) => {
                const r = n.getBoundingClientRect();
                return {x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height), bottom: Math.round(r.bottom)};
            };

            const eraw = el.getBoundingClientRect();
            const er = rect(el);
            const shareBtns = [...el.querySelectorAll('[data-ad-rendering-role="share_button"]')].filter(visible);
            const shareTop = shareBtns.length
                ? Math.min(...shareBtns.map(b => b.getBoundingClientRect().top))
                : eraw.top + eraw.height;

            const pageNameLinks = [...el.querySelectorAll('a[href]')]
                .filter(a => visible(a))
                .map((a, idx) => {
                    const r = rect(a);
                    const text = (a.innerText || a.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim();
                    return {idx, text, href: a.href || '', rect: r, relTop: Math.round(r.y - er.y)};
                })
                .filter(x =>
                    x.relTop >= 0 && x.relTop <= 85 &&
                    x.rect.w >= 35 && x.rect.w <= 280 &&
                    /facebook\\.com\\/[^/?#]+/.test(x.href || '')
                );

            const nameX = pageNameLinks.length ? pageNameLinks[0].rect.x : null;
            const nameBottom = pageNameLinks.length ? pageNameLinks[0].rect.bottom : (er.y + 25);

            const nodes = [...el.querySelectorAll('a[href]')]
                .map((a, idx) => {
                    const r = rect(a);
                    const href = a.href || '';
                    const text = (a.innerText || a.getAttribute('aria-label') || a.getAttribute('title') || '').replace(/\\s+/g, ' ').trim();
                    const aria = (a.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim();
                    const title = (a.getAttribute('title') || '').replace(/\\s+/g, ' ').trim();
                    const relTop = r.y - er.y;
                    const aboveShare = r.y < shareTop - minGap;
                    const belowPageName = visible(a) && r.y >= nameBottom - 4 && r.y <= nameBottom + 46;
                    const alignedWithName = nameX === null ? true : Math.abs(r.x - nameX) <= 55;
                    const smallHeaderAnchor =
                        visible(a) &&
                        relTop >= 16 && relTop <= maxRelTop &&
                        r.h >= 8 && r.h <= 30 &&
                        r.w >= 3 && r.w <= 190 &&
                        aboveShare;
                    const tnHint = /__tn__=.*%2CO|__tn__=%2CO|#\\?/.test(href);
                    const directPostHint = /\\/posts\\/|pfbid|story_fbid|permalink\\.php|\\/reel\\/|\\/videos\\/|\\/watch\\/|photo\\/\\?fbid|set=pcb/i.test(href);
                    const commentHint = /comment_id=|reply_comment_id=/i.test(href);
                    let score = 0;
                    if (directPostHint) score += 170;
                    if (smallHeaderAnchor) score += 120;
                    if (belowPageName) score += 110;
                    if (alignedWithName) score += 70;
                    if (tnHint) score += 80;
                    if (aboveShare) score += 90; else score -= 160;
                    if (commentHint) score -= 320;
                    if (r.y < er.y || r.y > shareTop) score -= 180;
                    if (r.w > 260 || r.h > 90) score -= 140;
                    return {
                        idx, text, aria, title, href,
                        rect: r,
                        relTop: Math.round(relTop),
                        aboveShare,
                        belowPageName,
                        alignedWithName,
                        tnHint,
                        directPostHint,
                        commentHint,
                        score
                    };
                })
                .filter(x => x.score > 40)
                .sort((a, b) => b.score - a.score);

            return {
                postRect: er,
                shareTop: Math.round(shareTop),
                pageNameLinks,
                best: nodes[0] || null,
                candidates: nodes.slice(0, 10)
            };
        }""", {
            "maxRelTop": HEADER_ANCHOR_MAX_RELTOP,
            "minGap": HEADER_TIMESTAMP_MIN_GAP_ABOVE_SHARE,
        })

        candidates = (info or {}).get("candidates", []) or []
        debug["candidates"] = candidates
        best = (info or {}).get("best")
        if not best:
            debug["reason"] = "no_geometry_header_anchor"
            return None, debug

        def accept_url(raw_url):
            if not raw_url:
                return None
            if re.search(r"comment_id=|reply_comment_id=", raw_url, flags=re.I):
                return None
            normalized = normalize_post_like_url_from_timestamp(raw_url, page_handle)
            ptype = infer_post_type_from_url(normalized)
            if ptype in {"post", "reel", "video", "photo"}:
                return normalized
            # Không nhận page URL dạng /yannews?__cft__ làm post_url.
            return None

        debug["time_text"] = best.get("text") or best.get("aria") or best.get("title")
        raw_href = best.get("href") or ""
        debug["raw_href"] = raw_href

        # Nếu href đã là post/reel/video/photo thì nhận ngay.
        normalized = accept_url(raw_href)
        if normalized:
            debug["normalized"] = normalized
            debug["found"] = True
            try:
                post_el.evaluate("(el, dbg) => { el.__resolved_header_ts_debug = dbg; }", debug)
            except Exception:
                pass
            return normalized, debug

        # Hover anchor nhỏ dưới page name để FB hydrate href và hiện tooltip ngày giờ.
        if do_hover:
            r = best.get("rect") or {}
            x = int(r.get("x", 0) + max(3, min(r.get("w", 10) / 2, max(r.get("w", 10) - 3, 3))))
            y = int(r.get("y", 0) + max(3, min(r.get("h", 10) / 2, max(r.get("h", 10) - 3, 3))))
            try:
                dismiss_hover_popups(page, reason="before_header_timestamp_hover", click_blank=True, verbose=False)
                debug_mouse_move(page, x, y, 'header_ts')
                page.wait_for_timeout(HEADER_ANCHOR_HOVER_TIMEOUT_MS)
            except Exception:
                pass

            tooltip = ""
            try:
                tip = page.query_selector('[role="tooltip"]')
                if tip:
                    tooltip = (tip.inner_text() or "").strip()
            except Exception:
                pass
            debug["tooltip"] = tooltip

            raw2 = post_el.evaluate("""(el, args) => {
                const x = args.x, y = args.y;
                const hovered = document.elementFromPoint(x, y);
                const a1 = hovered && hovered.closest && hovered.closest('a[href]');
                return a1 ? a1.href : '';
            }""", {"x": x, "y": y})

            if raw2:
                debug["raw_href"] = raw2
                normalized = accept_url(raw2)
                if normalized:
                    debug["normalized"] = normalized
                    debug["found"] = True
                    ts_unix, ts_human = parse_fb_timestamp_tooltip(tooltip)
                    debug["timestamp_unix"] = ts_unix
                    debug["timestamp_human"] = ts_human
                    try:
                        post_el.evaluate("(el, dbg) => { el.__resolved_header_ts_debug = dbg; }", debug)
                    except Exception:
                        pass
                    return normalized, debug

            # Fallback rất an toàn: nếu candidate có href page nhưng trong container có reel/video/photo/post direct link,
            # resolver cũ/fallback sẽ xử lý phía sau. Không ép nhận page URL.
            ts_unix, ts_human = parse_fb_timestamp_tooltip(tooltip)
            debug["timestamp_unix"] = ts_unix
            debug["timestamp_human"] = ts_human
            try:
                post_el.evaluate("(el, dbg) => { el.__resolved_header_ts_debug = dbg; }", debug)
            except Exception:
                pass

        debug["reason"] = "header_anchor_no_accepted_href"
        return None, debug

    except Exception as e:
        debug["reason"] = f"exception:{str(e)[:120]}"
        return None, debug

def get_best_post_url_from_element(page, post_el, page_handle: str = "") -> str:
    """Lấy URL tốt nhất của post.

    V5: ưu tiên timestamp ở header, vì đây là điểm ổn định nhất cho post thường,
    Reels, video, ảnh và link-card. Nếu không lấy được mới fallback sang scorer cũ.
    """
    page_handle = str(page_handle or "").strip("/")

    if HEADER_TIMESTAMP_RESOLVER:
        ts_url, ts_debug = get_header_timestamp_permalink(page, post_el, page_handle, do_hover=True)
        if ts_url:
            return ts_url

    try:
        target = post_el.evaluate_handle("""(el) => {
            const TIME_RE = /^(\\d+\\s*[smhdw]|\\d+\\s*(phút|giờ|ngày|tuần|tháng|năm)|vừa xong|just now|hôm qua|yesterday)$/i;
            const ar = el.getBoundingClientRect();
            const visible = (x) => {
                const r = x.getBoundingClientRect();
                return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight;
            };

            const timeLinks = [...el.querySelectorAll('a, span')]
                .filter(a => {
                    const txt = (a.innerText || a.getAttribute('aria-label') || '').trim();
                    if (!TIME_RE.test(txt)) return false;
                    if (!visible(a)) return false;
                    const r = a.getBoundingClientRect();
                    return r.top >= ar.top && r.top <= ar.top + Math.min(180, ar.height * 0.35);
                })
                .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);

            if (timeLinks.length) return timeLinks[0];

            const postLinks = [...el.querySelectorAll('a[href*="/posts/"], a[href*="pfbid"], a[href*="story_fbid"], a[href*="permalink.php"], a[href*="/reel/"], a[href*="/videos/"], a[href*="/watch/"], a[href*="/share/"]')]
                .filter(visible)
                .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
            return postLinks[0] || null;
        }""")
        target_el = target.as_element()
        if target_el:
            try:
                target_el.hover(timeout=1200)
                page.wait_for_timeout(450)
            except Exception:
                try:
                    box = target_el.bounding_box()
                    if box:
                        debug_mouse_move(page, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, "reaction_target")
                        page.wait_for_timeout(450)
                except Exception:
                    pass
    except Exception:
        pass

    try:
        raw_best = post_el.evaluate("""(el, pageHandle) => {
            const links = [...el.querySelectorAll('a[href]')];
            const ar = el.getBoundingClientRect();
            const isCommentUrl = (href) => /[?&](comment_id|reply_comment_id)=|comment_id%3D|comment_tracking/i.test(href || '');

            const scored = [];
            for (const a of links) {
                const href = a.href || '';
                if (!href || !href.includes('facebook.com')) continue;
                if (isCommentUrl(href)) continue;

                const r = a.getBoundingClientRect();
                const txt = (a.innerText || a.getAttribute('aria-label') || '').trim();
                let score = 0;

                if (pageHandle && href.includes('/' + pageHandle + '/posts/pfbid')) score += 3000;
                else if (/\\/[^/?#]+\\/posts\\/pfbid/i.test(href)) score += 2600;
                else if (href.includes('pfbid')) score += 2300;
                else if (href.includes('story_fbid') || href.includes('permalink.php')) score += 1900;
                else if (pageHandle && href.includes('/' + pageHandle + '/posts/')) score += 1600;
                else if (/\\/posts\\/[0-9]+/i.test(href)) score += 700;
                else if (href.includes('/reel/')) score += 1500;
                else if (href.includes('/videos/') || href.includes('/watch/') || href.includes('/share/v/')) score += 1400;
                else if (href.includes('set=pcb')) score += 450;
                else if (href.includes('photo/?fbid') || href.includes('/photo/')) score += 120;
                else if (href.includes('/share/')) score += 80;
                else continue;

                if (r.width > 0 && r.height > 0) {
                    if (r.top >= ar.top && r.top <= ar.top + Math.min(190, ar.height * 0.35)) score += 600;
                    if (r.bottom > 0 && r.top < innerHeight) score += 100;
                }

                if (/^(\\d+\\s*[smhdw]|\\d+\\s*(phút|giờ|ngày|tuần|tháng|năm)|vừa xong|just now|hôm qua|yesterday)$/i.test(txt)) {
                    score += 700;
                }

                scored.push({href, score});
            }

            scored.sort((a, b) => b.score - a.score);
            return scored[0]?.href || null;
        }""", page_handle)
    except Exception:
        raw_best = None

    return canonicalize_facebook_post_url(raw_best, page_handle)




def infer_post_type_from_url(url: str) -> str:
    """Gắn nhãn dạng bài dựa trên URL lấy được."""
    u = str(url or "").lower()
    if not u or u == "none":
        return "unknown"
    if "/reel/" in u or "/share/r/" in u:
        return "reel"
    if "/videos/" in u or "/watch/" in u or "/share/v/" in u:
        return "video"
    if "photo/?fbid" in u or "/photo/" in u:
        return "photo"
    if "/posts/" in u or "pfbid" in u or "story_fbid" in u or "permalink.php" in u or "/share/p/" in u:
        return "post"
    return "unknown"


def extract_external_url_from_post(post_el) -> str:
    """Lấy link bài báo ngoài nếu post là link card, không dùng làm post_url chính."""
    try:
        href = post_el.evaluate("""(el) => {
            const links = [...el.querySelectorAll('a[href]')].map(a => a.href || '').filter(Boolean);
            const ext = links.find(h =>
                !/facebook\\.com/i.test(h) ||
                /l\\.facebook\\.com\\/l\\.php|lm\\.facebook\\.com\\/l\\.php/i.test(h)
            );
            return ext || null;
        }""")
        if not href:
            return None
        from urllib.parse import urlparse, parse_qs, unquote
        p = urlparse(href)
        if "facebook.com" in p.netloc and p.path.endswith("/l.php"):
            u = (parse_qs(p.query).get("u") or [None])[0]
            return unquote(u) if u else href
        return href
    except Exception:
        return None

def extract_post_data(page, post_el, page_name: str, page_handle: str = '', pre_parsed_ts: int = None, pre_raw_ts: str = None, resolved_url: str = None) -> dict:
    """Build a complete post data dict from a post element."""
    data = {}

    # 1. URL & ID
    # Ưu tiên URL đã resolve ở main loop. Tránh gọi lại resolver lần 2 rồi bị null/hover nhầm.
    url = normalize_post_like_url_from_timestamp(resolved_url, page_handle) if resolved_url else get_best_post_url_from_element(page, post_el, page_handle)
    data['post_url'] = url
    data['post_id'] = url.rstrip('/').split('/')[-1] if url else f"temp_{int(time.time() * 1000)}"
    data['post_type'] = infer_post_type_from_url(url)
    data['external_url'] = extract_external_url_from_post(post_el)

    # Timestamp metadata từ header anchor, nếu đã resolve được ở get_best_post_url_from_element thì lấy cache.
    ts_dbg = None
    if CAPTURE_POST_TIMESTAMP:
        try:
            ts_dbg = post_el.evaluate("el => el.__resolved_header_ts_debug || null")
        except Exception:
            ts_dbg = None
        if not ts_dbg:
            try:
                _, ts_dbg = get_header_timestamp_permalink(page, post_el, page_handle, do_hover=True)
            except Exception:
                ts_dbg = None

    tooltip_ts = (ts_dbg or {}).get('tooltip')
    time_text_ts = (ts_dbg or {}).get('time_text')

    # Chỉ lưu raw timestamp nếu là tooltip ngày giờ thật. Không lưu text obfuscate.
    raw_ts = tooltip_ts if looks_like_valid_timestamp_raw(tooltip_ts) else None
    if not raw_ts and looks_like_valid_timestamp_raw(time_text_ts):
        raw_ts = time_text_ts

    ts_unix = (ts_dbg or {}).get('timestamp_unix')
    ts_human = (ts_dbg or {}).get('timestamp_human')
    if raw_ts and not ts_unix:
        ts_unix, ts_human = parse_fb_timestamp_tooltip(raw_ts)

    # Nếu không parse được thì để null, tránh đưa chuỗi rác vào dataset.
    timestamp_status = "ok" if ts_human else ("missing_or_unparsed" if ts_dbg else "not_attempted")

    data['post_timestamp_raw'] = raw_ts
    data['post_timestamp_unix'] = ts_unix
    data['post_timestamp_human'] = ts_human
    data['timestamp_source'] = (ts_dbg or {}).get('source')
    data['timestamp_semantics'] = (ts_dbg or {}).get('timestamp_semantics')
    data['clock_right_probe'] = (ts_dbg or {}).get('clock_right_probe')
    data['timestamp_url'] = (ts_dbg or {}).get('normalized') if ts_human else None
    data['timestamp_status'] = timestamp_status

    # 2. Expand "See more" / "Xem thêm"
    try:
        post_el.evaluate("""(el) => {
            el.querySelectorAll('[role="button"]').forEach(btn => {
                const t = (btn.innerText || '').trim();
                if (['Xem thêm', 'See more', 'See More'].includes(t)) btn.click();
            });
        }""")
        time.sleep(0.5)
    except Exception:
        pass

    # 3. Caption
    data['post_content'] = clean_caption_text(_extract_caption(post_el, page_name))

    # 5. Share & comment counts – chỉ parse khi có keyword đi kèm.
    # Giữ nguyên các phần timestamp/reaction đã chạy tốt, chỉ bỏ logic lấy số đứng một mình
    # vì nó gây lỗi 19m/41m timestamp -> 19M/41M comments.
    counts_raw_text = post_el.evaluate("""(el) => {
        const pieces = [];
        const fullText = (el.innerText || '').trim();
        if (fullText) pieces.push(fullText);
        for (const node of el.querySelectorAll('[aria-label], span[dir="auto"], a[role="link"], div[role="button"], span, a')) {
            const aria = node.getAttribute('aria-label') || '';
            const text = (node.innerText || '').trim();
            if (aria) pieces.push(aria);
            if (text) pieces.push(text);
        }
        return pieces.join('\\n');
    }""")
    counts = parse_comment_share_from_text(counts_raw_text)
    data['share_count']   = counts.get('share', 0)
    data['comment_count'] = counts.get('comment', 0)
    # Debug nhẹ để kiểm chứng share count nhưng không ảnh hưởng pipeline chính.
    data['count_extract_method'] = counts.get('_debug', {}).get('method', '')
    data['count_debug_numbers'] = counts.get('_debug', {}).get('numbers', [])
    data['count_debug_lines_tail'] = counts.get('_debug', {}).get('lines_tail', [])


    # 6. Reactions
    data['reactions_detail'] = get_reactions_detail(page, post_el)
    sum_detail = sum(data['reactions_detail'].values())
    total_disp = parse_count(post_el.evaluate("""(el) => {
        for (const s of el.querySelectorAll('span[dir="auto"]')) {
            const t = (s.innerText || '').trim();
            if (/^[\d.,]+[KkMmBb]?$/.test(t)) return t;
        }
        return '0';
    }"""))

    # Nếu tổng reaction hiển thị có nhưng modal detail bị rỗng, retry một lần.
    # Đây là lỗi hiếm do Facebook chưa mở/hydrate modal kịp.
    if sum_detail == 0 and total_disp > 0:
        print(f"      [WARN] reaction detail rỗng nhưng total≈{total_disp}; retry modal một lần")
        try:
            page.keyboard.press("Escape")
            dismiss_hover_popups(page, reason="before_reaction_retry", click_blank=True, verbose=True)
            time.sleep(0.4)
        except Exception:
            pass
        data['reactions_detail'] = get_reactions_detail(page, post_el)
        sum_detail = sum(data['reactions_detail'].values())

    data['total_reactions'] = sum_detail if sum_detail > 0 else total_disp
    # Ưu tiên detail_sum từ modal reaction khi có.

    # 7. Crawl Time
    data['crawl_time'] = int(time.time())
    data['crawl_time_human'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return data



def format_elapsed(seconds: float) -> str:
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def short_text(text: str, n: int = 50) -> str:
    text = str(text or "").replace("\n", " ").strip()
    return text[:n] + ("..." if len(text) > n else "")


def normalize_content_key(text: str) -> str:
    text = clean_caption_text(text or "")
    text = re.sub(r"\s+", " ", text).strip().lower()
    text = re.sub(r"https?://\S+", "", text)
    return text


def make_post_content_key(page_handle: str, text: str) -> str:
    key = normalize_content_key(text)
    return f"{page_handle}::{key}" if key else ""


def get_fast_caption(post_el, page_name: str) -> str:
    try:
        return clean_caption_text(_extract_caption(post_el, page_name))
    except Exception:
        return ""


def get_fast_total_reactions_from_container(post_el) -> int:
    try:
        raw = post_el.evaluate("""(el) => {
            const pieces = [];
            for (const node of el.querySelectorAll('[aria-label], span[dir="auto"], a[role="link"], div[role="button"]')) {
                const aria = node.getAttribute('aria-label') || '';
                const text = (node.innerText || '').trim();
                if (aria) pieces.push(aria);
                if (text) pieces.push(text);
            }
            return pieces.join('\\n');
        }""")
        counts = parse_comment_share_from_text(raw)
        nums = counts.get("_debug", {}).get("collapsed_action_numbers", []) or []
        if nums:
            return int(nums[0].get("value", 0) or 0)

        compact = post_el.evaluate("""(el) => {
            for (const s of el.querySelectorAll('span[dir="auto"]')) {
                const t = (s.innerText || '').trim();
                if (/^[\\d.,]+[KkMmBb]?$/.test(t)) return t;
            }
            return '0';
        }""")
        return parse_count(compact)
    except Exception:
        return 0


def collect_post_containers_from_share_buttons(page):
    """Lấy post container từ share_button nhưng chọn ancestor tốt nhất, không chọn ancestor đầu tiên.

    Lý do sửa:
    - Ancestor đầu tiên có width/height đủ lớn đôi khi chỉ chứa action row/media,
      chưa chứa header/timestamp/permalink nên quick_url = None.
    - Hàm này chấm điểm nhiều ancestor rồi chọn container có story_message/header/link/action tốt nhất.
    """
    result = {"posts": [], "debug": {"share_buttons": 0, "post_candidates": 0, "failed_buttons": 0}}

    share_btns = page.query_selector_all('[data-ad-rendering-role="share_button"]')
    result["debug"]["share_buttons"] = len(share_btns)

    posts = []
    seen_els = set()

    for btn in share_btns:
        try:
            handle = btn.evaluate_handle("""(el, maxDepth) => {
                const LINK_RE = /\\/posts\\/|pfbid|story_fbid|permalink\\.php|photo\\/\\?fbid|\\/photo\\/|set=pcb/i;
                const TIME_RE = /^(\\d+\\s*[smhdw]|\\d+\\s*(phút|giờ|ngày|tuần|tháng|năm)|vừa xong|just now|hôm qua|yesterday)$/i;

                const hasStory = (node) =>
                    !!node.querySelector('[data-ad-rendering-role="story_message"], [data-ad-comet-preview="message"], [data-ad-preview="message"]');

                const linkCount = (node) =>
                    [...node.querySelectorAll('a[href]')].filter(a => LINK_RE.test(a.href || '')).length;

                const hasTime = (node) =>
                    [...node.querySelectorAll('a, span, abbr')].some(x => {
                        const txt = (x.innerText || x.getAttribute('aria-label') || x.getAttribute('title') || '').trim();
                        return TIME_RE.test(txt);
                    });

                const hasHeaderTime = (node) => {
                    const nr = node.getBoundingClientRect();
                    const br = el.getBoundingClientRect();
                    return [...node.querySelectorAll('a, span, abbr')].some(x => {
                        const txt = (x.innerText || x.getAttribute('aria-label') || x.getAttribute('title') || '').trim();
                        if (!TIME_RE.test(txt)) return false;
                        const r = x.getBoundingClientRect();
                        if (r.width <= 0 || r.height <= 0) return false;
                        // Timestamp chính nằm gần đầu ancestor và phía trên share button/action row.
                        return r.top >= nr.top - 5 && r.top <= nr.top + 320 && r.top < br.top - 20;
                    });
                };

                const actionTextScore = (node) => {
                    const t = (node.innerText || '');
                    let score = 0;
                    if (/Like|Thích|React|người|people/i.test(t)) score += 10;
                    if (/Comment|Bình luận|Leave a comment/i.test(t)) score += 10;
                    if (/Share|Chia sẻ|Send this/i.test(t)) score += 10;
                    return score;
                };

                const candidates = [];
                let node = el.parentElement;

                for (let depth = 0; depth < maxDepth && node; depth++, node = node.parentElement) {
                    const r = node.getBoundingClientRect();
                    if (r.width < 320 || r.height < 220) continue;

                    let score = 0;
                    if (r.width >= 400 && r.width <= 980) score += 20;
                    if (r.height >= 300 && r.height <= 2600) score += 20;
                    if (r.height > 3200) score -= 80;
                    if (r.bottom > 0 && r.top < innerHeight) score += 25;

                    const lc = linkCount(node);
                    const ht = hasTime(node);
                    const hht = hasHeaderTime(node);
                    if (lc > 0) score += 40 + Math.min(lc, 5) * 5;
                    if (hasStory(node)) score += 50;
                    if (hht) score += 180;
                    else if (ht) score += 35;
                    if (!hht) score -= 90;
                    if (!ht && lc === 0) score -= 120;
                    score += actionTextScore(node);

                    // Quá nhiều story_message thường là shared/repost hoặc ancestor quá lớn.
                    const storyCount = node.querySelectorAll('[data-ad-rendering-role="story_message"], [data-ad-comet-preview="message"], [data-ad-preview="message"]').length;
                    if (storyCount > 1) score -= 35;

                    candidates.push({node, score, depth, w: r.width, h: r.height, links: lc, storyCount});
                }

                candidates.sort((a, b) => b.score - a.score);
                return candidates[0]?.node || null;
            }""", POST_CONTAINER_MAX_ANCESTOR_LEVELS)

            post_el = handle.as_element()
            if post_el is None:
                result["debug"]["failed_buttons"] += 1
                continue

            el_id = post_el.evaluate("el => el.__crawl_id || (el.__crawl_id = Math.random())")
            if el_id in seen_els:
                continue

            seen_els.add(el_id)
            posts.append(post_el)

        except Exception:
            result["debug"]["failed_buttons"] += 1
            continue

    result["posts"] = posts
    result["debug"]["post_candidates"] = len(posts)
    return result


def get_post_container_diagnostics(post_el):
    """Trả về lý do khả nghi khi không resolve được URL."""
    try:
        return post_el.evaluate("""(el) => {
            const LINK_PATTERNS = {
                pfbid: /pfbid/i,
                posts: /\\/posts\\//i,
                story_fbid: /story_fbid/i,
                permalink: /permalink\\.php/i,
                photo: /photo\\/\\?fbid|\\/photo\\//i,
                pcb: /set=pcb/i,
                comment: /comment_id|reply_comment_id|comment_tracking/i
            };
            const TIME_RE = /^(\\d+\\s*[smhdw]|\\d+\\s*(phút|giờ|ngày|tuần|tháng|năm)|vừa xong|just now|hôm qua|yesterday)$/i;

            const r = el.getBoundingClientRect();
            const links = [...el.querySelectorAll('a[href]')].map(a => ({
                href: a.href || '',
                text: (a.innerText || a.getAttribute('aria-label') || '').trim().slice(0, 80)
            }));

            const link_counts = {};
            for (const [k, pat] of Object.entries(LINK_PATTERNS)) {
                link_counts[k] = links.filter(x => pat.test(x.href)).length;
            }

            const time_nodes = [...el.querySelectorAll('a, span')]
                .map(x => (x.innerText || x.getAttribute('aria-label') || '').trim())
                .filter(t => TIME_RE.test(t))
                .slice(0, 6);

            const story = el.querySelector('[data-ad-rendering-role="story_message"], [data-ad-comet-preview="message"], [data-ad-preview="message"]');
            const story_text = story ? (story.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 120) : '';

            return {
                rect: {x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)},
                story_text,
                story_count: el.querySelectorAll('[data-ad-rendering-role="story_message"], [data-ad-comet-preview="message"], [data-ad-preview="message"]').length,
                share_buttons: el.querySelectorAll('[data-ad-rendering-role="share_button"]').length,
                all_links: links.length,
                link_counts,
                time_nodes,
                sample_links: links.filter(x =>
                    /pfbid|\\/posts\\/|story_fbid|permalink\\.php|photo\\/\\?fbid|set=pcb/i.test(x.href)
                ).slice(0, 6)
            };
        }""")
    except Exception as e:
        return {"error": str(e)[:160]}




def get_media_fallback_url_from_post(post_el, page_handle: str = "") -> str:
    """Fallback khi không resolve được post permalink nhưng bài là reel/video/photo."""
    try:
        raw = post_el.evaluate("""(el) => {
            const links = [...el.querySelectorAll('a[href]')].map(a => a.href || '').filter(Boolean);
            const preferred = [
                '/reel/',
                '/videos/',
                '/watch/',
                '/share/v/',
                'photo/?fbid',
                '/photo/',
                'set=pcb'
            ];
            for (const p of preferred) {
                const found = links.find(h => h.includes(p));
                if (found) return found;
            }
            return null;
        }""")
        if not raw:
            return None
        url = canonicalize_facebook_post_url(raw, page_handle)
        ptype = infer_post_type_from_url(url)
        if ptype in {"reel", "video"} and ACCEPT_REEL_VIDEO_URL:
            return url
        if ptype == "photo" and ACCEPT_PHOTO_URL:
            return url
        return None
    except Exception:
        return None

def resolve_post_url_with_retries(page, post_el, page_handle: str, retries: int = URL_RESOLVE_RETRIES):
    """Resolve URL với nhiều lần warm; trả về (url, debug_info)."""
    debug = {"attempts": [], "warm_moves": []}
    last_url = None

    for attempt in range(1, retries + 1):
        t0 = time.time()

        if attempt > 1:
            moved = warm_post_for_permalink(page, post_el, max_points=7)
            debug["warm_moves"].append(moved)
            page.wait_for_timeout(250)

        url = get_best_post_url_from_element(page, post_el, page_handle)
        dt = time.time() - t0
        last_url = url

        diag = get_post_container_diagnostics(post_el) if (not url or DEBUG_URL_DIAGNOSTICS) else {}
        debug["attempts"].append({
            "attempt": attempt,
            "url": url,
            "dt": round(dt, 2),
            "diag": diag if not url else {
                "link_counts": diag.get("link_counts", {}),
                "time_nodes": diag.get("time_nodes", [])[:3]
            }
        })

        if url:
            return url, debug

    return last_url, debug


def summarize_url_debug(debug_info):
    try:
        parts = []
        for a in debug_info.get("attempts", []):
            diag = a.get("diag", {}) or {}
            lc = diag.get("link_counts", {})
            times = diag.get("time_nodes", [])
            parts.append(
                f"try={a.get('attempt')} url={bool(a.get('url'))} "
                f"dt={a.get('dt')}s links={lc} times={times}"
            )
        return " | ".join(parts)
    except Exception:
        return str(debug_info)[:300]




def sleep_with_heartbeat(seconds: int, label: str, crawl_start_time: float, collected: int, target: int):
    """Ngủ nhưng vẫn in heartbeat để biết crawler không bị treo."""
    seconds = int(max(0, seconds))
    if seconds <= 0:
        return
    step = 20
    remaining = seconds
    while remaining > 0:
        chunk = min(step, remaining)
        time.sleep(chunk)
        remaining -= chunk
        if remaining > 0:
            print(
                f"[{format_elapsed(time.time() - crawl_start_time)}] "
                f"...{label}, còn ~{remaining}s | collected={collected}/{target}",
                flush=True
            )



def summarize_header_timestamp_debug(page, post_el, page_handle: str = "") -> str:
    """Dòng log ngắn để hiểu vì sao timestamp resolver fail."""
    try:
        _, dbg = get_header_timestamp_permalink(page, post_el, page_handle, do_hover=False)
        cands = dbg.get("candidates", [])[:3]
        if not cands:
            return f"header_ts=none reason={dbg.get('reason')}"
        parts = []
        for c in cands:
            href = c.get("href") or ""
            if len(href) > 80:
                href = href[:77] + "..."
            parts.append(f"text='{c.get('txt')}' relTop={c.get('relTop')} href={bool(c.get('href'))} {href}")
        return "header_ts: " + " | ".join(parts)
    except Exception as e:
        return f"header_ts_error={str(e)[:80]}"



# ===================== LIVE TIMESTAMP V10 HELPERS =====================

LIVE_TARGET_HEADER_Y = 170
LIVE_ALIGN_WAIT_MS = 750
LIVE_BASE_SCROLL_MIN = 650
LIVE_BASE_SCROLL_MAX = 1150
LIVE_HOVER_DELAYS_MS = [420, 850, 1300]
LIVE_HOVER_OFFSETS = [(0, 0), (2, 0), (-2, 0), (0, -10), (0, -18), (0, 10), (0, 18), (4, -12), (-4, -12), (4, 12), (-4, 12), (0, 5), (0, 7)]
LIVE_DETAIL_PAGE_FALLBACK = True
LIVE_DETAIL_PAGE_TIMEOUT_MS = 7000


def live_stable_key(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return hashlib.md5(text[:500].encode("utf-8", errors="ignore")).hexdigest()


def live_is_date_tooltip(text: str) -> bool:
    return looks_like_valid_timestamp_raw(text)


def live_is_accepted_post_url(href: str) -> bool:
    if not href:
        return False
    if re.search(r"comment_id=|reply_comment_id=", href, flags=re.I):
        return False
    normalized = normalize_post_like_url_from_timestamp(href)
    return infer_post_type_from_url(normalized) in {"post", "reel", "video", "photo"}


def live_read_tooltip(page):
    try:
        vals = []
        for tip in page.query_selector_all('[role="tooltip"]'):
            txt = (tip.inner_text() or "").strip()
            if txt:
                vals.append(txt)
        return " || ".join(vals)
    except Exception:
        return ""


def live_get_visible_post_summaries(page):
    """Re-query live DOM mỗi vòng, không filter visible trực tiếp trên share_button."""
    try:
        return page.evaluate("""() => {
            const visible = (n) => {
                const r = n.getBoundingClientRect();
                return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight;
            };
            const rect = (n) => {
                const r = n.getBoundingClientRect();
                return {x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height), bottom: Math.round(r.bottom)};
            };
            const storyText = (node) => {
                const sels = [
                    '[data-ad-rendering-role="story_message"]',
                    '[data-ad-comet-preview="message"]',
                    '[data-ad-preview="message"]'
                ];
                for (const sel of sels) {
                    const n = node.querySelector(sel);
                    const t = (n && n.innerText || '').replace(/\\s+/g, ' ').trim();
                    if (t) return t;
                }
                return (node.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 650);
            };
            const linkScore = (node) =>
                [...node.querySelectorAll('a[href]')].filter(a => /\\/posts\\/|pfbid|\\/reel\\/|\\/videos\\/|story_fbid|photo\\/\\?fbid|set=pcb/i.test(a.href || '')).length;
            const hasHeaderAnchor = (node, shareEl) => {
                const nr = node.getBoundingClientRect();
                const sr = shareEl.getBoundingClientRect();
                return [...node.querySelectorAll('a[href]')].some(a => {
                    if (!visible(a)) return false;
                    const r = a.getBoundingClientRect();
                    const rel = r.top - nr.top;
                    const href = a.href || '';
                    if (r.top >= sr.top - 15) return false;
                    if (rel < 8 || rel > 140) return false;
                    if (r.width > 340 || r.height > 55) return false;
                    return /__tn__=.*%2CO|__tn__=%2CO|\\/posts\\/|pfbid|\\/reel\\/|\\/videos\\/|story_fbid|photo\\/\\?fbid|set=pcb/i.test(href) || r.width <= 210;
                });
            };
            const hasStory = (node) =>
                !!node.querySelector('[data-ad-rendering-role="story_message"], [data-ad-comet-preview="message"], [data-ad-preview="message"]');

            const shareBtnsRaw = [...document.querySelectorAll('[data-ad-rendering-role="share_button"]')];
            const shareBtnsVisible = shareBtnsRaw.filter(visible);
            const posts = [];
            const seen = new Set();

            for (const btn of shareBtnsRaw) {
                const candidates = [];
                let node = btn.parentElement;
                for (let d = 0; d < 34 && node; d++, node = node.parentElement) {
                    const r = node.getBoundingClientRect();
                    if (r.width < 320 || r.height < 220) continue;

                    let score = 0;
                    if (r.width >= 400 && r.width <= 1250) score += 20;
                    if (r.height >= 260 && r.height <= 3600) score += 20;
                    if (r.bottom > 0 && r.top < innerHeight) score += 35;
                    if (hasStory(node)) score += 35;
                    if (hasHeaderAnchor(node, btn)) score += 240;
                    score += Math.min(linkScore(node), 5) * 20;
                    if (r.height > 4300) score -= 220;
                    candidates.push({node, score, depth: d});
                }

                candidates.sort((a, b) => b.score - a.score);
                const best = candidates[0]?.node;
                if (!best) continue;

                const text = storyText(best);
                if (!text) continue;
                const key = text.slice(0, 240);
                if (seen.has(key)) continue;
                seen.add(key);

                const br = rect(best);
                posts.push({caption: text, key, rect: br, score: candidates[0].score, depth: candidates[0].depth});
            }

            posts.sort((a, b) => {
                if (Math.abs(a.rect.y - b.rect.y) > 80) return a.rect.y - b.rect.y;
                return b.score - a.score;
            });

            return {share_buttons_raw: shareBtnsRaw.length, share_buttons_visible: shareBtnsVisible.length, posts};
        }""")
    except Exception as e:
        return {"share_buttons_raw": 0, "share_buttons_visible": 0, "posts": [], "error": str(e)[:200]}


def live_get_post_handle_by_key(page, key):
    try:
        h = page.evaluate_handle("""(key) => {
            const visible = (n) => {
                const r = n.getBoundingClientRect();
                return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight;
            };
            const storyText = (node) => {
                const sels = [
                    '[data-ad-rendering-role="story_message"]',
                    '[data-ad-comet-preview="message"]',
                    '[data-ad-preview="message"]'
                ];
                for (const sel of sels) {
                    const n = node.querySelector(sel);
                    const t = (n && n.innerText || '').replace(/\\s+/g, ' ').trim();
                    if (t) return t;
                }
                return (node.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 650);
            };
            const scoreNode = (node, shareEl) => {
                const r = node.getBoundingClientRect();
                if (r.width < 320 || r.height < 220) return -9999;
                let score = 0;
                if (r.width >= 400 && r.width <= 1250) score += 20;
                if (r.height >= 260 && r.height <= 3600) score += 20;
                if (r.bottom > 0 && r.top < innerHeight) score += 35;
                if (node.querySelector('[data-ad-rendering-role="story_message"], [data-ad-comet-preview="message"], [data-ad-preview="message"]')) score += 35;
                const nr = node.getBoundingClientRect();
                const sr = shareEl.getBoundingClientRect();
                const hasHeader = [...node.querySelectorAll('a[href]')].some(a => {
                    if (!visible(a)) return false;
                    const ar = a.getBoundingClientRect();
                    const rel = ar.top - nr.top;
                    const href = a.href || '';
                    if (ar.top >= sr.top - 15) return false;
                    if (rel < 8 || rel > 140) return false;
                    if (ar.width > 340 || ar.height > 55) return false;
                    return /__tn__=.*%2CO|__tn__=%2CO|\\/posts\\/|pfbid|\\/reel\\/|\\/videos\\/|story_fbid|photo\\/\\?fbid|set=pcb/i.test(href) || ar.width <= 210;
                });
                if (hasHeader) score += 240;
                return score;
            };

            const shareBtns = [...document.querySelectorAll('[data-ad-rendering-role="share_button"]')];
            let best = null;
            let bestScore = -9999;

            for (const btn of shareBtns) {
                let node = btn.parentElement;
                for (let d = 0; d < 34 && node; d++, node = node.parentElement) {
                    const t = storyText(node);
                    if (!t || !t.startsWith(key.slice(0, Math.min(180, key.length)))) continue;
                    const s = scoreNode(node, btn);
                    if (s > bestScore) {
                        bestScore = s;
                        best = node;
                    }
                }
            }
            return best;
        }""", key)
        return h.as_element()
    except Exception:
        return None


def live_align_post_header(page, key, target_y=LIVE_TARGET_HEADER_Y):
    out = {"ok": False, "before": None, "after": None, "error": ""}
    post_el = live_get_post_handle_by_key(page, key)
    if not post_el:
        out["error"] = "not_found_before_align"
        return None, out
    try:
        before = post_el.evaluate("""(el) => {
            const r = el.getBoundingClientRect();
            return {x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height), bottom: Math.round(r.bottom), innerH: window.innerHeight};
        }""")
        out["before"] = before

        page.evaluate("""({el, targetY}) => {
            const r = el.getBoundingClientRect();
            window.scrollBy({top: r.top - targetY, left: 0, behavior: 'instant'});
        }""", {"el": post_el, "targetY": target_y})
        page.wait_for_timeout(LIVE_ALIGN_WAIT_MS)

        fresh_el = live_get_post_handle_by_key(page, key)
        if not fresh_el:
            out["error"] = "not_found_after_align"
            return None, out

        after = fresh_el.evaluate("""(el) => {
            const r = el.getBoundingClientRect();
            return {x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height), bottom: Math.round(r.bottom), innerH: window.innerHeight};
        }""")
        out["after"] = after
        out["ok"] = True
        return fresh_el, out
    except Exception as e:
        out["error"] = str(e)[:220]
        return None, out


def live_get_candidate_snapshot(post_el):
    return post_el.evaluate("""(el) => {
        const rect = (n) => {
            const r = n.getBoundingClientRect();
            return {x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height), bottom: Math.round(r.bottom)};
        };
        const visible = (n) => {
            const r = n.getBoundingClientRect();
            return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight;
        };

        const er = rect(el);
        const shareBtns = [...el.querySelectorAll('[data-ad-rendering-role="share_button"]')];
        const shareTops = shareBtns.map(b => b.getBoundingClientRect().top).filter(x => Number.isFinite(x));
        const shareTop = shareTops.length ? Math.min(...shareTops) : (er.y + er.h);

        const commentMarkers = [...el.querySelectorAll('a, span, div')]
            .map((n, i) => ({i, text: (n.innerText || n.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim(), rect: rect(n), visible: visible(n)}))
            .filter(x => /View more comments|Xem thêm bình luận|Write a comment|Viết bình luận|Reply|Trả lời/i.test(x.text))
            .slice(0, 20);
        const commentTop = commentMarkers.length ? Math.min(...commentMarkers.map(x => x.rect.y)) : null;

        const pageNameLinks = [...el.querySelectorAll('a[href]')]
            .filter(a => visible(a))
            .map((a, i) => {
                const r = rect(a);
                const text = (a.innerText || a.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim();
                return {i, text, href: a.href || '', rect: r, relTop: Math.round(r.y - er.y)};
            })
            .filter(x => x.relTop >= 0 && x.relTop <= 95 && x.rect.w >= 30 && x.rect.w <= 320 && /facebook\\.com\\/[^/?#]+/.test(x.href));

        const nameX = pageNameLinks.length ? pageNameLinks[0].rect.x : null;
        const nameBottom = pageNameLinks.length ? pageNameLinks[0].rect.bottom : (er.y + 25);

        const allAnchors = [...el.querySelectorAll('a[href]')].map((a, idx) => {
            const r = rect(a);
            const href = a.href || '';
            const text = (a.innerText || a.getAttribute('aria-label') || a.getAttribute('title') || '').replace(/\\s+/g, ' ').trim();
            const aria = (a.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim();
            const title = (a.getAttribute('title') || '').replace(/\\s+/g, ' ').trim();
            const relTop = r.y - er.y;
            const aboveShare = r.y < shareTop - 15;
            const belowComment = commentTop !== null && r.y >= commentTop - 4;
            const belowPageName = visible(a) && r.y >= nameBottom - 8 && r.y <= nameBottom + 58;
            const alignedWithName = nameX === null ? true : Math.abs(r.x - nameX) <= 75;
            const smallHeaderAnchor = (
                visible(a) &&
                relTop >= 6 && relTop <= 145 &&
                r.h >= 6 && r.h <= 55 &&
                r.w >= 3 && r.w <= 340 &&
                aboveShare
            );
            const tnHint = /__tn__=.*%2CO|__tn__=%2CO|#\\?/.test(href);
            const directPostHint = /\\/posts\\/|pfbid|story_fbid|permalink\\.php|\\/reel\\/|\\/videos\\/|\\/watch\\/|photo\\/\\?fbid|set=pcb/i.test(href);
            const commentHint = /comment_id=|reply_comment_id=/i.test(href) || belowComment;
            const imageOrMediaBig = r.w > 260 && r.h > 180 && /photo\/\?fbid|set=pcb/i.test(href);
            const hashtagHint = /^#/.test(text) || /\/hashtag\//i.test(href) || /[?&]hashtag=/i.test(href);
            const tsTextHint = /^(Today|Yesterday)(\s+at\s+\d{1,2}:\d{1,2})?$|^\d+\s*[hm]$|^\d+\s*(phút|giờ|ngày)$|^\d{1,2}\s+tháng\s+\d{1,2}|\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b.*\bat\s+\d{1,2}:\d{1,2}|\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b/i.test(text + ' ' + aria + ' ' + title);

            let score = 0;
            if (directPostHint) score += 170;
            if (smallHeaderAnchor) score += 140;
            if (belowPageName) score += 130;
            if (alignedWithName) score += 70;
            if (tnHint) score += 80;
            if (tsTextHint) score += 240;
            if (aboveShare) score += 110; else score -= 180;
            if (commentHint) score -= 340;
            if (hashtagHint) score -= 700;
            if (imageOrMediaBig) score -= 180;
            if (r.y < er.y || r.y > shareTop) score -= 200;
            if (r.w > 380 || r.h > 140) score -= 120;

            return {idx, text, aria, title, href, rect: r, relTop: Math.round(relTop), visible: visible(a), aboveShare, belowComment, belowPageName, alignedWithName, smallHeaderAnchor, tnHint, directPostHint, commentHint, hashtagHint, tsTextHint, imageOrMediaBig, score};
        });

        const candidates = allAnchors
            .filter(x => x.visible && x.score > 20 && !x.hashtagHint)
            .sort((a, b) => b.score - a.score)
            .slice(0, 14);

        return {post_rect: er, share_top: Math.round(shareTop), comment_top: commentTop ? Math.round(commentTop) : null, page_name_links: pageNameLinks, candidates, comment_markers: commentMarkers};
    }""")


def live_accept_candidate_text_if_date(cand):
    for field in ("text", "aria", "title"):
        raw = cand.get(field)
        if raw and looks_like_valid_timestamp_raw(raw) and live_is_accepted_post_url(cand.get("href")):
            ts_unix, ts_human = parse_fb_timestamp_tooltip(raw)
            return {"success": bool(ts_human), "raw": raw, "href": cand.get("href"), "normalized": normalize_post_like_url_from_timestamp(cand.get("href")), "timestamp_unix": ts_unix, "timestamp_human": ts_human, "source": "feed_text", "reason": "candidate_text_date", "timestamp_semantics": "displayed_post_time"}
    return None


def _is_hashtag_like_text(*vals):
    raw = " ".join(str(v or "") for v in vals)
    return bool(re.search(r"(^|\\s)#\\w|/hashtag/|[?&]hashtag=", raw, flags=re.I))


def live_hover_candidate(page, cand):
    attempts = []

    if HASHTAG_HOVER_SKIP and _is_hashtag_like_text(cand.get("text"), cand.get("aria"), cand.get("title"), cand.get("href")):
        attempts.append({
            "delay_ms": 0,
            "offset": [0, 0],
            "hover_href": cand.get("href") or "",
            "hover_normalized": None,
            "tooltip": "",
            "tooltip_is_date": False,
            "success": False,
            "reason": "skip_hashtag_candidate_before_hover",
        })
        return attempts

    r = cand.get("rect") or {}
    base_x = int(r.get("x", 0) + max(3, min(r.get("w", 10) / 2, max(r.get("w", 10) - 3, 3))))
    base_y = int(r.get("y", 0) + max(3, min(r.get("h", 10) / 2, max(r.get("h", 10) - 3, 3))))
    candidate_start = time.time()

    for delay in LIVE_HOVER_DELAYS_MS:
        for dx, dy in LIVE_HOVER_OFFSETS:
            if time.time() - candidate_start > HOVER_CANDIDATE_MAX_SECONDS:
                attempts.append({
                    "delay_ms": delay,
                    "offset": [dx, dy],
                    "hover_href": "",
                    "hover_normalized": None,
                    "tooltip": "",
                    "tooltip_is_date": False,
                    "success": False,
                    "reason": f"candidate_hover_budget_exceeded>{HOVER_CANDIDATE_MAX_SECONDS}s",
                })
                return attempts

            x, y = base_x + dx, base_y + dy
            item = {
                "delay_ms": delay,
                "offset": [dx, dy],
                "hover_href": "",
                "hover_normalized": None,
                "tooltip": "",
                "tooltip_is_date": False,
                "success": False,
                "reason": "",
                "element_tag": "",
                "element_text": "",
                "element_aria": "",
                "element_title": "",
            }
            try:
                if DISMISS_HOVERCARD_BEFORE_TIMESTAMP:
                    dismiss_hover_popups(page, reason="before_live_timestamp_hover", click_blank=True, verbose=False)
                else:
                    page.keyboard.press("Escape")
                    debug_mouse_move(page, 5, 5, 'reset')
                    page.wait_for_timeout(80)

                debug_mouse_move(page, x, y, 'feed_ts_hover')
                page.wait_for_timeout(delay)

                tooltip = live_read_tooltip(page)
                info = page.evaluate("""({x, y}) => {
                    const n = document.elementFromPoint(x, y);
                    if (!n) return {href:'', tag:'', text:'', aria:'', title:''};
                    const a = n.closest && n.closest('a[href]');
                    const clean = s => (s || '').replace(/\\s+/g, ' ').trim();
                    return {
                        href: a ? a.href : '',
                        tag: (n.tagName || '').toLowerCase(),
                        text: clean(n.innerText || n.textContent || '').slice(0, 160),
                        aria: clean(n.getAttribute && n.getAttribute('aria-label') || '').slice(0, 160),
                        title: clean(n.getAttribute && n.getAttribute('title') || '').slice(0, 160)
                    };
                }""", {"x": x, "y": y}) or {}
                href = info.get("href") or ""

                item["hover_href"] = href
                item["hover_normalized"] = normalize_post_like_url_from_timestamp(href)
                item["tooltip"] = tooltip
                item["tooltip_is_date"] = live_is_date_tooltip(tooltip)
                item["success"] = bool(live_is_accepted_post_url(href))
                item["element_tag"] = info.get("tag") or ""
                item["element_text"] = info.get("text") or ""
                item["element_aria"] = info.get("aria") or ""
                item["element_title"] = info.get("title") or ""

                if HASHTAG_HOVER_SKIP and _is_hashtag_like_text(href, tooltip, item["element_text"], item["element_aria"], item["element_title"]):
                    item["reason"] = "hover_hit_hashtag_skip_candidate"
                    attempts.append(item)
                    if PRINT_TIMESTAMP_HOVER_REASON:
                        print(
                            f"      [HOVER_SKIP_HASHTAG] offset={dx},{dy} "
                            f"elem={short_text(item.get('element_text'), 50)!r} href={short_text(href, 70)}",
                            flush=True
                        )
                    dismiss_hover_popups(page, reason="after_hover_hit_hashtag", click_blank=True, verbose=False)
                    return attempts

                if item["success"] and item["tooltip_is_date"]:
                    item["reason"] = "post_url_and_date_tooltip"
                    attempts.append(item)
                    return attempts
                elif item["success"]:
                    item["reason"] = "post_url_without_date_tooltip"
                elif re.search(r"comment_id=|reply_comment_id=", str(href), flags=re.I):
                    item["reason"] = "comment_url"
                elif tooltip:
                    item["reason"] = "non_date_tooltip"
                else:
                    item["reason"] = "no_tooltip_no_post_href"

                if not (item.get("success") and item.get("tooltip_is_date")):
                    dismiss_hover_popups(page, reason="after_bad_timestamp_hover:" + item.get("reason", ""), click_blank=True, verbose=False)
            except Exception as e:
                item["reason"] = "exception"
                item["error"] = str(e)[:220]
            attempts.append(item)

    return attempts



def live_probe_clock_right_edge(page, cand, timestamp_raw=None, normalized_url=None):
    """Probe nhanh icon đồng hồ nằm bên phải timestamp text.

    Kế thừa từ TTCP probe V8.4:
    - Dùng rect.right + offset, không dùng center + offset.
    - Timestamp chính vẫn là text đang hiển thị: Today at hh:mm / Yesterday at hh:mm.
    - Tooltip "Added Today at ..." chỉ lưu debug, không thay thế timestamp chính.
    """
    if not CLOCK_RIGHT_EDGE_PROBE:
        return None

    r = cand.get("rect") or {}
    base_x = int(r.get("right", r.get("x", 0) + r.get("w", 0)))
    base_y = int(r.get("y", 0) + max(3, min(r.get("h", 10) / 2, max(r.get("h", 10) - 3, 3))))

    attempts = []
    added_re = re.compile(r"\b(Added|Updated|Posted)\s+(Today|Yesterday)\s+at\s+\d{1,2}:\d{1,2}\b", re.I)

    for dx, dy in CLOCK_RIGHT_EDGE_OFFSETS:
        x, y = base_x + dx, base_y + dy
        item = {
            "offset_from_right": [dx, dy],
            "x": x,
            "y": y,
            "tooltip": "",
            "element_tag": "",
            "element_text": "",
            "element_aria": "",
            "element_title": "",
            "href": "",
            "matched_added_tooltip": False,
        }
        try:
            dismiss_hover_popups(page, reason="before_clock_right_edge_probe", click_blank=True, verbose=False)
            debug_mouse_move(page, x, y, "clock_right_probe")
            page.wait_for_timeout(CLOCK_RIGHT_EDGE_HOVER_MS)

            tooltip = live_read_tooltip(page) or ""
            info = page.evaluate("""({x, y}) => {
                const n = document.elementFromPoint(x, y);
                if (!n) return {tag:'', text:'', aria:'', title:'', href:''};
                const a = n.closest && n.closest('a[href]');
                const clean = s => (s || '').replace(/\\s+/g, ' ').trim();
                return {
                    tag: (n.tagName || '').toLowerCase(),
                    text: clean(n.innerText || n.textContent || '').slice(0, 140),
                    aria: clean(n.getAttribute && n.getAttribute('aria-label') || '').slice(0, 140),
                    title: clean(n.getAttribute && n.getAttribute('title') || '').slice(0, 140),
                    href: a ? a.href : ''
                };
            }""", {"x": x, "y": y}) or {}

            item["tooltip"] = tooltip
            item["element_tag"] = info.get("tag") or ""
            item["element_text"] = info.get("text") or ""
            item["element_aria"] = info.get("aria") or ""
            item["element_title"] = info.get("title") or ""
            item["href"] = info.get("href") or ""
            item["matched_added_tooltip"] = bool(added_re.search(str(tooltip)))
            attempts.append(item)

            if CLOCK_RIGHT_EDGE_VERBOSE:
                print(
                    f"      [CLOCK_RIGHT_EDGE_V9.3.2] right+{dx},{dy} tag={item['element_tag']} "
                    f"tooltip={str(tooltip)[:80]!r}",
                    flush=True
                )

            if item["matched_added_tooltip"]:
                ts_unix, ts_human = parse_fb_timestamp_tooltip(timestamp_raw)
                return {
                    "found": True,
                    "source": "clock_right_edge_probe",
                    "timestamp_raw": timestamp_raw,
                    "timestamp_unix": ts_unix,
                    "timestamp_human": ts_human,
                    "normalized": normalized_url,
                    "clock_tooltip": tooltip,
                    "clock_attempt": item,
                    "attempts": attempts,
                    "timestamp_semantics": "displayed_post_time; clock_added_tooltip_debug_only",
                }

            # Public icon nằm sau clock; gặp Public thì dừng sớm để không mất 30s/post.
            if str(tooltip).strip().lower() == "public":
                break

        except Exception as e:
            item["error"] = str(e)[:180]
            attempts.append(item)

    return {
        "found": False,
        "source": "clock_right_edge_probe",
        "timestamp_raw": timestamp_raw,
        "normalized": normalized_url,
        "attempts": attempts,
    }


def live_choose_best_attempt(attempts):
    for a in attempts:
        if a.get("success") and a.get("tooltip_is_date"):
            return a
    for a in attempts:
        if a.get("success"):
            return a
    for a in attempts:
        if a.get("tooltip_is_date"):
            return a
    return attempts[0] if attempts else None


def live_detail_page_timestamp_probe(context, post_url):
    out = {"opened": False, "final_url": "", "timestamp_tooltip": "", "timestamp_href": "", "success": False, "error": ""}
    if not LIVE_DETAIL_PAGE_FALLBACK or not post_url:
        return out

    p = None
    try:
        p = context.new_page()
        p.goto(post_url, wait_until="domcontentloaded", timeout=LIVE_DETAIL_PAGE_TIMEOUT_MS)
        p.wait_for_timeout(1400)
        out["opened"] = True
        out["final_url"] = p.url

        candidates = p.evaluate("""() => {
            const rect = (n) => {
                const r = n.getBoundingClientRect();
                return {x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height), bottom: Math.round(r.bottom)};
            };
            const visible = (n) => {
                const r = n.getBoundingClientRect();
                return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight;
            };
            return [...document.querySelectorAll('a[href]')]
                .map((a, idx) => {
                    const r = rect(a);
                    const href = a.href || '';
                    const text = (a.innerText || a.getAttribute('aria-label') || a.getAttribute('title') || '').replace(/\\s+/g, ' ').trim();
                    let score = 0;
                    if (visible(a)) score += 80;
                    if (r.y >= 0 && r.y <= 460) score += 120;
                    if (r.h >= 6 && r.h <= 55 && r.w >= 3 && r.w <= 340) score += 100;
                    if (/\\/posts\\/|pfbid|story_fbid|\\/reel\\/|\\/videos\\/|\\/watch\\//i.test(href)) score += 180;
                    if (/comment_id=|reply_comment_id=/i.test(href)) score -= 280;
                    return {idx, text, href, rect: r, score};
                })
                .filter(x => x.score > 100)
                .sort((a,b) => b.score - a.score)
                .slice(0, 10);
        }""")

        for cand in candidates:
            raw = cand.get("text")
            if raw and looks_like_valid_timestamp_raw(raw) and live_is_accepted_post_url(cand.get("href")):
                out["timestamp_tooltip"] = raw
                out["timestamp_href"] = cand.get("href")
                out["success"] = True
                return out

            r = cand.get("rect") or {}
            base_x = int(r.get("x", 0) + max(3, min(r.get("w", 10) / 2, max(r.get("w", 10) - 3, 3))))
            base_y = int(r.get("y", 0) + max(3, min(r.get("h", 10) / 2, max(r.get("h", 10) - 3, 3))))
            for dx, dy in LIVE_HOVER_OFFSETS[:5]:
                x, y = base_x + dx, base_y + dy
                dismiss_hover_popups(p, reason="detail_page_before_timestamp_hover", click_blank=True, verbose=False)
                debug_mouse_move(p, x, y, 'detail_ts_hover')
                p.wait_for_timeout(900)
                tooltip = live_read_tooltip(p)
                href = p.evaluate("""({x, y}) => {
                    const n = document.elementFromPoint(x, y);
                    const a = n && n.closest && n.closest('a[href]');
                    return a ? a.href : '';
                }""", {"x": x, "y": y})

                if live_is_date_tooltip(tooltip) and not re.search(r"comment_id=|reply_comment_id=", str(href), flags=re.I):
                    out["timestamp_tooltip"] = tooltip
                    out["timestamp_href"] = href
                    out["success"] = True
                    return out
    except Exception as e:
        out["error"] = str(e)[:260]
    finally:
        try:
            if p:
                p.close()
        except Exception:
            pass

    return out


def live_resolve_timestamp_and_url(context, page, post_el, page_handle):
    result = {"status": "FAIL", "url": None, "debug": None, "reason": ""}
    resolve_start = time.time()
    try:
        snap = live_get_candidate_snapshot(post_el)
        candidates = snap.get("candidates", [])
        url_candidate = None
        url_candidate_raw = None

        for cand in candidates[:8]:
            if time.time() - resolve_start > URL_RESOLVE_MAX_SECONDS:
                result['reason'] = f"url_resolve_timeout>{URL_RESOLVE_MAX_SECONDS}s"
                return result
            text_accept = live_accept_candidate_text_if_date(cand)
            if text_accept and text_accept.get("success"):
                # Timestamp hiển thị parse được thì nhận luôn; probe clock chỉ để debug.
                try:
                    r = cand.get("rect") or {}
                    x = int(r.get("x", 0) + max(3, min(r.get("w", 10) / 2, max(r.get("w", 10) - 3, 3))))
                    y = int(r.get("y", 0) + max(3, min(r.get("h", 10) / 2, max(r.get("h", 10) - 3, 3))))
                    debug_mouse_move(page, x, y, "feed_text_ts")
                    page.wait_for_timeout(120)
                except Exception:
                    pass

                clock_probe = live_probe_clock_right_edge(
                    page,
                    cand,
                    timestamp_raw=text_accept.get("raw"),
                    normalized_url=text_accept.get("normalized"),
                )

                dbg = {
                    "found": True,
                    "raw_href": text_accept.get("href"),
                    "normalized": text_accept.get("normalized"),
                    "time_text": text_accept.get("raw"),
                    "tooltip": text_accept.get("raw"),
                    "timestamp_unix": text_accept.get("timestamp_unix"),
                    "timestamp_human": text_accept.get("timestamp_human"),
                    "reason": text_accept.get("reason"),
                    "source": text_accept.get("source"),
                    "timestamp_semantics": text_accept.get("timestamp_semantics"),
                    "clock_right_probe": clock_probe,
                    "candidates": candidates[:5],
                }
                post_el.evaluate("(el, dbg) => { el.__resolved_header_ts_debug = dbg; }", dbg)
                result.update({"status": "OK_TIMESTAMP", "url": dbg["normalized"], "debug": dbg})
                return result

            attempts = live_hover_candidate(page, cand)
            best = live_choose_best_attempt(attempts)
            if best and best.get("success"):
                normalized = best.get("hover_normalized")
                if normalized and not url_candidate:
                    url_candidate = normalized
                    url_candidate_raw = best.get("hover_href")

                displayed_raw = cand.get("text") or cand.get("aria") or cand.get("title")
                if displayed_raw and looks_like_valid_timestamp_raw(displayed_raw) and not best.get("tooltip_is_date"):
                    ts_unix, ts_human = parse_fb_timestamp_tooltip(displayed_raw)
                    if ts_human:
                        clock_probe = live_probe_clock_right_edge(page, cand, timestamp_raw=displayed_raw, normalized_url=normalized)
                        dbg = {
                            "found": True,
                            "raw_href": best.get("hover_href"),
                            "normalized": normalized,
                            "time_text": displayed_raw,
                            "tooltip": displayed_raw,
                            "timestamp_unix": ts_unix,
                            "timestamp_human": ts_human,
                            "reason": "displayed_timestamp_text_no_tooltip_clock_probe",
                            "source": "feed_text_after_hover",
                            "timestamp_semantics": "displayed_post_time",
                            "clock_right_probe": clock_probe,
                            "candidates": candidates[:5],
                        }
                        post_el.evaluate("(el, dbg) => { el.__resolved_header_ts_debug = dbg; }", dbg)
                        result.update({"status": "OK_TIMESTAMP", "url": normalized, "debug": dbg})
                        return result

                if best.get("tooltip_is_date"):
                    ts_unix, ts_human = parse_fb_timestamp_tooltip(best.get("tooltip"))
                    dbg = {
                        "found": True,
                        "raw_href": best.get("hover_href"),
                        "normalized": normalized,
                        "time_text": cand.get("text") or cand.get("aria") or cand.get("title"),
                        "tooltip": best.get("tooltip"),
                        "timestamp_unix": ts_unix,
                        "timestamp_human": ts_human,
                        "reason": best.get("reason"),
                        "source": "feed_hover",
                        "timestamp_semantics": "tooltip_date",
                        "candidates": candidates[:5],
                    }
                    post_el.evaluate("(el, dbg) => { el.__resolved_header_ts_debug = dbg; }", dbg)
                    result.update({"status": "OK_TIMESTAMP", "url": normalized, "debug": dbg})
                    return result

        if url_candidate:
            if time.time() - resolve_start > URL_RESOLVE_MAX_SECONDS:
                result.update({"status": "URL_ONLY", "url": url_candidate, "reason": f"url_resolve_budget_exceeded>{URL_RESOLVE_MAX_SECONDS}s"})
                return result
            dp = live_detail_page_timestamp_probe(context, url_candidate)
            if dp.get("success"):
                raw = dp.get("timestamp_tooltip")
                ts_unix, ts_human = parse_fb_timestamp_tooltip(raw)
                dbg = {
                    "found": True,
                    "raw_href": dp.get("timestamp_href") or url_candidate_raw,
                    "normalized": normalize_post_like_url_from_timestamp(dp.get("timestamp_href") or dp.get("final_url") or url_candidate),
                    "time_text": raw,
                    "tooltip": raw,
                    "timestamp_unix": ts_unix,
                    "timestamp_human": ts_human,
                    "reason": "detail_page_timestamp",
                    "source": "detail_page_hover",
                    "candidates": candidates[:5],
                }
                post_el.evaluate("(el, dbg) => { el.__resolved_header_ts_debug = dbg; }", dbg)
                result.update({"status": "OK_TIMESTAMP", "url": url_candidate, "debug": dbg})
                return result

            result.update({"status": "URL_ONLY", "url": url_candidate, "reason": "post_url_found_but_no_date_tooltip"})
            return result

        result["reason"] = "no_post_url_candidate"
        return result
    except Exception as e:
        result["reason"] = f"exception:{str(e)[:160]}"
        return result


def live_scroll_down(page, multiplier=1.0):
    page.evaluate("""({minY, maxY, multiplier}) => {
        const y = (minY + Math.random() * (maxY - minY)) * multiplier;
        window.scrollBy({top: y, left: 0, behavior: 'instant'});
    }""", {"minY": LIVE_BASE_SCROLL_MIN, "maxY": LIVE_BASE_SCROLL_MAX, "multiplier": multiplier})
    time.sleep(1.15)

# =================== END LIVE TIMESTAMP V10 HELPERS ===================

def short_timestamp_for_log(post_data: dict) -> str:
    raw = str((post_data or {}).get("post_timestamp_raw") or "")
    human = str((post_data or {}).get("post_timestamp_human") or "")
    status = str((post_data or {}).get("timestamp_status") or "")
    if human and human != "None":
        return human[5:16]  # MM-DD HH:MM
    if raw and status == "ok":
        return raw.replace("Thursday ", "").replace("Friday ", "")[:16]
    return "-"


# ===================== CHUNK/STRESS HELPERS =====================

def load_json_file_safe(path: str):
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[WARN] Không đọc được JSON {path}: {e}")
        return []


def seed_output_json_if_needed(json_file: str):
    """Nếu output chưa có, copy seed từ file cũ để resume mà không đè dữ liệu gốc."""
    if not COPY_SEED_ON_EMPTY:
        return
    if os.path.exists(json_file):
        return
    if not SEED_JSON_PATH or not os.path.exists(SEED_JSON_PATH):
        print(f"[SEED] Không thấy seed file: {SEED_JSON_PATH}. Sẽ bắt đầu file mới.")
        return

    seed_data = load_json_file_safe(SEED_JSON_PATH)
    if not seed_data:
        print(f"[SEED] Seed file rỗng hoặc lỗi: {SEED_JSON_PATH}")
        return

    os.makedirs(os.path.dirname(json_file), exist_ok=True)
    save_json_atomic(json_file, seed_data)
    print(f"[SEED] Đã copy {len(seed_data)} records từ seed sang output mới:")
    print(f"       seed  = {SEED_JSON_PATH}")
    print(f"       output= {json_file}")


def get_browser_health(page):
    """Log nhanh sức khỏe DOM/renderer. Chỉ để chẩn đoán, không đảm bảo mọi trình duyệt đều có JS heap."""
    try:
        return page.evaluate("""() => {
            const perfMem = performance && performance.memory ? performance.memory : null;
            return {
                dom_nodes: document.getElementsByTagName('*').length,
                dialogs: document.querySelectorAll('[role="dialog"]').length,
                tooltips: document.querySelectorAll('[role="tooltip"]').length,
                videos: document.querySelectorAll('video').length,
                iframes: document.querySelectorAll('iframe').length,
                scroll_y: Math.round(window.scrollY || 0),
                inner_h: window.innerHeight,
                js_heap_used_mb: perfMem ? Math.round(perfMem.usedJSHeapSize / 1024 / 1024) : null,
                js_heap_total_mb: perfMem ? Math.round(perfMem.totalJSHeapSize / 1024 / 1024) : null
            };
        }""")
    except Exception as e:
        return {"error": str(e)[:160]}


def log_health(page, prefix="[HEALTH]"):
    h = get_browser_health(page)
    print(
        f"{prefix} dom={h.get('dom_nodes')} dialogs={h.get('dialogs')} "
        f"tooltips={h.get('tooltips')} videos={h.get('videos')} "
        f"scroll_y={h.get('scroll_y')} heap={h.get('js_heap_used_mb')}/{h.get('js_heap_total_mb')}MB",
        flush=True
    )


def close_all_dialogs(page, reason="", max_attempts=4):
    """Cố đóng modal/overlay Facebook. Trả True nếu không còn dialog hoặc chỉ còn dialog không chặn."""
    ok = False
    last_count = None
    for attempt in range(1, max_attempts + 1):
        try:
            last_count = page.evaluate("""() => document.querySelectorAll('[role="dialog"]').length""")
        except Exception:
            last_count = None

        if not last_count:
            ok = True
            break

        print(f"[DIALOG_CLOSE] reason={reason} attempt={attempt} dialogs_before={last_count}", flush=True)

        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(350)
        except Exception:
            pass

        # Click các nút close trong dialog nếu có.
        try:
            page.evaluate("""() => {
                const candidates = [...document.querySelectorAll('[role="dialog"] [aria-label], [role="dialog"] [role="button"]')];
                for (const el of candidates) {
                    const label = (el.getAttribute('aria-label') || el.innerText || '').toLowerCase();
                    if (
                        label.includes('close') ||
                        label.includes('đóng') ||
                        label.includes('thoát') ||
                        label === 'x'
                    ) {
                        try { el.click(); } catch(e) {}
                    }
                }
            }""")
            page.wait_for_timeout(500)
        except Exception:
            pass

        # Click vùng trống bên phải để làm mất focus/ẩn hovercard.
        try:
            dismiss_hover_popups(page, reason=f"close_all_dialogs:{reason}", click_blank=True, verbose=False)
        except Exception:
            pass

    try:
        remain = page.evaluate("""() => document.querySelectorAll('[role="dialog"]').length""")
    except Exception:
        remain = None

    if remain:
        print(f"[DIALOG_CLOSE_FAIL] reason={reason} dialogs_after={remain}", flush=True)
        return False
    return True


def recover_feed(page, target_url, reason, attempt):
    """Recovery khi feed đứng hoặc modal kẹt."""
    print(f"[RECOVERY] attempt={attempt} reason={reason}", flush=True)
    log_health(page, "[HEALTH_BEFORE_RECOVERY]")

    close_all_dialogs(page, reason=f"recovery:{reason}", max_attempts=5)

    try:
        if attempt == 1:
            # Scroll mạnh hơn, không reload ngay.
            page.mouse.wheel(0, 2600)
            page.wait_for_timeout(1800)
        elif attempt == 2 and AVOID_RELOAD_RECOVERY:
            # V6.2: không reload trong crawler vì reload làm rơi về đầu page và mất vị trí deep-scroll.
            print("[RECOVERY_INFO] AVOID_RELOAD_RECOVERY=True -> chỉ scroll mạnh, không reload.", flush=True)
            page.mouse.wheel(0, 9000)
            page.wait_for_timeout(2600)
        elif attempt == 2:
            page.reload(wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
        else:
            if AVOID_RELOAD_RECOVERY:
                print("[RECOVERY_INFO] Bỏ qua goto để tránh mất vị trí. Kết thúc session nếu vẫn không tiến triển.", flush=True)
                page.mouse.wheel(0, 12000)
                page.wait_for_timeout(3000)
            else:
                page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(5500)
    except Exception as e:
        print(f"[RECOVERY_WARN] {e}", flush=True)

    log_health(page, "[HEALTH_AFTER_RECOVERY]")


def should_stop_session(initial_saved_count, collected_this_session):
    total_now = initial_saved_count + collected_this_session
    if total_now >= TARGET_POSTS:
        return True, f"Đã đạt TARGET_POSTS tổng: {total_now}/{TARGET_POSTS}"
    if collected_this_session >= SESSION_POST_LIMIT:
        return True, f"Đã đạt SESSION_POST_LIMIT: thêm {collected_this_session} bài trong session này"
    return False, ""

# =================== END CHUNK/STRESS HELPERS ===================


# ===================== CHECKPOINT/WARM-JUMP HELPERS V3 =====================

def compute_dataset_frontier(saved_data: list):
    """Tính mốc mới nhất/cũ nhất trong JSON hiện có."""
    ts_values = []
    for item in saved_data or []:
        try:
            ts = int(item.get("post_timestamp_unix") or 0)
            if ts > 0:
                ts_values.append(ts)
        except Exception:
            pass

    def fmt(ts):
        try:
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return None

    if not ts_values:
        return {
            "total_records": len(saved_data or []),
            "oldest_timestamp_unix": None,
            "oldest_timestamp_human": None,
            "newest_timestamp_unix": None,
            "newest_timestamp_human": None,
        }

    oldest = min(ts_values)
    newest = max(ts_values)
    return {
        "total_records": len(saved_data or []),
        "oldest_timestamp_unix": oldest,
        "oldest_timestamp_human": fmt(oldest),
        "newest_timestamp_unix": newest,
        "newest_timestamp_human": fmt(newest),
    }


def load_checkpoint_file(checkpoint_file: str):
    if not checkpoint_file or not os.path.exists(checkpoint_file):
        return None
    try:
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            ck = json.load(f)
        return ck if isinstance(ck, dict) else None
    except Exception as e:
        print(f"[CHECKPOINT_WARN] Không đọc được checkpoint: {e}", flush=True)
        return None


def save_checkpoint_file(checkpoint_file: str, saved_data: list, page=None, reason: str = ""):
    """Lưu scroll_y + mốc thời gian cũ nhất để lần sau warm jump."""
    try:
        frontier = compute_dataset_frontier(saved_data)
        health = get_browser_health(page) if page else {}
        ck = {
            "reason": reason,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_records": len(saved_data or []),
            "frontier": frontier,
            "scroll_y": health.get("scroll_y"),
            "dom_nodes": health.get("dom_nodes"),
            "videos": health.get("videos"),
            "dialogs": health.get("dialogs"),
            "js_heap_used_mb": health.get("js_heap_used_mb"),
            "js_heap_total_mb": health.get("js_heap_total_mb"),
        }
        os.makedirs(os.path.dirname(checkpoint_file), exist_ok=True)
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(ck, f, ensure_ascii=False, indent=2)
        print(
            f"[CHECKPOINT] reason={reason} total={ck['total_records']} "
            f"oldest={frontier.get('oldest_timestamp_human')} scroll_y={ck.get('scroll_y')}",
            flush=True
        )
    except Exception as e:
        print(f"[CHECKPOINT_WARN] Không lưu được checkpoint: {e}", flush=True)


def estimate_bootstrap_scroll_y(saved_count: int):
    if not saved_count:
        return 0
    return min(int(saved_count * BOOTSTRAP_SCROLL_PER_RECORD), BOOTSTRAP_MAX_SCROLL_Y)


def warm_jump_to_resume_area(page, checkpoint_file: str, saved_data: list):
    """Nhảy gần vùng đã dừng để giảm thời gian scroll qua duplicate.

    Lưu ý: Facebook feed là feed động, scroll_y không phải tọa độ tuyệt đối ổn định.
    Vì vậy hàm này chỉ jump gần vùng cũ rồi để crawler tiếp tục scan/validate bằng URL/timestamp.
    """
    if not ENABLE_WARM_JUMP_FROM_CHECKPOINT:
        print("[WARM_JUMP] disabled", flush=True)
        return

    ck = load_checkpoint_file(checkpoint_file)
    target_y = None
    source = None

    if ck and ck.get("scroll_y"):
        try:
            target_y = int(float(ck.get("scroll_y")) * WARM_JUMP_SCROLL_FACTOR)
            source = "checkpoint_scroll_y"
        except Exception:
            target_y = None

    if target_y is None:
        # Bootstrap cho lần đầu dùng V3, khi chưa có checkpoint từ phiên trước.
        target_y = estimate_bootstrap_scroll_y(len(saved_data or []))
        source = "bootstrap_estimate"

    if not target_y or target_y < 5000:
        print(f"[WARM_JUMP] Bỏ qua vì target_y quá nhỏ: {target_y}", flush=True)
        return

    print(f"[WARM_JUMP] source={source} target_y≈{target_y} | sẽ scroll từng bước để Facebook kịp render.", flush=True)
    log_health(page, "[HEALTH_BEFORE_WARM_JUMP]")

    try:
        steps = 12
        for i in range(1, steps + 1):
            y = int(target_y * i / steps)
            page.evaluate("(y) => window.scrollTo({top: y, left: 0, behavior: 'instant'})", y)
            page.wait_for_timeout(900)
        # Một vài wheel nhỏ để kích lazy-load sau khi nhảy.
        for _ in range(4):
            page.mouse.wheel(0, 1400)
            page.wait_for_timeout(700)
    except Exception as e:
        print(f"[WARM_JUMP_WARN] {e}", flush=True)

    try:
        final_y = int(page.evaluate("() => Math.round(window.scrollY || 0)"))
        ratio = final_y / max(1, target_y)
        if ratio < WARM_JUMP_MIN_ACCEPT_RATIO:
            print(
                f"[WARM_JUMP_UNDERREACHED] final_y={final_y} target_y={target_y} ratio={ratio:.2f}; "
                f"có thể do popup/FB lazy-load/chưa load sâu. Session vẫn tiếp tục nhưng nếu quá chậm nên restart.",
                flush=True
            )
    except Exception:
        pass
    log_health(page, "[HEALTH_AFTER_WARM_JUMP]")

# =================== END CHECKPOINT/WARM-JUMP HELPERS V3 ===================


# ===================== V4 OVERRIDES =====================

def warm_jump_to_resume_area(page, checkpoint_file: str, saved_data: list):
    """V4: warm-jump bằng mouse wheel thay vì scrollTo cứng.

    Lý do: Facebook chỉ tăng chiều cao document khi scroll thật/lazy-load.
    scrollTo(280k) có thể chỉ tới ~30k nếu DOM chưa load đủ. Dùng wheel lặp
    sẽ kích load feed tự nhiên hơn, rồi crawler vẫn kiểm tra trùng bằng URL.
    """
    if not ENABLE_WARM_JUMP_FROM_CHECKPOINT:
        print("[WARM_JUMP] disabled", flush=True)
        return

    ck = load_checkpoint_file(checkpoint_file)
    ck_y = 0
    if ck and ck.get("scroll_y"):
        try:
            ck_y = int(float(ck.get("scroll_y")) * WARM_JUMP_SCROLL_FACTOR)
        except Exception:
            ck_y = 0

    bootstrap_y = estimate_bootstrap_scroll_y(len(saved_data or []))
    target_y = max(ck_y, bootstrap_y)

    if not target_y or target_y < 5000:
        print(f"[WARM_JUMP] Bỏ qua vì target_y quá nhỏ: {target_y}", flush=True)
        return

    print(
        f"[WARM_JUMP] target_y≈{target_y} "
        f"(checkpoint≈{ck_y}, bootstrap≈{bootstrap_y}) | dùng wheel để kích lazy-load.",
        flush=True
    )
    log_health(page, "[HEALTH_BEFORE_WARM_JUMP]")

    start = time.time()
    stagnant = 0
    last_y = -1
    max_seconds = WARM_JUMP_MAX_SECONDS
    step = 0

    while time.time() - start < max_seconds:
        try:
            cur_y = int(page.evaluate("() => Math.round(window.scrollY || 0)"))
        except Exception:
            cur_y = 0

        if step % 10 == 0:
            dismiss_hover_popups(page, reason="warm_jump_periodic", click_blank=True, verbose=False)
            h = get_browser_health(page)
            print(
                f"[WARM_JUMP_PROGRESS] step={step} scroll_y={cur_y}/{target_y} "
                f"dom={h.get('dom_nodes')} live_videos={h.get('videos')} heap={h.get('js_heap_used_mb')}/{h.get('js_heap_total_mb')}MB",
                flush=True
            )

        if cur_y >= int(target_y * 0.82) and step >= 12:
            break

        if abs(cur_y - last_y) < 250:
            stagnant += 1
        else:
            stagnant = 0
        last_y = cur_y

        try:
            if stagnant >= 8:
                page.keyboard.press("End")
                page.wait_for_timeout(1000)
                stagnant = 0
            else:
                page.mouse.wheel(0, 5200)
                page.wait_for_timeout(650)
        except Exception:
            try:
                page.evaluate("() => window.scrollBy(0, 5200)")
                page.wait_for_timeout(650)
            except Exception:
                pass

        step += 1

    # Sau khi jump, wheel nhẹ thêm để các post quanh vùng đó render.
    try:
        for _ in range(4):
            page.mouse.wheel(0, 1600)
            page.wait_for_timeout(550)
    except Exception:
        pass

    log_health(page, "[HEALTH_AFTER_WARM_JUMP]")


def no_new_candidate_log(round_no, live, reasons, duplicate_skip_streak, collected, session_target, total_now, page):
    if not PRINT_NO_CANDIDATE_LOG:
        return
    if round_no % NO_CANDIDATE_LOG_EVERY != 0 and duplicate_skip_streak % 10 != 0:
        return
    h = get_browser_health(page)
    print(
        f"[NO_NEW_CANDIDATE] live_posts={len(live.get('posts') or [])} "
        f"share_raw={live.get('share_buttons_raw')} "
        f"đã_xét={reasons.get('accepted_key', 0)} "
        f"trùng_caption={reasons.get('content_duplicate', 0)} "
        f"ngoài_view={reasons.get('above_or_invalid', 0)} "
        f"dup_streak={duplicate_skip_streak} "
        f"new={collected}/{session_target} total={total_now}/{TARGET_POSTS} "
        f"scroll_y={h.get('scroll_y')} dom={h.get('dom_nodes')} "
        f"=> scroll tiếp, chưa xem là feed đứng.",
        flush=True
    )

# =================== END V4 OVERRIDES ===================


def apply_page_config(cfg: dict):
    """Cập nhật global config theo từng page."""
    global TARGET_POSTS, SAVE_DIR_NAME, CHECKPOINT_FILE_NAME, SEED_JSON_PATH, COPY_SEED_ON_EMPTY
    global FORCE_PAGE_NAME, FORCE_PAGE_HANDLE, FORCE_OUTPUT_JSON_NAME, BOOTSTRAP_MAX_SCROLL_Y

    TARGET_POSTS = int(cfg.get("target_posts", TARGET_POSTS))
    SAVE_DIR_NAME = cfg.get("save_dir_name", SAVE_DIR_NAME)
    CHECKPOINT_FILE_NAME = cfg.get("checkpoint_file_name", CHECKPOINT_FILE_NAME)
    SEED_JSON_PATH = cfg.get("seed_json_path")
    COPY_SEED_ON_EMPTY = bool(SEED_JSON_PATH)
    FORCE_PAGE_NAME = cfg.get("page_name") or FORCE_PAGE_NAME
    FORCE_PAGE_HANDLE = cfg.get("page_handle") or FORCE_PAGE_HANDLE
    FORCE_OUTPUT_JSON_NAME = cfg.get("output_json_name") or FORCE_OUTPUT_JSON_NAME

    # Khi đã có nhiều records, scroll_y cần sâu hơn. Cap 1.2M để tránh warm-jump quá lâu.
    BOOTSTRAP_MAX_SCROLL_Y = int(cfg.get("bootstrap_max_scroll_y", 1200000))


def active_page_configs():
    owner_aliases = {
        "p": "phuc",
        "phúc": "phuc",
        "phuc": "phuc",
        "hân": "han",
        "han": "han",
        "nhung": "nhung",
        "nhung": "nhung",
        "yến": "yen",
        "yen": "yen",
        "all": "all",
        "team": "all",
        "": "all",
    }
    selected_owner = owner_aliases.get(CRAWL_OWNER, CRAWL_OWNER)
    configs = [cfg for cfg in PAGE_CONFIGS if cfg.get("enabled", True) and cfg.get("url")]

    if selected_owner not in ("all", "team", ""):
        configs = [cfg for cfg in configs if str(cfg.get("owner_key", "")).lower() == selected_owner]

    if CRAWL_PAGE_KEYS:
        configs = [cfg for cfg in configs if str(cfg.get("key", "")).lower() in CRAWL_PAGE_KEYS]

    return configs

def main():
    configs = active_page_configs()
    print(f"[MULTIPAGE V9.3.2.2] pages={len(configs)} | session_limit/page={SESSION_POST_LIMIT}")
    for cfg in configs:
        print(
            f"[MULTIPAGE V9.3.2.2] config key={cfg.get('key')} "
            f"target={cfg.get('target_posts', TARGET_POSTS)} "
            f"output=data/{cfg.get('save_dir_name')}/{cfg.get('output_json_name')}"
        )

    with sync_playwright() as pw:
        print("Khởi động Playwright kết nối CDP...")
        try:
            browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
        except Exception as e:
            print(f"[LỖI] Không thể kết nối Chrome CDP: {e}")
            print("      Khởi động Chrome với flag: --remote-debugging-port=9222")
            return

        context = browser.contexts[0]
        page = next((p for p in context.pages if "facebook.com" in p.url), None)
        if not page:
            page = context.new_page()

        for cfg in configs:
            apply_page_config(cfg)
            target_url = cfg["url"]
            save_dir = os.path.join('data', SAVE_DIR_NAME)
            os.makedirs(save_dir, exist_ok=True)

            print("\n" + "=" * 45)
            print(f"[PAGE_CONFIG] key={cfg.get('key')} target={TARGET_POSTS} output={os.path.join(save_dir, FORCE_OUTPUT_JSON_NAME)}")
            print(f"ĐANG TRUY CẬP TRANG: {target_url}")
            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=60_000)
            except PlaywrightTimeoutError as e:
                print(f"[GOTO_TIMEOUT] lần 1: {e}")
                dismiss_hover_popups(page, reason="goto_timeout_before_retry", click_blank=True, verbose=True)
                page.goto(target_url, wait_until="domcontentloaded", timeout=90_000)
            time.sleep(3)
            close_all_dialogs(page, reason="after_page_load", max_attempts=3)
            dismiss_hover_popups(page, reason="after_page_load", click_blank=True, verbose=True)
            ensure_visual_cursor(page)
            print(f"-> URL thực tế sau khi load: {page.url}")

            if "search" in page.url or page.url == "https://www.facebook.com/":
                print("[!] CẢNH BÁO: Trình duyệt bị chuyển hướng. Kiểm tra URL hoặc trạng thái đăng nhập!")

            # --- Page name ---
            page_name = page.evaluate("""() => {
                const h1s = [...document.querySelectorAll('h1')].map(e => e.innerText.trim());
                const h1 = h1s.find(t => t && t !== 'Chats' && t !== 'Facebook');
                return h1 || document.title.split('|')[0].trim();
            }""")

            # --- Follower count (exact/fallback from HTML + visible header) ---
            html_content   = page.content()
            page_followers = 0
            for pat in [
                r'"follower_count"\s*:\s*(\d+)',
                r'"subscribe_count"\s*:\s*(\d+)',
                r'"followers_count"\s*:\s*(\d+)',
            ]:
                m = re.search(pat, html_content)
                if m:
                    page_followers = int(m.group(1))
                    break

            if not page_followers:
                fl_raw = page.evaluate("""() => {
                    const texts = [];
                    for (const e of [...document.querySelectorAll('h1, h2, a, span, div')]) {
                        const txt = (e.innerText || e.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim();
                        if (txt) texts.push(txt);
                    }

                    // Ưu tiên cụm followers/người theo dõi. Không lower-case toàn bộ để giữ M = million,
                    // tránh parse_count hiểu '21m' là 21 phút.
                    for (const t of texts) {
                        const m = t.match(/([\d.,]+\s*(?:[KMBkmb]|nghìn|ngàn|triệu|tỷ)?)\s*(?:người theo dõi|followers)/i);
                        if (m) return m[1].replace(/\s+/g, '');
                    }

                    // Một số header gom cụm: "21M likes · 21M followers"
                    const body = texts.join(' | ');
                    const m2 = body.match(/([\d.,]+\s*(?:[KMBkmb]|nghìn|ngàn|triệu|tỷ)?)\s*(?:người theo dõi|followers)/i);
                    if (m2) return m2[1].replace(/\s+/g, '');

                    return '0';
                }""")
                # Riêng follower: nếu JS trả 21m thì đổi thành 21M để không bị hiểu là minute.
                if isinstance(fl_raw, str) and re.fullmatch(r"[\d.,]+m", fl_raw.strip()):
                    fl_raw = fl_raw.strip()[:-1] + "M"
                page_followers = parse_count(fl_raw)

            detected_page_name = page_name
            detected_handle = str(target_url or "").rstrip("/").split("/")[-1]

            if STRICT_PAGE_IDENTITY and detected_page_name in {"Notifications", "Facebook", "Chats", ""}:
                print(f"[PAGE_IDENTITY_WARN] detected_page_name={detected_page_name!r}; vẫn dùng FORCE_PAGE_NAME={FORCE_PAGE_NAME!r}, không tạo file mới.")

            page_name = FORCE_PAGE_NAME or detected_page_name
            page_handle = FORCE_PAGE_HANDLE or detected_handle
            print(f"Domain: {page_name} | detected={detected_page_name} | Người theo dõi: {page_followers}")

            safe_page_name = re.sub(r'[^\\w]', '_', page_name).strip('_') or page_handle or "facebook_page"
            output_json_name = FORCE_OUTPUT_JSON_NAME or ("posts_" + safe_page_name + ".json")
            json_file  = os.path.join(save_dir, output_json_name)
            checkpoint_file = os.path.join(save_dir, CHECKPOINT_FILE_NAME)
            seed_output_json_if_needed(json_file)

            seen_urls  = set()
            seen_content_keys = set()
            saved_data = []
            if os.path.exists(json_file):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        saved_data = json.load(f)
                    for item in saved_data:
                        if item.get('post_url'):
                            seen_urls.add(item['post_url'])
                        ck = make_post_content_key(page_handle, item.get('post_content', ''))
                        if ck:
                            seen_content_keys.add(ck)
                except json.JSONDecodeError:
                    pass
            initial_saved_count = len(saved_data)
            session_target = min(SESSION_POST_LIMIT, max(0, TARGET_POSTS - initial_saved_count))
            print(f"Đã tải {initial_saved_count} bài viết từ {json_file}")
            frontier = compute_dataset_frontier(saved_data)
            print(
                f"[FRONTIER] newest={frontier.get('newest_timestamp_human')} | "
                f"oldest={frontier.get('oldest_timestamp_human')} | total={frontier.get('total_records')}"
            )
            print(f"[SESSION] Cần thu thêm tối đa {session_target} bài mới trong session này; mục tiêu tổng {TARGET_POSTS}.")

            if session_target > 0:
                warm_jump_to_resume_area(page, checkpoint_file, saved_data)

            if session_target <= 0:
                print(f"[SESSION DONE] File đã đủ mục tiêu tổng: {initial_saved_count}/{TARGET_POSTS}")
                continue

            collected       = 0
            processed_count = 0  # số candidate đã kiểm tra, kể cả bị bỏ qua
            consecutive_old = 0
            posts_in_batch  = 0
            stop_page       = False
            scroll_rounds   = 0
            empty_rounds    = 0
            crawl_start_time = time.time()
            last_success_time = crawl_start_time

            live_accepted_keys = set()
            url_only_skips = 0
            timestamp_fail_skips = 0
            stale_retry = 0
            zero_share_rounds = 0
            duplicate_skip_streak = 0
            duplicate_no_new_rounds = 0
            recovery_attempts = 0
            last_health_new_count = 0
            last_tab_reset_new_count = 0

            while collected < session_target and not stop_page:
                live = live_get_visible_post_summaries(page)
                live_posts = live.get("posts") or []

                if DEBUG_SCROLL_SUMMARY:
                    print(
                        f"[{format_elapsed(time.time() - crawl_start_time)}] "
                        f"[LiveScan] round={scroll_rounds} "
                        f"share_raw={live.get('share_buttons_raw')} "
                        f"share_visible={live.get('share_buttons_visible')} "
                        f"live_posts={len(live_posts)} "
                        f"new={collected}/{session_target} total={initial_saved_count + collected}/{TARGET_POSTS} "
                        f"dup_streak={duplicate_skip_streak} url_only={url_only_skips} ts_fail={timestamp_fail_skips} stale={stale_retry}",
                        flush=True
                    )

                if int(live.get("share_buttons_raw") or 0) == 0:
                    zero_share_rounds += 1
                    if zero_share_rounds == 8:
                        print("[RECOVERY] share_raw=0 liên tục 8 vòng -> reload page và chờ render lại", flush=True)
                        page.reload(wait_until="domcontentloaded", timeout=30_000)
                        page.wait_for_timeout(4500)
                    scroll_rounds += 1
                    if scroll_rounds >= MAX_SCROLLS:
                        print(f"[Dừng] Đạt giới hạn scroll ({MAX_SCROLLS} vòng).")
                        break
                    live_scroll_down(page, multiplier=0.8)
                    continue
                else:
                    zero_share_rounds = 0

                target_summary = None
                no_candidate_reasons = {"accepted_key": 0, "content_duplicate": 0, "above_or_invalid": 0}
                scan_skip_log_count = 0

                for s in live_posts:
                    sk = live_stable_key(s.get("caption"))
                    if sk in live_accepted_keys:
                        no_candidate_reasons["accepted_key"] += 1
                        scan_skip_log_count += 1
                        if PRINT_SCAN_SKIP_REASON and scan_skip_log_count <= 2 and (scroll_rounds % SCAN_SKIP_LOG_EVERY == 0):
                            print(
                                f"    [SKIP ĐÃ XÉT TRONG VIEW] round={scroll_rounds} | {short_text(s.get('caption'), 55)}",
                                flush=True
                            )
                        continue

                    fast_caption_for_key = s.get("caption") or ""
                    content_key = make_post_content_key(page_handle, fast_caption_for_key)
                    if DEDUP_BY_CONTENT and content_key and content_key in seen_content_keys:
                        # Đây là post đã thu rồi theo caption/content, không phải feed đứng.
                        live_accepted_keys.add(sk)
                        duplicate_skip_streak += 1
                        duplicate_no_new_rounds += 1
                        no_candidate_reasons["content_duplicate"] += 1
                        scan_skip_log_count += 1
                        if PRINT_DUPLICATE_POST_LOG and scan_skip_log_count <= 3:
                            print(
                                f"    [TRÙNG CONTENT - FAST SKIP] dup_streak={duplicate_skip_streak} | {short_text(fast_caption_for_key, 60)}",
                                flush=True
                            )
                        continue

                    if (s.get("rect") or {}).get("bottom", 0) < -180:
                        no_candidate_reasons["above_or_invalid"] += 1
                        continue

                    s["_stable_key"] = sk
                    target_summary = s
                    break

                if not target_summary:
                    scroll_rounds += 1
                    if scroll_rounds >= MAX_SCROLLS:
                        print(f"[Dừng] Đạt giới hạn scroll ({MAX_SCROLLS} vòng).")
                        break

                    total_now_for_log = initial_saved_count + collected

                    # Nếu vẫn có live_posts nhưng toàn post đã xét/đã thu, đây là duplicate zone.
                    # Không recovery sớm, chỉ fast-scroll qua vùng trùng.
                    if live_posts and (no_candidate_reasons["accepted_key"] or no_candidate_reasons["content_duplicate"]):
                        no_new_candidate_log(
                            scroll_rounds, live, no_candidate_reasons, duplicate_skip_streak,
                            collected, session_target, total_now_for_log, page
                        )

                        if duplicate_no_new_rounds >= DUPLICATE_NO_NEW_RECOVERY_ROUNDS:
                            recovery_attempts += 1
                            if recovery_attempts <= MAX_RECOVERY_ATTEMPTS_PER_PAGE:
                                recover_feed(page, target_url, f"duplicate_zone_rounds={duplicate_no_new_rounds}", recovery_attempts)
                                duplicate_no_new_rounds = 0
                                empty_rounds = 0
                                live_accepted_keys.clear()
                                continue
                            print(f"[Dừng] Đi qua vùng trùng quá lâu sau {recovery_attempts} recovery attempts.", flush=True)
                            break

                        live_scroll_down(page, multiplier=FAST_SKIP_SCROLL_MULTIPLIER)
                        continue

                    empty_rounds += 1
                    if empty_rounds >= STAGNATION_ROUNDS_BEFORE_RECOVERY:
                        recovery_attempts += 1
                        if recovery_attempts <= MAX_RECOVERY_ATTEMPTS_PER_PAGE:
                            recover_feed(page, target_url, f"no_live_candidate_empty_rounds={empty_rounds}", recovery_attempts)
                            empty_rounds = 0
                            live_accepted_keys.clear()
                            continue
                        print(f"[Dừng] Không có candidate hợp lệ sau {recovery_attempts} recovery attempts.")
                        break

                    live_scroll_down(page, multiplier=1.35 if empty_rounds > 4 else 0.9)
                    continue

                post_el, align_info = live_align_post_header(page, target_summary["key"], LIVE_TARGET_HEADER_Y)
                if not post_el:
                    stale_retry += 1
                    print(
                        f"  [STALE_RETRY] align={align_info.get('error')} | {short_text(target_summary.get('caption'), 55)}",
                        flush=True
                    )
                    live_scroll_down(page, multiplier=0.55)
                    continue

                processed_count += 1
                candidate_start = time.time()

                ts_res = live_resolve_timestamp_and_url(context, page, post_el, page_handle)
                quick_url = ts_res.get("url")
                if ts_res.get("status") != "OK_TIMESTAMP":
                    live_accepted_keys.add(target_summary["_stable_key"])
                    if ts_res.get("status") == "URL_ONLY":
                        url_only_skips += 1
                        print(
                            f"  {processed_count}. [Bỏ qua timestamp URL_ONLY] "
                            f"t+{format_elapsed(time.time() - crawl_start_time)} "
                            f"url={short_text(quick_url, 90)} reason={ts_res.get('reason')} | {short_text(target_summary.get('caption'), 45)}",
                            flush=True
                        )
                    else:
                        timestamp_fail_skips += 1
                        print(
                            f"  {processed_count}. [Bỏ qua timestamp FAIL] "
                            f"t+{format_elapsed(time.time() - crawl_start_time)} "
                            f"reason={ts_res.get('reason')} | {short_text(target_summary.get('caption'), 45)}",
                            flush=True
                        )
                    live_scroll_down(page, multiplier=0.75)
                    continue

                quick_url = normalize_post_like_url_from_timestamp(quick_url, page_handle)
                if not quick_url:
                    live_accepted_keys.add(target_summary["_stable_key"])
                    timestamp_fail_skips += 1
                    print(f"  {processed_count}. [Bỏ qua URL sau timestamp] {short_text(target_summary.get('caption'), 45)}", flush=True)
                    live_scroll_down(page, multiplier=0.75)
                    continue

                if quick_url in seen_urls:
                    duplicate_skip_streak += 1
                    duplicate_no_new_rounds += 1
                    live_accepted_keys.add(target_summary["_stable_key"])
                    if PRINT_DUPLICATE_POST_LOG:
                        print(
                            f"  {processed_count}. [POST ĐÃ THU RỒI - URL] "
                            f"dup_streak={duplicate_skip_streak} "
                            f"new={collected}/{session_target} total={initial_saved_count + collected}/{TARGET_POSTS} "
                            f"url={short_text(quick_url, 80)} | {short_text(target_summary.get('caption'), 45)}",
                            flush=True
                        )
                    mult = FAST_SKIP_SCROLL_MULTIPLIER if (FAST_SKIP_EXISTING and duplicate_skip_streak >= FAST_SKIP_AFTER_DUPLICATES) else 0.9
                    live_scroll_down(page, multiplier=mult)
                    continue

                url_resolve_dt = time.time() - candidate_start
                if url_resolve_dt > 20:
                    print(f"[SLOW_URL_RESOLVE] {url_resolve_dt:.1f}s status={ts_res.get('status')} reason={ts_res.get('reason')} | {short_text(target_summary.get('caption'), 70)}", flush=True)

                fast_caption = get_fast_caption(post_el, page_name)
                text_preview_quick = short_text(fast_caption or target_summary.get("caption") or "", 45)
                content_key = make_post_content_key(page_handle, fast_caption)

                if DEDUP_BY_CONTENT and content_key and content_key in seen_content_keys:
                    duplicate_skip_streak += 1
                    duplicate_no_new_rounds += 1
                    seen_urls.add(quick_url)
                    live_accepted_keys.add(target_summary["_stable_key"])
                    if PRINT_DUPLICATE_POST_LOG:
                        print(
                            f"  {processed_count}. [POST ĐÃ THU RỒI - CONTENT] "
                            f"dup_streak={duplicate_skip_streak} "
                            f"new={collected}/{session_target} total={initial_saved_count + collected}/{TARGET_POSTS} "
                            f"url={short_text(quick_url, 80)} | {text_preview_quick}",
                            flush=True
                        )
                    mult = FAST_SKIP_SCROLL_MULTIPLIER if (FAST_SKIP_EXISTING and duplicate_skip_streak >= FAST_SKIP_AFTER_DUPLICATES) else 0.9
                    live_scroll_down(page, multiplier=mult)
                    continue

                if PREFILTER_LOW_REACTION_BEFORE_MODAL:
                    fast_total = get_fast_total_reactions_from_container(post_el)
                    if 0 < fast_total < MIN_REACTIONS:
                        seen_urls.add(quick_url)
                        live_accepted_keys.add(target_summary["_stable_key"])
                        duplicate_no_new_rounds = 0
                        if content_key:
                            seen_content_keys.add(content_key)
                        print(
                            f"  {processed_count}. [Bỏ qua nhanh] "
                            f"t+{format_elapsed(time.time() - crawl_start_time)} "
                            f"total≈{fast_total} < {MIN_REACTIONS} "
                            f"new={collected}/{session_target} total={initial_saved_count + collected}/{TARGET_POSTS} | {text_preview_quick}",
                            flush=True
                        )
                        live_scroll_down(page, multiplier=0.75)
                        continue

                status = check_valid_post(post_el)
                if status != 'OK':
                    print(f"  {processed_count}. [Bỏ qua] {status} collected={collected}/{TARGET_POSTS} | {text_preview_quick}", flush=True)
                    seen_urls.add(quick_url)
                    live_accepted_keys.add(target_summary["_stable_key"])
                    live_scroll_down(page, multiplier=0.75)
                    continue

                meta_start = time.time()
                post_data = extract_post_data(
                    page,
                    post_el,
                    page_name,
                    page_handle=page_handle,
                    pre_parsed_ts=None,
                    pre_raw_ts=None,
                    resolved_url=quick_url,
                )
                meta_dt = time.time() - meta_start
                dialog_stuck_after_extract = False
                if not close_all_dialogs(page, reason="after_extract_post_data", max_attempts=4):
                    dialog_stuck_after_extract = True
                    print("[WARN] Modal/dialog không đóng sạch sau extract; sẽ lưu post hiện tại rồi kết thúc session để supervisor restart Chrome, không reload về đầu page.", flush=True)

                if not post_data.get('post_url'):
                    print(
                        f"  {processed_count}. [Bỏ qua URL sau metadata] "
                        f"t+{format_elapsed(time.time() - crawl_start_time)} "
                        f"meta={meta_dt:.1f}s collected={collected}/{TARGET_POSTS} | {text_preview_quick}",
                        flush=True
                    )
                    live_accepted_keys.add(target_summary["_stable_key"])
                    live_scroll_down(page, multiplier=0.75)
                    continue

                if not post_data.get("post_timestamp_human"):
                    timestamp_fail_skips += 1
                    live_accepted_keys.add(target_summary["_stable_key"])
                    print(
                        f"  {processed_count}. [Bỏ qua timestamp missing sau metadata] "
                        f"t+{format_elapsed(time.time() - crawl_start_time)} "
                        f"url={url_resolve_dt:.1f}s meta={meta_dt:.1f}s | {text_preview_quick}",
                        flush=True
                    )
                    live_scroll_down(page, multiplier=0.75)
                    continue

                post_data['source_type']     = "Facebook"
                post_data['page_name']       = page_name
                post_data['page_url']        = target_url
                post_data['page_handle']     = str(target_url or '').rstrip('/').split('/')[-1]
                post_data['page_followers']  = page_followers

                rd = post_data.get('reactions_detail', {}) or {}
                post_data['like_count']      = rd.get('Like', 0)
                post_data['love_count']      = rd.get('Love', 0)
                post_data['haha_count']      = rd.get('Haha', 0)
                post_data['wow_count']       = rd.get('Wow', 0)
                post_data['sad_count']       = rd.get('Sad', 0)
                post_data['angry_count']     = rd.get('Angry', 0)
                post_data['care_count']      = rd.get('Care', 0)
                if FLATTEN_REACTIONS:
                    post_data.pop('reactions_detail', None)

                denom = page_followers if page_followers and page_followers > 0 else None
                post_data['share_per_follower'] = (post_data.get('share_count', 0) / denom) if denom else None
                post_data['comment_per_follower'] = (post_data.get('comment_count', 0) / denom) if denom else None
                post_data['reaction_per_follower'] = (post_data.get('total_reactions', 0) / denom) if denom else None

                if not KEEP_DEBUG_FIELDS:
                    post_data.pop('count_debug_numbers', None)
                    post_data.pop('count_debug_lines_tail', None)
                    post_data.pop('count_extract_method', None)

                for _k in ['url', 'content', 'title', 'domain_name', 'author',
                           'creation_time', 'creation_time_human', 'raw_creation_time', 'created_at',
                           'feedback_id', 'label', 'topic_label']:
                    post_data.pop(_k, None)

                _field_order = [
                    'source_type',
                    'page_name', 'page_url', 'page_handle', 'page_followers',
                    'post_url', 'post_id', 'post_type', 'external_url',
                    'post_timestamp_raw', 'post_timestamp_unix', 'post_timestamp_human',
                    'timestamp_source', 'timestamp_url', 'timestamp_status',
                    'post_content',
                    'like_count', 'love_count', 'haha_count', 'wow_count',
                    'sad_count', 'angry_count', 'care_count', 'total_reactions',
                    'comment_count', 'share_count',
                    'share_per_follower', 'comment_per_follower', 'reaction_per_follower',
                    'crawl_time', 'crawl_time_human',
                ]
                post_data = {k: post_data.get(k) for k in _field_order if k in post_data}

                post_content  = post_data.get('post_content', '')
                exact_content_key = make_post_content_key(page_handle, post_content)
                if DEDUP_BY_CONTENT and exact_content_key and exact_content_key in seen_content_keys:
                    seen_urls.add(quick_url)
                    live_accepted_keys.add(target_summary["_stable_key"])
                    print(
                        f"  {processed_count}. [Bỏ qua trùng nội dung] "
                        f"t+{format_elapsed(time.time() - crawl_start_time)} "
                        f"collected={collected}/{TARGET_POSTS} | {short_text(post_content, 45)}",
                        flush=True
                    )
                    live_scroll_down(page, multiplier=0.65)
                    continue

                text_preview  = (post_content[:40].replace('\n', ' ') + '...') if post_content else '(trống)'

                if (
                    post_data.get('total_reactions', 0) == 0
                    and post_data.get('comment_count', 0) == 0
                    and post_data.get('share_count', 0) == 0
                ):
                    print(f"  {processed_count}. [Bỏ qua metadata=0] t+{format_elapsed(time.time() - crawl_start_time)} url={url_resolve_dt:.1f}s meta={meta_dt:.1f}s collected={collected}/{TARGET_POSTS} | {text_preview}", flush=True)
                    live_accepted_keys.add(target_summary["_stable_key"])
                    live_scroll_down(page, multiplier=0.75)
                    continue

                if post_data['total_reactions'] < MIN_REACTIONS:
                    print(f"  {processed_count}. [Bỏ qua tương tác] t+{format_elapsed(time.time() - crawl_start_time)} total={post_data['total_reactions']} < {MIN_REACTIONS} url={url_resolve_dt:.1f}s meta={meta_dt:.1f}s collected={collected}/{TARGET_POSTS} | {text_preview}", flush=True)
                    seen_urls.add(quick_url)
                    live_accepted_keys.add(target_summary["_stable_key"])
                    live_scroll_down(page, multiplier=0.75)
                    continue

                seen_urls.add(quick_url)
                live_accepted_keys.add(target_summary["_stable_key"])
                if exact_content_key:
                    seen_content_keys.add(exact_content_key)
                saved_data.append(post_data)
                collected += 1
                save_json_atomic(json_file, saved_data)
                save_checkpoint_file(checkpoint_file, saved_data, page, reason="success")
                last_success_time = time.time()
                empty_rounds = 0
                recovery_attempts = 0
                duplicate_skip_streak = 0
                duplicate_no_new_rounds = 0

                total_now = initial_saved_count + collected

                print(
                    f"  {processed_count}. [THÀNH CÔNG new={collected}/{session_target} total={total_now}/{TARGET_POSTS}] "
                    f"t+{format_elapsed(last_success_time - crawl_start_time)} "
                    f"url={url_resolve_dt:.1f}s meta={meta_dt:.1f}s "
                    f"type={post_data.get('post_type')} "
                    f"ts={short_timestamp_for_log(post_data)} "
                    f"react={post_data.get('total_reactions')} "
                    f"cmt={post_data.get('comment_count', 0)} "
                    f"share={post_data.get('share_count', 0)} | {text_preview}",
                    flush=True
                )

                if collected - last_health_new_count >= HEALTH_EVERY_NEW_POSTS:
                    log_health(page, f"[HEALTH new={collected} total={total_now}]")
                    last_health_new_count = collected

                if collected - last_tab_reset_new_count >= TAB_RESET_EVERY_NEW_POSTS and collected < session_target:
                    print(f"[TAB_RESET] Đã thu thêm {collected} bài trong session, reload page để giảm DOM/modal bloat.", flush=True)
                    recover_feed(page, target_url, "periodic_tab_reset", 2)
                    live_accepted_keys.clear()
                    last_tab_reset_new_count = collected

                stop_now, stop_reason = should_stop_session(initial_saved_count, collected)
                if dialog_stuck_after_extract and END_SESSION_ON_DIALOG_STUCK_AFTER_SAVE:
                    print("[SESSION PAUSE] dialog_stuck_after_extract sau khi đã lưu post; dừng session để restart Chrome, tránh mất deep-scroll.", flush=True)
                    break

                if stop_now:
                    print(f"[SESSION DONE] {stop_reason}", flush=True)
                    break

                posts_in_batch += 1
                if posts_in_batch >= BATCH_SIZE and collected < TARGET_POSTS:
                    sleep_time = random.randint(*BATCH_SLEEP)
                    print(
                        f"\n[{format_elapsed(time.time() - crawl_start_time)}] "
                        f"[NGHỈ] Batch={posts_in_batch} bài | New={collected}/{session_target} | Total={initial_saved_count + collected}/{TARGET_POSTS} | Nghỉ {sleep_time}s...",
                        flush=True
                    )
                    sleep_with_heartbeat(sleep_time, "đang nghỉ batch", crawl_start_time, collected, TARGET_POSTS)
                    posts_in_batch = 0

                scroll_rounds += 1
                if scroll_rounds >= MAX_SCROLLS:
                    print(f"[Dừng] Đạt giới hạn scroll ({MAX_SCROLLS} vòng).")
                    break
                live_scroll_down(page, multiplier=0.75)
            print(f"\n[HOÀN THÀNH SESSION] Thu thêm {collected} bài mới; tổng file hiện có {initial_saved_count + collected}/{TARGET_POSTS} từ {page_name}", flush=True)
            save_checkpoint_file(checkpoint_file, saved_data, page, reason="session_end")
            close_all_dialogs(page, reason="end_page", max_attempts=5)
            sleep_next = random.randint(*PAGE_SLEEP)
            print(f"[PAGE_SLEEP] Chờ {sleep_next}s trước khi sang trang tiếp theo...", flush=True)
            sleep_with_heartbeat(sleep_next, "đang nghỉ chuyển page", crawl_start_time, collected, TARGET_POSTS)


if __name__ == "__main__":
    main()

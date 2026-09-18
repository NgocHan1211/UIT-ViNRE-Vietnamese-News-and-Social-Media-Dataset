import os
import json
import time
import random
import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

# ===================== CONFIG =====================
# Accurate mode: luôn mở reaction modal để lấy metadata chi tiết.
# Chỉnh nhanh:
# - TARGET_PAGES: danh sách page cần crawl.
# - TARGET_POSTS: số bài muốn thu mỗi page.

TARGET_POSTS = 3000
MIN_REACTIONS = 50

MAX_SCROLLS = 20000
MAX_EMPTY_ROUNDS = 500

BATCH_SIZE = 50
BATCH_SLEEP = (30, 100)
PAGE_SLEEP = (100, 200)

KEEP_DEBUG_FIELDS = False
FLATTEN_REACTIONS = True

DEBUG_URL_DIAGNOSTICS = False
DEBUG_SCROLL_SUMMARY = True
DEDUP_BY_CONTENT = True
PREFILTER_LOW_REACTION_BEFORE_MODAL = True
URL_RESOLVE_RETRIES = 2
POST_CONTAINER_MAX_ANCESTOR_LEVELS = 28

# ==================================================
# ===================== PAGES =====================
TARGET_PAGES = [
    # "https://www.facebook.com/congdongvnexpress",       # PQ
    # "https://www.facebook.com/baotuoitre",              # PQ
    # "https://www.facebook.com/schannel.vn",             # Nhung
    # "https://www.facebook.com/thongtinchinhphu",        # Nhung
    # "https://www.facebook.com/K14vn/",                  # Hân
    # "https://www.facebook.com/Theanh28",                # Hân
    # "https://www.facebook.com/yannews",                 # Yến 
    # "https://www.facebook.com/vietnamnet.vn"            # Yến 
    
    # Thêm/xóa page ở đây.
]
# ==================================================

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
    
    """
    text = str(raw_text or "").replace("\xa0", " ")

    patterns = {
        "comment": [
            r"([\d.,]+\s*(?:K|M|B|k|m|b|N|T|nghìn|ngàn|triệu|tỷ)?)\s*(?:comments?|bình luận)\b",
            r"(?:comments?|bình luận|Leave a comment)\D{0,25}([\d.,]+\s*(?:K|M|B|k|m|b|N|T|nghìn|ngàn|triệu|tỷ)?)",
        ],
        "share": [
            r"([\d.,]+\s*(?:K|M|B|k|m|b|N|T|nghìn|ngàn|triệu|tỷ)?)\s*(?:shares?|chia sẻ)\b",
            r"(?:shares?|chia sẻ)\D{0,25}([\d.,]+\s*(?:K|M|B|k|m|b|N|T|nghìn|ngàn|triệu|tỷ)?)",
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
                'a[href*="set=pcb"]'
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
            page.mouse.move(x, y)
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
            const patterns = ['/posts/', 'pfbid', 'story_fbid', 'permalink.php', 'photo/?fbid', '/photo/', 'set=pcb'];
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
    """Return 'OK' or a skip-reason string."""
    try:
        return post_el.evaluate("""(el) => {
            const links = [...el.querySelectorAll('a[href]')];
            if (links.some(a => a.href.includes('/reel/') || a.href.includes('/videos/')))
                return 'Video/Reel';
            // Shared post: multiple story_message containers
            if (el.querySelectorAll('[data-ad-rendering-role="story_message"]').length > 1)
                return 'Bài Chia sẻ';
            return 'OK';
        }""") or 'OK'
    except Exception:
        return 'OK'


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
            const modal = document.querySelector('[role="dialog"]');
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

        page.wait_for_selector('[role="dialog"]', timeout=3000)
        time.sleep(1.0)
        raw = _read_tabs()
        if not raw:
            page.keyboard.press("Escape")
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
        time.sleep(0.5)
        return {k: resolved.get(k, 0) for k in KNOWN}

    except Exception as e:
        print(f"      [!] reactions modal error: {e}")
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


def get_best_post_url_from_element(page, post_el, page_handle: str = "") -> str:
    """Hover timestamp trong post container rồi chọn URL tốt nhất, ưu tiên pfbid."""
    page_handle = str(page_handle or "").strip("/")

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

            const postLinks = [...el.querySelectorAll('a[href*="/posts/"], a[href*="pfbid"], a[href*="story_fbid"], a[href*="permalink.php"]')]
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
                        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
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
                else if (href.includes('set=pcb')) score += 450;
                else if (href.includes('photo/?fbid') || href.includes('/photo/')) score += 120;
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


def extract_post_data(page, post_el, page_name: str, page_handle: str = '', pre_parsed_ts: int = None, pre_raw_ts: str = None) -> dict:
    """Build a complete post data dict from a post element."""
    data = {}

    # 1. URL & ID
    url = get_best_post_url_from_element(page, post_el, page_handle)
    data['post_url'] = url
    data['post_id'] = url.rstrip('/').split('/')[-1] if url else f"temp_{int(time.time() * 1000)}"

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


    counts_raw_text = post_el.evaluate("""(el) => {
        const pieces = [];
        for (const node of el.querySelectorAll('[aria-label], span[dir="auto"], a[role="link"], div[role="button"]')) {
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
                    [...node.querySelectorAll('a, span')].some(x => {
                        const txt = (x.innerText || x.getAttribute('aria-label') || '').trim();
                        return TIME_RE.test(txt);
                    });

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
                    if (lc > 0) score += 40 + Math.min(lc, 5) * 5;
                    if (hasStory(node)) score += 50;
                    if (hasTime(node)) score += 35;
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

def main():
    save_dir = os.path.join('data', 'json-targeted-crawl')
    os.makedirs(save_dir, exist_ok=True)

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

        for target_url in TARGET_PAGES:
            print("\n" + "=" * 45)
            print(f"ĐANG TRUY CẬP TRANG: {target_url}")
            page.goto(target_url, wait_until="domcontentloaded", timeout=30_000)
            time.sleep(3)
            print(f"-> URL thực tế sau khi load: {page.url}")

            if "search" in page.url or page.url == "https://www.facebook.com/":
                print("[!] CẢNH BÁO: Trình duyệt bị chuyển hướng. Kiểm tra URL hoặc trạng thái đăng nhập!")

            # --- Page name ---
            page_name = page.evaluate("""() => {
                const h1s = [...document.querySelectorAll('h1')].map(e => e.innerText.trim());
                const h1 = h1s.find(t => t && t !== 'Chats' && t !== 'Facebook');
                return h1 || document.title.split('|')[0].trim();
            }""")

            # --- Follower count (exact from source HTML) ---
            html_content   = page.content()
            page_followers = 0
            for pat in [r'"follower_count"\s*:\s*(\d+)',
                        r'"subscribe_count"\s*:\s*(\d+)']:
                m = re.search(pat, html_content)
                if m:
                    page_followers = int(m.group(1))
                    break
            if not page_followers:
                fl_raw = page.evaluate("""() => {
                    for (const e of [...document.querySelectorAll('a, span')]) {
                        const t = (e.innerText || '').toLowerCase();
                        if (t.includes('người theo dõi') || t.includes('followers')) {
                            const m = t.match(/([\d.,]+\s*[km]?)\s*(người theo dõi|followers)/);
                            if (m) return m[1];
                        }
                    }
                    return '0';
                }""")
                page_followers = parse_count(fl_raw)

            print(f"Domain: {page_name} | Người theo dõi: {page_followers}")

            page_handle = str(target_url or "").rstrip("/").split("/")[-1]
            clean_name_raw = page_handle if page_name in {"Notifications", "Facebook", "Chats", ""} else page_name
            clean_name = re.sub(r'[^\w]', '_', clean_name_raw).strip('_') or page_handle or "facebook_page"
            json_file  = os.path.join(save_dir, f"posts_{clean_name}.json")

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
            print(f"Đã tải {len(saved_data)} bài viết từ {json_file}")

            collected       = 0
            processed_count = 0  # số candidate đã kiểm tra, kể cả bị bỏ qua
            consecutive_old = 0
            posts_in_batch  = 0
            stop_page       = False
            scroll_rounds   = 0
            empty_rounds    = 0
            crawl_start_time = time.time()
            last_success_time = crawl_start_time

            while collected < TARGET_POSTS and not stop_page:
                round_collected_before = collected
                collection = collect_post_containers_from_share_buttons(page)
                posts = collection["posts"]
                collect_dbg = collection["debug"]

                if DEBUG_SCROLL_SUMMARY:
                    print(
                        f"[{format_elapsed(time.time() - crawl_start_time)}] "
                        f"[Scan] scroll={scroll_rounds} share_btns={collect_dbg.get('share_buttons')} "
                        f"candidates={collect_dbg.get('post_candidates')} failed_btns={collect_dbg.get('failed_buttons')} "
                        f"collected={collected}/{TARGET_POSTS}",
                        flush=True
                    )

                for post_el in posts:
                    if collected >= TARGET_POSTS:
                        break
                    try:
                        # Kiểm tra element còn gắn vào DOM không (Facebook virtual scroll xóa cũ)
                        is_connected = post_el.evaluate("el => el.isConnected")
                        if not is_connected:
                            continue

                        processed_count += 1
                        candidate_start = time.time()
                        since_last_success = candidate_start - last_success_time

                        # --- Dedup bằng URL thật trong đúng container post ---
                        quick_url, url_debug = resolve_post_url_with_retries(page, post_el, page_handle)

                        if not quick_url:
                            diag = get_post_container_diagnostics(post_el)
                            story_preview = short_text(diag.get("story_text", ""), 70)
                            print(
                                f"  {processed_count}. [Bỏ qua URL] "
                                f"t+{format_elapsed(time.time() - crawl_start_time)} "
                                f"| {story_preview}",
                                flush=True
                            )
                            continue

                        if quick_url in seen_urls:
                            continue

                        url_resolve_dt = time.time() - candidate_start

                        # Quick caption preview (story_message selector, không dùng innerText toàn block)
                        text_preview_quick = post_el.evaluate("""(el) => {
                            const c = el.querySelector('[data-ad-rendering-role="story_message"]');
                            if (c) return (c.innerText || '').trim().slice(0, 40).replace(/\\n/g, ' ') + '...';
                            return '(chưa có caption)';
                        }""")

                        fast_caption = get_fast_caption(post_el, page_name)
                        content_key = make_post_content_key(page_handle, fast_caption)

                        if DEDUP_BY_CONTENT and content_key and content_key in seen_content_keys:
                            seen_urls.add(quick_url)
                            continue

                        if PREFILTER_LOW_REACTION_BEFORE_MODAL:
                            fast_total = get_fast_total_reactions_from_container(post_el)
                            if 0 < fast_total < MIN_REACTIONS:
                                seen_urls.add(quick_url)
                                if content_key:
                                    seen_content_keys.add(content_key)
                                print(
                                    f"  {processed_count}. [Bỏ qua nhanh] "
                                    f"t+{format_elapsed(time.time() - crawl_start_time)} "
                                    f"total≈{fast_total} < {MIN_REACTIONS} "
                                    f"collected={collected}/{TARGET_POSTS} | {short_text(fast_caption or text_preview_quick, 45)}",
                                    flush=True
                                )
                                continue

                        status = check_valid_post(post_el)
                        if status != 'OK':
                            print(f"  {processed_count}. [Bỏ qua] {status} collected={collected}/{TARGET_POSTS} | {text_preview_quick}", flush=True)
                            seen_urls.add(quick_url)
                            continue

                        # --- Timestamp ---
                        # Bỏ qua timestamp để tránh nhầm thời gian bình luận.
                        # Không filter START_TIME/END_TIME nữa; crawl theo số lượng post và điều kiện tương tác.
                        ts_raw = None
                        c_time_pre = None

                        # Accurate: extract_post_data sẽ mở modal reaction để lấy chi tiết metadata.
                        meta_start = time.time()
                        post_data = extract_post_data(
                            page,
                            post_el,
                            page_name,
                            page_handle=page_handle,
                            pre_parsed_ts=c_time_pre,
                            pre_raw_ts=ts_raw,
                        )
                        meta_dt = time.time() - meta_start
                        post_data['source_type']     = "Facebook"
                        post_data['page_name']       = page_name
                        post_data['page_url']        = target_url
                        post_data['page_handle']     = str(target_url or '').rstrip('/').split('/')[-1]
                        post_data['page_followers']  = page_followers

                        # Flatten reactions: chỉ giữ một kiểu tên field, tránh lặp reactions_detail + *_count.
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

                        # Engagement normalized theo follower, phục vụ dashboard sau này.
                        denom = page_followers if page_followers and page_followers > 0 else None
                        post_data['share_per_follower'] = (post_data.get('share_count', 0) / denom) if denom else None
                        post_data['comment_per_follower'] = (post_data.get('comment_count', 0) / denom) if denom else None
                        post_data['reaction_per_follower'] = (post_data.get('total_reactions', 0) / denom) if denom else None

                        if not KEEP_DEBUG_FIELDS:
                            post_data.pop('count_debug_numbers', None)
                            post_data.pop('count_debug_lines_tail', None)
                            post_data.pop('count_extract_method', None)

                        # Schema gọn, không lặp field.
                        for _k in ['url', 'content', 'title', 'domain_name', 'author',
                                   'creation_time', 'creation_time_human', 'raw_creation_time', 'created_at',
                                   'feedback_id', 'label', 'topic_label']:
                            post_data.pop(_k, None)

                        # Reorder field để JSON dễ đọc và ổn định.
                        _field_order = [
                            'source_type',
                            'page_name', 'page_url', 'page_handle', 'page_followers',
                            'post_url', 'post_id',
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
                            print(
                                f"  {processed_count}. [Bỏ qua trùng nội dung] "
                                f"t+{format_elapsed(time.time() - crawl_start_time)} "
                                f"collected={collected}/{TARGET_POSTS} | {short_text(post_content, 45)}",
                                flush=True
                            )
                            continue

                        text_preview  = (post_content[:40].replace('\n', ' ') + '...') if post_content else '(trống)'

                        if (
                            post_data.get('total_reactions', 0) == 0
                            and post_data.get('comment_count', 0) == 0
                            and post_data.get('share_count', 0) == 0
                        ):
                            print(f"  {processed_count}. [Bỏ qua metadata=0] t+{format_elapsed(time.time() - crawl_start_time)} url={url_resolve_dt:.1f}s meta={meta_dt:.1f}s collected={collected}/{TARGET_POSTS} | {text_preview}", flush=True)
                            continue

                        if post_data['total_reactions'] < MIN_REACTIONS:
                            print(f"  {processed_count}. [Bỏ qua tương tác] t+{format_elapsed(time.time() - crawl_start_time)} total={post_data['total_reactions']} < {MIN_REACTIONS} url={url_resolve_dt:.1f}s meta={meta_dt:.1f}s collected={collected}/{TARGET_POSTS} | {text_preview}", flush=True)
                            seen_urls.add(quick_url)
                            continue

                        # Save real-time
                        seen_urls.add(quick_url)
                        if exact_content_key:
                            seen_content_keys.add(exact_content_key)
                        saved_data.append(post_data)
                        collected += 1
                        save_json_atomic(json_file, saved_data)
                        last_success_time = time.time()
                        print(
                            f"  {processed_count}. [THÀNH CÔNG {collected}/{TARGET_POSTS}] "
                            f"t+{format_elapsed(last_success_time - crawl_start_time)} "
                            f"url={url_resolve_dt:.1f}s meta={meta_dt:.1f}s "
                            f"react={post_data.get('total_reactions')} "
                            f"cmt={post_data.get('comment_count', 0)} "
                            f"share={post_data.get('share_count', 0)} | {text_preview}",
                            flush=True
                        )

                        # --- Kiểm tra nghỉ theo Batch ---
                        posts_in_batch += 1
                        if posts_in_batch >= BATCH_SIZE and collected < TARGET_POSTS:
                            sleep_time = random.randint(*BATCH_SLEEP)
                            print(
                                f"\n[{format_elapsed(time.time() - crawl_start_time)}] "
                                f"[NGHỈ] Batch={posts_in_batch} bài | Tổng={collected}/{TARGET_POSTS} | Nghỉ {sleep_time}s...",
                                flush=True
                            )
                            sleep_with_heartbeat(sleep_time, "đang nghỉ batch", crawl_start_time, collected, TARGET_POSTS)
                            posts_in_batch = 0

                    except Exception as e:
                        print(f"  {processed_count}. [LỖI] collected={collected}/{TARGET_POSTS}: {e}", flush=True)
                        continue

                if collected >= TARGET_POSTS:
                    break
                if stop_page:
                    break
                scroll_rounds += 1
                if collected == round_collected_before:
                    empty_rounds += 1
                else:
                    empty_rounds = 0
                if scroll_rounds >= MAX_SCROLLS:
                    print(f"[Dừng] Đạt giới hạn scroll ({MAX_SCROLLS} vòng).")
                    break
                if empty_rounds >= MAX_EMPTY_ROUNDS:
                    print(f"[Dừng] {MAX_EMPTY_ROUNDS} vòng liên tiếp không thu thêm bài mới. Có thể page đã hết bài phù hợp hoặc Facebook chưa render thêm.")
                    break
                human_scroll(page)
                time.sleep(1.2)

            print(f"\n[HOÀN THÀNH] Đã thu {collected}/{TARGET_POSTS} bài viết từ {page_name}", flush=True)
            sleep_next = random.randint(*PAGE_SLEEP)
            print(f"[PAGE_SLEEP] Chờ {sleep_next}s trước khi sang trang tiếp theo...", flush=True)
            sleep_with_heartbeat(sleep_next, "đang nghỉ chuyển page", crawl_start_time, collected, TARGET_POSTS)


if __name__ == "__main__":
    main()

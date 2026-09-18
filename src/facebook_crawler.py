import os
import json
import time
import random
import re
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta

# ================= CẤU HÌNH HỆ THỐNG =================
TARGET_POSTS = 3  # Đổi thành 250 khi chạy thật
MIN_REACTIONS = 50

# Mốc thời gian (01/01/2026 - 12/05/2026)
START_TIME = int(datetime(2026, 1, 1).timestamp())
END_TIME = int(datetime(2026, 5, 12, 23, 59, 59).timestamp())

# Cấu hình cứng danh sách 15 Fanpage mục tiêu
TARGET_PAGES = [
    # Nhóm Thể Thao
    "https://www.facebook.com/trollbongda",
    # Thêm các URL Fanpage mục tiêu vào đây...
    # "https://www.facebook.com/ghienbongda",
]
# ======================================================

def parse_count(text): 
    """Chuyển đổi các chuỗi chứa K, M, B thành số nguyên (Int)"""
    if not text:
        return 0
    text = str(text).strip().replace(",", ".").upper()
    m = re.search(r"([\d.]+)\s*([KMB]?)", text)
    if not m:
        return 0
    num = float(m.group(1))
    suffix = m.group(2)
    if suffix == "K":   num *= 1_000
    elif suffix == "M": num *= 1_000_000
    elif suffix == "B": num *= 1_000_000_000
    return int(num)

def parse_facebook_time(time_str):
    if not time_str:
        return int(time.time())
        
    time_str = str(time_str).lower().strip()
    if time_str.isdigit():
        return int(time_str)
        
    now = datetime.now()
    try:
        if 'vừa xong' in time_str or 'just now' in time_str:
            return int(now.timestamp())
        elif 'phút' in time_str or 'm' in time_str or 'min' in time_str:
            m = re.search(r'(\d+)', time_str)
            if m: return int((now - timedelta(minutes=int(m.group(1)))).timestamp())
        elif 'giờ' in time_str or 'h' in time_str or 'hour' in time_str:
            m = re.search(r'(\d+)', time_str)
            if m: return int((now - timedelta(hours=int(m.group(1)))).timestamp())
        elif 'ngày' in time_str or 'd' in time_str or 'day' in time_str:
            m = re.search(r'(\d+)', time_str)
            if m: return int((now - timedelta(days=int(m.group(1)))).timestamp())
        elif 'hôm qua' in time_str or 'yesterday' in time_str:
            return int((now - timedelta(days=1)).timestamp())
        elif 'tháng' in time_str or 'month' in time_str:
            m = re.search(r'(\d+)', time_str)
            if m: return int((now - timedelta(days=int(m.group(1))*30)).timestamp())
        elif 'năm' in time_str or 'year' in time_str:
            m = re.search(r'(\d+)', time_str)
            if m: return int((now - timedelta(days=int(m.group(1))*365)).timestamp())
    except:
        pass
    
    return int(now.timestamp())

def human_scroll(page):
    """Giả lập thao tác cuộn chuột mượt mà của con người"""
    page.evaluate("""() => new Promise(resolve => {
        let total = 0;
        const target = 1800 + Math.random()*600;
        const step   = 80  + Math.random()*50;
        const delay  = 28  + Math.random()*20;
        const t = setInterval(() => {
            window.scrollBy(0, step); total += step;
            if (total >= target) { clearInterval(t); resolve(); }
        }, delay);
    })""")
    time.sleep(random.uniform(2.5, 4.0))

def check_valid_post(post_element):
    """Lọc rác: Bỏ qua bài Share, Video, Reels"""
    status = post_element.evaluate("""(el) => {
        // 1. Loại bỏ Reels/Videos
        const links = [...el.querySelectorAll('a[href]')].map(a => a.href.toLowerCase());
        const isReelOrVideo = links.some(href => href.includes('/reel/') || href.includes('/videos/') || href.includes('/watch/'));
        if (isReelOrVideo) return "Video/Reel";
        
        // 2. Loại bỏ Shared Posts (Bài Chia sẻ)
        const isShared = links.some(href => href.includes('/share/'));
        if (isShared) return "Bài Chia sẻ (URL có /share/)";
        
        // Dự phòng: Kiểm tra thẻ chứa tác giả thứ 2 (biểu hiện của bài share)
        const messageContainers = el.querySelectorAll('[data-ad-rendering-role="story_message"], [data-ad-comet-preview="message"]');
        if (messageContainers.length > 1) return "Bài Chia sẻ (Nhiều khung text)";
        
        return "OK";
    }""")
    return status

def get_reactions_detail(page, post_element):
    """Lấy số lượng chính xác từng loại cảm xúc"""
    counts = {"like": 0, "love": 0, "haha": 0, "wow": 0, "sad": 0, "angry": 0, "care": 0}
    reaction_map = {
        "thích": "like", "like": "like",
        "yêu thích": "love", "love": "love",
        "haha": "haha", "wow": "wow",
        "buồn": "sad", "sad": "sad",
        "phẫn nộ": "angry", "angry": "angry",
        "thương thương": "care", "care": "care",
    }
    
    # Bước 1: Quét thuộc tính ẩn (aria-label)
    labels_raw = post_element.evaluate("""(el) => {
        return [...el.querySelectorAll('[aria-label]')]
            .map(e => e.getAttribute('aria-label'))
            .filter(l => l && /người|people|times/i.test(l));
    }""")
    
    needs_click = False
    for lbl in (labels_raw or []):
        ll = lbl.lower()
        m = re.search(r"([\d.,]+\s*[KkMmBb]?)", lbl)
        if m:
            val_str = m.group(1).upper()
            if any(char in val_str for char in ["K", "M", "B"]):
                needs_click = True
                break # Gặp số làm tròn -> Thoát quét ẩn để click Modal
            
            val = parse_count(val_str)
            for vn, key in reaction_map.items():
                if vn in ll:
                    counts[key] = max(counts[key], val)
                    break
                    
    # Kiểm tra thêm tổng hiển thị bên ngoài xem có K/M không
    total_raw = post_element.evaluate("""(el) => {
        const spans = [...el.querySelectorAll('span[dir="auto"]')];
        for (const s of spans) {
            const t = s.innerText;
            if (t && /^[\d.,]+[KkMmBb]?$/.test(t)) return t;
        }
        return "";
    }""")
    
    if total_raw and any(char in total_raw.upper() for char in ["K", "M", "B"]):
        needs_click = True
        
    if not needs_click and sum(counts.values()) > 0:
        return counts
        
    # Bước 2: Bắt buộc Click vào Modal nếu bị giấu số
    try:
        clicked = post_element.evaluate("""(el) => {
            const btns = [...el.querySelectorAll('[role="button"]')];
            const reactionBtn = btns.find(b => {
                const aria = b.getAttribute('aria-label');
                return aria && (/người|people|reactions/i.test(aria) || /Thích|Like/i.test(aria));
            });
            if (reactionBtn) {
                reactionBtn.click();
                return true;
            }
            return false;
        }""")
        
        if clicked:
            time.sleep(2.5) # Chờ Modal hiển thị
            
            modal_data = page.evaluate("""() => {
                const dialogs = [...document.querySelectorAll('[role="dialog"]')];
                if (dialogs.length === 0) return null;
                const dialog = dialogs[dialogs.length - 1]; // Lấy Modal trên cùng
                
                const tabs = [...dialog.querySelectorAll('[role="tab"]')];
                const res = {};
                tabs.forEach(tab => {
                    const aria = tab.getAttribute('aria-label');
                    if (aria) res[aria] = tab.innerText || "";
                });
                
                // Đóng Modal để không lỗi bài sau
                const closeBtn = dialog.querySelector('[aria-label="Đóng"], [aria-label="Close"], [aria-label="Đóng bảng chi tiết cảm xúc"]');
                if (closeBtn) closeBtn.click();
                
                return res;
            }""")
            
            # Đảm bảo đóng bằng phím cứng (Escape) để không che khuất bài sau
            page.keyboard.press("Escape")
            time.sleep(1) # Chờ Modal đóng
            
            if modal_data:
                counts = {"like": 0, "love": 0, "haha": 0, "wow": 0, "sad": 0, "angry": 0, "care": 0}
                for aria_label, inner_text in modal_data.items():
                    ll = aria_label.lower()
                    val = 0
                    m = re.search(r"([\d.,]+)", inner_text)
                    if m:
                        val = parse_count(m.group(1))
                    else:
                        m2 = re.search(r"([\d.,]+)", aria_label)
                        if m2:
                            val = parse_count(m2.group(1))
                            
                    for vn, key in reaction_map.items():
                        if vn in ll:
                            counts[key] = max(counts[key], val)
                            break
    except Exception as e:
        print(f"  [!] Lỗi khi xử lý Modal: {e}")
        
    return counts

def extract_post_data(page, post_element):
    """Trích xuất và gộp tất cả dữ liệu bài viết vào một Dict"""
    data = {}
    
    # 1. URL và ID
    url = page.evaluate("""(el) => {
        const links = [...el.querySelectorAll('a[href]')];
        for (const pattern of ['/posts/', 'pfbid', 'story_fbid']) {
            const a = links.find(a => a.href.includes(pattern));
            if (a) return a.href.split('?')[0];
        }
        // Xử lý bài đăng dạng Ảnh (Troll Bóng Đá rất hay dùng dạng này)
        const photo = links.find(a => a.href.includes('/photo/'));
        if (photo) {
            const m = photo.href.match(/set=(pcb\.[^&]+)/);
            if (m) {
                const base = photo.href.split('/photo/')[0];
                return base + '/posts/' + m[1];
            }
            return photo.href.split('?')[0];
        }
        return null;
    }""", post_element)
    
    data['post_url'] = url
    data['post_id'] = url.split('/')[-1] if url else f"temp_{int(time.time()*1000)}"
    data['feedback_id'] = f"feedback:{data['post_id']}"
    
    # 2. Mở rộng "Xem thêm"
    try:
        post_element.evaluate("""(el) => {
            el.querySelectorAll('[role="button"]').forEach(btn => {
                const t = (btn.innerText || '').trim();
                if (['Xem thêm','See more','See More'].includes(t)) btn.click();
            });
        }""")
        time.sleep(0.5)
    except:
        pass
        
    # 3. Content (Loại bỏ ảnh)
    data['post_content'] = post_element.evaluate("""(el) => {
        const container = el.querySelector('[data-ad-rendering-role="story_message"]') ||
                          el.querySelector('[data-ad-comet-preview="message"]') ||
                          el.querySelector('[data-ad-preview="message"]');
        let nodes = [];
        if (container) {
            nodes = [...container.querySelectorAll('[dir="auto"]')];
        } else {
            // Lọc các thẻ dir="auto" KHÔNG nằm trong bình luận (ul, form)
            nodes = [...el.querySelectorAll('[dir="auto"]')].filter(n => !n.closest('ul') && !n.closest('form'));
        }
        const parts = [];
        nodes.forEach(n => {
            const clone = n.cloneNode(true);
            clone.querySelectorAll('[role="button"], svg, img').forEach(e => e.remove());
            const t = clone.innerText.trim();
            if (t && t.length >= 3) parts.push(t);
        });
        const unique = [...new Set(parts)];
        unique.sort((a, b) => b.length - a.length);
        return unique.slice(0, 3).join('\\n').trim();
    }""")
    
    # 4. Thời gian đăng bài (Vá lỗi None)
    ts_str = post_element.evaluate("""(el) => {
        const abbr = el.querySelector('abbr[data-utime]');
        if (abbr) return abbr.getAttribute('data-utime') || abbr.getAttribute('title');
        
        const sels = ['a[href*="/posts/"]','a[href*="pfbid"]','a[href*="story_fbid"]','a[href*="/reel/"]','a[href*="/photo/"]'];
        for (const s of sels) {
            const a = el.querySelector(s);
            if (a) {
                const lbl = a.getAttribute('aria-label');
                if (lbl && lbl.length > 2) return lbl;
            }
        }
        for (const span of el.querySelectorAll('span')) {
            const t = (span.innerText || '').trim();
            if (t.length < 25 && /giờ|phút|ngày|hôm|tháng|yesterday|hour|min|ago/i.test(t))
                return t;
        }
        return null;
    }""")
    data['creation_time'] = parse_facebook_time(ts_str) if ts_str else int(time.time())
    
    # 5. Shares & Comments
    share_str = post_element.evaluate("""(el) => {
        const spans = [...el.querySelectorAll('div[role="button"] span, span')];
        for (const s of spans) {
            const t = (s.innerText || '').trim();
            const m = t.match(/^([\d.,]+[KkMm]?)\s*(chia sẻ|shares?)$/i);
            if (m) return m[1];
        }
        return '0';
    }""")
    data['share_count'] = parse_count(share_str)
    
    comment_str = post_element.evaluate("""(el) => {
        const spans = [...el.querySelectorAll('div[role="button"] span, span')];
        for (const s of spans) {
            const t = (s.innerText || '').trim();
            const m = t.match(/^([\d.,]+[KkMm]?)\s*(bình luận|comments?)$/i);
            if (m) return m[1];
        }
        return '0';
    }""")
    data['comment_count'] = parse_count(comment_str)
    
    # 6. Reactions và Data Integrity Check
    data['reactions_detail'] = get_reactions_detail(page, post_element)
    sum_details = sum(data['reactions_detail'].values())
    
    total_disp_str = post_element.evaluate("""(el) => {
        const spans = [...el.querySelectorAll('span[dir="auto"]')];
        for (const s of spans) {
            const t = s.innerText;
            if (t && /^[\d.,]+[KkMmBb]?$/.test(t)) return t;
        }
        return '0';
    }""")
    total_disp = parse_count(total_disp_str)
    
    # Logic kiểm tra toàn vẹn (Validation): Lấy tổng của detail nếu nó khác biệt
    data['total_reactions'] = sum_details if sum_details > 0 else total_disp
    
    if data['total_reactions'] != total_disp and sum_details > 0:
        print(f"      [Validation] Cập nhật tổng Reaction: Hiển thị ({total_disp}) -> Thực tế ({sum_details})")
    
    return data

def main():
    save_dir = os.path.join('data', 'json-targeted-crawl')
    os.makedirs(save_dir, exist_ok=True)
    
    print("Khởi động Playwright kết nối CDP...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            
            # Mở tab mới hoặc lấy tab hiện tại
            page = next((pg for pg in context.pages if "facebook.com" in pg.url), None)
            if not page:
                page = context.new_page()

            # Lặp qua từng Page trong danh sách TARGET_PAGES
            for target_url in TARGET_PAGES:
                print(f"\n=============================================")
                print(f"ĐANG TRUY CẬP TRANG: {target_url}")
                page.goto(target_url)
                time.sleep(5) # Đợi trang load hoàn toàn
                
                print(f"-> URL thực tế sau khi load: {page.url}")
                if "search" in page.url or page.url == "https://www.facebook.com/" or "home" in page.url.lower():
                    print("[!] CẢNH BÁO: Trình duyệt bị chuyển hướng. Kiểm tra URL hoặc trạng thái đăng nhập!")
                
                # Trích xuất Page Name và Followers
                page_info = page.evaluate("""() => {
                    const h1s = [...document.querySelectorAll('h1')].map(e => e.innerText.trim());
                    const h1 = h1s.find(t => t && t !== 'Chats' && t !== 'Facebook');
                    const name = h1 || document.title.split('|')[0].trim();
                    return { name };
                }""")
                
                page_name = page_info['name']
                
                # Tìm số follower CHÍNH XÁC trong ruột HTML (chống bị làm tròn 3K7)
                html_content = page.content()
                exact_followers = 0
                
                # Danh sách các Regex bóc tách từ JSON ẩn của Facebook
                patterns = [
                    r'"follower_count"\s*:\s*(\d+)',
                    r'"page_followers"\s*:\s*\{\s*"count"\s*:\s*(\d+)',
                    r'"subscribe_count"\s*:\s*(\d+)',
                    r'follower_count\s*:\s*(\d+)',
                    r'"follower_count_string"\s*:\s*"([\d.,]+)"'
                ]
                
                for p in patterns:
                    match_fol = re.search(p, html_content)
                    if match_fol:
                        try:
                            # Xử lý trường hợp chuỗi chứa dấu phẩy/chấm
                            raw_val = match_fol.group(1).replace(',', '').replace('.', '')
                            exact_followers = int(raw_val)
                            break
                        except:
                            continue
                            
                if exact_followers > 0:
                    page_followers = exact_followers
                else:
                    # Fallback quét text nếu không tìm thấy trong JSON (sẽ bị làm tròn)
                    followers_text = page.evaluate("""() => {
                        const els = [...document.querySelectorAll('a, span')];
                        for (const e of els) {
                            const t = (e.innerText || '').toLowerCase();
                            if (t.includes('người theo dõi') || t.includes('followers')) {
                                const m = t.match(/([\d.,]+\s*[kkmbb]?)\s*(người theo dõi|followers|follower)/);
                                if (m) return m[1];
                            }
                        }
                        return "0";
                    }""")
                    page_followers = parse_count(followers_text)
                
                clean_page_name = "".join([c if c.isalnum() else "_" for c in page_name]).strip("_")
                json_file = os.path.join(save_dir, f"posts_{clean_page_name}.json")
                
                seen_urls = set()
                saved_data = []
                
                # Nạp file JSON cũ để tăng tốc cào (Incremental)
                if os.path.exists(json_file):
                    with open(json_file, 'r', encoding='utf-8') as f:
                        try:
                            saved_data = json.load(f)
                            for item in saved_data:
                                if item.get('post_url'):
                                    seen_urls.add(item['post_url'])
                        except json.JSONDecodeError:
                            pass
                            
                print(f"Domain: {page_name} | Người theo dõi: {page_followers}")
                print(f"Đã tải {len(saved_data)} bài viết từ {json_file}")
                
                collected = 0
                consecutive_old = 0
                processed_count = 0
                seen_y = set()
                
                while collected < TARGET_POSTS:
                    # Lọc DOM qua nút Share để xác định chính xác block bài viết (vượt qua Skeleton)
                    share_btns = page.query_selector_all('[data-ad-rendering-role="share_button"]')
                    
                    posts = []
                    for btn in share_btns:
                        post_handle = page.evaluate_handle("""(btn) => {
                            let el = btn;
                            for (let i = 0; i < 30; i++) {
                                el = el.parentElement;
                                if (!el) return null;
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 400 && rect.height > 150) return el;
                            }
                            return null;
                        }""", btn)
                        if post_handle:
                            posts.append(post_handle)
                    
                    for post_el in posts:
                        try:
                            bbox = post_el.bounding_box()
                            if not bbox or bbox["width"] < 400 or bbox["height"] < 150:
                                continue

                            key = round(bbox["y"] / 5) * 5
                            if key in seen_y:
                                continue
                            
                            # Facebook hiện tại giấu thẻ a[href] trên một số tài khoản.
                            # Không bắt buộc phải có link (Xử lý các block bài viết ẩn URL)
                            
                            # Cố gắng lấy URL, nếu không có thì gán None
                            try:
                                has_link = post_el.evaluate("""(el) => {
                                    return !![...el.querySelectorAll('a[href]')].find(a =>
                                        a.href.includes('/posts/')   ||
                                        a.href.includes('pfbid')     ||
                                        a.href.includes('story_fbid')||
                                        a.href.includes('/reel/')    ||
                                        a.href.includes('/videos/')  ||
                                        a.href.includes('/photo/')
                                    );
                                }""")
                            except:
                                has_link = False
                                
                            # CHỈ ĐÁNH DẤU ĐÃ XEM KHI ĐÂY LÀ POST THẬT
                            seen_y.add(key)
                            
                            processed_count += 1
                            
                            # 1. Bỏ qua Shared, Reels, Videos
                            valid_status = check_valid_post(post_el)
                            if valid_status != "OK":
                                print(f"  {processed_count}. [Bỏ qua]: {valid_status}")
                                continue
                                
                            post_data = extract_post_data(page, post_el)
                            
                            # Bỏ qua trùng lặp bằng Content nếu không có URL
                            post_content = post_data.get('post_content', '')
                            content_hash = hash(post_content[:50]) if post_content else None
                            
                            if not post_data['post_url'] and not post_content:
                                print(f"  {processed_count}. [Bỏ qua]: Bài viết trống (Không URL, Không nội dung)")
                                continue
                                
                            text_preview = post_content[:40].replace('\n', ' ') + "..." if post_content else "Không có chữ"
                            is_dup = False
                            if post_data['post_url'] and post_data['post_url'] in seen_urls:
                                is_dup = True
                            elif not post_data['post_url'] and content_hash in seen_urls:
                                is_dup = True
                                
                            if is_dup:
                                print(f"  {processed_count}. [Bỏ qua]: Đã quét ở lần cuộn trước (Text: {text_preview})")
                                continue
                                
                            if post_data['post_url']:
                                seen_urls.add(post_data['post_url'])
                            if content_hash:
                                seen_urls.add(content_hash)
                                
                            # Gán metadata từ page
                            post_data['page_name'] = page_name
                            post_data['page_followers'] = page_followers
                            
                            # 2. Bộ lọc Thời gian
                            c_time = post_data['creation_time']
                            if c_time is not None:
                                if c_time > END_TIME:
                                    print(f"  {processed_count}. [Bỏ qua]: Bài quá MỚI (Text: {text_preview})")
                                    continue
                                    
                                if c_time < START_TIME:
                                    print(f"  {processed_count}. [Bỏ qua]: Bài quá CŨ (Text: {text_preview})")
                                    consecutive_old += 1
                                    if consecutive_old >= 3:
                                        print(f"  [Bẫy Bài Ghim] Gặp 3 bài viết cũ liên tiếp. Đã duyệt hết tháng 1/2026.")
                                        collected = TARGET_POSTS # Kích hoạt thoát while
                                        break
                                    continue
                                else:
                                    consecutive_old = 0
                                
                            # 3. Bộ lọc Nhiễu thống kê
                            if post_data['total_reactions'] < MIN_REACTIONS:
                                print(f"  {processed_count}. [Bỏ qua]: Tương tác thấp ({post_data['total_reactions']} < {MIN_REACTIONS}) - (Text: {text_preview})")
                                continue
                                
                            # 4. Lưu trữ Real-time
                            saved_data.append(post_data)
                            seen_urls.add(post_data['post_url'])
                            collected += 1
                            
                            print(f"  {processed_count}. [THÀNH CÔNG {collected}/{TARGET_POSTS}]: {post_data['post_url']} ({post_data['total_reactions']} react)")
                            
                            with open(json_file, 'w', encoding='utf-8') as f:
                                json.dump(saved_data, f, ensure_ascii=False, indent=4)
                                
                            if collected >= TARGET_POSTS:
                                break
                        except Exception as e:
                            continue
                            
                    human_scroll(page)
                    time.sleep(2)
                    
                print(f"XONG TRANG: {page_name}. File lưu tại: {json_file}")
            
            print(f"\n=============================================")
            print("ĐÃ THU THẬP XONG TOÀN BỘ DANH SÁCH TARGET_PAGES!")
            
        except Exception as e:
            print(f"Lỗi CDP Playwright: {e}")

if __name__ == "__main__":
    main()

#!/bin/bash

# ============================================================
# FACEBOOK MULTIPAGE ROUND-ROBIN SUPERVISOR V9.3.2 - TEAM
# ============================================================
# Chạy theo người bằng biến môi trường CRAWL_OWNER:
#   phuc | han | nhung | yen | all
#
# Ví dụ:
#   CRAWL_OWNER=phuc caffeinate -dimsu ./run_facebook_multipage_v9_3_2.sh
#   CRAWL_OWNER=han  caffeinate -dimsu ./run_facebook_multipage_v9_3_2.sh
# ============================================================

PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
CHROME_BIN="${CHROME_BIN:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
CHROME_PROFILE="${CHROME_PROFILE:-$HOME/chrome-cdp-fb}"

CRAWLER_FILE="src/facebook_crawler_multipage_v9_3_2_team_pages.py"
PAGE_NAME="multipage_v9_3_2_${CRAWL_OWNER:-all}"

# Nghỉ giữa các vòng full-cycle. Mac 8GB nên để 5-8 phút.
REST_SECONDS="${REST_SECONDS:-420}"

# Đổi về 0 nếu muốn chạy hoài đến khi Ctrl+C.
STOP_AT_TARGET="${STOP_AT_TARGET:-1}"

CRAWL_OWNER="${CRAWL_OWNER:-all}"
export CRAWL_OWNER

cd "$PROJECT_DIR" || exit 1

if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

mkdir -p logs

echo "[$(date '+%d/%m/%Y - %H:%M:%S')] V9.3.2 supervisor | owner=$CRAWL_OWNER"
echo "[$(date '+%d/%m/%Y - %H:%M:%S')] Preflight compile check..."
python -m py_compile "$CRAWLER_FILE"
if [ $? -ne 0 ]; then
  echo "[$(date '+%d/%m/%Y - %H:%M:%S')] ERROR: Python compile failed. Stop supervisor."
  exit 1
fi

TARGET_JSONS=()

add_target() {
  TARGET_JSONS+=("$1:$2")
}

case "$CRAWL_OWNER" in
  phuc|p|phúc)
    add_target "data/json-yannews-chunk-v1/posts_YAN_News.json" 1000
    add_target "data/json-vnexpress-multipage-v7/posts_VnExpress_net.json" 1000
    add_target "data/json-dantri-multipage-v7/posts_Dantri.json" 1000
    add_target "data/json-vtv24-multipage-v7/posts_Tin_tuc_VTV24.json" 1000
    ;;
  han|hân)
    add_target "data/json-han-kenh14-v9-3-2/posts_Kenh14_vn.json" 1000
    add_target "data/json-han-theanh28-v9-3-2/posts_Theanh28_Entertainment.json" 1000
    add_target "data/json-han-nguoilaodong-v9-3-2/posts_Nguoi_Lao_Dong.json" 1000
    add_target "data/json-han-daiphatthanh-sound-v9-3-2/posts_Dai_Phat_Thanh_Sound.json" 1000
    ;;
  nhung)
    add_target "data/json-nhung-thongtinchinhphu-v9-3-2/posts_Thong_tin_Chinh_phu.json" 1000
    add_target "data/json-nhung-tuoitre-v9-3-2/posts_Tuoi_Tre.json" 1000
    add_target "data/json-nhung-tintuccand-v9-3-2/posts_Tin_tuc_CAND.json" 1000
    add_target "data/json-nhung-daibieunhandan-v9-3-2/posts_Dai_bieu_Nhan_dan.json" 1000
    ;;
  yen|yến)
    add_target "data/json-yen-schannel-v9-3-2/posts_Schannel.json" 1000
    add_target "data/json-yen-vietnamnet-v9-3-2/posts_Vietnamnet_vn.json" 1000
    add_target "data/json-yen-cafebiz-v9-3-2/posts_CafeBiz.json" 1000
    add_target "data/json-yen-weibovietnam-v9-3-2/posts_Weibo_Vietnam.json" 1000
    ;;
  all|team|"")
    add_target "data/json-yannews-chunk-v1/posts_YAN_News.json" 1000
    add_target "data/json-vnexpress-multipage-v7/posts_VnExpress_net.json" 1000
    add_target "data/json-dantri-multipage-v7/posts_Dantri.json" 1000
    add_target "data/json-vtv24-multipage-v7/posts_Tin_tuc_VTV24.json" 1000
    add_target "data/json-han-kenh14-v9-3-2/posts_Kenh14_vn.json" 1000
    add_target "data/json-han-theanh28-v9-3-2/posts_Theanh28_Entertainment.json" 1000
    add_target "data/json-han-nguoilaodong-v9-3-2/posts_Nguoi_Lao_Dong.json" 1000
    add_target "data/json-han-daiphatthanh-sound-v9-3-2/posts_Dai_Phat_Thanh_Sound.json" 1000
    add_target "data/json-nhung-thongtinchinhphu-v9-3-2/posts_Thong_tin_Chinh_phu.json" 1000
    add_target "data/json-nhung-tuoitre-v9-3-2/posts_Tuoi_Tre.json" 1000
    add_target "data/json-nhung-tintuccand-v9-3-2/posts_Tin_tuc_CAND.json" 1000
    add_target "data/json-nhung-daibieunhandan-v9-3-2/posts_Dai_bieu_Nhan_dan.json" 1000
    add_target "data/json-yen-schannel-v9-3-2/posts_Schannel.json" 1000
    add_target "data/json-yen-vietnamnet-v9-3-2/posts_Vietnamnet_vn.json" 1000
    add_target "data/json-yen-cafebiz-v9-3-2/posts_CafeBiz.json" 1000
    add_target "data/json-yen-weibovietnam-v9-3-2/posts_Weibo_Vietnam.json" 1000
    ;;
  *)
    echo "[$(date '+%d/%m/%Y - %H:%M:%S')] ERROR: CRAWL_OWNER không hợp lệ: $CRAWL_OWNER"
    echo "Hợp lệ: phuc | han | nhung | yen | all"
    exit 1
    ;;
esac

count_file_records() {
python - "$1" <<'PY'
import json, os, sys
p = sys.argv[1]
if not os.path.exists(p):
    print(0)
else:
    try:
        data = json.load(open(p, "r", encoding="utf-8"))
        print(len(data) if isinstance(data, list) else 0)
    except Exception:
        print(0)
PY
}

all_targets_done() {
  local done_count=0
  local total_count=${#TARGET_JSONS[@]}

  for item in "${TARGET_JSONS[@]}"; do
    local path="${item%%:*}"
    local target="${item##*:}"
    local count=$(count_file_records "$path")
    echo "[$(date '+%d/%m/%Y - %H:%M:%S')] $path: $count/$target"
    if [ "$count" -ge "$target" ]; then
      done_count=$((done_count + 1))
    fi
  done

  [ "$done_count" -eq "$total_count" ]
}

close_chrome_debug() {
  pkill -f "remote-debugging-port=9222" >/dev/null 2>&1 || true
  pkill -f "chrome-cdp-fb" >/dev/null 2>&1 || true
  sleep 4
}

open_chrome_debug() {
  "$CHROME_BIN" \
    --remote-debugging-port=9222 \
    --user-data-dir="$CHROME_PROFILE" \
    --disable-background-timer-throttling \
    --disable-renderer-backgrounding \
    --disable-features=CalculateNativeWinOcclusion \
    >/tmp/chrome_cdp_fb.log 2>&1 &
  sleep 14
}

echo "[$(date '+%d/%m/%Y - %H:%M:%S')] Start supervisor."
echo "[$(date '+%d/%m/%Y - %H:%M:%S')] Project: $PROJECT_DIR"

while true; do
  echo "[$(date '+%d/%m/%Y - %H:%M:%S')] Current progress:"
  if all_targets_done && [ "$STOP_AT_TARGET" = "1" ]; then
    echo "[$(date '+%d/%m/%Y - %H:%M:%S')] DONE: all target files reached target."
    break
  fi

  echo "[$(date '+%d/%m/%Y - %H:%M:%S')] Restart Chrome Debug..."
  close_chrome_debug
  open_chrome_debug

  TS=$(date +%Y%m%d_%H%M%S)
  LOG_FILE="logs/fb_${PAGE_NAME}_${TS}.txt"

  echo "[$(date '+%d/%m/%Y - %H:%M:%S')] Run crawler. Log: $LOG_FILE"
  python -u "$CRAWLER_FILE" 2>&1 | tee "$LOG_FILE"

  echo "[$(date '+%d/%m/%Y - %H:%M:%S')] Cycle ended. Progress:"
  all_targets_done

  if all_targets_done && [ "$STOP_AT_TARGET" = "1" ]; then
    echo "[$(date '+%d/%m/%Y - %H:%M:%S')] DONE after cycle."
    close_chrome_debug
    break
  fi

  echo "[$(date '+%d/%m/%Y - %H:%M:%S')] Close Chrome Debug and rest ${REST_SECONDS}s..."
  close_chrome_debug
  sleep "$REST_SECONDS"
done

echo "[$(date '+%d/%m/%Y - %H:%M:%S')] Supervisor stopped."

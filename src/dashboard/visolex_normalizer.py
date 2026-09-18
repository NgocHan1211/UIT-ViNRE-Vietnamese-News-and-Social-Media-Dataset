"""
visolex_normalizer.py
----------------------
Module tích hợp NHẸ của ViSoLex (https://github.com/HaDung2002/visolex) vào Streamlit.

Chỉ sử dụng phần `dict/dictionary.json` của ViSoLex (NSW Lookup) — KHÔNG cần
GPU, KHÔNG cần torch/transformers, KHÔNG cần checkpoint mô hình.
Đây là cách triển khai khả thi để chạy trên Streamlit Cloud / server thường.

Nếu sau này muốn nâng cấp lên chuẩn hoá theo ngữ cảnh bằng ViSoBERT/BARTpho
(độ chính xác cao hơn nhưng cần >=12GB GPU RAM), nên tách thành một service
riêng (FastAPI/Flask) và gọi qua HTTP từ dashboard này, thay vì load model
trực tiếp trong tiến trình Streamlit.

Cách lấy file dictionary.json:
    git clone --depth 1 https://github.com/HaDung2002/visolex.git
    cp visolex/dict/dictionary.json <project>/data/visolex_dictionary.json
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

import streamlit as st

# Đường dẫn mặc định tới file dictionary đã copy từ repo ViSoLex
DEFAULT_DICT_PATH = Path(__file__).parent / "data" / "visolex_dictionary.json"

# Regex tách từ tiếng Việt (giữ dấu) và dấu câu riêng
_TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ỹà-ỹ]+|[^\sA-Za-zÀ-ỹà-ỹ0-9]+", re.UNICODE)


# Danh sách các từ tiếng Việt chuẩn phổ biến bị gán sai nhãn/chuẩn hoá sai trong từ điển ViSoLex gốc
STANDARD_WORDS_BLACKLIST = {
    "là", "trong", "khi", "nam", "an", "làm", "sau", "gia", "nhân", "thể", "đầu", "hà", "trung", 
    "đang", "định", "còn", "quan", "nhưng", "hàng", "qua", "điều", "tuổi", "lên", "viên", "đường", 
    "thực", "giá", "đây", "tự", "minh", "thì", "lực", "nay", "do", "bà", "tới", "ai", "ăn", "tịch", 
    "sử", "thương", "nên", "phương", "thu", "chị", "ý", "quy", "chiến", "vi", "bất", "kỳ", "pháp", 
    "mang", "giả", "giữ", "ngay", "trai", "quyết", "vị", "diện", "danh", "ban", "gì", "đặc", "sở", 
    "khác", "cái", "tối", "thi", "trang", "tra", "kiến", "mở", "biểu", "cá", "chuyên", "chi", "dài", 
    "tư", "hải", "tìm", "mắt", "đàn", "thay", "nhiệm", "cuối", "mức", "chế", "đẹp", "nghỉ",
    "yêu", "nhiều", "lần", "mới", "hiểu", "ra", "được", "dưới", "khuyên", "có", "hơi", "phũ", 
    "chạm", "lòng", "ngã", "tôi", "hoặc", "quanh", "ngày", "đêm", "học", "sinh", "chết", "con", 
    "mẹ", "thế", "này", "kia", "sao", "cho", "với", "về", "đã", "mọi", "thứ", "cuộc", "sống", 
    "người", "bạn", "xung", "quanh", "đều", "phũ phàng", "tự ái", "bè", "dây", "tử", "những", 
    "xứng", "chó", "chú", "chúa", "chút", "chưa", "chờ", "chơi", "bình thường", "vui vẻ", "vui"
}


@st.cache_data(show_spinner="Đang tải từ điển ViSoLex...")
def load_visolex_dictionary(dict_path: str | Path = DEFAULT_DICT_PATH) -> dict:
    """Tải dictionary.json của ViSoLex, cache lại để không đọc lại mỗi lần rerun."""
    path = Path(dict_path)
    if not path.exists():
        st.error(
            f"Không tìm thấy file dictionary tại `{path}`.\n\n"
            "Hãy tải về từ repo ViSoLex: "
            "`git clone --depth 1 https://github.com/HaDung2002/visolex.git` "
            "rồi copy `visolex/dict/dictionary.json` vào đúng đường dẫn trên."
        )
        return {}
    with open(path, encoding="utf-8") as f:
        raw_dict = json.load(f)
        # Lọc bỏ các từ tiếng Việt chuẩn bị gán nhãn sai
        return {k: v for k, v in raw_dict.items() if k.lower() not in STANDARD_WORDS_BLACKLIST}


def tokenize(text: str) -> list[str]:
    """Tách câu thành token (giữ nguyên dấu câu như token riêng)."""
    return _TOKEN_RE.findall(text)


def lookup_nsw(word: str, dictionary: dict) -> Optional[dict]:
    """
    Tra một từ trong dictionary ViSoLex.
    Trả về {"candidates": [...], "details": [...]} hoặc None nếu không có.
    """
    entry = dictionary.get(word.lower())
    if not entry or not isinstance(entry, dict):
        return None

    candidates = entry.get("normalized", []) or []
    resp = entry.get("response", {})
    
    details = []
    if isinstance(resp, dict):
        details_val = resp.get("normalized")
        if isinstance(details_val, dict):
            details = [details_val]
        elif isinstance(details_val, list):
            details = details_val
        else:
            # Handle cases like "ko" where response is nested under the word key
            word_val = resp.get(word.lower())
            if isinstance(word_val, dict):
                details_val2 = word_val.get("normalized")
                if isinstance(details_val2, list):
                    details = details_val2
                elif isinstance(details_val2, dict):
                    details = [details_val2]
    elif isinstance(resp, list):
        for item in resp:
            if isinstance(item, dict):
                d_val = item.get("normalized")
                if isinstance(d_val, dict):
                    details.append(d_val)
                elif isinstance(d_val, list):
                    details.extend(d_val)
                    
    return {"candidates": candidates, "details": details}


def normalize_sentence(text: str, dictionary: dict) -> tuple[str, list[dict]]:
    """
    Chuẩn hoá một câu: thay mỗi từ NSW bằng ứng viên đầu tiên trong dictionary.
    Trả về (câu_đã_chuẩn_hoá, danh_sách_nsw_phát_hiện).

    Lưu ý: đây là cách tra cứu trực tiếp (rule/dictionary-based), KHÔNG xét
    ngữ cảnh câu như mô hình ViSoBERT/BARTpho — với từ đa nghĩa (vd "t" có thể
    là "tôi"/"tao"/"tới"...) sẽ luôn chọn ứng viên đầu tiên trong dict.
    """
    tokens = tokenize(text)
    normalized_tokens: list[str] = []
    nsw_found: list[dict] = []

    for tok in tokens:
        # Bỏ qua các từ viết hoa chữ đầu hoặc viết hoa toàn bộ (thường là danh từ riêng hoặc từ chuẩn viết hoa)
        # Ngoại trừ các từ teencode/viết tắt cực kỳ phổ biến đứng đầu câu
        if (tok.istitle() or tok.isupper()) and tok.lower() not in ["ko", "đc", "k", "h", "t", "mk"]:
            normalized_tokens.append(tok)
            continue

        result = lookup_nsw(tok, dictionary)
        if result and result["candidates"]:
            normalized_tokens.append(result["candidates"][0])
            nsw_found.append({"original": tok, "candidates": result["candidates"]})
        else:
            normalized_tokens.append(tok)

    normalized_text = " ".join(normalized_tokens)
    # Dọn khoảng trắng trước dấu câu: "đẹp ." -> "đẹp."
    normalized_text = re.sub(r"\s+([.,!?;:])", r"\1", normalized_text)
    return normalized_text, nsw_found

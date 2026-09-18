"""
label_map.py
============
Bảng nhãn chính thức — nguồn duy nhất (Single Source of Truth) cho toàn pipeline.
Import file này trong create_pilot_dataset.py và validate_pilot.py để đảm bảo
nhất quán khi Guideline được cập nhật (v3.x → v3.y).

Taxonomy: 18 nhãn (T01–T18) theo Annotation Guideline N2.1
Source Type: Phân loại 6 nhóm nguồn theo chiến lược lấy mẫu phân tầng Tầng 1
"""

# ── TAXONOMY LABELS (T01 – T18) ─────────────────────────────────────────────
# Cập nhật nhãn tại đây khi Guideline thay đổi phiên bản.

LABEL_MAP: dict[str, str] = {
    "T01": "POLITICS_GOVERNMENT",       # Chính trị, chính sách, hoạt động nhà nước, đảng
    "T02": "INTERNATIONAL",             # Quan hệ ngoại giao, tin tức quốc tế, sự kiện nước ngoài
    "T03": "ECONOMY_BUSINESS",          # Kinh tế vĩ mô, doanh nghiệp, thị trường, tài chính
    "T04": "SOCIETY",                   # Vấn đề xã hội, chính sách dân sinh, đời sống cộng đồng
    "T05": "LAW_CRIME",                 # Pháp luật, tội phạm, khởi tố, xét xử, bắt giữ
    "T06": "HEALTH",                    # Y tế, sức khỏe, dịch bệnh, thuốc, bệnh viện
    "T07": "EDUCATION",                 # Giáo dục, tuyển sinh, học đường, nghiên cứu
    "T08": "TECHNOLOGY_SCIENCE",        # Công nghệ, AI, khoa học, đổi mới sáng tạo
    "T09": "ENVIRONMENT",               # Môi trường, biến đổi khí hậu, năng lượng tái tạo
    "T10": "WEATHER_DISASTER",          # Thời tiết, thiên tai, bão lũ, sạt lở
    "T11": "SPORTS",                    # Thể thao, giải đấu, kết quả thi đấu
    "T12": "ENTERTAINMENT",             # Giải trí, showbiz, phim ảnh, âm nhạc, nghệ sĩ
    "T13": "LIFESTYLE",                 # Ẩm thực, du lịch, thời trang, làm đẹp, review
    "T14": "HUMAN_INTEREST",            # Câu chuyện cảm động, nghị lực, hy sinh cá nhân
    "T15": "LABOR_EMPLOYMENT",          # Việc làm, lao động, lương, bảo hiểm xã hội
    "T16": "TRAFFIC_TRANSPORT",         # Giao thông, tai nạn, hạ tầng, phương tiện
    "T17": "REAL_ESTATE_CONSTRUCTION",  # Bất động sản, nhà ở, xây dựng, quy hoạch
    "T18": "OTHER_UNCLEAR",             # Không đủ ngữ cảnh / không khớp nhãn nào / caption quá ngắn
}

# Chiều ngược: tên nhãn → mã ID
LABEL_NAME_TO_ID: dict[str, str] = {v: k for k, v in LABEL_MAP.items()}

# Danh sách tên nhãn (dùng cho Data Validation trên Google Sheets)
VALID_LABEL_NAMES: list[str] = list(LABEL_MAP.values())

# Danh sách mã ID (dùng cho dropdown ID)
VALID_LABEL_IDS: list[str] = list(LABEL_MAP.keys())


# ── SOURCE TYPE MAPPING ──────────────────────────────────────────────────────
# Phân loại 3 nhóm nguồn theo tỷ lệ đề xuất:
#   Báo điện tử | Entertainment news | Other

SOURCE_TYPE_MAP: dict[str, str] = {
    # ── Báo điện tử chính thống ─────────────────────────────────────────────
    "Thông tin Chính phủ":                           "Báo điện tử",
    "Đại biểu Nhân dân":                             "Báo điện tử",
    "Dân trí":                                       "Báo điện tử",
    "Tuổi Trẻ":                                      "Báo điện tử",
    "VnExpress.net":                                 "Báo điện tử",
    "Vietnamnet.vn":                                 "Báo điện tử",
    "Người Lao Động":                                "Báo điện tử",
    "CafeBiz":                                       "Báo điện tử",
    "Tin tức VTV24":                                 "Báo điện tử",
    "Tin tức CAND":                                  "Báo điện tử",
    "Cục Cảnh sát điều tra tội phạm về ma tuý":     "Báo điện tử",

    # ── Entertainment news ──────────────────────────────────────────────────
    "Kenh14.vn":                                     "Entertainment news",
    "Schannel":                                      "Entertainment news",
    "Theanh28 Entertainment":                        "Entertainment news",
    "YAN News":                                      "Entertainment news",
    "Weibo Việt Nam":                                "Entertainment news",

    # ── Other ───────────────────────────────────────────────────────────────
    "Đài Phát Thanh.":                               "Other",
}

# Nhãn mặc định cho page chưa được map
DEFAULT_SOURCE_TYPE = "Other"

# Danh sách 3 loại nguồn hợp lệ
VALID_SOURCE_TYPES: list[str] = [
    "Báo điện tử",
    "Entertainment news",
    "Other",
]


# ── CONTENT LENGTH BUCKETS ───────────────────────────────────────────────────
# Phân loại độ dài theo chiến lược lấy mẫu Tầng 2

def get_length_bucket(word_count: int) -> str:
    """Trả về nhóm độ dài dựa theo số từ."""
    if word_count <= 5:
        return "Very Short (≤5w)"
    elif word_count <= 15:
        return "Short (6-15w)"
    elif word_count <= 50:
        return "Medium (16-50w)"
    else:
        return "Long (>50w)"

VALID_LENGTH_BUCKETS: list[str] = [
    "Very Short (≤5w)",
    "Short (6-15w)",
    "Medium (16-50w)",
    "Long (>50w)",
]

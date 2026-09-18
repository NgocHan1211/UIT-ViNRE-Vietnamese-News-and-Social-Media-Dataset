"""
create_pilot_dataset.py
=======================
Tạo tập Pilot 500 mẫu theo chiến lược lấy mẫu lai 4 nhóm:
  - Nhóm A: A_Random_Baseline (250 mẫu - 50%)
  - Nhóm B: B_Candidate_Coverage (180 mẫu - 36%)
  - Nhóm C: C_Boundary_Pairs (50 mẫu - 10%)
  - Nhóm D: D_Hard_Cases (20 mẫu - 4%)

Thứ tự lấy mẫu (khó trước, dễ/random sau) để tránh cạn kiệt candidate:
  Nhóm D (Hard cases) → Nhóm C (Boundary pairs) → Nhóm B (Candidate coverage) → Nhóm A (Random baseline)

Output:
  pilot_set.csv       — 500 rows, đầy đủ cột IAA và metadata
  pool_set.csv        — rows còn lại để huấn luyện/kiểm tra sau này
  pilot_ids.csv       — danh sách record_id + strata_label để anti-leakage
  pilot_report.txt    — báo cáo chi tiết phân bổ tầng, độ dài, nguồn tin
"""

import argparse
import os
import random
from collections import Counter
import pandas as pd

# Import bảng nhãn tập trung
try:
    from label_map import SOURCE_TYPE_MAP, DEFAULT_SOURCE_TYPE, get_length_bucket, LABEL_MAP
except ImportError:
    SOURCE_TYPE_MAP = {}
    DEFAULT_SOURCE_TYPE = "Other"
    def get_length_bucket(wc):
        if wc <= 5: return "Very Short (≤5w)"
        elif wc <= 15: return "Short (6-15w)"
        elif wc <= 50: return "Medium (16-50w)"
        else: return "Long (>50w)"
    LABEL_MAP = {}

# ── DEFAULT CONFIG ─────────────────────────────────────────────────────────────
INPUT_FILE    = "Annotation_Template_TeamCrawl.csv"
OUTPUT_DIR    = "."
RANDOM_SEED   = 42
TARGET_TOTAL  = 500

# ── IAA COLUMN SCHEMA ─────────────────────────────────────────────────────────
IAA_COLUMNS_ANNOTATOR = {
    "annotator_1_topic_label": "",
    "annotator_1_topic_id":    "",
    "annotator_1_note":        "",
    "annotator_2_topic_label": "",
    "annotator_2_topic_id":    "",
    "annotator_2_note":        "",
    "annotator_3_topic_label": "",
    "annotator_3_topic_id":    "",
    "annotator_3_note":        "",
    "flag_ambiguity":          0,
}

IAA_COLUMNS_ADJUDICATOR = {
    "is_disagreement":    "",
    "adjudicator_reason": "",
}

# ── 18-LABEL KEYWORDS (IPTC-based) ───────────────────────────────────────────
LABEL_KEYWORDS = {
    "T01": [
        "chính trị", "chính phủ", "nhà nước", "quốc hội", "thủ tướng",
        "chủ tịch nước", "bộ trưởng", "bộ ngành", "nghị quyết",
        "chính sách công", "quản lý nhà nước", "bầu cử", "bổ nhiệm",
        "miễn nhiệm", "ngoại giao", "UBND", "HĐND"
    ],
    "T02": [
        "quan hệ quốc tế", "ngoại giao", "hiệp ước", "trừng phạt", "viện trợ nước ngoài",
        "tổ chức quốc tế", "người tị nạn", "Mỹ", "Trung Quốc", "Nga",
        "Ukraine", "Israel", "Hàn Quốc", "Nhật Bản", "EU", "ASEAN",
        "Liên Hợp Quốc"
    ],
    "T03": [
        "kinh tế", "kinh doanh", "tài chính", "doanh nghiệp", "thị trường",
        "ngân hàng", "lãi suất", "tín dụng", "chứng khoán", "cổ phiếu",
        "trái phiếu", "vàng", "ngoại tệ", "tỷ giá", "đầu tư", "thuế",
        "thương mại", "xuất nhập khẩu", "giá xăng", "giá điện"
    ],
    "T04": [
        "xã hội", "cộng đồng", "dân sinh", "an sinh", "từ thiện", "quyên góp",
        "hoạt động xã hội", "chính sách xã hội", "gia đình", "kết hôn", "ly hôn",
        "trẻ em", "người già", "phụ nữ", "bình đẳng giới", "phát triển cộng đồng"
    ],
    "T05": [
        "tội phạm", "pháp luật", "tư pháp", "vi phạm pháp luật", "công an",
        "cảnh sát", "điều tra", "bắt giữ", "khởi tố", "truy tố", "xét xử",
        "tòa án", "bản án", "thi hành án", "xử phạt", "lừa đảo", "ma túy",
        "tham nhũng", "buôn lậu", "truy nã", "tạm giam"
    ],
    "T06": [
        "sức khỏe", "y tế", "bệnh", "bệnh viện", "bác sĩ", "bệnh nhân",
        "thuốc", "vaccine", "điều trị", "phòng bệnh", "xét nghiệm",
        "triệu chứng", "dinh dưỡng", "sức khỏe tinh thần", "y tế công cộng",
        "Bộ Y tế", "sốt xuất huyết", "cúm"
    ],
    "T07": [
        "giáo dục", "trường học", "học sinh", "sinh viên", "giáo viên",
        "giảng viên", "đại học", "tuyển sinh", "kỳ thi", "điểm thi",
        "điểm chuẩn", "học phí", "chương trình học", "sách giáo khoa",
        "đào tạo", "học nghề", "Bộ GD&ĐT", "thi tốt nghiệp THPT"
    ],
    "T08": [
        "khoa học", "công nghệ", "nghiên cứu khoa học", "phát minh",
        "khám phá", "AI", "trí tuệ nhân tạo", "robot", "phần mềm",
        "phần cứng", "máy tính", "điện thoại", "internet", "vi mạch",
        "bán dẫn", "vũ trụ", "tế bào", "gen", "công nghệ sinh học"
    ],
    "T09": [
        "môi trường", "biến đổi khí hậu", "nhiệt độ toàn cầu", "hiệu ứng nhà kính",
        "năng lượng tái tạo", "năng lượng xanh", "rác thải", "nhựa", "tái chế",
        "bảo tồn", "đa dạng sinh học", "phát thải", "carbon", "ô nhiễm",
        "nước sạch", "phá rừng"
    ],
    "T10": [
        "thời tiết", "dự báo", "nhiệt độ", "mưa", "nắng", "gió", "bão",
        "áp thấp", "không khí lạnh", "nóng", "lạnh", "độ ẩm", "sương mù",
        "triều cường", "thiên tai", "lũ lụt", "sạt lở", "động đất", "sóng thần",
        "hỏa hoạn", "cháy", "tai nạn", "cứu hộ", "cứu nạn", "thương vong",
        "thiệt hại", "sập cầu", "nổ", "đắm tàu", "rơi máy bay"
    ],
    "T11": [
        "thể thao", "bóng đá", "bóng rổ", "tennis", "cầu lông", "chạy bộ",
        "marathon", "olympic", "giải đấu", "trận đấu", "cầu thủ",
        "vận động viên", "huấn luyện viên", "cúp", "huy chương", "bàn thắng",
        "tỉ số"
    ],
    "T12": [
        "nghệ thuật", "văn hóa", "giải trí", "showbiz", "phim", "nhạc",
        "ca sĩ", "diễn viên", "nghệ sĩ", "concert", "album", "bài hát",
        "sách", "truyện", "triển lãm", "lễ hội", "sự kiện", "truyền hình",
        "rạp chiếu phim"
    ],
    "T13": [
        " ẩm thực", "du lịch", "thời trang", "làm đẹp", "mẹo", "review",
        "trải nghiệm", "xu hướng", "sống khỏe", "nấu ăn", "món ăn",
        "khách sạn", "resort", "điểm đến", "phối đồ", "skincare"
    ],
    "T14": [
        "nghị lực", "vượt khó", "cảm động", "tấm gương", "hy sinh",
        "hoàn cảnh", "câu chuyện", "kỳ tích", "nhân văn", "giúp đỡ",
        "chia sẻ", "tình người", "ấm áp"
    ],
    "T15": [
        "lao động", "việc làm", "tuyển dụng", "thất nghiệp", "lương",
        "thu nhập", "bảo hiểm xã hội", "sa thải", "công nhân", "nhân sự",
        "hợp đồng lao động", "công đoàn", "đình công"
    ],
    "T16": [
        "giao thông", "vận tải", "vận chuyển", "giao thông công cộng",
        "đường bộ", "đường sắt", "hàng không", "đường thủy", "taxi",
        "ride-hailing", "hạ tầng", "đường sá", "cầu", "cao tốc", "metro",
        "sân bay", "cảng", "phân luồng", "kẹt xe", "ùn tắc", "quy hoạch giao thông",
        "xe máy", "xe buýt", "vành đai", "quốc lộ", "BOT"
    ],
    "T17": [
        "bất động sản", "nhà đất", "chung cư", "nhà ở", "xây dựng",
        "quy hoạch", "dự án đô thị", "căn hộ", "đất nền", "môi giới"
    ],
    "T18": [
        "không rõ", "cập nhật", "xem thêm", "tại đây", "ai biết",
        "hot quá", "đỉnh thật", "ủa rồi sao", "mọi người chú ý",
        "cập nhật mới nhất"
    ]
}

BOUNDARY_PAIRS = [
    ("T04", "T14", "SOCIETY_vs_HUMAN_INTEREST"),
    ("T16", "T05", "TRAFFIC_TRANSPORT_vs_LAW_CRIME"),
    ("T01", "T05", "POLITICS_GOVERNMENT_vs_LAW_CRIME"),
    ("T10", "T09", "WEATHER_DISASTER_vs_ENVIRONMENT"),
    ("T03", "T05", "ECONOMY_BUSINESS_vs_LAW_CRIME"),
    ("T06", "T13", "HEALTH_vs_LIFESTYLE"),
    ("T07", "T08", "EDUCATION_vs_TECHNOLOGY_SCIENCE"),
    ("T12", "T14", "ENTERTAINMENT_vs_HUMAN_INTEREST"),
]

# ── HELPERS ───────────────────────────────────────────────────────────────────

def has_any_kw(text: str, keywords: list) -> bool:
    """Kiểm tra xem text có chứa bất kỳ keyword nào không (case-insensitive)."""
    t = str(text).lower()
    return any(kw in t for kw in keywords)

def get_matched_topics(text: str) -> list[str]:
    """Trả về danh sách label_ids match với text (chỉ T01-T17)."""
    matched = []
    for label_id in ["T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08", "T09", "T10", "T11", "T12", "T13", "T14", "T15", "T16", "T17"]:
        if has_any_kw(text, LABEL_KEYWORDS[label_id]):
            matched.append(label_id)
    return matched

def get_matched_keywords(text: str, keywords: list) -> str:
    """Trả về các từ khóa được tìm thấy trong text (giới hạn 3 từ đầu)."""
    t = str(text).lower()
    found = [kw for kw in keywords if kw in t]
    if not found:
        return "none"
    return f"matched: {', '.join(found[:3])}"

def enrich_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Thêm các cột metadata: word_count, content_length_bucket, source_type."""
    df = df.copy()
    df["word_count"] = (
        df["post_content_for_labeling"]
        .fillna("")
        .apply(lambda x: len(str(x).split()))
    )
    df["content_length_bucket"] = df["word_count"].apply(get_length_bucket)
    df["source_type"] = (
        df["page_name"]
        .fillna("")
        .map(SOURCE_TYPE_MAP)
        .fillna(DEFAULT_SOURCE_TYPE)
    )
    return df

def add_iaa_scaffold(df: pd.DataFrame) -> pd.DataFrame:
    """Thêm các cột IAA rỗng vào pilot_set."""
    df = df.copy()
    for col, default_val in {**IAA_COLUMNS_ANNOTATOR, **IAA_COLUMNS_ADJUDICATOR}.items():
        if col not in df.columns:
            df[col] = default_val
    return df

def split_pilot_dataset(pilot_df: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Phân tách tập Pilot thành Phase 1 (100 mẫu) và Phase 2 (còn lại) phân tầng, đồng thời gán nhãn cột pilot_phase."""
    p1_indices = []
    total_len = len(pilot_df)

    if total_len == 500:
        # Nhóm A (250) -> 50
        df_a = pilot_df[pilot_df["strata_label"] == "A_Random_Baseline"]
        p1_a = df_a.sample(n=50, random_state=seed)
        p1_indices.extend(p1_a.index.tolist())

        # Nhóm B (180): Lấy 36 mẫu (mỗi nhãn trong 18 nhãn lấy đúng 2 mẫu)
        df_b = pilot_df[pilot_df["strata_label"] == "B_Candidate_Coverage"]
        for label_name, group in df_b.groupby("candidate_label"):
            sampled = group.sample(n=2, random_state=seed)
            p1_indices.extend(sampled.index.tolist())

        # Nhóm C (50) -> 10
        df_c = pilot_df[pilot_df["strata_label"] == "C_Boundary_Pairs"]
        p1_c = df_c.sample(n=10, random_state=seed)
        p1_indices.extend(p1_c.index.tolist())

        # Nhóm D (20) -> 4
        df_d = pilot_df[pilot_df["strata_label"] == "D_Hard_Cases"]
        p1_d = df_d.sample(n=4, random_state=seed)
        p1_indices.extend(p1_d.index.tolist())
    else:
        # Mặc định / Dự phòng cho tập 600 mẫu (Nhóm A: 60, Nhóm B: 30, Nhóm C: 10)
        df_a = pilot_df[pilot_df["strata_label"] == "A_Random_Baseline"]
        if len(df_a) > 0:
            p1_a = df_a.sample(n=min(60, len(df_a)), random_state=seed)
            p1_indices.extend(p1_a.index.tolist())

        df_b = pilot_df[pilot_df["strata_label"] == "B_Candidate_Coverage"]
        if len(df_b) > 0:
            labels = sorted(df_b["candidate_label"].dropna().unique())
            rng = random.Random(seed)
            two_sample_labels = rng.sample(labels, min(12, len(labels)))
            for label_name, group in df_b.groupby("candidate_label"):
                n_samples = 2 if label_name in two_sample_labels else 1
                sampled = group.sample(n=min(n_samples, len(group)), random_state=seed)
                p1_indices.extend(sampled.index.tolist())

        df_c = pilot_df[pilot_df["strata_label"] == "C_Hard_Edge_Cases"]
        if len(df_c) > 0:
            p1_c = df_c.sample(n=min(10, len(df_c)), random_state=seed)
            p1_indices.extend(p1_c.index.tolist())

        # Bù đủ 100 mẫu nếu chưa đủ
        if len(p1_indices) < 100:
            needed = 100 - len(p1_indices)
            remaining_pool = pilot_df[~pilot_df.index.isin(p1_indices)]
            p1_extra = remaining_pool.sample(n=min(needed, len(remaining_pool)), random_state=seed)
            p1_indices.extend(p1_extra.index.tolist())

    # Gán nhãn cột pilot_phase vào dataframe
    pilot_df = pilot_df.copy()
    pilot_df["pilot_phase"] = "Phase_2"
    pilot_df.loc[pilot_df.index.isin(p1_indices), "pilot_phase"] = "Phase_1"

    # Sắp xếp lại vị trí cột pilot_phase đứng ngay sau candidate_reason để giữ giao diện đẹp
    cols = list(pilot_df.columns)
    if "pilot_phase" in cols:
        cols.remove("pilot_phase")
        idx = cols.index("candidate_reason") + 1
        cols.insert(idx, "pilot_phase")
        pilot_df = pilot_df[cols]

    # Tạo 2 tập con
    p1_df = pilot_df[pilot_df["pilot_phase"] == "Phase_1"].copy()
    p2_df = pilot_df[pilot_df["pilot_phase"] == "Phase_2"].copy()

    # Reset index và shuffle ngẫu nhiên từng tập độc lập
    p1_df = p1_df.sample(frac=1, random_state=seed).reset_index(drop=True)
    p2_df = p2_df.sample(frac=1, random_state=seed).reset_index(drop=True)

    return pilot_df, p1_df, p2_df

def build_split_report(p1_df: pd.DataFrame, p2_df: pd.DataFrame) -> str:
    """Tạo báo cáo bổ sung cho việc phân chia Phase 1 & Phase 2."""
    sep = "=" * 65
    lines = [
        "",
        sep,
        "MULTI-PHASE PILOT SPLIT DETAILS",
        sep,
        f"Phase 1 (100 samples) : {len(p1_df):,}",
        f"Phase 2 (còn lại)      : {len(p2_df):,}",
        "",
        "── Phase 1 Strata distribution ──",
    ]
    for s, c in p1_df["strata_label"].value_counts().items():
        pct = c / len(p1_df) * 100
        lines.append(f"  {s:50s}: {c:3d}  ({pct:5.1f}%)")
    lines.append("")

    lines.append("── Phase 2 Strata distribution ──")
    for s, c in p2_df["strata_label"].value_counts().items():
        pct = c / len(p2_df) * 100
        lines.append(f"  {s:50s}: {c:3d}  ({pct:5.1f}%)")
    lines.append("")

    lines.append("── Phase 1 Group B (Label Candidate Coverage) distribution ──")
    df_b1 = p1_df[p1_df["strata_label"] == "B_Candidate_Coverage"]
    for lbl in sorted(df_b1["candidate_label"].dropna().unique()):
        c = (df_b1["candidate_label"] == lbl).sum()
        lines.append(f"  {lbl:30s}: {c}")
    lines.append("")

    lines.append("── Phase 2 Group B (Label Candidate Coverage) distribution ──")
    df_b2 = p2_df[p2_df["strata_label"] == "B_Candidate_Coverage"]
    for lbl in sorted(df_b2["candidate_label"].dropna().unique()):
        c = (df_b2["candidate_label"] == lbl).sum()
        lines.append(f"  {lbl:30s}: {c}")
    lines.append("")

    return "\n".join(lines)

def build_report(df_orig: pd.DataFrame,
                 pilot_df: pd.DataFrame,
                 pool_df: pd.DataFrame) -> str:
    """Tạo báo cáo phân bổ chi tiết."""
    lines = []
    sep = "=" * 65

    lines += [sep, "PILOT SAMPLING REPORT (500 SAMPLES)", sep]
    lines += [
        f"Input rows            : {len(df_orig):,}",
        f"Pilot rows            : {len(pilot_df):,}",
        f"Pool rows             : {len(pool_df):,}",
        f"Total check           : {len(pilot_df) + len(pool_df):,} (should be {len(df_orig):,})",
        "",
    ]

    # ── Group/Strata distribution ──────────────────────────────────────────
    lines.append("── Group / strata_label distribution ──")
    for s, c in pilot_df["strata_label"].value_counts().items():
        pct = c / len(pilot_df) * 100
        lines.append(f"  {s:50s}: {c:3d}  ({pct:5.1f}%)")
    lines.append("")

    # ── sampling_method distribution ────────────────────────────────────────
    lines.append("── sampling_method distribution ──")
    for s, c in pilot_df["sampling_method"].value_counts().items():
        pct = c / len(pilot_df) * 100
        lines.append(f"  {s:50s}: {c:3d}  ({pct:5.1f}%)")
    lines.append("")

    # ── Source type distribution ───────────────────────────────────────────
    lines.append("── Source type distribution in pilot ──")
    for st, c in pilot_df["source_type"].value_counts().items():
        pct = c / len(pilot_df) * 100
        lines.append(f"  {st:30s}: {c:3d}  ({pct:5.1f}%)")
    lines.append("")

    # ── Content length bucket ──────────────────────────────────────────────
    lines.append("── Content length bucket in pilot ──")
    bucket_order = ["Very Short (≤5w)", "Short (6-15w)", "Medium (16-50w)", "Long (>50w)"]
    for bucket in bucket_order:
        c = (pilot_df["content_length_bucket"] == bucket).sum()
        pct = c / len(pilot_df) * 100
        lines.append(f"  {bucket:20s}: {c:3d}  ({pct:5.1f}%)")
    lines.append("")

    # ── Page coverage ──────────────────────────────────────────────────────
    lines.append("── Page coverage in pilot ──")
    all_pages   = set(df_orig["page_name"].dropna().unique())
    page_counts = pilot_df["page_name"].value_counts()
    covered     = set(page_counts.index)
    for pg in sorted(all_pages):
        n    = page_counts.get(pg, 0)
        src  = SOURCE_TYPE_MAP.get(pg, DEFAULT_SOURCE_TYPE)
        icon = "✅" if n > 0 else "❌"
        lines.append(f"  {icon} {pg:50s} ({src}): {n}")
    lines.append(f"\n  Coverage: {len(covered)}/{len(all_pages)} pages")
    lines.append("")

    return "\n".join(lines)

# ── PARSE ARGS ────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tạo tập Pilot 500 mẫu theo chiến lược lấy mẫu lai 4 nhóm."
    )
    parser.add_argument(
        "--input", "-i",
        default=INPUT_FILE,
        help=f"Đường dẫn tới file input CSV (mặc định: {INPUT_FILE})",
    )
    parser.add_argument(
        "--output", "-o",
        default=OUTPUT_DIR,
        help=f"Thư mục output (mặc định: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=RANDOM_SEED,
        help=f"Random seed (mặc định: {RANDOM_SEED})",
    )
    parser.add_argument(
        "--target", "-t",
        type=int,
        default=TARGET_TOTAL,
        help=f"Số rows mục tiêu cho pilot (mặc định: {TARGET_TOTAL})",
    )
    parser.add_argument(
        "--skip-size-check",
        action="store_true",
        default=False,
        help="Bỏ qua kiểm tra kích thước dataset gốc",
    )
    return parser.parse_args()

# ── MAIN ──────────────────────────────────────────────────────────────────────

def create_pilot(input_file: str = INPUT_FILE,
                 output_dir: str = OUTPUT_DIR,
                 seed: int = RANDOM_SEED,
                 target: int = TARGET_TOTAL,
                 skip_size_check: bool = False):

    random.seed(seed)
    df_raw = pd.read_csv(input_file, encoding="utf-8-sig")
    n_rows = len(df_raw)
    print(f"📂 Loaded {input_file} containing {n_rows:,} rows")

    # 1. Enrich metadata
    df = enrich_metadata(df_raw)
    
    df["strata_label"] = "unlabeled"
    df["sampling_method"] = "none"
    df["candidate_label"] = "none"
    df["candidate_reason"] = "none"

    used_indices = set()
    pilot_parts = []

    # ──────────────────────────────────────────────────────────────────────────
    # NHÓM D: SPECIAL HARD CASES (20 mẫu)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n🟤 Sampling Group D: Special hard cases (20 samples)...")
    group_d_indices = []

    # D1. Very short (10 samples)
    print("   Sampling Sub-group D1: Very short (word_count <= 5)...")
    mask_very_short = df["word_count"] <= 5
    vs_pool = df[mask_very_short & ~df.index.isin(used_indices)].index.tolist()
    random.Random(seed).shuffle(vs_pool)
    vs_sampled = vs_pool[:10]
    for idx in vs_sampled:
        df.at[idx, "strata_label"] = "D_Hard_Cases"
        df.at[idx, "sampling_method"] = "D_Hard_Cases_VeryShort"
        df.at[idx, "candidate_reason"] = f"word_count: {df.at[idx, 'word_count']}"
    used_indices.update(vs_sampled)
    group_d_indices.extend(vs_sampled)
    print(f"   → Very short: sampled {len(vs_sampled)} / 10 rows")

    # D2. Multi-topic (10 samples)
    print("   Sampling Sub-group D2: Multi-topic (matches >= 2 labels)...")
    df["matched_topics"] = df["post_content_for_labeling"].fillna("").apply(get_matched_topics)
    mask_multi = df["matched_topics"].apply(len) >= 2
    multi_pool = df[mask_multi & ~df.index.isin(used_indices)].index.tolist()
    random.Random(seed).shuffle(multi_pool)
    multi_sampled = multi_pool[:10]
    for idx in multi_sampled:
        df.at[idx, "strata_label"] = "D_Hard_Cases"
        df.at[idx, "sampling_method"] = "D_Hard_Cases_MultiTopic"
        df.at[idx, "candidate_reason"] = f"matched topics: {', '.join(df.at[idx, 'matched_topics'])}"
    used_indices.update(multi_sampled)
    group_d_indices.extend(multi_sampled)
    print(f"   → Multi-topic: sampled {len(multi_sampled)} / 10 rows")

    pilot_parts.append(df.loc[group_d_indices])

    # ──────────────────────────────────────────────────────────────────────────
    # NHÓM C: BOUNDARY PAIRS (50 mẫu)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n🔴 Sampling Group C: Boundary pairs (50 samples)...")
    boundary_candidates = {}
    for la, lb, name in BOUNDARY_PAIRS:
        mask_a = df["post_content_for_labeling"].fillna("").apply(lambda x: has_any_kw(x, LABEL_KEYWORDS[la]))
        mask_b = df["post_content_for_labeling"].fillna("").apply(lambda x: has_any_kw(x, LABEL_KEYWORDS[lb]))
        boundary_candidates[name] = df[mask_a & mask_b].index.tolist()

    boundary_sampled = []
    pairs_cycle = sorted(list(boundary_candidates.keys()))
    for name in pairs_cycle:
        random.Random(seed).shuffle(boundary_candidates[name])

    idx_in_pair = {name: 0 for name in pairs_cycle}
    attempts = 0
    while len(boundary_sampled) < 50 and attempts < 1000:
        attempts += 1
        added_any = False
        for name in pairs_cycle:
            if len(boundary_sampled) >= 50:
                break
            pool = boundary_candidates[name]
            while idx_in_pair[name] < len(pool):
                cand = pool[idx_in_pair[name]]
                idx_in_pair[name] += 1
                if cand not in used_indices and cand not in boundary_sampled:
                    boundary_sampled.append(cand)
                    
                    df.at[cand, "strata_label"] = "C_Boundary_Pairs"
                    df.at[cand, "sampling_method"] = "C_Boundary_Pairs"
                    df.at[cand, "candidate_reason"] = f"boundary pair: {name}"
                    
                    added_any = True
                    break
        if not added_any:
            break

    used_indices.update(boundary_sampled)
    pilot_parts.append(df.loc[boundary_sampled])
    print(f"   → Boundary Pairs: sampled {len(boundary_sampled)} / 50 rows")

    # ──────────────────────────────────────────────────────────────────────────
    # NHÓM B: LABEL CANDIDATE COVERAGE (180 mẫu)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n🟡 Sampling Group B: Label candidate coverage (180 samples)...")
    group_b_indices = []

    for label_id in sorted(LABEL_KEYWORDS.keys()):
        label_name = LABEL_MAP.get(label_id, "UNKNOWN")
        kws = LABEL_KEYWORDS[label_id]
        
        mask_kw = df["post_content_for_labeling"].fillna("").apply(lambda x: has_any_kw(x, kws))
        available = df[mask_kw & ~df.index.isin(used_indices)].copy()
        
        available["other_matches_count"] = available["post_content_for_labeling"].fillna("").apply(
            lambda x: len([lid for lid in LABEL_KEYWORDS.keys() if lid != label_id and has_any_kw(x, LABEL_KEYWORDS[lid])])
        )
        
        available = available.sort_values(by="other_matches_count")
        sampled_label_indices = available.head(10).index.tolist()
        
        for idx in sampled_label_indices:
            df.at[idx, "strata_label"] = "B_Candidate_Coverage"
            df.at[idx, "sampling_method"] = "B_Candidate_Coverage"
            df.at[idx, "candidate_label"] = label_name
            df.at[idx, "candidate_reason"] = get_matched_keywords(df.at[idx, "post_content_for_labeling"], kws)
            
        used_indices.update(sampled_label_indices)
        group_b_indices.extend(sampled_label_indices)
        print(f"   → Nhãn {label_id} ({label_name:30s}): sampled {len(sampled_label_indices)} / 10 rows")

    pilot_parts.append(df.loc[group_b_indices])

    # ──────────────────────────────────────────────────────────────────────────
    # NHÓM A: STRATIFIED RANDOM BASELINE (250 mẫu)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n🟢 Sampling Group A: Stratified random baseline (250 samples)...")
    
    # 3x4 grid quotas for 250 samples
    grid_quotas = {
        "Báo điện tử": {
            "Very Short (≤5w)": 1,
            "Short (6-15w)": 38,
            "Medium (16-50w)": 65,
            "Long (>50w)": 27,
        },
        "Entertainment news": {
            "Very Short (≤5w)": 0,
            "Short (6-15w)": 34,
            "Medium (16-50w)": 59,
            "Long (>50w)": 23,
        },
        "Other": {
            "Very Short (≤5w)": 0,
            "Short (6-15w)": 1,
            "Medium (16-50w)": 1,
            "Long (>50w)": 1,
        }
    }

    group_a_indices = []
    for src_type, length_dict in grid_quotas.items():
        for len_bucket, quota in length_dict.items():
            if quota <= 0:
                continue
            
            mask_cell = (df["source_type"] == src_type) & (df["content_length_bucket"] == len_bucket)
            cell_pool = df[mask_cell & ~df.index.isin(used_indices)].index.tolist()
            
            random.Random(seed).shuffle(cell_pool)
            cell_sampled = cell_pool[:quota]
            
            for idx in cell_sampled:
                df.at[idx, "strata_label"] = "A_Random_Baseline"
                df.at[idx, "sampling_method"] = "A_Random_Baseline"
                df.at[idx, "candidate_reason"] = f"source_type: {src_type}, length_bucket: {len_bucket}"
                
            used_indices.update(cell_sampled)
            group_a_indices.extend(cell_sampled)
            print(f"   → Cell [{src_type:20s} x {len_bucket:18s}]: sampled {len(cell_sampled)} / {quota}")

    pilot_parts.append(df.loc[group_a_indices])

    # ──────────────────────────────────────────────────────────────────────────
    # Gộp và Shuffle
    # ──────────────────────────────────────────────────────────────────────────
    pilot_df = pd.concat([p for p in pilot_parts if len(p) > 0])
    pilot_df = pilot_df.sample(frac=1, random_state=seed).reset_index(drop=True)

    pool_df = df[~df.index.isin(used_indices)].copy()

    # Thêm IAA scaffold columns
    print("\n📋 Adding IAA scaffold columns...")
    pilot_df = add_iaa_scaffold(pilot_df)

    # Cột output
    base_cols_orig = [c for c in df_raw.columns if c in pilot_df.columns]
    meta_cols = ["source_type", "word_count", "content_length_bucket", "strata_label", "sampling_method", "candidate_label", "candidate_reason"]
    ann_cols = list(IAA_COLUMNS_ANNOTATOR.keys())
    adj_cols = list(IAA_COLUMNS_ADJUDICATOR.keys())

    ordered_cols = (
        base_cols_orig
        + [c for c in meta_cols if c not in base_cols_orig]
        + ann_cols
        + adj_cols
    )
    extra = [c for c in pilot_df.columns if c not in ordered_cols]
    ordered_cols += extra
    pilot_df = pilot_df[ordered_cols]

    pool_ordered = base_cols_orig + [c for c in meta_cols if c not in base_cols_orig and c in pool_df.columns]
    pool_df = pool_df[[c for c in pool_ordered if c in pool_df.columns]]

    # Output
    os.makedirs(output_dir, exist_ok=True)
    pilot_path  = os.path.join(output_dir, "pilot_set.csv")
    pool_path   = os.path.join(output_dir, "pool_set.csv")
    ids_path    = os.path.join(output_dir, "pilot_ids.csv")
    report_path = os.path.join(output_dir, "pilot_report.txt")

    pilot_df.to_csv(pilot_path, index=False, encoding="utf-8-sig")
    pool_df.to_csv(pool_path,   index=False, encoding="utf-8-sig")
    pilot_df[["record_id", "strata_label"]].to_csv(ids_path, index=False, encoding="utf-8-sig")

    # Báo cáo
    report_text = build_report(df, pilot_df, pool_df)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    # ── PHÂN CHIA THÀNH CÁC GIAI ĐOẠN (PHASE 1 & PHASE 2) ───────────────────
    print("\n✂️ Tiến hành phân tách phân tầng thành Phase 1 & Phase 2...")
    pilot_df_with_phase, p1_df, p2_df = split_pilot_dataset(pilot_df, seed)

    # Ghi đè lại file pilot_set.csv để chứa thêm cột pilot_phase (không đè lên cột cũ)
    pilot_df_with_phase.to_csv(pilot_path, index=False, encoding="utf-8-sig")

    # Xuất các file riêng cho Phase 1 và Phase 2
    pilot_100_path = os.path.join(output_dir, "pilot_set_100.csv")
    pilot_400_path = os.path.join(output_dir, "pilot_set_400.csv")
    ids_100_path   = os.path.join(output_dir, "pilot_ids_100.csv")
    ids_400_path   = os.path.join(output_dir, "pilot_ids_400.csv")

    p1_df.to_csv(pilot_100_path, index=False, encoding="utf-8-sig")
    p2_df.to_csv(pilot_400_path, index=False, encoding="utf-8-sig")
    p1_df[["record_id", "strata_label"]].to_csv(ids_100_path, index=False, encoding="utf-8-sig")
    p2_df[["record_id", "strata_label"]].to_csv(ids_400_path, index=False, encoding="utf-8-sig")

    # Bổ sung báo cáo phân tách vào pilot_report.txt
    split_report_text = build_split_report(p1_df, p2_df)
    with open(report_path, "a", encoding="utf-8") as f:
        f.write(split_report_text)

    print("\n" + report_text)
    print(split_report_text)
    print("\n✅ Generation Complete:")
    print(f"   {pilot_path}  ({len(pilot_df_with_phase)} rows, {len(pilot_df_with_phase.columns)} cols - với cột pilot_phase)")
    print(f"   {pool_path}  ({len(pool_df)} rows, {len(pool_df.columns)} cols)")
    print(f"   {ids_path}")
    print(f"   {pilot_100_path}  ({len(p1_df)} rows)")
    print(f"   {pilot_400_path}  ({len(p2_df)} rows)")
    print(f"   {ids_100_path}")
    print(f"   {ids_400_path}")
    print(f"   {report_path}")

    return pilot_df_with_phase, pool_df

if __name__ == "__main__":
    args = parse_args()
    create_pilot(
        input_file      = args.input,
        output_dir      = args.output,
        seed            = args.seed,
        target          = args.target,
        skip_size_check = args.skip_size_check,
    )

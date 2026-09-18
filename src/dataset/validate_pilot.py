"""
validate_pilot.py
=================
Unit test cho pilot_set.csv và pool_set.csv.
Chạy sau create_pilot_dataset.py để đảm bảo:

  1.  Số dòng pilot gần đúng target (~270)
  2.  pilot + pool = original (không mất dữ liệu)
  3.  Không trùng lặp record_id trong pilot
  4.  Không data leakage: pilot ∩ pool = ∅
  5.  Tất cả record_id gốc có mặt đúng 1 lần
  6.  strata_label đầy đủ, không null
  7.  Không có row vừa là Tier3 vừa là Tier5 (deduplication đúng)
  8.  Page coverage đạt 100% (tất cả pages trong gốc đều có trong pilot)
  9.  Metadata columns (source_type, word_count, content_length_bucket) hợp lệ
  10. IAA scaffold columns có mặt trong pilot_set, vắng mặt trong pool_set
  11. Không có record_id null trong bất kỳ file nào
  12. pilot_ids.csv khớp với record_id trong pilot_set.csv

Cách dùng:
  # Dùng mặc định:
  python validate_pilot.py

  # Tùy chỉnh đường dẫn và target:
  python validate_pilot.py \\
      --original Annotation_Template_TeamCrawl.csv \\
      --pilot    pilot_set.csv \\
      --pool     pool_set.csv \\
      --ids      pilot_ids.csv \\
      --expected-pilot 270
"""

import argparse
import os
import sys

import pandas as pd

# Import bảng nhãn tập trung
try:
    from label_map import VALID_SOURCE_TYPES, VALID_LENGTH_BUCKETS, DEFAULT_SOURCE_TYPE
    from create_pilot_dataset import IAA_COLUMNS_ANNOTATOR, IAA_COLUMNS_ADJUDICATOR
except ImportError:
    VALID_SOURCE_TYPES  = []
    VALID_LENGTH_BUCKETS = []
    DEFAULT_SOURCE_TYPE  = "Không rõ nguồn"
    IAA_COLUMNS_ANNOTATOR   = {}
    IAA_COLUMNS_ADJUDICATOR = {}


# ── DEFAULT CONFIG ─────────────────────────────────────────────────────────────
ORIGINAL_FILE  = "Annotation_Template_TeamCrawl.csv"
PILOT_FILE     = "pilot_set.csv"
POOL_FILE      = "pool_set.csv"
IDS_FILE       = "pilot_ids.csv"
EXPECTED_PILOT = 500
ID_COL         = "record_id"

# Cột bắt buộc trong pilot (dành cho IAA trên Google Sheets)
IAA_ALL_COLS = list(IAA_COLUMNS_ANNOTATOR.keys()) + list(IAA_COLUMNS_ADJUDICATOR.keys())

# Cột metadata bổ sung
METADATA_COLS = ["source_type", "word_count", "content_length_bucket", "strata_label", "sampling_method", "candidate_label", "candidate_reason"]


# ── HELPERS ───────────────────────────────────────────────────────────────────

def check(condition: bool, msg_pass: str, msg_fail: str) -> bool:
    if condition:
        print(f"  ✅ {msg_pass}")
        return True
    else:
        print(f"  ❌ FAIL: {msg_fail}")
        return False


# ── PARSE ARGS ────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Kiểm tra tính toàn vẹn của pilot_set.csv và pool_set.csv."
    )
    parser.add_argument("--original", default=ORIGINAL_FILE,
                        help=f"File dataset gốc (mặc định: {ORIGINAL_FILE})")
    parser.add_argument("--pilot",    default=PILOT_FILE,
                        help=f"File pilot set (mặc định: {PILOT_FILE})")
    parser.add_argument("--pool",     default=POOL_FILE,
                        help=f"File pool set (mặc định: {POOL_FILE})")
    parser.add_argument("--ids",      default=IDS_FILE,
                        help=f"File pilot IDs (mặc định: {IDS_FILE})")
    parser.add_argument("--expected-pilot", type=int, default=EXPECTED_PILOT,
                        help=f"Số rows mục tiêu của pilot (mặc định: {EXPECTED_PILOT})")
    return parser.parse_args()


# ── MAIN ──────────────────────────────────────────────────────────────────────

def validate(original_file: str = ORIGINAL_FILE,
             pilot_file:    str = PILOT_FILE,
             pool_file:     str = POOL_FILE,
             ids_file:      str = IDS_FILE,
             expected_pilot: int = EXPECTED_PILOT) -> bool:

    errors = 0

    print("=" * 65)
    print("VALIDATE PILOT DATASET")
    print("=" * 65)

    # ── Kiểm tra files tồn tại ───────────────────────────────────────────
    for fpath in [original_file, pilot_file, pool_file, ids_file]:
        if not os.path.exists(fpath):
            print(f"  ❌ File không tồn tại: {fpath}")
            sys.exit(1)

    df_orig  = pd.read_csv(original_file, encoding="utf-8-sig")
    df_pilot = pd.read_csv(pilot_file,    encoding="utf-8-sig")
    df_pool  = pd.read_csv(pool_file,     encoding="utf-8-sig")
    df_ids   = pd.read_csv(ids_file,      encoding="utf-8-sig")

    print(f"\n📊 Row counts:"
          f"  original={len(df_orig):,}"
          f"  pilot={len(df_pilot):,}"
          f"  pool={len(df_pool):,}")
    print(f"   Pilot cols: {len(df_pilot.columns)}"
          f"  |  Pool cols: {len(df_pool.columns)}\n")

    # ── CHECK 1: Pilot size gần đúng target ──────────────────────────────
    print("── CHECK 1: Pilot size ──")
    if not check(
        abs(len(df_pilot) - expected_pilot) <= 10,
        f"Pilot size = {len(df_pilot)} (target ~{expected_pilot})",
        f"Pilot size {len(df_pilot)} lệch quá xa target {expected_pilot}",
    ):
        errors += 1

    # ── CHECK 2: pilot + pool = original ─────────────────────────────────
    print("\n── CHECK 2: pilot + pool = original ──")
    total = len(df_pilot) + len(df_pool)
    if not check(
        total == len(df_orig),
        f"pilot ({len(df_pilot)}) + pool ({len(df_pool)}) = {total} ✓",
        f"pilot + pool = {total} ≠ {len(df_orig)}",
    ):
        errors += 1

    # ── CHECK 3: Không trùng lặp trong pilot ─────────────────────────────
    print("\n── CHECK 3: No duplicates in pilot ──")
    dup_count = df_pilot[ID_COL].duplicated().sum()
    if not check(
        dup_count == 0,
        "Không có record_id trùng lặp trong pilot",
        f"{dup_count} record_id bị trùng",
    ):
        errors += 1

    # ── CHECK 4: Không data leakage ──────────────────────────────────────
    print("\n── CHECK 4: No leakage pilot ↔ pool ──")
    pilot_ids = set(df_pilot[ID_COL].tolist())
    pool_ids  = set(df_pool[ID_COL].tolist())
    overlap   = pilot_ids & pool_ids
    if not check(
        len(overlap) == 0,
        "Pilot và pool không giao nhau ✓",
        f"{len(overlap)} record_id xuất hiện ở cả 2 tập: {list(overlap)[:5]}",
    ):
        errors += 1

    # ── CHECK 5: Tất cả original IDs có mặt đúng 1 lần ──────────────────
    print("\n── CHECK 5: All original IDs accounted for ──")
    orig_ids = set(df_orig[ID_COL].tolist())
    union    = pilot_ids | pool_ids
    missing  = orig_ids - union
    extra    = union - orig_ids
    if not check(
        len(missing) == 0 and len(extra) == 0,
        "Tất cả record_id gốc có mặt đúng 1 lần ✓",
        f"Missing: {len(missing)}, Extra: {len(extra)}",
    ):
        errors += 1

    # ── CHECK 6: strata_label không null ─────────────────────────────────
    print("\n── CHECK 6: strata_label not null ──")
    if "strata_label" not in df_pilot.columns:
        print("  ❌ FAIL: Cột strata_label không tồn tại trong pilot_set.csv")
        errors += 1
    else:
        null_count = df_pilot["strata_label"].isna().sum()
        if not check(
            null_count == 0,
            "strata_label đầy đủ, không có null ✓",
            f"{null_count} rows có strata_label = null",
        ):
            errors += 1

    # ── CHECK 7: Không giao nhau giữa các nhóm strata_label ─────────────────
    print("\n── CHECK 7: No overlap between strata_label groups ──")
    if "strata_label" in df_pilot.columns:
        group_a_ids = set(df_pilot[df_pilot["strata_label"] == "A_Random_Baseline"][ID_COL])
        group_b_ids = set(df_pilot[df_pilot["strata_label"] == "B_Candidate_Coverage"][ID_COL])
        group_c_ids = set(df_pilot[df_pilot["strata_label"] == "C_Hard_Edge_Cases"][ID_COL])
        cross_ab = group_a_ids & group_b_ids
        cross_bc = group_b_ids & group_c_ids
        cross_ac = group_a_ids & group_c_ids
        total_cross = len(cross_ab) + len(cross_bc) + len(cross_ac)
        if not check(
            total_cross == 0,
            "Không có sự chồng chéo record_id giữa các nhóm A, B, C ✓",
            f"Phát hiện sự chồng chéo: A∩B={len(cross_ab)}, B∩C={len(cross_bc)}, A∩C={len(cross_ac)}",
        ):
            errors += 1

    # ── CHECK 8: Page coverage 100% ──────────────────────────────────────
    print("\n── CHECK 8: Page coverage ──")
    all_pages     = set(df_orig["page_name"].dropna().unique())
    pilot_pages   = set(df_pilot["page_name"].dropna().unique())
    missing_pages = all_pages - pilot_pages
    if not check(
        len(missing_pages) == 0,
        f"Tất cả {len(all_pages)} pages có trong pilot ✓",
        f"{len(missing_pages)} pages thiếu: {missing_pages}",
    ):
        errors += 1

    # ── CHECK 9: Metadata columns hợp lệ ─────────────────────────────────
    print("\n── CHECK 9: Metadata columns ──")
    for col in METADATA_COLS:
        if col not in df_pilot.columns:
            print(f"  ❌ FAIL: Cột '{col}' thiếu trong pilot_set.csv")
            errors += 1
        else:
            null_n = df_pilot[col].isna().sum()
            if not check(
                null_n == 0,
                f"'{col}' đầy đủ, không null",
                f"'{col}' có {null_n} giá trị null",
            ):
                errors += 1

    # Kiểm tra source_type chỉ chứa giá trị hợp lệ
    if "source_type" in df_pilot.columns and VALID_SOURCE_TYPES:
        invalid_src = df_pilot[~df_pilot["source_type"].isin(VALID_SOURCE_TYPES)]
        if not check(
            len(invalid_src) == 0,
            "source_type chỉ chứa giá trị hợp lệ",
            f"{len(invalid_src)} rows có source_type không hợp lệ: "
            f"{invalid_src['source_type'].unique().tolist()}",
        ):
            errors += 1

    # Kiểm tra content_length_bucket
    if "content_length_bucket" in df_pilot.columns and VALID_LENGTH_BUCKETS:
        invalid_len = df_pilot[~df_pilot["content_length_bucket"].isin(VALID_LENGTH_BUCKETS)]
        if not check(
            len(invalid_len) == 0,
            "content_length_bucket chỉ chứa giá trị hợp lệ",
            f"{len(invalid_len)} rows có content_length_bucket không hợp lệ",
        ):
            errors += 1

    # ── CHECK 10: IAA scaffold columns CÓ trong pilot ────────────────────
    print("\n── CHECK 10: IAA scaffold columns trong pilot_set ──")
    if IAA_ALL_COLS:
        missing_iaa = [c for c in IAA_ALL_COLS if c not in df_pilot.columns]
        if not check(
            len(missing_iaa) == 0,
            f"Tất cả {len(IAA_ALL_COLS)} cột IAA có mặt trong pilot_set ✓",
            f"Thiếu {len(missing_iaa)} cột: {missing_iaa}",
        ):
            errors += 1

    # ── CHECK 11: IAA scaffold KHÔNG có trong pool ────────────────────────
    print("\n── CHECK 11: IAA scaffold columns VẮNG trong pool_set ──")
    if IAA_ALL_COLS:
        present_in_pool = [c for c in IAA_ALL_COLS if c in df_pool.columns]
        if not check(
            len(present_in_pool) == 0,
            "pool_set không có cột IAA ✓ (đúng thiết kế)",
            f"pool_set có {len(present_in_pool)} cột IAA không cần thiết: {present_in_pool}",
        ):
            errors += 1  # warning, không fail cứng

    # ── CHECK 12: pilot_ids.csv khớp với pilot_set.csv ───────────────────
    print("\n── CHECK 12: pilot_ids.csv khớp với pilot_set.csv ──")
    ids_in_file = set(df_ids[ID_COL].tolist())
    if not check(
        ids_in_file == pilot_ids,
        f"pilot_ids.csv khớp hoàn toàn ({len(ids_in_file)} IDs) ✓",
        f"Không khớp: {len(ids_in_file - pilot_ids)} thừa, "
        f"{len(pilot_ids - ids_in_file)} thiếu",
    ):
        errors += 1

    # ── CHECK 13: Không có record_id null ─────────────────────────────────
    print("\n── CHECK 13: No null record_id ──")
    for name, df_ in [("original", df_orig), ("pilot", df_pilot), ("pool", df_pool)]:
        n_null = df_[ID_COL].isna().sum()
        if not check(
            n_null == 0,
            f"{name}: không có null record_id",
            f"{name}: {n_null} null record_id",
        ):
            errors += 1

    # ── CHECK 14: Phân chia Phase 1 (100) và Phase 2 (còn lại) phân tầng ──
    print("\n── CHECK 14: Phase 1 & Phase 2 split validation ──")
    dir_name = os.path.dirname(pilot_file) or "."
    pilot_100_file = os.path.join(dir_name, "pilot_set_100.csv")
    pilot_400_file = os.path.join(dir_name, "pilot_set_400.csv")
    ids_100_file   = os.path.join(dir_name, "pilot_ids_100.csv")
    ids_400_file   = os.path.join(dir_name, "pilot_ids_400.csv")

    split_files_exist = True
    for fp in [pilot_100_file, pilot_400_file, ids_100_file, ids_400_file]:
        if not os.path.exists(fp):
            print(f"  ❌ FAIL: File phân chia không tồn tại: {fp}")
            errors += 1
            split_files_exist = False

    if split_files_exist:
        df_p1 = pd.read_csv(pilot_100_file, encoding="utf-8-sig")
        df_p2 = pd.read_csv(pilot_400_file, encoding="utf-8-sig")
        df_ids1 = pd.read_csv(ids_100_file, encoding="utf-8-sig")
        df_ids2 = pd.read_csv(ids_400_file, encoding="utf-8-sig")

        # Check sizes
        if not check(len(df_p1) == 100, "Phase 1: kích thước đúng 100 dòng", f"Phase 1 size = {len(df_p1)} ≠ 100"):
            errors += 1
            
        expected_p2_size = len(df_pilot) - 100
        if not check(len(df_p2) == expected_p2_size, f"Phase 2: kích thước đúng {expected_p2_size} dòng", f"Phase 2 size = {len(df_p2)} ≠ {expected_p2_size}"):
            errors += 1

        # Check disjointness and union
        p1_ids = set(df_p1[ID_COL].tolist())
        p2_ids = set(df_p2[ID_COL].tolist())
        intersect = p1_ids & p2_ids
        if not check(len(intersect) == 0, "Phase 1 và Phase 2 không giao nhau ✓", f"Phase 1 và Phase 2 trùng lặp {len(intersect)} record_id"):
            errors += 1

        union_p = p1_ids | p2_ids
        if not check(union_p == pilot_ids, "Hợp của Phase 1 và Phase 2 bằng đúng tập Pilot gốc ✓", "Hợp của Phase 1 và Phase 2 khác tập Pilot gốc"):
            errors += 1

        # Check IDs files
        if not check(set(df_ids1[ID_COL].tolist()) == p1_ids, "pilot_ids_100.csv khớp với pilot_set_100.csv ✓", "pilot_ids_100.csv không khớp"):
            errors += 1
        if not check(set(df_ids2[ID_COL].tolist()) == p2_ids, "pilot_ids_400.csv khớp với pilot_set_400.csv ✓", "pilot_ids_400.csv không khớp"):
            errors += 1

        # Check strata counts
        if len(df_pilot) == 600:
            expected_p1_strata = {"A_Random_Baseline": 60, "B_Candidate_Coverage": 30, "C_Hard_Edge_Cases": 10}
            expected_p2_strata = {"A_Random_Baseline": 300, "B_Candidate_Coverage": 150, "C_Hard_Edge_Cases": 50}
        else:
            expected_p1_strata = {"A_Random_Baseline": 50, "B_Candidate_Coverage": 36, "C_Boundary_Pairs": 10, "D_Hard_Cases": 4}
            expected_p2_strata = {"A_Random_Baseline": 200, "B_Candidate_Coverage": 144, "C_Boundary_Pairs": 40, "D_Hard_Cases": 16}

        p1_strata_counts = df_p1["strata_label"].value_counts().to_dict()
        p2_strata_counts = df_p2["strata_label"].value_counts().to_dict()

        p1_strata_ok = all(p1_strata_counts.get(k, 0) == v for k, v in expected_p1_strata.items())
        if not check(p1_strata_ok, f"Phase 1 strata distribution khớp thiết kế {expected_p1_strata} ✓", f"Phase 1 strata mismatch: {p1_strata_counts}"):
            errors += 1

        p2_strata_ok = all(p2_strata_counts.get(k, 0) == v for k, v in expected_p2_strata.items())
        if not check(p2_strata_ok, f"Phase 2 strata distribution khớp thiết kế {expected_p2_strata} ✓", f"Phase 2 strata mismatch: {p2_strata_counts}"):
            errors += 1

        # Check label candidate coverage (Group B: all 18 labels represented in Phase 1 and 2)
        df_b1 = df_p1[df_p1["strata_label"] == "B_Candidate_Coverage"]
        df_b2 = df_p2[df_p2["strata_label"] == "B_Candidate_Coverage"]

        b1_label_counts = df_b1["candidate_label"].value_counts().to_dict()
        b2_label_counts = df_b2["candidate_label"].value_counts().to_dict()

        if len(df_pilot) == 600:
            b1_labels_ok = len(b1_label_counts) == 18 and all(v in [1, 2] for v in b1_label_counts.values())
            if not check(b1_labels_ok, "Phase 1 Group B chứa đúng 18 nhãn, mỗi nhãn 1 hoặc 2 mẫu ✓", f"Phase 1 Group B label counts mismatch: {b1_label_counts}"):
                errors += 1
            b2_labels_ok = len(b2_label_counts) == 18 and all(v in [8, 9] for v in b2_label_counts.values())
            if not check(b2_labels_ok, "Phase 2 Group B chứa đúng 18 nhãn, mỗi nhãn 8 hoặc 9 mẫu ✓", f"Phase 2 Group B label counts mismatch: {b2_label_counts}"):
                errors += 1
        else:
            b1_labels_ok = len(b1_label_counts) == 18 and all(v == 2 for v in b1_label_counts.values())
            if not check(b1_labels_ok, "Phase 1 Group B chứa đúng 18 nhãn, mỗi nhãn đúng 2 mẫu ✓", f"Phase 1 Group B label counts mismatch: {b1_label_counts}"):
                errors += 1
            b2_labels_ok = len(b2_label_counts) == 18 and all(v == 8 for v in b2_label_counts.values())
            if not check(b2_labels_ok, "Phase 2 Group B chứa đúng 18 nhãn, mỗi nhãn đúng 8 mẫu ✓", f"Phase 2 Group B label counts mismatch: {b2_label_counts}"):
                errors += 1

        # Check pilot_phase column
        if not check("pilot_phase" in df_p1.columns, "Cột 'pilot_phase' có mặt trong Phase 1 ✓", "Cột 'pilot_phase' thiếu trong Phase 1"):
            errors += 1
        if not check(df_p1["pilot_phase"].nunique() == 1 and df_p1["pilot_phase"].iloc[0] == "Phase_1", "Giá trị cột 'pilot_phase' trong Phase 1 là 'Phase_1' ✓", "Sai giá trị 'pilot_phase' trong Phase 1"):
            errors += 1
        if not check(df_p2["pilot_phase"].nunique() == 1 and df_p2["pilot_phase"].iloc[0] == "Phase_2", "Giá trị cột 'pilot_phase' trong Phase 2 là 'Phase_2' ✓", "Sai giá trị 'pilot_phase' trong Phase 2"):
            errors += 1

    # ── SUMMARY ──────────────────────────────────────────────────────────
    print("\n── Strata distribution ──")
    if "strata_label" in df_pilot.columns:
        for s, c in df_pilot["strata_label"].value_counts().items():
            print(f"  {s:50s}: {c:3d}  ({c/len(df_pilot)*100:.1f}%)")

    print("\n── Content length bucket in pilot ──")
    if "content_length_bucket" in df_pilot.columns:
        for b, c in df_pilot["content_length_bucket"].value_counts().items():
            print(f"  {b:22s}: {c:3d}  ({c/len(df_pilot)*100:.1f}%)")

    print("\n── Source type in pilot ──")
    if "source_type" in df_pilot.columns:
        for s, c in df_pilot["source_type"].value_counts().items():
            print(f"  {s:30s}: {c:3d}  ({c/len(df_pilot)*100:.1f}%)")

    print("\n── Page distribution in pilot ──")
    all_pages = set(df_orig["page_name"].dropna().unique())
    for pg in sorted(all_pages):
        n    = (df_pilot["page_name"] == pg).sum()
        icon = "✅" if n > 0 else "❌"
        print(f"  {icon} {pg}: {n}")

    print("\n── IAA scaffold columns check ──")
    for col in IAA_ALL_COLS:
        present = col in df_pilot.columns
        null_n  = df_pilot[col].isna().sum() if present else -1
        print(f"  {'✅' if present else '❌'} {col:45s}"
              + (f"  (null={null_n})" if present else "  (MISSING)"))

    print("\n" + "=" * 65)
    if errors == 0:
        print("✅ ALL CHECKS PASSED — Pilot sẵn sàng cho IAA 🎉")
    else:
        print(f"❌ {errors} CHECK(S) FAILED — Xem lỗi ở trên trước khi giao annotators")
    print("=" * 65)

    return errors == 0


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = parse_args()
    ok = validate(
        original_file   = args.original,
        pilot_file      = args.pilot,
        pool_file       = args.pool,
        ids_file        = args.ids,
        expected_pilot  = args.expected_pilot,
    )
    sys.exit(0 if ok else 1)

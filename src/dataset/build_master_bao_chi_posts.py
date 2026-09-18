#!/usr/bin/env python3
"""Build press-only Master and annotation CSV files.

This script reuses the normalizers from build_master_facebook_posts.py, then
filters raw input down to the news/press sources requested for the project.
Default output is intentionally small: one Master CSV and one annotation CSV.
"""

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from build_master_facebook_posts import (
    ANNOTATION_COLUMNS,
    ENRICHED_COLUMNS,
    apply_annotation_file,
    assign_duplicates,
    clean_text,
    discover_json_post_files,
    iter_json_records,
    normalize_json_post,
    row_priority,
    set_dedup_key,
    write_annotation_template,
    write_csv,
)


PRESS_SOURCE_RULES = [
    {
        "id": "congdongvnexpress",
        "name": "Cộng đồng VnExpress",
        "owner": "vitrend",
        "handle": "congdongvnexpress",
        "tokens": ["01_existing_vitrend_raw", "posts_congdongvnexpress"],
    },
    {
        "id": "cuc_canh_sat_ma_tuy",
        "name": "Cục Cảnh sát điều tra tội phạm về ma tuý",
        "owner": "han",
        "tokens": ["02_team_crawled_raw_han", "posts_cuc_canh_sat_dieu_tra_toi_pham_ve_ma_tuy"],
    },
    {
        "id": "nguoi_lao_dong",
        "name": "Người Lao Động",
        "owner": "han",
        "handle": "nguoilaodong",
        "tokens": ["02_team_crawled_raw_han", "posts_nguoilaodong"],
    },
    {
        "id": "dai_bieu_nhan_dan",
        "name": "Đại biểu Nhân dân",
        "owner": "nhung",
        "tokens": ["02_team_crawled_raw_nhung", "posts_dai_bieu_nhan_dan"],
    },
    {
        "id": "tin_tuc_cand",
        "name": "Tin tức CAND",
        "owner": "nhung",
        "tokens": ["02_team_crawled_raw_nhung", "posts_tin_tuc_cand"],
    },
    {
        "id": "tuoi_tre",
        "name": "Tuổi Trẻ",
        "owner": "nhung",
        "tokens": ["02_team_crawled_raw_nhung", "posts_tuoi_tre"],
    },
    {
        "id": "dantri",
        "name": "Dân trí",
        "owner": "phuc",
        "tokens": ["02_team_crawled_raw_phuc", "posts_dantri"],
    },
    {
        "id": "vnexpress",
        "name": "VnExpress",
        "owner": "phuc",
        "tokens": ["02_team_crawled_raw_phuc", "posts_vnexpress_net"],
    },
    {
        "id": "vtv24",
        "name": "Tin tức VTV24",
        "owner": "phuc",
        "tokens": ["02_team_crawled_raw_phuc", "posts_tin_tuc_vtv24"],
    },
    {
        "id": "vietnamnet",
        "name": "Vietnamnet",
        "owner": "yen",
        "tokens": ["02_team_crawled_raw_yen", "posts_vietnamnet_vn"],
    },
]


def slug_text(value: Any) -> str:
    text = clean_text(value).replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def match_press_rule(path: Path, data_dir: Path) -> Optional[Dict[str, Any]]:
    path_slug = slug_text(path.relative_to(data_dir).as_posix())
    for rule in PRESS_SOURCE_RULES:
        if all(token in path_slug for token in rule["tokens"]):
            return rule
    return None


def discover_press_files(data_dir: Path) -> List[Tuple[Path, Dict[str, Any]]]:
    matched: List[Tuple[Path, Dict[str, Any]]] = []
    for path in discover_json_post_files(data_dir):
        rule = match_press_rule(path, data_dir)
        if rule is not None:
            matched.append((path, rule))
    return sorted(matched, key=lambda item: item[0].as_posix())


def apply_press_source_overrides(row: Dict[str, Any], rule: Dict[str, Any]) -> None:
    row["page_name"] = rule["name"]

    handle = clean_text(rule.get("handle"))
    if handle and not clean_text(row.get("page_handle")):
        row["page_handle"] = handle
    if handle and not clean_text(row.get("page_url")):
        row["page_url"] = f"https://www.facebook.com/{handle}"

    set_dedup_key(row)


def write_readme(
    output_dir: Path,
    master_path: Path,
    annotation_path: Path,
    rows: List[Dict[str, Any]],
    annotation_rows: int,
    selected_files: List[Tuple[Path, Dict[str, Any]]],
    data_dir: Path,
    skipped: List[Dict[str, str]],
) -> None:
    source_stats: Dict[str, Dict[str, Any]] = {}
    for rule in PRESS_SOURCE_RULES:
        source_stats[rule["id"]] = {
            "name": rule["name"],
            "owner": rule["owner"],
            "raw_rows": 0,
            "unique_rows": 0,
            "files": [],
        }

    for path, rule in selected_files:
        source_stats[rule["id"]]["files"].append(path.relative_to(data_dir).as_posix())

    for row in rows:
        source_id = clean_text(row.get("_press_source_id"))
        if not source_id:
            continue
        source_stats[source_id]["raw_rows"] += 1
        if int(row.get("is_duplicate") or 0) == 0:
            source_stats[source_id]["unique_rows"] += 1

    unique_rows = [row for row in rows if int(row.get("is_duplicate") or 0) == 0]
    usable_counts = {
        "usable_for_topic_labeling": sum(int(r.get("usable_for_topic_labeling") or 0) for r in unique_rows),
        "needs_topic_label": sum(int(r.get("needs_topic_label") or 0) for r in unique_rows),
        "usable_for_topic_training": sum(int(r.get("usable_for_topic_training") or 0) for r in unique_rows),
        "usable_for_reaction_analysis": sum(int(r.get("usable_for_reaction_analysis") or 0) for r in unique_rows),
        "usable_for_engagement_analysis": sum(int(r.get("usable_for_engagement_analysis") or 0) for r in unique_rows),
        "usable_for_time_analysis": sum(int(r.get("usable_for_time_analysis") or 0) for r in unique_rows),
    }

    source_table_lines = [
        "| Nguồn | Owner | Raw rows | Unique rows | File raw |",
        "|---|---|---:|---:|---|",
    ]
    for rule in PRESS_SOURCE_RULES:
        stat = source_stats[rule["id"]]
        files = "<br>".join(f"`{file}`" for file in stat["files"]) if stat["files"] else "Không tìm thấy"
        source_table_lines.append(
            f"| {stat['name']} | {stat['owner']} | {stat['raw_rows']} | {stat['unique_rows']} | {files} |"
        )

    skipped_text = "Không có."
    if skipped:
        skipped_text = "\n".join(f"- `{item['path']}`: {item['reason']}" for item in skipped)

    readme = f"""# Báo chí only

Folder này chứa dataset chỉ gồm các nguồn báo chí/news đã chọn từ raw:

```text
data/01_Raw_Data/
```

Không lấy dữ liệu từ Archive.

## File trong folder

| File | Dòng | Cột | Duplicate | Dùng để làm gì |
|---|---:|---:|---:|---|
| `{master_path.name}` | {len(unique_rows):,} | {len(ENRICHED_COLUMNS)} | 0 | Master báo chí duy nhất, đã dedup và có cột enriched. |
| `{annotation_path.name}` | {annotation_rows:,} | {len(ANNOTATION_COLUMNS)} | 0 | Template gán nhãn topic cho các post báo chí có caption. |

## Nguồn được lấy

{chr(10).join(source_table_lines)}

## Cờ usable hiện tại

```text
usable_for_topic_labeling:      {usable_counts['usable_for_topic_labeling']:,}
needs_topic_label:              {usable_counts['needs_topic_label']:,}
usable_for_topic_training:      {usable_counts['usable_for_topic_training']:,}
usable_for_reaction_analysis:   {usable_counts['usable_for_reaction_analysis']:,}
usable_for_engagement_analysis: {usable_counts['usable_for_engagement_analysis']:,}
usable_for_time_analysis:       {usable_counts['usable_for_time_analysis']:,}
```

`usable_for_topic_training = 0` trước khi điền `topic_label_final` là bình thường.

## Cấu trúc CSV

Master dùng cùng schema với Master tổng:

```text
ENRICHED_COLUMNS trong src/build_master_facebook_posts.py
```

Hiện Master có {len(ENRICHED_COLUMNS)} cột. Annotation template dùng:

```text
ANNOTATION_COLUMNS trong src/build_master_facebook_posts.py
```

Hiện annotation template có {len(ANNOTATION_COLUMNS)} cột.

Xem header trực tiếp:

```bash
python3 - <<'PY'
import csv

for path in [
    "data/02_Processed_Data/Báo chí only/{master_path.name}",
    "data/02_Processed_Data/Báo chí only/{annotation_path.name}",
]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        print(path)
        print("Số cột:", len(reader.fieldnames or []))
        print(reader.fieldnames)
        print()
PY
```

## Rule quan trọng

```text
has_page_followers = 1
nếu page_followers > 0
```

```text
usable_for_reaction_analysis = 1
nếu total_reactions có giá trị
và like + love + haha + wow + sad + angry + care + sorry == total_reactions
```

## Build lại

```bash
python3 src/build_master_bao_chi_posts.py
```

Sau khi điền nhãn trong template, merge lại:

```bash
python3 src/build_master_bao_chi_posts.py \\
  --annotation-file "data/02_Processed_Data/Báo chí only/{annotation_path.name}"
```

## File bị bỏ qua

{skipped_text}
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")


def build_press_master(
    data_dir: Path,
    output_dir: Path,
    label_mode: str,
    annotation_file: Optional[Path] = None,
) -> Tuple[Path, Path]:
    rows: List[Dict[str, Any]] = []
    skipped: List[Dict[str, str]] = []
    selected_files = discover_press_files(data_dir)
    found_source_ids = {rule["id"] for _, rule in selected_files}

    for rule in PRESS_SOURCE_RULES:
        if rule["id"] not in found_source_ids:
            skipped.append({"path": rule["name"], "reason": "source_file_not_found"})

    for path, rule in selected_files:
        try:
            count = 0
            for idx, item in iter_json_records(path):
                if "post_content" not in item:
                    continue
                row = normalize_json_post(item, path, data_dir, idx, label_mode)
                apply_press_source_overrides(row, rule)
                row["_press_source_id"] = rule["id"]
                row["_press_source_name"] = rule["name"]
                rows.append(row)
                count += 1
            if count == 0:
                skipped.append({"path": path.as_posix(), "reason": "no_post_records"})
        except Exception as exc:
            skipped.append({"path": path.as_posix(), "reason": f"read_error:{exc}"})

    rows.sort(key=row_priority)
    assign_duplicates(rows)

    if annotation_file is not None:
        applied = apply_annotation_file(rows, annotation_file)
        skipped.append({"path": annotation_file.as_posix(), "reason": f"annotation_applied:{applied}_rows"})

    output_dir.mkdir(parents=True, exist_ok=True)
    master_path = output_dir / "Master_Facebook_News_Posts_Bao_Chi_Only.csv"
    annotation_path = output_dir / "Annotation_Template_Bao_Chi_Only.csv"
    deduped_rows = [row for row in rows if int(row.get("is_duplicate") or 0) == 0]

    write_csv(master_path, deduped_rows, ENRICHED_COLUMNS)
    write_annotation_template(annotation_path, deduped_rows, unique_only=False)

    annotation_rows = 0
    with annotation_path.open("r", encoding="utf-8-sig", newline="") as f:
        annotation_rows = max(sum(1 for _ in csv.DictReader(f)), 0)

    write_readme(output_dir, master_path, annotation_path, rows, annotation_rows, selected_files, data_dir, skipped)
    return master_path, annotation_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build press-only Master Facebook News Posts CSV.")
    parser.add_argument("--data-dir", default="data", help="Path to reorganized data directory.")
    parser.add_argument(
        "--output-dir",
        default="data/02_Processed_Data/Báo chí only",
        help="Directory where press-only CSV files will be written.",
    )
    parser.add_argument(
        "--label-mode",
        choices=["empty-final", "old-as-weak"],
        default="empty-final",
        help="Keep final labels empty or reuse old labels as weak labels if present.",
    )
    parser.add_argument(
        "--annotation-file",
        default="",
        help="Optional CSV file containing record_id and final annotation columns.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    annotation_file = Path(args.annotation_file) if args.annotation_file else None
    master_path, annotation_path = build_press_master(
        Path(args.data_dir),
        Path(args.output_dir),
        args.label_mode,
        annotation_file,
    )
    print(f"Wrote press-only master CSV: {master_path}")
    print(f"Wrote press-only annotation template: {annotation_path}")
    print(f"Wrote README: {Path(args.output_dir) / 'README.md'}")


if __name__ == "__main__":
    main()

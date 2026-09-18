#!/usr/bin/env python3
"""Build the team-crawled-only Master CSV.

This script keeps only rows from data/01_Raw_Data/02_Team_Crawled_Raw that
have a non-empty page_name. ViTrend/Archive sources are excluded.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from build_master_facebook_posts import (
    ENRICHED_COLUMNS,
    apply_annotation_file,
    assign_duplicates,
    clean_text,
    discover_json_post_files,
    iter_json_records,
    normalize_json_post,
    row_priority,
    set_dedup_key,
    write_csv,
)


TEAM_MASTER_SCHEMA_VERSION = "teamcrawl_v1"

REMOVED_MASTER_COLUMNS = {
    # Constant in this dataset.
    "data_origin",
    "data_source_group",
    "source_type",
    # Master output is already deduped, so these are redundant.
    "is_duplicate",
    "duplicate_of",
    # No ViTrend/targeted labels are used in team-crawl-only data.
    "old_label",
    "old_topic_label",
    "old_label_source",
    # These currently duplicate post_content_for_labeling.
    "post_content_raw",
    "post_content_clean",
    # TeamCrawl currently uses exactly three usable_* flags.
    "usable_for_topic_labeling",
    "usable_for_topic_training",
    "usable_for_topic_evaluation",
    "usable_for_time_analysis",
}

def build_team_master_columns() -> List[str]:
    columns: List[str] = []
    for col in ENRICHED_COLUMNS:
        if col == "usable_for_topic_labeling":
            columns.append("usable_for_topic_classification")
        if col in REMOVED_MASTER_COLUMNS:
            continue
        columns.append(col)
    return columns


TEAM_MASTER_COLUMNS = build_team_master_columns()

TEAM_ANNOTATION_COLUMNS = [
    "record_id",
    "usable_for_topic_classification",
    "needs_topic_label",
    "page_name",
    "post_url",
    "post_content_for_labeling",
    "topic_label_final",
    "topic_label_id",
    "label_status",
    "label_source",
    "annotator_1",
    "annotator_2",
    "annotation_round",
    "annotation_note",
    "is_uncertain_label",
]

PAGE_NAME_OVERRIDES_BY_FILE = {
    "posts_nguoilaodong.json": "Người Lao Động",
}


def is_team_crawled_path(path: Path, data_dir: Path) -> bool:
    rel = path.relative_to(data_dir).as_posix()
    return rel.startswith("01_Raw_Data/02_Team_Crawled_Raw/")


def discover_team_post_files(data_dir: Path) -> List[Path]:
    return [path for path in discover_json_post_files(data_dir) if is_team_crawled_path(path, data_dir)]


def normalize_team_row(item: Dict[str, Any], path: Path, data_dir: Path, idx: int, label_mode: str) -> Dict[str, Any]:
    row = normalize_json_post(item, path, data_dir, idx, label_mode)
    row["master_schema_version"] = TEAM_MASTER_SCHEMA_VERSION
    if path.name in PAGE_NAME_OVERRIDES_BY_FILE:
        row["page_name"] = PAGE_NAME_OVERRIDES_BY_FILE[path.name]
        set_dedup_key(row)
    return row


def set_team_usage_flags(row: Dict[str, Any]) -> None:
    has_content = bool(clean_text(row.get("post_content_for_labeling")))
    has_final_label = bool(clean_text(row.get("topic_label_final")))
    row["usable_for_topic_classification"] = 1 if has_content else 0
    row["needs_topic_label"] = 1 if has_content and not has_final_label else 0


def write_team_annotation_template(path: Path, rows: List[Dict[str, Any]]) -> None:
    template_rows = [row for row in rows if int(row.get("usable_for_topic_classification") or 0) == 1]
    write_csv(path, template_rows, TEAM_ANNOTATION_COLUMNS)


def build_team_master(
    data_dir: Path,
    output_dir: Path,
    label_mode: str,
    annotation_file: Optional[Path] = None,
) -> Tuple[Path, Path, Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    skipped: List[Dict[str, str]] = []

    for path in discover_team_post_files(data_dir):
        try:
            count = 0
            for idx, item in iter_json_records(path):
                if "post_content" not in item:
                    continue

                row = normalize_team_row(item, path, data_dir, idx, label_mode)
                if not clean_text(row.get("page_name")):
                    skipped.append({"path": path.as_posix(), "reason": f"missing_page_name:index_{idx}"})
                    continue

                rows.append(row)
                count += 1

            if count == 0:
                skipped.append({"path": path.as_posix(), "reason": "no_post_records_after_filter"})
        except Exception as exc:
            skipped.append({"path": path.as_posix(), "reason": f"read_error:{exc}"})

    rows.sort(key=row_priority)
    assign_duplicates(rows)
    for row in rows:
        set_team_usage_flags(row)

    if annotation_file is not None:
        applied = apply_annotation_file(rows, annotation_file)
        for row in rows:
            set_team_usage_flags(row)
        skipped.append({"path": annotation_file.as_posix(), "reason": f"annotation_applied:{applied}_rows"})

    deduped_rows = [row for row in rows if int(row.get("is_duplicate") or 0) == 0]

    output_dir.mkdir(parents=True, exist_ok=True)
    master_path = output_dir / "Master_Facebook_News_Posts_TeamCrawl.csv"
    annotation_path = output_dir / "Annotation_Template_TeamCrawl.csv"

    write_csv(master_path, deduped_rows, TEAM_MASTER_COLUMNS)
    write_team_annotation_template(annotation_path, deduped_rows)

    summary = {
        "raw_rows_after_filter": len(rows),
        "master_rows": len(deduped_rows),
        "duplicate_rows_removed": len(rows) - len(deduped_rows),
        "master_columns": len(TEAM_MASTER_COLUMNS),
        "annotation_rows": sum(int(row.get("usable_for_topic_classification") or 0) for row in deduped_rows),
        "annotation_columns": len(TEAM_ANNOTATION_COLUMNS),
        "skipped_rows_or_files": len(skipped),
        "removed_master_columns": sorted(REMOVED_MASTER_COLUMNS),
    }
    return master_path, annotation_path, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build team-crawled-only Master Facebook News Posts CSV.")
    parser.add_argument("--data-dir", default="data", help="Path to reorganized data directory.")
    parser.add_argument(
        "--output-dir",
        default="data/02_Processed_Data",
        help="Directory where TeamCrawl CSV files will be written.",
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
    master_path, annotation_path, summary = build_team_master(
        Path(args.data_dir),
        Path(args.output_dir),
        args.label_mode,
        annotation_file,
    )

    print(f"Wrote team-crawl master CSV: {master_path}")
    print(f"Wrote team-crawl annotation template: {annotation_path}")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()

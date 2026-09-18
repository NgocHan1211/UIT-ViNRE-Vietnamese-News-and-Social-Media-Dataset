#!/usr/bin/env python3
"""Create annotator split files from the TeamCrawl master dataset.

Default behavior:
- Load the deduplicated TeamCrawl master CSV.
- Remove rows whose post_content_for_labeling appears in any pilot CSV.
- Select 100 common overlap rows with a fixed random seed.
- Split the remaining rows evenly across annotators A/B/C.
- Put private usable_for_engagement=1 rows before 0 rows.
- Write annotation CSVs, internal logs, validation checks, and a report.
"""

from __future__ import annotations

import argparse
import csv
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


DEFAULT_MASTER_PATH = Path("data/02_Processed_Data/Master_Facebook_News_Posts_TeamCrawl_After_Dedup.csv")
DEFAULT_PILOT_DIR = Path("data/04_Labeling_Pilot")
DEFAULT_SCHEMA_REF = DEFAULT_PILOT_DIR / "Topic Annotation Pilot Set 100 [2] - IAA_Merge.csv"
DEFAULT_OUTPUT_DIR = Path("data/05_Labeling")
DEFAULT_SEED = 42
DEFAULT_COMMON_SIZE = 100

ANNOTATION_COLUMNS = [
    "record_id",
    "usable_for_topic_classification",
    "usable_for_engagement",
    "needs_topic_label",
    "page_name",
    "post_content_for_labeling",
    "annotator_topic_label",
    "annotator_topic_id",
    "annotator_note",
    "annotator_uncertain",
    "label_status",
]

ASSIGNMENT_LOG_COLUMNS = [
    "record_id",
    "post_content_for_labeling",
    "normalized_post_content",
    "page_name",
    "usable_for_topic_classification",
    "usable_for_engagement",
    "needs_topic_label",
    "sampling_group",
    "is_common_overlap",
    "assigned_to",
    "row_position_in_annotation_file",
    "source_pool",
    "removed_from_pilot",
]

REMOVED_PILOT_LOG_COLUMNS = [
    "record_id",
    "post_content_for_labeling",
    "normalized_post_content",
    "matched_pilot_file",
    "reason_removed",
]

INTERNAL_FORBIDDEN_COLUMNS = {
    "normalized_post_content",
    "sampling_group",
    "is_common_overlap",
    "assigned_to",
    "assigned_annotator",
    "source_file",
    "source_pool",
    "row_order_type",
    "is_pilot_removed",
    "split",
    "sampling_method",
}

ZERO_WIDTH_RE = re.compile("[\u200b\u200c\u200d\ufeff]")
SPACE_RE = re.compile(r"\s+")

CsvRow = Dict[str, str]


def normalize_content(value: object) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = ZERO_WIDTH_RE.sub("", text)
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    text = SPACE_RE.sub(" ", text)
    return text.strip().casefold()


def truthy_1(value: object) -> str:
    return "1" if str(value).strip().lower() in {"1", "1.0", "true", "yes"} else "0"


def read_csv(path: Path) -> Tuple[List[str], List[CsvRow]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [dict(row) for row in reader]
        fieldnames = list(reader.fieldnames or [])
    return fieldnames, rows


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[CsvRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def annotation_row(master_row: CsvRow) -> CsvRow:
    return {
        "record_id": master_row.get("record_id", ""),
        "usable_for_topic_classification": truthy_1(master_row.get("usable_for_topic_classification", "")),
        "usable_for_engagement": truthy_1(
            master_row.get("usable_for_engagement_analysis", master_row.get("usable_for_engagement", ""))
        ),
        "needs_topic_label": truthy_1(master_row.get("needs_topic_label", "")),
        "page_name": master_row.get("page_name", ""),
        "post_content_for_labeling": master_row.get("post_content_for_labeling", ""),
        "annotator_topic_label": "",
        "annotator_topic_id": "",
        "annotator_note": "",
        "annotator_uncertain": "",
        "label_status": "unlabeled",
    }


def sort_private_rows(rows: List[CsvRow], seed: int, seed_offset: int) -> List[CsvRow]:
    usable = [row for row in rows if annotation_row(row)["usable_for_engagement"] == "1"]
    unusable = [row for row in rows if annotation_row(row)["usable_for_engagement"] == "0"]
    random.Random(seed + seed_offset).shuffle(usable)
    random.Random(seed + seed_offset + 1000).shuffle(unusable)
    return usable + unusable


def load_pilot_contents(pilot_dir: Path) -> Tuple[List[Path], Dict[str, List[str]], List[CsvRow]]:
    pilot_files = sorted(pilot_dir.glob("*.csv"))
    pilot_content_to_files: Dict[str, List[str]] = defaultdict(list)
    pilot_file_counts: List[CsvRow] = []

    for path in pilot_files:
        fieldnames, rows = read_csv(path)
        if "post_content_for_labeling" not in fieldnames:
            pilot_file_counts.append(
                {
                    "pilot_file": path.name,
                    "rows": str(len(rows)),
                    "usable_content_rows": "0",
                    "unique_normalized_contents": "0",
                    "skipped": "missing_post_content_for_labeling",
                }
            )
            continue

        local_keys = set()
        usable_content_rows = 0
        for row in rows:
            key = normalize_content(row.get("post_content_for_labeling", ""))
            if not key:
                continue
            usable_content_rows += 1
            local_keys.add(key)
            if path.name not in pilot_content_to_files[key]:
                pilot_content_to_files[key].append(path.name)

        pilot_file_counts.append(
            {
                "pilot_file": path.name,
                "rows": str(len(rows)),
                "usable_content_rows": str(usable_content_rows),
                "unique_normalized_contents": str(len(local_keys)),
                "skipped": "",
            }
        )

    return pilot_files, pilot_content_to_files, pilot_file_counts


def filter_master_pool(
    master_rows: List[CsvRow],
    pilot_content_to_files: Dict[str, List[str]],
) -> Tuple[List[CsvRow], List[CsvRow], List[CsvRow], List[CsvRow], List[CsvRow]]:
    pilot_keys = set(pilot_content_to_files)
    removed_pilot_log: List[CsvRow] = []
    blank_content_removed: List[CsvRow] = []
    duplicate_record_removed: List[CsvRow] = []
    duplicate_content_removed: List[CsvRow] = []
    pool: List[CsvRow] = []
    seen_record_id = set()
    seen_content = set()

    for row in master_rows:
        record_id = str(row.get("record_id", "")).strip()
        content = row.get("post_content_for_labeling", "")
        norm = normalize_content(content)
        if not norm:
            blank_content_removed.append(row)
            continue

        if norm in pilot_keys:
            removed_pilot_log.append(
                {
                    "record_id": record_id,
                    "post_content_for_labeling": content,
                    "normalized_post_content": norm,
                    "matched_pilot_file": "; ".join(sorted(pilot_content_to_files[norm])),
                    "reason_removed": "matched_post_content_for_labeling_in_pilot",
                }
            )
            continue

        if record_id in seen_record_id:
            duplicate_record_removed.append(row)
            continue

        if norm in seen_content:
            duplicate_content_removed.append(row)
            continue

        seen_record_id.add(record_id)
        seen_content.add(norm)
        row["_normalized_post_content"] = norm
        pool.append(row)

    return pool, removed_pilot_log, blank_content_removed, duplicate_record_removed, duplicate_content_removed


def split_pool(pool: List[CsvRow], common_size: int, seed: int) -> Tuple[List[CsvRow], Dict[str, List[CsvRow]]]:
    if len(pool) < common_size:
        raise ValueError(f"Pool has only {len(pool)} rows; need at least {common_size} common overlap rows.")

    common_indices = random.Random(seed).sample(range(len(pool)), common_size)
    common_index_set = set(common_indices)
    common_overlap = [pool[i] for i in common_indices]
    private_pool = [row for i, row in enumerate(pool) if i not in common_index_set]

    private_pool_shuffled = private_pool[:]
    random.Random(seed).shuffle(private_pool_shuffled)

    n_private = len(private_pool_shuffled)
    base = n_private // 3
    remainder = n_private % 3
    sizes = {
        "A": base + (1 if remainder >= 1 else 0),
        "B": base + (1 if remainder >= 2 else 0),
        "C": base,
    }

    private_raw: Dict[str, List[CsvRow]] = {}
    start = 0
    for annotator in ["A", "B", "C"]:
        end = start + sizes[annotator]
        private_raw[annotator] = private_pool_shuffled[start:end]
        start = end

    private_ordered = {
        "A": sort_private_rows(private_raw["A"], seed, 101),
        "B": sort_private_rows(private_raw["B"], seed, 202),
        "C": sort_private_rows(private_raw["C"], seed, 303),
    }
    return common_overlap, private_ordered


def build_annotation_files(
    output_dir: Path,
    common_overlap: List[CsvRow],
    private_ordered: Dict[str, List[CsvRow]],
) -> Dict[str, List[CsvRow]]:
    annotations: Dict[str, List[CsvRow]] = {}
    common_rows = [annotation_row(row) for row in common_overlap]
    write_csv(output_dir / "common_overlap_100.csv", ANNOTATION_COLUMNS, common_rows)

    for annotator in ["A", "B", "C"]:
        private_rows = [annotation_row(row) for row in private_ordered[annotator]]
        rows = common_rows + private_rows
        annotations[annotator] = rows
        write_csv(output_dir / f"annotation_{annotator}.csv", ANNOTATION_COLUMNS, rows)
        write_csv(output_dir / f"private_{annotator}.csv", ANNOTATION_COLUMNS, private_rows)

    return annotations


def build_assignment_log(
    common_overlap: List[CsvRow],
    private_ordered: Dict[str, List[CsvRow]],
    source_pool_name: str,
) -> List[CsvRow]:
    assignment_log: List[CsvRow] = []

    for pos, row in enumerate(common_overlap, start=1):
        ann = annotation_row(row)
        assignment_log.append(
            {
                "record_id": ann["record_id"],
                "post_content_for_labeling": ann["post_content_for_labeling"],
                "normalized_post_content": row["_normalized_post_content"],
                "page_name": ann["page_name"],
                "usable_for_topic_classification": ann["usable_for_topic_classification"],
                "usable_for_engagement": ann["usable_for_engagement"],
                "needs_topic_label": ann["needs_topic_label"],
                "sampling_group": "common_overlap",
                "is_common_overlap": "1",
                "assigned_to": "A,B,C",
                "row_position_in_annotation_file": str(pos),
                "source_pool": source_pool_name,
                "removed_from_pilot": "0",
            }
        )

    for annotator in ["A", "B", "C"]:
        for pos, row in enumerate(private_ordered[annotator], start=101):
            ann = annotation_row(row)
            assignment_log.append(
                {
                    "record_id": ann["record_id"],
                    "post_content_for_labeling": ann["post_content_for_labeling"],
                    "normalized_post_content": row["_normalized_post_content"],
                    "page_name": ann["page_name"],
                    "usable_for_topic_classification": ann["usable_for_topic_classification"],
                    "usable_for_engagement": ann["usable_for_engagement"],
                    "needs_topic_label": ann["needs_topic_label"],
                    "sampling_group": "private_assignment",
                    "is_common_overlap": "0",
                    "assigned_to": annotator,
                    "row_position_in_annotation_file": str(pos),
                    "source_pool": source_pool_name,
                    "removed_from_pilot": "0",
                }
            )

    return assignment_log


def duplicate_count(values: Iterable[str]) -> int:
    return sum(count - 1 for count in Counter(values).values() if count > 1)


def private_order_ok(rows: List[CsvRow], common_size: int) -> bool:
    seen_zero = False
    for row in rows[common_size:]:
        if row["usable_for_engagement"] == "0":
            seen_zero = True
        elif seen_zero and row["usable_for_engagement"] == "1":
            return False
    return True


def validate_outputs(
    annotations: Dict[str, List[CsvRow]],
    assignment_log: List[CsvRow],
    pool: List[CsvRow],
    pilot_keys: set,
    common_size: int,
) -> List[CsvRow]:
    validation: List[CsvRow] = []

    def add_check(name: str, passed: bool, detail: str) -> None:
        validation.append({"check": name, "passed": "PASS" if passed else "FAIL", "detail": detail})

    all_annotation_rows = annotations["A"] + annotations["B"] + annotations["C"]
    private_record_sets = {
        a: {row["record_id"] for row in annotations[a][common_size:]}
        for a in ["A", "B", "C"]
    }

    add_check(
        "3 annotation files have same schema",
        all(list(row.keys()) == ANNOTATION_COLUMNS for rows in annotations.values() for row in rows[:1]),
        ", ".join(ANNOTATION_COLUMNS),
    )
    forbidden_found = set(ANNOTATION_COLUMNS) & INTERNAL_FORBIDDEN_COLUMNS
    add_check(
        "annotation files do not contain internal columns",
        not forbidden_found,
        "forbidden columns found: " + ", ".join(sorted(forbidden_found)),
    )

    blank_cols = ["annotator_topic_label", "annotator_topic_id", "annotator_note", "annotator_uncertain"]
    add_check(
        "annotator columns are blank",
        all(all(row[col] == "" for col in blank_cols) for rows in annotations.values() for row in rows),
        "checked: " + ", ".join(blank_cols),
    )
    add_check(
        "label_status is unlabeled",
        all(row["label_status"] == "unlabeled" for rows in annotations.values() for row in rows),
        "all annotation rows",
    )

    first_ids = [[row["record_id"] for row in annotations[a][:common_size]] for a in ["A", "B", "C"]]
    add_check(
        "first 100 rows have same record_id and order in A/B/C",
        first_ids[0] == first_ids[1] == first_ids[2],
        f"first_common={first_ids[0][0]} last_common={first_ids[0][-1]}",
    )

    private_overlap_count = (
        len(private_record_sets["A"] & private_record_sets["B"])
        + len(private_record_sets["B"] & private_record_sets["C"])
        + len(private_record_sets["C"] & private_record_sets["A"])
    )
    add_check(
        "private A/B/C record_id do not overlap",
        private_overlap_count == 0,
        f"pairwise private overlap count={private_overlap_count}",
    )

    annotation_pilot_overlap = [
        row for row in all_annotation_rows if normalize_content(row["post_content_for_labeling"]) in pilot_keys
    ]
    add_check(
        "annotation rows do not overlap pilot contents",
        len(annotation_pilot_overlap) == 0,
        f"pilot overlaps in annotation={len(annotation_pilot_overlap)}",
    )

    record_dup_detail = "; ".join(
        f"{a}={duplicate_count(row['record_id'] for row in annotations[a])}" for a in ["A", "B", "C"]
    )
    add_check(
        "no duplicate record_id within each annotation file",
        all(duplicate_count(row["record_id"] for row in annotations[a]) == 0 for a in ["A", "B", "C"]),
        record_dup_detail,
    )

    content_dup_detail = "; ".join(
        f"{a}={duplicate_count(normalize_content(row['post_content_for_labeling']) for row in annotations[a])}"
        for a in ["A", "B", "C"]
    )
    add_check(
        "no duplicate post_content_for_labeling within each annotation file",
        all(
            duplicate_count(normalize_content(row["post_content_for_labeling"]) for row in annotations[a]) == 0
            for a in ["A", "B", "C"]
        ),
        content_dup_detail,
    )

    add_check(
        "private usable_for_engagement=1 rows come before 0 rows",
        all(private_order_ok(annotations[a], common_size) for a in ["A", "B", "C"]),
        "; ".join(f"{a}={private_order_ok(annotations[a], common_size)}" for a in ["A", "B", "C"]),
    )

    unique_assignment_records = len({row["record_id"] for row in assignment_log})
    add_check(
        "assignment_log unique record_id equals filtered pool rows",
        unique_assignment_records == len(pool),
        f"unique_assignment_log={unique_assignment_records}; pool={len(pool)}",
    )

    total_annotation_rows = sum(len(annotations[a]) for a in ["A", "B", "C"])
    add_check(
        "total annotation rows equals unique records + 200",
        total_annotation_rows == len(pool) + (2 * common_size),
        f"total_annotation_rows={total_annotation_rows}; unique_records+200={len(pool) + (2 * common_size)}",
    )

    return validation


def build_distribution_rows(annotations: Dict[str, List[CsvRow]], common_size: int) -> List[CsvRow]:
    rows: List[CsvRow] = []
    for annotator in ["A", "B", "C"]:
        annotation_rows = annotations[annotator]
        private_rows = annotation_rows[common_size:]
        rows.append(
            {
                "annotator": annotator,
                "total_rows": str(len(annotation_rows)),
                "common_rows": str(common_size),
                "private_rows": str(len(private_rows)),
                "total_usable_for_engagement_1": str(
                    sum(1 for row in annotation_rows if row["usable_for_engagement"] == "1")
                ),
                "total_usable_for_engagement_0": str(
                    sum(1 for row in annotation_rows if row["usable_for_engagement"] == "0")
                ),
                "private_usable_for_engagement_1": str(
                    sum(1 for row in private_rows if row["usable_for_engagement"] == "1")
                ),
                "private_usable_for_engagement_0": str(
                    sum(1 for row in private_rows if row["usable_for_engagement"] == "0")
                ),
            }
        )
    return rows


def write_report(
    output_dir: Path,
    master_path: Path,
    pilot_dir: Path,
    schema_ref: Path,
    schema_ref_columns: List[str],
    pilot_files: List[Path],
    pilot_file_counts: List[CsvRow],
    master_rows: List[CsvRow],
    pilot_key_count: int,
    removed_pilot_log: List[CsvRow],
    blank_content_removed: List[CsvRow],
    duplicate_record_removed: List[CsvRow],
    duplicate_content_removed: List[CsvRow],
    pool: List[CsvRow],
    common_overlap: List[CsvRow],
    private_ordered: Dict[str, List[CsvRow]],
    annotations: Dict[str, List[CsvRow]],
    distribution_rows: List[CsvRow],
    validation: List[CsvRow],
    seed: int,
    common_size: int,
) -> None:
    common_usable = Counter(annotation_row(row)["usable_for_engagement"] for row in common_overlap)
    n_private = sum(len(private_ordered[a]) for a in ["A", "B", "C"])
    total_annotation_rows = sum(len(annotations[a]) for a in ["A", "B", "C"])

    lines: List[str] = [
        "# Split For Label Report",
        "",
        "## Input",
        "",
        f"- Script: `src/create_annotation_splits.py`",
        f"- Master: `{master_path}`",
        f"- Pilot directory: `{pilot_dir}`",
        f"- Schema reference: `{schema_ref}`",
        f"- Output directory: `{output_dir}`",
        f"- Seed: `{seed}`",
        "",
        "## Normalization",
        "",
        "Pilot matching and duplicate checks use normalized `post_content_for_labeling`: Unicode NFKC, zero-width character removal, CR/LF/tab to space, whitespace collapse, strip, and casefold.",
        "",
        "## Schema",
        "",
        f"- Pilot reference columns: {len(schema_ref_columns)}",
        "- The pilot reference is an IAA merge/adjudication file. The generated annotator files use the annotator-facing equivalent schema with required blank annotator fields and `usable_for_engagement` mapped from `usable_for_engagement_analysis`.",
        "- Internal sampling/tracking columns are excluded from annotator files and kept only in logs.",
        "",
        "Annotator file columns:",
        "",
        "```text",
        *ANNOTATION_COLUMNS,
        "```",
        "",
        "## Pilot Removal",
        "",
        f"- Master rows loaded: {len(master_rows):,}",
        f"- Pilot CSV files scanned: {len(pilot_files):,}",
        f"- Unique normalized pilot contents: {pilot_key_count:,}",
        f"- Rows removed because they matched pilot content: {len(removed_pilot_log):,}",
        f"- Rows removed because `post_content_for_labeling` was blank: {len(blank_content_removed):,}",
        f"- Rows removed as duplicate `record_id` after pilot removal: {len(duplicate_record_removed):,}",
        f"- Rows removed as duplicate normalized content after pilot removal: {len(duplicate_content_removed):,}",
        f"- Full annotation pool after filtering: {len(pool):,}",
        "",
        "Pilot files scanned:",
        "",
        "| Pilot file | Rows | Usable content rows | Unique normalized contents |",
        "|---|---:|---:|---:|",
    ]

    for row in pilot_file_counts:
        lines.append(
            f"| `{row['pilot_file']}` | {int(row['rows']):,} | "
            f"{int(row['usable_content_rows']):,} | {int(row['unique_normalized_contents']):,} |"
        )

    lines.extend(
        [
            "",
            "## Split Result",
            "",
            f"- Common overlap rows: {len(common_overlap):,}",
            f"- Private pool rows: {n_private:,}",
            f"- Common usable_for_engagement=1: {common_usable.get('1', 0):,}",
            f"- Common usable_for_engagement=0: {common_usable.get('0', 0):,}",
            "",
            "| Annotator | Total rows | Common rows | Private rows | Private usable=1 | Private usable=0 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in distribution_rows:
        lines.append(
            f"| {row['annotator']} | {int(row['total_rows']):,} | {int(row['common_rows']):,} | "
            f"{int(row['private_rows']):,} | {int(row['private_usable_for_engagement_1']):,} | "
            f"{int(row['private_usable_for_engagement_0']):,} |"
        )

    lines.extend(
        [
            "",
            f"- Total rows across annotation_A/B/C: {total_annotation_rows:,}",
            f"- Unique records to annotate: {len(pool):,}",
            f"- Expected total rows across 3 files: unique records + 200 = {len(pool) + (2 * common_size):,}",
            "",
            "## Output Files",
            "",
        ]
    )
    for name in [
        "annotation_A.csv",
        "annotation_B.csv",
        "annotation_C.csv",
        "assignment_log.csv",
        "removed_pilot_log.csv",
        "common_overlap_100.csv",
        "private_A.csv",
        "private_B.csv",
        "private_C.csv",
        "annotation_distribution_check.csv",
        "validation_check.csv",
    ]:
        lines.append(f"- `{output_dir / name}`")

    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```bash",
            "python3 src/create_annotation_splits.py",
            "```",
            "",
            "## Validation",
            "",
            "| Check | Result | Detail |",
            "|---|---|---|",
        ]
    )
    for row in validation:
        detail = row["detail"].replace("|", "\\|")
        lines.append(f"| {row['check']} | {row['passed']} | {detail} |")

    lines.extend(
        [
            "",
            "## IAA Usage",
            "",
            "Use only rows 1-100 from `annotation_A.csv`, `annotation_B.csv`, and `annotation_C.csv` for IAA. Do not compute IAA on private rows. Compute IAA before adjudication.",
            "",
            "## Notes",
            "",
            "- `label_status` is `unlabeled` for every annotator-facing row.",
            "- `annotator_topic_label`, `annotator_topic_id`, `annotator_note`, and `annotator_uncertain` are blank for every annotator-facing row.",
            "- Common rows have identical record IDs and identical order in all three annotation files.",
            "- Private rows are non-overlapping across A/B/C and are ordered with `usable_for_engagement=1` before `0`.",
        ]
    )

    (output_dir / "split_for_label_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def create_splits(args: argparse.Namespace) -> int:
    schema_ref_columns, _ = read_csv(args.schema_ref)
    master_columns, master_rows = read_csv(args.master_path)
    required_master_columns = {
        "record_id",
        "post_content_for_labeling",
        "page_name",
        "usable_for_topic_classification",
        "needs_topic_label",
        "usable_for_engagement_analysis",
    }
    missing_master = sorted(required_master_columns - set(master_columns))
    if missing_master:
        raise ValueError(f"Missing master columns: {missing_master}")

    pilot_files, pilot_content_to_files, pilot_file_counts = load_pilot_contents(args.pilot_dir)
    pool, removed_pilot_log, blank_content_removed, duplicate_record_removed, duplicate_content_removed = (
        filter_master_pool(master_rows, pilot_content_to_files)
    )
    common_overlap, private_ordered = split_pool(pool, args.common_size, args.seed)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    annotations = build_annotation_files(args.output_dir, common_overlap, private_ordered)

    source_pool_name = "Master_Facebook_News_Posts_TeamCrawl_After_Dedup_after_removing_pilot"
    assignment_log = build_assignment_log(common_overlap, private_ordered, source_pool_name)
    write_csv(args.output_dir / "assignment_log.csv", ASSIGNMENT_LOG_COLUMNS, assignment_log)
    write_csv(args.output_dir / "removed_pilot_log.csv", REMOVED_PILOT_LOG_COLUMNS, removed_pilot_log)

    distribution_rows = build_distribution_rows(annotations, args.common_size)
    write_csv(args.output_dir / "annotation_distribution_check.csv", list(distribution_rows[0].keys()), distribution_rows)

    validation = validate_outputs(
        annotations=annotations,
        assignment_log=assignment_log,
        pool=pool,
        pilot_keys=set(pilot_content_to_files),
        common_size=args.common_size,
    )
    write_csv(args.output_dir / "validation_check.csv", ["check", "passed", "detail"], validation)

    write_report(
        output_dir=args.output_dir,
        master_path=args.master_path,
        pilot_dir=args.pilot_dir,
        schema_ref=args.schema_ref,
        schema_ref_columns=schema_ref_columns,
        pilot_files=pilot_files,
        pilot_file_counts=pilot_file_counts,
        master_rows=master_rows,
        pilot_key_count=len(pilot_content_to_files),
        removed_pilot_log=removed_pilot_log,
        blank_content_removed=blank_content_removed,
        duplicate_record_removed=duplicate_record_removed,
        duplicate_content_removed=duplicate_content_removed,
        pool=pool,
        common_overlap=common_overlap,
        private_ordered=private_ordered,
        annotations=annotations,
        distribution_rows=distribution_rows,
        validation=validation,
        seed=args.seed,
        common_size=args.common_size,
    )

    failures = [row for row in validation if row["passed"] != "PASS"]
    print(f"output_dir {args.output_dir}")
    print(f"master_rows {len(master_rows)}")
    print(f"pilot_files {len(pilot_files)}")
    print(f"unique_pilot_contents {len(pilot_content_to_files)}")
    print(f"removed_pilot_rows {len(removed_pilot_log)}")
    print(f"annotation_pool_rows {len(pool)}")
    print(f"common_overlap_rows {len(common_overlap)}")
    for annotator in ["A", "B", "C"]:
        print(f"annotation_{annotator}_rows {len(annotations[annotator])} private {len(annotations[annotator]) - args.common_size}")
    print(f"total_annotation_rows {sum(len(annotations[a]) for a in ['A', 'B', 'C'])}")
    print(f"expected_total_annotation_rows {len(pool) + (2 * args.common_size)}")
    print(f"validation_failures {len(failures)}")

    return 1 if failures else 0


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create A/B/C annotation split CSV files.")
    parser.add_argument("--master-path", type=Path, default=DEFAULT_MASTER_PATH)
    parser.add_argument("--pilot-dir", type=Path, default=DEFAULT_PILOT_DIR)
    parser.add_argument("--schema-ref", type=Path, default=DEFAULT_SCHEMA_REF)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--common-size", type=int, default=DEFAULT_COMMON_SIZE)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    return create_splits(args)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a post-level Master CSV from the reorganized data folder.

By default the script normalizes only post-level JSON/JSONL sources under
data/01_Raw_Data into one table. Old labeled CSV ingestion is opt-in for
audit only. It keeps duplicates for audit, then marks them with
is_duplicate/duplicate_of and writes separate deduped outputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


MASTER_SCHEMA_VERSION = "v1"

DATA_ORIGIN_PRIORITY = {
    "team_crawled": 10,
    "targeted_candidate": 20,
    "vitrend_raw": 30,
    "labeled_csv_old": 40,
    "old_or_redundant": 50,
    "debug_probe": 60,
    "unknown": 90,
}

SCHEMA_PRIORITY = {
    "schema_5_new_timestamp": 10,
    "schema_8_targeted_post_type": 20,
    "schema_7_targeted_label": 30,
    "schema_4_basic": 40,
    "schema_2_legacy_json": 50,
    "schema_3_legacy_jsonl": 55,
    "csv_old_labeled_post": 70,
    "csv_old_post_content": 75,
    "unknown": 99,
}

BASE_COLUMNS = [
    "master_schema_version",
    "record_id",
    "data_origin",
    "data_source_group",
    "crawler_owner",
    "raw_schema_type",
    "raw_file_path",
    "raw_file_name",
    "raw_record_index",
    "post_id",
    "post_url",
    "content_hash",
    "dedup_key",
    "is_duplicate",
    "duplicate_of",
    "source_type",
    "page_name",
    "page_handle",
    "page_url",
    "page_followers",
    "page_followers_raw",
    "has_page_followers",
    "post_type",
    "external_url",
    "post_content_raw",
    "post_content_clean",
    "post_content_for_labeling",
    "post_content_length",
    "word_count",
    "old_label",
    "old_topic_label",
    "old_label_source",
    "topic_label_final",
    "topic_label_id",
    "label_status",
    "label_source",
    "annotator_1",
    "annotator_2",
    "annotation_round",
    "annotation_note",
    "is_uncertain_label",
    "like_count",
    "love_count",
    "haha_count",
    "wow_count",
    "sad_count",
    "angry_count",
    "care_count",
    "sorry_count",
    "total_reactions",
    "reaction_detail_sum",
    "reaction_detail_coverage_ratio",
    "has_reaction_total",
    "has_reaction_details",
    "reaction_details_status",
    "share_count",
    "comment_count",
    "has_share_count",
    "has_comment_count",
    "has_engagement_basic",
    "post_created_time_raw",
    "post_created_time_unix",
    "post_created_time_human",
    "post_created_date",
    "post_created_hour",
    "post_created_weekday",
    "timestamp_source",
    "timestamp_status",
    "has_post_created_time",
    "crawl_time_raw",
    "crawl_time_unix",
    "crawl_time_human",
    "metadata_observed_at",
    "has_crawl_time",
    "reaction_per_follower",
    "share_per_follower",
    "comment_per_follower",
    "engagement_total",
    "engagement_per_follower",
    "usable_for_topic_labeling",
    "needs_topic_label",
    "usable_for_topic_training",
    "usable_for_topic_evaluation",
    "usable_for_reaction_analysis",
    "usable_for_engagement_analysis",
    "usable_for_time_analysis",
    "exclude_reason",
    "quality_note",
]

ENRICHED_EXTRA_COLUMNS = [
    "special_reaction_total",
    "positive_reaction_total",
    "negative_reaction_total",
    "love_ratio",
    "haha_ratio",
    "wow_ratio",
    "sad_ratio",
    "angry_ratio",
    "care_ratio",
    "approval_index",
    "outrage_index",
    "amusement_index",
    "empathy_index",
    "polarity_score",
]

ENRICHED_COLUMNS = (
    BASE_COLUMNS[: BASE_COLUMNS.index("usable_for_topic_training")]
    + ENRICHED_EXTRA_COLUMNS
    + BASE_COLUMNS[BASE_COLUMNS.index("usable_for_topic_training") :]
)

ANNOTATION_COLUMNS = [
    "record_id",
    "is_duplicate",
    "usable_for_topic_labeling",
    "needs_topic_label",
    "page_name",
    "post_url",
    "post_content_for_labeling",
    "old_label",
    "old_topic_label",
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


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\ufeff", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_text_for_hash(value: Any) -> str:
    text = clean_text(value).lower()
    return re.sub(r"\s+", " ", text)


def sha256_short(value: str, length: int = 16) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)

    text = clean_text(value)
    if not text:
        return None

    lowered = text.lower().replace(",", ".")
    multiplier = 1
    if lowered.endswith("k"):
        multiplier = 1_000
        lowered = lowered[:-1]
    elif lowered.endswith("m"):
        multiplier = 1_000_000
        lowered = lowered[:-1]

    cleaned = re.sub(r"[^0-9.\-]", "", lowered)
    if cleaned in {"", "-", ".", "-."}:
        return None
    try:
        return int(float(cleaned) * multiplier)
    except ValueError:
        return None


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = clean_text(value)
    if not text:
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def to_csv_value(value: Any) -> Any:
    if value is None:
        return ""
    return value


def unix_to_parts(ts: Optional[int]) -> Tuple[str, str, str, str]:
    if ts is None:
        return "", "", "", ""
    try:
        dt = datetime.fromtimestamp(int(ts))
    except (ValueError, OSError, OverflowError):
        return "", "", "", ""
    return (
        dt.strftime("%Y-%m-%d %H:%M:%S"),
        dt.strftime("%Y-%m-%d"),
        str(dt.hour),
        dt.strftime("%A"),
    )


def value_present(value: Any) -> bool:
    return value is not None and clean_text(value) != ""


def has_key_value(item: Dict[str, Any], key: str) -> bool:
    return key in item and value_present(item.get(key))


def infer_source_metadata(path: Path, data_dir: Path) -> Tuple[str, str, str]:
    rel = path.relative_to(data_dir).as_posix()
    parts = rel.split("/")

    if rel.startswith("01_Raw_Data/01_Existing_ViTrend_Raw/"):
        return "vitrend_raw", "Existing_ViTrend_Raw", "vitrend"

    if rel.startswith("01_Raw_Data/02_Team_Crawled_Raw/"):
        owner = parts[2].lower() if len(parts) > 2 else "unknown"
        return "team_crawled", "Team_Crawled_Raw", owner

    if rel.startswith("03_Archive_Not_For_Training/labeled_unused/json-targeted-crawl/"):
        owner = "han" if path.name.startswith("Han_") else "unknown"
        return "targeted_candidate", "Archive_Labeled_Unused", owner

    if rel.startswith("03_Archive_Not_For_Training/labeled_unused/csv-data(labeled)/"):
        return "labeled_csv_old", "Archive_Labeled_Unused", "unknown"

    if rel.startswith("03_Archive_Not_For_Training/debug_probe/"):
        return "debug_probe", "Archive_Debug_Probe", "unknown"

    if rel.startswith("03_Archive_Not_For_Training/old_or_redundant/"):
        return "old_or_redundant", "Archive_Old_Or_Redundant", "unknown"

    return "unknown", "unknown", "unknown"


def infer_json_schema(item: Dict[str, Any], path: Path) -> str:
    if "reactions_detail" in item:
        return "schema_3_legacy_jsonl" if path.suffix == ".jsonl" else "schema_2_legacy_json"
    if "label" in item or "topic_label" in item:
        return "schema_7_targeted_label"
    if "post_timestamp_unix" in item or "post_timestamp_human" in item:
        return "schema_5_new_timestamp"
    if "post_type" in item or "external_url" in item:
        return "schema_8_targeted_post_type"
    if "source_type" in item and "post_content" in item:
        return "schema_4_basic"
    return "unknown"


def empty_row() -> Dict[str, Any]:
    row = {col: "" for col in ENRICHED_COLUMNS}
    row["master_schema_version"] = MASTER_SCHEMA_VERSION
    row["is_duplicate"] = 0
    row["is_uncertain_label"] = 0
    row["has_page_followers"] = 0
    row["has_reaction_total"] = 0
    row["has_reaction_details"] = 0
    row["has_share_count"] = 0
    row["has_comment_count"] = 0
    row["has_engagement_basic"] = 0
    row["has_post_created_time"] = 0
    row["has_crawl_time"] = 0
    row["usable_for_topic_labeling"] = 0
    row["needs_topic_label"] = 0
    row["usable_for_topic_training"] = 0
    row["usable_for_topic_evaluation"] = 0
    row["usable_for_reaction_analysis"] = 0
    row["usable_for_engagement_analysis"] = 0
    row["usable_for_time_analysis"] = 0
    return row


def set_source_fields(row: Dict[str, Any], path: Path, data_dir: Path, raw_schema_type: str, index: int) -> None:
    data_origin, data_source_group, crawler_owner = infer_source_metadata(path, data_dir)
    row["data_origin"] = data_origin
    row["data_source_group"] = data_source_group
    row["crawler_owner"] = crawler_owner
    row["raw_schema_type"] = raw_schema_type
    row["raw_file_path"] = path.as_posix()
    row["raw_file_name"] = path.name
    row["raw_record_index"] = index


def set_content_fields(row: Dict[str, Any], raw_content: Any) -> None:
    raw = clean_text(raw_content)
    row["post_content_raw"] = raw
    row["post_content_clean"] = raw
    row["post_content_for_labeling"] = raw
    row["post_content_length"] = len(raw)
    row["word_count"] = len(raw.split()) if raw else 0
    row["content_hash"] = sha256_short(normalize_text_for_hash(raw))


def set_dedup_key(row: Dict[str, Any]) -> None:
    post_id = clean_text(row.get("post_id"))
    post_url = clean_text(row.get("post_url"))
    content_hash = clean_text(row.get("content_hash"))
    page_name = clean_text(row.get("page_name")).lower()
    raw_file = clean_text(row.get("raw_file_path"))
    raw_idx = clean_text(row.get("raw_record_index"))

    if post_id:
        row["dedup_key"] = f"post_id:{post_id}"
    elif post_url:
        row["dedup_key"] = f"post_url:{post_url}"
    elif content_hash and page_name:
        row["dedup_key"] = f"content_page:{content_hash}:{page_name}"
    elif content_hash:
        row["dedup_key"] = f"content:{content_hash}"
    else:
        row["dedup_key"] = f"raw:{raw_file}:{raw_idx}"


def set_reaction_status(row: Dict[str, Any], detail_keys_present: bool, total_key_present: bool) -> None:
    detail_cols = [
        "like_count",
        "love_count",
        "haha_count",
        "wow_count",
        "sad_count",
        "angry_count",
        "care_count",
        "sorry_count",
    ]
    detail_sum = sum(safe_int(row.get(col)) or 0 for col in detail_cols)
    total = safe_int(row.get("total_reactions"))

    row["reaction_detail_sum"] = detail_sum if detail_keys_present else ""
    row["has_reaction_details"] = 1 if detail_keys_present else 0
    row["has_reaction_total"] = 1 if total_key_present else 0

    if total is not None and detail_keys_present:
        if total > 0:
            row["reaction_detail_coverage_ratio"] = round(detail_sum / total, 6)
        elif detail_sum == 0:
            row["reaction_detail_coverage_ratio"] = 1.0
        else:
            row["reaction_detail_coverage_ratio"] = ""
    else:
        row["reaction_detail_coverage_ratio"] = ""

    if total_key_present and detail_keys_present:
        row["reaction_details_status"] = "full" if total is not None and detail_sum == total else "partial"
    elif total_key_present:
        row["reaction_details_status"] = "total_only"
    elif detail_keys_present:
        row["reaction_details_status"] = "partial"
    else:
        row["reaction_details_status"] = "missing"


def set_engagement_fields(row: Dict[str, Any], item: Dict[str, Any]) -> None:
    share_present = "share_count" in item and value_present(item.get("share_count"))
    comment_present = "comment_count" in item and value_present(item.get("comment_count"))
    reaction_present = value_present(row.get("total_reactions"))

    row["has_share_count"] = 1 if share_present else 0
    row["has_comment_count"] = 1 if comment_present else 0
    row["has_engagement_basic"] = 1 if reaction_present or share_present or comment_present else 0

    total_reactions = safe_int(row.get("total_reactions")) or 0
    share_count = safe_int(row.get("share_count")) or 0
    comment_count = safe_int(row.get("comment_count")) or 0
    engagement_total = total_reactions + share_count + comment_count
    row["engagement_total"] = engagement_total

    followers = safe_int(row.get("page_followers"))
    if followers and followers > 0:
        if reaction_present:
            row["reaction_per_follower"] = round(total_reactions / followers, 10)
        if share_present:
            row["share_per_follower"] = round(share_count / followers, 10)
        if comment_present:
            row["comment_per_follower"] = round(comment_count / followers, 10)
        row["engagement_per_follower"] = round(engagement_total / followers, 10)


def set_enriched_fields(row: Dict[str, Any]) -> None:
    love = safe_int(row.get("love_count")) or 0
    haha = safe_int(row.get("haha_count")) or 0
    wow = safe_int(row.get("wow_count")) or 0
    sad = safe_int(row.get("sad_count")) or 0
    angry = safe_int(row.get("angry_count")) or 0
    care = safe_int(row.get("care_count")) or 0
    total = safe_int(row.get("total_reactions")) or 0

    special = love + haha + wow + sad + angry + care
    positive = love + care
    negative = sad + angry
    row["special_reaction_total"] = special
    row["positive_reaction_total"] = positive
    row["negative_reaction_total"] = negative

    if total > 0:
        row["love_ratio"] = round(love / total, 6)
        row["haha_ratio"] = round(haha / total, 6)
        row["wow_ratio"] = round(wow / total, 6)
        row["sad_ratio"] = round(sad / total, 6)
        row["angry_ratio"] = round(angry / total, 6)
        row["care_ratio"] = round(care / total, 6)
        row["approval_index"] = row["love_ratio"]
        row["outrage_index"] = row["angry_ratio"]
        row["amusement_index"] = row["haha_ratio"]
        row["empathy_index"] = round((sad + care) / total, 6)
        row["polarity_score"] = round((positive - negative) / total, 6)


def set_timestamp_fields(row: Dict[str, Any], item: Dict[str, Any], raw_schema_type: str) -> None:
    post_raw = ""
    post_unix: Optional[int] = None
    post_human = ""
    timestamp_source = ""
    timestamp_status = ""

    if raw_schema_type in {"schema_2_legacy_json", "schema_3_legacy_jsonl"}:
        post_raw = clean_text(item.get("creation_time"))
        post_unix = safe_int(item.get("creation_time"))
        post_human, _, _, _ = unix_to_parts(post_unix)
        timestamp_source = "legacy_creation_time" if post_unix is not None else "missing"
        timestamp_status = "ok" if post_unix is not None else "missing"
    elif raw_schema_type == "schema_5_new_timestamp":
        post_raw = clean_text(item.get("post_timestamp_raw"))
        post_unix = safe_int(item.get("post_timestamp_unix"))
        post_human = clean_text(item.get("post_timestamp_human"))
        timestamp_source = clean_text(item.get("timestamp_source")) or "url_or_dom"
        timestamp_status = clean_text(item.get("timestamp_status")) or ("ok" if post_unix else "missing")
    else:
        timestamp_source = "missing"
        timestamp_status = "missing"

    derived_human, post_date, post_hour, post_weekday = unix_to_parts(post_unix)
    row["post_created_time_raw"] = post_raw
    row["post_created_time_unix"] = post_unix if post_unix is not None else ""
    row["post_created_time_human"] = post_human or derived_human
    row["post_created_date"] = post_date
    row["post_created_hour"] = post_hour
    row["post_created_weekday"] = post_weekday
    row["timestamp_source"] = timestamp_source
    row["timestamp_status"] = timestamp_status
    row["has_post_created_time"] = 1 if post_unix is not None and timestamp_status == "ok" else 0

    crawl_raw = item.get("crawl_time")
    crawl_unix = safe_int(crawl_raw)
    crawl_human = clean_text(item.get("crawl_time_human"))
    if crawl_unix is not None:
        row["crawl_time_raw"] = clean_text(crawl_raw)
        row["crawl_time_unix"] = crawl_unix
        row["crawl_time_human"] = crawl_human or unix_to_parts(crawl_unix)[0]
        row["metadata_observed_at"] = row["crawl_time_human"]
        row["has_crawl_time"] = 1


def set_label_fields(row: Dict[str, Any], item: Dict[str, Any], raw_schema_type: str, label_mode: str) -> None:
    old_label = ""
    old_topic_label = ""
    old_label_source = "none"

    if raw_schema_type.startswith("csv_"):
        if "label_from_content" in item:
            old_label = clean_text(item.get("label_from_content"))
            old_label_source = "csv_old_label_from_content" if old_label else "none"
        elif "label" in item:
            old_label = clean_text(item.get("label"))
            old_label_source = "csv_old_label" if old_label else "none"
    elif "label" in item or "topic_label" in item:
        old_label = clean_text(item.get("label"))
        old_topic_label = clean_text(item.get("topic_label"))
        old_label_source = "targeted_page_label" if old_label or old_topic_label else "none"

    row["old_label"] = old_label
    row["old_topic_label"] = old_topic_label
    row["old_label_source"] = old_label_source

    if label_mode == "old-as-weak" and (old_topic_label or old_label):
        row["topic_label_final"] = old_topic_label or old_label
        row["topic_label_id"] = slug_label(row["topic_label_final"])
        row["label_status"] = "weak_labeled"
        row["label_source"] = "old_label_reused"
    else:
        row["topic_label_final"] = ""
        row["topic_label_id"] = ""
        row["label_status"] = "unlabeled"
        row["label_source"] = "none"


def slug_label(value: Any) -> str:
    text = normalize_text_for_hash(value)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def normalize_json_post(
    item: Dict[str, Any],
    path: Path,
    data_dir: Path,
    index: int,
    label_mode: str,
) -> Dict[str, Any]:
    raw_schema_type = infer_json_schema(item, path)
    row = empty_row()
    set_source_fields(row, path, data_dir, raw_schema_type, index)

    row["source_type"] = clean_text(item.get("source_type")) or ("Facebook" if raw_schema_type.startswith("schema_") else "")
    row["page_name"] = clean_text(item.get("page_name"))
    row["page_handle"] = clean_text(item.get("page_handle"))
    row["page_url"] = clean_text(item.get("page_url"))
    row["page_followers_raw"] = clean_text(item.get("page_followers"))
    page_followers = safe_int(item.get("page_followers"))
    row["page_followers"] = page_followers if page_followers is not None else ""
    row["has_page_followers"] = 1 if page_followers is not None and page_followers > 0 else 0

    row["post_id"] = clean_text(item.get("post_id"))
    row["post_url"] = clean_text(item.get("post_url"))
    row["post_type"] = clean_text(item.get("post_type"))
    row["external_url"] = clean_text(item.get("external_url"))
    set_content_fields(row, item.get("post_content"))

    detail_keys_present = False
    total_key_present = "total_reactions" in item and value_present(item.get("total_reactions"))

    if "reactions_detail" in item and isinstance(item.get("reactions_detail"), dict):
        detail = item.get("reactions_detail") or {}
        key_map = {
            "like": "like_count",
            "love": "love_count",
            "haha": "haha_count",
            "wow": "wow_count",
            "sad": "sad_count",
            "angry": "angry_count",
            "care": "care_count",
            "support": "care_count",
            "sorry": "sorry_count",
        }
        for raw_key, value in detail.items():
            dest = key_map.get(str(raw_key).strip().lower())
            if dest:
                row[dest] = safe_int(value) or 0
                detail_keys_present = True
    else:
        for col in [
            "like_count",
            "love_count",
            "haha_count",
            "wow_count",
            "sad_count",
            "angry_count",
            "care_count",
        ]:
            if col in item:
                row[col] = safe_int(item.get(col)) or 0
                detail_keys_present = True

    if total_key_present:
        total = safe_int(item.get("total_reactions"))
        row["total_reactions"] = total if total is not None else ""

    for col in ["share_count", "comment_count"]:
        if col in item and value_present(item.get(col)):
            parsed = safe_int(item.get(col))
            row[col] = parsed if parsed is not None else clean_text(item.get(col))

    # Keep crawler-provided rates if present; they may be overwritten if computable.
    for col in ["reaction_per_follower", "share_per_follower", "comment_per_follower"]:
        if col in item and value_present(item.get(col)):
            parsed = safe_float(item.get(col))
            row[col] = parsed if parsed is not None else clean_text(item.get(col))

    set_reaction_status(row, detail_keys_present, total_key_present)
    set_engagement_fields(row, item)
    set_enriched_fields(row)
    set_timestamp_fields(row, item, raw_schema_type)
    set_label_fields(row, item, raw_schema_type, label_mode)
    set_dedup_key(row)
    set_quality_and_usage(row)
    return row


def normalize_csv_row(
    item: Dict[str, Any],
    path: Path,
    data_dir: Path,
    index: int,
    comments_by_post: Counter,
    label_mode: str,
) -> Dict[str, Any]:
    raw_schema_type = "csv_old_labeled_post" if any(k in item for k in ("label", "label_from_content", "keywords")) else "csv_old_post_content"
    row = empty_row()
    set_source_fields(row, path, data_dir, raw_schema_type, index)

    row["post_id"] = clean_text(item.get("post_id"))
    set_content_fields(row, item.get("content"))
    set_label_fields(row, item, raw_schema_type, label_mode)

    if row["post_id"] and row["post_id"] in comments_by_post:
        row["comment_count"] = comments_by_post[row["post_id"]]
        row["has_comment_count"] = 1
        row["has_engagement_basic"] = 1

    if "keywords" in item and clean_text(item.get("keywords")):
        note = f"old_keywords={clean_text(item.get('keywords'))}"
        row["quality_note"] = note

    set_reaction_status(row, detail_keys_present=False, total_key_present=False)
    set_engagement_fields(row, {"comment_count": row.get("comment_count")} if row.get("comment_count") != "" else {})
    set_enriched_fields(row)
    set_dedup_key(row)
    set_quality_and_usage(row)
    return row


def set_quality_and_usage(row: Dict[str, Any]) -> None:
    exclude_reasons = []
    if not clean_text(row.get("post_content_for_labeling")):
        exclude_reasons.append("missing_content")
    if row.get("is_duplicate") == 1:
        exclude_reasons.append("duplicate")

    accepted_label_status = {"human_verified", "human_labeled", "weak_labeled", "weak_labeled_checked"}
    eval_label_status = {"human_verified", "human_labeled"}

    has_content = bool(clean_text(row.get("post_content_for_labeling")))
    has_final_label = bool(clean_text(row.get("topic_label_final")))
    label_status = clean_text(row.get("label_status"))
    not_duplicate = row.get("is_duplicate") != 1

    row["usable_for_topic_labeling"] = 1 if has_content and not_duplicate else 0
    row["needs_topic_label"] = 1 if has_content and not_duplicate and not has_final_label else 0

    usable_topic = has_content and has_final_label and label_status in accepted_label_status and not_duplicate
    row["usable_for_topic_training"] = 1 if usable_topic else 0
    row["usable_for_topic_evaluation"] = 1 if usable_topic and label_status in eval_label_status else 0

    has_reaction_details = int(row.get("has_reaction_details") or 0) == 1
    has_full_reaction_details = has_reaction_details and clean_text(row.get("reaction_details_status")) == "full"
    has_reaction_total = int(row.get("has_reaction_total") or 0) == 1
    has_share_count = int(row.get("has_share_count") or 0) == 1
    has_comment_count = int(row.get("has_comment_count") or 0) == 1
    has_post_created_time = int(row.get("has_post_created_time") or 0) == 1
    share_count = safe_int(row.get("share_count")) or 0
    comment_count = safe_int(row.get("comment_count")) or 0
    has_comment_or_share_value = comment_count > 0 or share_count > 0

    row["usable_for_reaction_analysis"] = 1 if not_duplicate and has_reaction_total and has_full_reaction_details else 0
    row["usable_for_engagement_analysis"] = (
        1
        if (
            not_duplicate
            and has_full_reaction_details
            and has_share_count
            and has_comment_count
            and has_comment_or_share_value
        )
        else 0
    )
    row["usable_for_time_analysis"] = 1 if not_duplicate and has_post_created_time else 0

    row["exclude_reason"] = ";".join(exclude_reasons)


def iter_json_records(path: Path) -> Iterable[Tuple[int, Dict[str, Any]]]:
    if path.suffix == ".jsonl":
        with path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                if isinstance(item, dict):
                    yield idx, item
        return

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        for idx, item in enumerate(data):
            if isinstance(item, dict):
                yield idx, item


def discover_json_post_files(data_dir: Path) -> List[Path]:
    paths = []
    for path in data_dir.rglob("*"):
        if path.suffix not in {".json", ".jsonl"}:
            continue
        name = path.name
        rel = path.relative_to(data_dir).as_posix()
        if data_dir.name != "01_Raw_Data" and not rel.startswith("01_Raw_Data/"):
            continue
        if rel.startswith("02_Processed_Data/"):
            continue
        if name.startswith("checkpoint_") or name == "comments.json":
            continue
        if "/checkpoints/" in rel or "/docs_before_reorg/" in rel:
            continue
        paths.append(path)
    return sorted(paths)


def load_comments_by_post(csv_dir: Path) -> Counter:
    comments_path = csv_dir / "comments_new.csv"
    counts: Counter = Counter()
    if not comments_path.exists():
        return counts
    with comments_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            post_id = clean_text(row.get("post_id"))
            if post_id:
                counts[post_id] += 1
    return counts


def discover_csv_post_files(csv_dir: Path) -> List[Path]:
    if not csv_dir.exists():
        return []
    paths = []
    for path in sorted(csv_dir.glob("*.csv")):
        if path.name == "comments_new.csv":
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fields = set(reader.fieldnames or [])
        if "content" in fields:
            paths.append(path)
    return paths


def record_quality_score(row: Dict[str, Any]) -> Tuple[int, int, int, int, int, int, int, int, int, int, int]:
    """Score duplicate candidates; higher is better."""
    content_len = safe_int(row.get("post_content_length")) or len(clean_text(row.get("post_content_for_labeling")))
    return (
        1 if clean_text(row.get("post_content_for_labeling")) else 0,
        1 if clean_text(row.get("topic_label_final")) or clean_text(row.get("old_topic_label")) or clean_text(row.get("old_label")) else 0,
        1 if clean_text(row.get("post_id")) else 0,
        1 if clean_text(row.get("post_url")) else 0,
        1 if int(row.get("has_post_created_time") or 0) == 1 else 0,
        1 if int(row.get("has_reaction_details") or 0) == 1 else 0,
        1 if int(row.get("has_engagement_basic") or 0) == 1 else 0,
        1 if int(row.get("has_page_followers") or 0) == 1 else 0,
        -DATA_ORIGIN_PRIORITY.get(clean_text(row.get("data_origin")) or "unknown", 90),
        -SCHEMA_PRIORITY.get(clean_text(row.get("raw_schema_type")) or "unknown", 99),
        content_len,
    )


def assign_duplicates(rows: List[Dict[str, Any]]) -> None:
    for idx, row in enumerate(rows, start=1):
        row["record_id"] = f"REC_{idx:06d}"
        row["is_duplicate"] = 0
        row["duplicate_of"] = ""

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = clean_text(row.get("dedup_key"))
        if key:
            grouped[key].append(row)

    for group_rows in grouped.values():
        if len(group_rows) <= 1:
            continue
        keeper = max(group_rows, key=lambda row: (record_quality_score(row), -safe_int(str(row["record_id"]).replace("REC_", "")) if row.get("record_id") else 0))
        keeper_id = keeper["record_id"]
        for row in group_rows:
            if row is keeper:
                row["is_duplicate"] = 0
                row["duplicate_of"] = ""
            else:
                row["is_duplicate"] = 1
                row["duplicate_of"] = keeper_id

    for row in rows:
        set_quality_and_usage(row)


def row_priority(row: Dict[str, Any]) -> Tuple[int, int, str, int]:
    origin = clean_text(row.get("data_origin")) or "unknown"
    schema = clean_text(row.get("raw_schema_type")) or "unknown"
    path = clean_text(row.get("raw_file_path"))
    idx = safe_int(row.get("raw_record_index")) or 0
    return (
        DATA_ORIGIN_PRIORITY.get(origin, 90),
        SCHEMA_PRIORITY.get(schema, 99),
        path,
        idx,
    )


def write_csv(path: Path, rows: List[Dict[str, Any]], columns: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: to_csv_value(row.get(col)) for col in columns})


def write_summary(path: Path, rows: List[Dict[str, Any]], skipped: List[Dict[str, Any]]) -> None:
    def unique_counter(field: str) -> Counter:
        return Counter(r.get(field) for r in rows if int(r.get("is_duplicate") or 0) == 0)

    def duplicate_counter(field: str) -> Counter:
        return Counter(r.get(field) for r in rows if int(r.get("is_duplicate") or 0) == 1)

    by_raw_file = {}
    grouped_by_file: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped_by_file[clean_text(row.get("raw_file_path"))].append(row)
    for raw_file, file_rows in sorted(grouped_by_file.items()):
        by_raw_file[raw_file] = {
            "total_rows": len(file_rows),
            "unique_rows": sum(1 for r in file_rows if int(r.get("is_duplicate") or 0) == 0),
            "duplicate_rows": sum(1 for r in file_rows if int(r.get("is_duplicate") or 0) == 1),
            "crawler_owner": clean_text(file_rows[0].get("crawler_owner")) if file_rows else "",
            "data_origin": clean_text(file_rows[0].get("data_origin")) if file_rows else "",
            "raw_schema_type": clean_text(file_rows[0].get("raw_schema_type")) if file_rows else "",
        }

    summary = {
        "total_rows": len(rows),
        "unique_rows": sum(1 for r in rows if int(r.get("is_duplicate") or 0) == 0),
        "duplicate_rows": sum(1 for r in rows if int(r.get("is_duplicate") or 0) == 1),
        "by_data_origin": Counter(r.get("data_origin") for r in rows),
        "by_data_origin_unique": unique_counter("data_origin"),
        "by_data_origin_duplicate": duplicate_counter("data_origin"),
        "by_raw_schema_type": Counter(r.get("raw_schema_type") for r in rows),
        "by_raw_schema_type_unique": unique_counter("raw_schema_type"),
        "by_raw_schema_type_duplicate": duplicate_counter("raw_schema_type"),
        "by_crawler_owner": Counter(r.get("crawler_owner") for r in rows),
        "by_crawler_owner_unique": unique_counter("crawler_owner"),
        "by_crawler_owner_duplicate": duplicate_counter("crawler_owner"),
        "by_raw_file": by_raw_file,
        "usable_counts": {
            "topic_labeling": sum(int(r.get("usable_for_topic_labeling") or 0) for r in rows),
            "needs_topic_label": sum(int(r.get("needs_topic_label") or 0) for r in rows),
            "topic_training": sum(int(r.get("usable_for_topic_training") or 0) for r in rows),
            "topic_evaluation": sum(int(r.get("usable_for_topic_evaluation") or 0) for r in rows),
            "reaction_analysis": sum(int(r.get("usable_for_reaction_analysis") or 0) for r in rows),
            "engagement_analysis": sum(int(r.get("usable_for_engagement_analysis") or 0) for r in rows),
            "time_analysis": sum(int(r.get("usable_for_time_analysis") or 0) for r in rows),
        },
        "skipped": skipped,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def apply_annotation_file(rows: List[Dict[str, Any]], annotation_file: Path) -> int:
    if not annotation_file.exists():
        raise FileNotFoundError(f"Annotation file not found: {annotation_file}")

    rows_by_id = {clean_text(row.get("record_id")): row for row in rows}
    applied = 0
    update_columns = [
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

    with annotation_file.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if "record_id" not in (reader.fieldnames or []):
            raise ValueError("Annotation file must contain record_id column")

        for ann in reader:
            record_id = clean_text(ann.get("record_id"))
            if not record_id or record_id not in rows_by_id:
                continue

            row = rows_by_id[record_id]
            has_update = False
            for col in update_columns:
                if col in ann and clean_text(ann.get(col)) != "":
                    row[col] = clean_text(ann.get(col))
                    has_update = True

            if clean_text(row.get("topic_label_final")) and not clean_text(row.get("topic_label_id")):
                row["topic_label_id"] = slug_label(row.get("topic_label_final"))
            if clean_text(row.get("topic_label_final")) and not clean_text(row.get("label_status")):
                row["label_status"] = "human_labeled"
            if clean_text(row.get("topic_label_final")) and not clean_text(row.get("label_source")):
                row["label_source"] = "manual"

            set_quality_and_usage(row)
            if has_update:
                applied += 1

    return applied


def write_annotation_template(path: Path, rows: List[Dict[str, Any]], unique_only: bool = True) -> None:
    template_rows = rows
    if unique_only:
        template_rows = [row for row in rows if int(row.get("is_duplicate") or 0) == 0]
    template_rows = [row for row in template_rows if int(row.get("usable_for_topic_labeling") or 0) == 1]
    write_csv(path, template_rows, ANNOTATION_COLUMNS)


def build_master(
    data_dir: Path,
    output_dir: Path,
    label_mode: str,
    include_labeled_csv: bool,
    annotation_file: Optional[Path] = None,
    annotation_template_path: Optional[Path] = None,
    write_audit_files: bool = False,
) -> Tuple[Path, Optional[Path]]:
    rows: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for path in discover_json_post_files(data_dir):
        try:
            count = 0
            for idx, item in iter_json_records(path):
                if "post_content" not in item:
                    continue
                rows.append(normalize_json_post(item, path, data_dir, idx, label_mode))
                count += 1
            if count == 0:
                skipped.append({"path": path.as_posix(), "reason": "no_post_records"})
        except Exception as exc:  # Keep the run going and report bad files.
            skipped.append({"path": path.as_posix(), "reason": f"read_error:{exc}"})

    csv_dir = data_dir / "03_Archive_Not_For_Training" / "labeled_unused" / "csv-data(labeled)"
    if include_labeled_csv:
        comments_by_post = load_comments_by_post(csv_dir)
        for path in discover_csv_post_files(csv_dir):
            try:
                with path.open("r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    for idx, item in enumerate(reader):
                        rows.append(normalize_csv_row(item, path, data_dir, idx, comments_by_post, label_mode))
            except Exception as exc:
                skipped.append({"path": path.as_posix(), "reason": f"read_error:{exc}"})
    else:
        skipped.append(
            {
                "path": csv_dir.as_posix(),
                "reason": "excluded_by_default:labeled_csv_old_is_preprocessed_duplicate_source",
            }
        )

    rows.sort(key=row_priority)
    assign_duplicates(rows)

    if annotation_file is not None:
        applied = apply_annotation_file(rows, annotation_file)
        skipped.append({"path": annotation_file.as_posix(), "reason": f"annotation_applied:{applied}_rows"})

    output_dir.mkdir(parents=True, exist_ok=True)
    master_path = output_dir / "Master_Facebook_News_Posts.csv"
    deduped_rows = [row for row in rows if int(row.get("is_duplicate") or 0) == 0]

    if annotation_template_path is not None:
        write_annotation_template(annotation_template_path, deduped_rows, unique_only=False)

    # The default Master is the single file used downstream: unique rows plus
    # enriched reaction/engagement fields.
    write_csv(master_path, deduped_rows, ENRICHED_COLUMNS)

    if write_audit_files:
        audit_dir = output_dir / "_audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        write_csv(audit_dir / "Master_Facebook_News_Posts_All_Rows.csv", rows, BASE_COLUMNS)
        write_csv(audit_dir / "Master_Facebook_News_Posts_All_Rows_Enriched.csv", rows, ENRICHED_COLUMNS)
        write_csv(audit_dir / "Master_Facebook_News_Posts_Deduped_Base.csv", deduped_rows, BASE_COLUMNS)
        write_summary(audit_dir / "Master_Facebook_News_Posts_summary.json", rows, skipped)

    return master_path, annotation_template_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Master Facebook News Posts CSV.")
    parser.add_argument("--data-dir", default="data", help="Path to reorganized data directory.")
    parser.add_argument(
        "--output-dir",
        default="data/02_Processed_Data",
        help="Directory where Master CSV files will be written.",
    )
    parser.add_argument(
        "--label-mode",
        choices=["empty-final", "old-as-weak"],
        default="empty-final",
        help=(
            "empty-final keeps topic_label_final blank for later annotation; "
            "old-as-weak copies old labels into topic_label_final as weak labels."
        ),
    )
    parser.add_argument(
        "--include-labeled-csv",
        action="store_true",
        help=(
            "Also ingest old CSV/XLSX-derived labeled CSV files under "
            "03_Archive_Not_For_Training/labeled_unused/csv-data(labeled). "
            "Default is off because these files are preprocessed/labeled ViTrend data "
            "and duplicate raw posts heavily."
        ),
    )
    parser.add_argument(
        "--annotation-file",
        default="",
        help=(
            "Optional CSV file containing record_id and final annotation columns. "
            "When provided, values are merged into Master before usability flags are computed."
        ),
    )
    parser.add_argument(
        "--write-annotation-template",
        action="store_true",
        help="Write a CSV template for human annotation using unique rows only.",
    )
    parser.add_argument(
        "--annotation-template-path",
        default="",
        help=(
            "Optional output path for the annotation template. "
            "Defaults to data/02_Processed_Data/Annotation_Template.csv."
        ),
    )
    parser.add_argument(
        "--write-audit-files",
        action="store_true",
        help=(
            "Write optional duplicate/audit outputs under data/02_Processed_Data/_audit. "
            "Default is off so the processed folder only has one Master CSV and one annotation CSV."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    annotation_file = Path(args.annotation_file) if args.annotation_file else None
    annotation_template_path = None
    if args.write_annotation_template:
        annotation_template_path = (
            Path(args.annotation_template_path)
            if args.annotation_template_path
            else output_dir / "Annotation_Template.csv"
        )

    master_path, annotation_template_written = build_master(
        data_dir,
        output_dir,
        args.label_mode,
        args.include_labeled_csv,
        annotation_file,
        annotation_template_path,
        args.write_audit_files,
    )

    print(f"Wrote master CSV: {master_path}")
    if annotation_template_written is not None:
        print(f"Wrote annotation template: {annotation_template_written}")
    if args.write_audit_files:
        print(f"Wrote audit files under: {output_dir / '_audit'}")


if __name__ == "__main__":
    main()

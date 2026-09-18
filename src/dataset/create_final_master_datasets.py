#!/usr/bin/env python3
"""Create final DS107 master, modeling, Streamlit, and QA datasets.

The script joins final/pilot topic labels back to the deduplicated TeamCrawl
master, recomputes analysis flags/metrics, and writes technical reports.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = PROJECT_ROOT / "data/02_Processed_Data/Master_Facebook_News_Posts_TeamCrawl_After_Dedup.csv"
LABEL_DIRS = [
    PROJECT_ROOT / "data/05_Labeling/Final_Labeled",
    PROJECT_ROOT / "data/05_Labeling/Final_Pilot_Labeled",
]
OUTPUT_DIR = PROJECT_ROOT / "data/06_Final_Master_Data"
CSV_ENCODING = "utf-8-sig"

TOPIC_ID_TO_LABEL = {
    "T01": "T01. POLITICS",
    "T02": "T02. ECONOMY_BUSINESS_AND_FINANCE",
    "T03": "T03. CRIME_LAW_AND_JUSTICE",
    "T04": "T04. HEALTH",
    "T05": "T05. EDUCATION",
    "T06": "T06. SCIENCE_AND_TECHNOLOGY",
    "T07": "T07. ENVIRONMENT",
    "T08": "T08. WEATHER",
    "T09": "T09. DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT",
    "T10": "T10. ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA",
    "T11": "T11. SPORT",
    "T12": "T12. SOCIETY",
    "T13": "T13. HUMAN_INTEREST",
    "T14": "T14. LABOR",
    "T15": "T15. LIFESTYLE_AND_LEISURE",
    "T16": "T16. WORLD_INTERNATIONAL",
    "T17": "T17. TRANSPORT_INFRASTRUCTURE",
    "T18": "T18. OTHER_UNCLEAR",
}
VALID_TOPIC_IDS = set(TOPIC_ID_TO_LABEL)
VALID_MODEL_TOPIC_IDS = {f"T{i:02d}" for i in range(1, 18)}

TAXONOMY_SOURCE_NOTES = {
    **{f"T{i:02d}": "IPTC" for i in range(1, 16)},
    "T16": "bổ sung theo VNTC/Việt Nam",
    "T17": "bổ sung theo đặc thù Việt Nam/Đông Nam Á",
    "T18": "nhãn kỹ thuật cho caption Facebook",
}

TRUE_CONFLICT_TYPES = {
    "duplicate_label_topic_conflict",
    "unresolved_duplicate_label_topic_conflict",
    "invalid_topic_label",
    "label_record_id_not_found_in_master",
}

PILOT_QUALITY_NOTE = "pilot_or_calibration_sample_exclude_from_test"

MANUAL_PAGE_FOLLOWER_OVERRIDES = {
    "theanh28": {
        "page_name": "Theanh28 Entertainment",
        "page_url": "https://www.facebook.com/Theanh28",
        "page_followers": 13_000_000,
    },
    "canhsatdieutratoiphammatuy": {
        "page_name": "Cục Cảnh sát điều tra tội phạm về ma tuý",
        "page_url": "https://www.facebook.com/Canhsatdieutratoiphammatuy",
        "page_followers": 1_100_000,
    },
}

PILOT_FILE_CONFIG = {
    "[DS107] Topic Annotation Pilot Set 100 - IAA_Merge-2.csv": {
        "topic_label_col": "topic_label_final",
        "topic_id_col": "topic_label_final_id",
        "annotation_round": "pilot_100_final",
    },
    "[DS107] Topic Annotation Pilot Set 400 - IAA_Merge-4.csv": {
        "topic_label_col": "topic_label_final_train",
        "topic_id_col": "topic_label_final_id_train",
        "annotation_round": "pilot_400_final",
    },
    "Topic Annotation Pilot Set 100 [2] - IAA_Merge-2.csv": {
        "topic_label_col": "topic_label_final_train",
        "topic_id_col": "topic_label_final_id_train",
        "annotation_round": "pilot_100_additional_final",
    },
}

MASTER_EXPECTED_COLUMNS = [
    "master_schema_version",
    "record_id",
    "crawler_owner",
    "raw_schema_type",
    "raw_file_path",
    "raw_file_name",
    "raw_record_index",
    "post_id",
    "post_url",
    "content_hash",
    "dedup_key",
    "page_name",
    "page_handle",
    "page_url",
    "page_followers",
    "page_followers_raw",
    "has_page_followers",
    "post_type",
    "external_url",
    "post_content_for_labeling",
    "post_content_length",
    "word_count",
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
    "usable_for_topic_classification",
    "needs_topic_label",
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
    "usable_for_reaction_analysis",
    "usable_for_engagement_analysis",
    "exclude_reason",
    "quality_note",
    "has_metadata_outlier",
    "metadata_outlier_reason",
    "usable_for_engagement_analysis_strict",
]

LABEL_UPDATE_COLUMNS = [
    "topic_label_final",
    "topic_label_id",
    "label_status",
    "label_source",
    "annotator_1",
    "annotator_2",
    "annotation_round",
    "annotation_note",
    "is_uncertain_label",
    "exclude_reason",
    "quality_note",
]

NORMALIZED_LABEL_COLUMNS = [
    "record_id",
    *LABEL_UPDATE_COLUMNS,
    "label_file_source",
    "source_group",
    "label_row_number",
    "label_has_any_topic_input",
    "is_valid_topic_label",
    "raw_topic_label_id",
    "raw_topic_label_final",
    "raw_label_columns",
]

CONFLICT_COLUMNS = [
    "issue_type",
    "record_id",
    "topic_label_id_candidates",
    "topic_label_final_candidates",
    "label_file_source",
    "details",
]

STREAMLIT_COLUMNS = [
    "record_id",
    "caption",
    "topic_label_final",
    "topic_label_id",
    "label_status",
    "label_source",
    "is_uncertain_label",
    "page_name",
    "page_handle",
    "page_url",
    "post_url",
    "crawler_owner",
    "raw_schema_type",
    "page_followers",
    "has_page_followers",
    "post_created_time_human",
    "post_created_date",
    "post_created_hour",
    "post_created_weekday",
    "timestamp_status",
    "has_post_created_time",
    "metadata_observed_at",
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
    "reaction_details_status",
    "has_reaction_total",
    "has_reaction_details",
    "share_count",
    "comment_count",
    "has_share_count",
    "has_comment_count",
    "has_engagement_basic",
    "positive_reaction_total",
    "negative_reaction_total",
    "special_reaction_total",
    "all_reaction_total_for_formula",
    "reaction_intensity",
    "reaction_valence",
    "polarity_score",
    "love_ratio",
    "care_ratio",
    "haha_ratio",
    "wow_ratio",
    "sad_ratio",
    "angry_ratio",
    "approval_reaction_index",
    "outrage_reaction_index",
    "amusement_reaction_index",
    "empathy_reaction_index",
    "engagement_total",
    "reaction_per_follower",
    "share_per_follower",
    "comment_per_follower",
    "engagement_per_follower",
    "usable_for_topic_classification",
    "usable_for_reaction_analysis",
    "usable_for_engagement_analysis",
    "has_metadata_outlier",
    "metadata_outlier_reason",
    "usable_for_engagement_analysis_strict",
    "exclude_reason",
    "quality_note",
]

NUMERIC_COLUMNS = [
    "like_count",
    "love_count",
    "haha_count",
    "wow_count",
    "sad_count",
    "angry_count",
    "care_count",
    "sorry_count",
    "total_reactions",
    "share_count",
    "comment_count",
    "page_followers",
]

REACTION_DETAIL_MAIN_COLUMNS = [
    "like_count",
    "love_count",
    "haha_count",
    "wow_count",
    "sad_count",
    "angry_count",
    "care_count",
]

BLANK_STRINGS = {"", "nan", "none", "nat", "<na>", "null"}


def rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def clean_value(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in BLANK_STRINGS:
        return ""
    return text


def blank_mask(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip().str.lower()
    return series.isna() | text.isin(BLANK_STRINGS)


def first_non_empty(df: pd.DataFrame, candidates: Sequence[str]) -> pd.Series:
    result = pd.Series(pd.NA, index=df.index, dtype="object")
    for col in candidates:
        if col not in df.columns:
            continue
        series = df[col]
        result = result.where(~blank_mask(result), series.where(~blank_mask(series), pd.NA))
    return result


def unique_non_empty(values: Iterable[object]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        text = clean_value(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def join_unique(values: Iterable[object]) -> str:
    return "; ".join(unique_non_empty(values))


def ensure_columns(df: pd.DataFrame, columns: Sequence[str], default: object = pd.NA) -> List[str]:
    created = []
    for col in columns:
        if col not in df.columns:
            df[col] = default
            created.append(col)
    return created


def normalize_label_name(value: object) -> str:
    text = clean_value(value).upper()
    text = re.sub(r"^T\s*0?([1-9]|1[0-8])[\s._:-]*", "", text)
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


TOPIC_NAME_TO_ID: Dict[str, str] = {}
for topic_id, label in TOPIC_ID_TO_LABEL.items():
    TOPIC_NAME_TO_ID[normalize_label_name(label)] = topic_id
    TOPIC_NAME_TO_ID[normalize_label_name(label.split(".", 1)[-1])] = topic_id
TOPIC_NAME_TO_ID.update(
    {
        "SCIENCE_AND_TECHNOLOGY": "T06",
        "TECHNOLOGY_AND_SCIENCE": "T06",
        "TECHNOLOGY_SCIENCE": "T06",
        "SCIENCE_TECHNOLOGY": "T06",
        "WEATHER": "T08",
        "DISASTER": "T09",
        "DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT": "T09",
        "EMERGENCY_INCIDENT": "T09",
        "SPORTS": "T11",
        "MEDIA_ENTERTAINMENT": "T10",
        "ENTERTAINMENT_AND_MEDIA": "T10",
        "LABOR": "T14",
        "LABOR_EMPLOYMENT": "T14",
        "LABOUR": "T14",
        "EMPLOYMENT": "T14",
        "TRANSPORT": "T17",
        "INFRASTRUCTURE_TRANSPORT": "T17",
        "TRANSPORT_INFRASTRUCTURE": "T17",
        "OTHER": "T18",
        "UNCLEAR": "T18",
    }
)


def extract_explicit_topic_id(value: object) -> Optional[str]:
    text = clean_value(value).upper()
    if not text:
        return None
    match = re.search(r"T\s*0?([1-9]|1[0-8])(?=[^0-9]|$)", text)
    if match:
        return f"T{int(match.group(1)):02d}"
    if re.fullmatch(r"0?([1-9]|1[0-8])", text):
        return f"T{int(text):02d}"
    return None


def extract_topic_id(value: object) -> Optional[str]:
    explicit_id = extract_explicit_topic_id(value)
    if explicit_id:
        return explicit_id
    text = clean_value(value)
    if not text:
        return None
    return TOPIC_NAME_TO_ID.get(normalize_label_name(text))


def standardize_topic_fields(topic_id_value: object, topic_final_value: object) -> Tuple[Optional[str], object, bool]:
    raw_id = clean_value(topic_id_value)
    raw_final = clean_value(topic_final_value)
    has_any_topic_input = bool(raw_id or raw_final)

    final_explicit_id = extract_explicit_topic_id(raw_final)
    final_name_id = TOPIC_NAME_TO_ID.get(normalize_label_name(raw_final))
    id_explicit_id = extract_explicit_topic_id(raw_id)
    id_name_id = TOPIC_NAME_TO_ID.get(normalize_label_name(raw_id))
    topic_id = final_explicit_id or final_name_id or id_explicit_id or id_name_id
    if topic_id not in VALID_TOPIC_IDS:
        return None, pd.NA, has_any_topic_input

    return topic_id, TOPIC_ID_TO_LABEL[topic_id], has_any_topic_input


def to_flag(value: object, default: int = 0) -> int:
    text = clean_value(value).lower()
    if not text:
        return default
    if text in {"0", "0.0", "false", "no", "n", "khong", "không"}:
        return 0
    if text in {"1", "1.0", "true", "yes", "y", "co", "có", "x"}:
        return 1
    return 1


def append_quality_note(existing: object, note: str) -> str:
    current = clean_value(existing)
    if not current:
        return note
    if note in current:
        return current
    return f"{current}; {note}"


def infer_annotators(df: pd.DataFrame, source_path: Path, source_group: str) -> str:
    names = []
    for col in df.columns:
        match = re.match(r"annotator_([^_]+)_topic_label", str(col))
        if match:
            names.append(match.group(1))
    if names:
        return "; ".join(sorted(set(names)))

    filename = source_path.name.lower()
    inferred = []
    for name in ["Han", "Nhung", "Yen"]:
        if name.lower() in filename:
            inferred.append(name)
    if inferred:
        return "; ".join(inferred)
    return source_group


def read_master(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing master input: {path}")
    df = pd.read_csv(path, encoding=CSV_ENCODING, low_memory=False)
    if "record_id" not in df.columns:
        raise ValueError(f"Master input must contain record_id: {path}")
    df["record_id"] = df["record_id"].astype("string").str.strip()
    if blank_mask(df["record_id"]).any():
        raise ValueError("Master input contains blank record_id values.")
    return df


def discover_label_files(label_dirs: Sequence[Path]) -> List[Tuple[Path, str]]:
    files: List[Tuple[Path, str]] = []
    valid_suffixes = {".csv", ".xlsx", ".xls"}
    for label_dir in label_dirs:
        if not label_dir.exists():
            continue
        for path in sorted(label_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.name.startswith("~$"):
                continue
            if path.suffix.lower() not in valid_suffixes:
                continue
            files.append((path, label_dir.name))
    return files


def read_label_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, encoding=CSV_ENCODING, low_memory=False)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported label file type: {path}")


def label_input_config(source_path: Path, source_group: str) -> Dict[str, object]:
    if source_group == "Final_Labeled":
        return {
            "topic_label_candidates": ["annotator_topic_label", "topic_label_final", "topic_label_final_train"],
            "topic_id_candidates": ["annotator_topic_id", "topic_label_id", "topic_label_final_id"],
            "label_status": "human_labeled",
            "label_source": "manual",
            "annotation_round": "final_full",
            "note_candidates": ["annotator_note", "annotation_note"],
            "uncertain_candidates": ["annotator_uncertain", "is_uncertain_label"],
            "is_pilot": False,
        }

    pilot_config = PILOT_FILE_CONFIG.get(source_path.name)
    if pilot_config:
        return {
            "topic_label_candidates": [str(pilot_config["topic_label_col"])],
            "topic_id_candidates": [str(pilot_config["topic_id_col"])],
            "label_status": "human_verified",
            "label_source": "manual_adjudicated",
            "annotation_round": str(pilot_config["annotation_round"]),
            "note_candidates": ["annotation_note", "adjudicator_reason"],
            "uncertain_candidates": ["is_uncertain_label", "flag_ambiguity"],
            "is_pilot": True,
        }

    return {
        "topic_label_candidates": ["topic_label_final_train", "topic_label_final"],
        "topic_id_candidates": ["topic_label_final_id_train", "topic_label_final_id", "topic_label_id"],
        "label_status": "human_verified",
        "label_source": "manual_adjudicated",
        "annotation_round": "pilot_final",
        "note_candidates": ["annotation_note", "adjudicator_reason"],
        "uncertain_candidates": ["is_uncertain_label", "flag_ambiguity"],
        "is_pilot": source_group == "Final_Pilot_Labeled",
    }


def normalize_label_dataframe(df: pd.DataFrame, source_path: Path, source_group: str) -> pd.DataFrame:
    config = label_input_config(source_path, source_group)
    normalized = pd.DataFrame(index=df.index)
    normalized["record_id"] = first_non_empty(df, ["record_id", "Record ID", "recordID"]).map(clean_value)

    raw_topic_final = first_non_empty(df, config["topic_label_candidates"])  # type: ignore[arg-type]
    raw_topic_id = first_non_empty(df, config["topic_id_candidates"])  # type: ignore[arg-type]
    standardized = [
        standardize_topic_fields(topic_id_value, topic_final_value)
        for topic_id_value, topic_final_value in zip(raw_topic_id, raw_topic_final)
    ]
    normalized["topic_label_id"] = [item[0] if item[0] else pd.NA for item in standardized]
    normalized["topic_label_final"] = [item[1] for item in standardized]
    normalized["label_has_any_topic_input"] = [item[2] for item in standardized]
    normalized["is_valid_topic_label"] = normalized["topic_label_id"].isin(VALID_TOPIC_IDS)
    normalized["raw_topic_label_id"] = raw_topic_id.map(clean_value)
    normalized["raw_topic_label_final"] = raw_topic_final.map(clean_value)

    normalized["label_status"] = str(config["label_status"])
    normalized["label_source"] = str(config["label_source"])

    annotator_1 = first_non_empty(df, ["annotator_1"]).map(clean_value)
    annotator_1.loc[annotator_1 == ""] = infer_annotators(df, source_path, source_group)
    normalized["annotator_1"] = annotator_1
    normalized["annotator_2"] = first_non_empty(df, ["annotator_2"]).map(clean_value)

    normalized["annotation_round"] = str(config["annotation_round"])

    note = first_non_empty(df, config["note_candidates"]).map(clean_value)  # type: ignore[arg-type]
    adjudicator_reason = first_non_empty(df, ["adjudicator_reason"]).map(clean_value)
    combined_notes = []
    for base_note, reason in zip(note, adjudicator_reason):
        if base_note and reason and reason not in base_note:
            combined_notes.append(f"{base_note}; adjudicator_reason: {reason}")
        elif base_note:
            combined_notes.append(base_note)
        else:
            combined_notes.append(reason)
    normalized["annotation_note"] = combined_notes

    uncertain = first_non_empty(df, config["uncertain_candidates"])  # type: ignore[arg-type]
    normalized["is_uncertain_label"] = uncertain.map(to_flag)
    normalized["exclude_reason"] = first_non_empty(df, ["exclude_reason"]).map(clean_value)

    quality_note = first_non_empty(df, ["quality_note"]).map(clean_value)
    if config["is_pilot"]:
        quality_note = quality_note.map(lambda value: append_quality_note(value, PILOT_QUALITY_NOTE))
    normalized["quality_note"] = quality_note

    normalized["label_file_source"] = rel_path(source_path)
    normalized["source_group"] = source_group
    normalized["label_row_number"] = df.index + 2
    normalized["raw_label_columns"] = "; ".join(str(col) for col in df.columns)

    return normalized[NORMALIZED_LABEL_COLUMNS]


def metadata_score(row: pd.Series) -> int:
    return sum(1 for col in LABEL_UPDATE_COLUMNS if clean_value(row.get(col)) != "")


def status_priority(value: object) -> int:
    text = clean_value(value).lower()
    if text in {"human_verified", "adjudicated"}:
        return 2
    if text == "human_labeled":
        return 1
    if text == "excluded":
        return 1
    return 0


def source_priority(value: object) -> int:
    return 1 if clean_value(value) == "Final_Labeled" else 0


def choose_best_metadata_row(group: pd.DataFrame) -> pd.Series:
    scored = group.copy()
    scored["_metadata_score"] = scored.apply(metadata_score, axis=1)
    scored["_status_priority"] = scored["label_status"].map(status_priority)
    scored["_source_priority"] = scored["source_group"].map(source_priority)
    scored = scored.sort_values(
        ["_metadata_score", "_status_priority", "_source_priority", "label_file_source"],
        ascending=[False, False, False, True],
    )
    return scored.iloc[0].drop(labels=["_metadata_score", "_status_priority", "_source_priority"])


def make_conflict(issue_type: str, rows: pd.DataFrame, details: str) -> Dict[str, str]:
    return {
        "issue_type": issue_type,
        "record_id": join_unique(rows["record_id"]) if "record_id" in rows else "",
        "topic_label_id_candidates": join_unique(rows["topic_label_id"]) if "topic_label_id" in rows else "",
        "topic_label_final_candidates": join_unique(rows["topic_label_final"]) if "topic_label_final" in rows else "",
        "label_file_source": join_unique(rows["label_file_source"]) if "label_file_source" in rows else "",
        "details": details,
    }


def resolve_topic_conflict(group: pd.DataFrame) -> Optional[pd.Series]:
    highest_status = group["label_status"].map(status_priority).max()
    if highest_status > 0:
        status_group = group[group["label_status"].map(status_priority) == highest_status]
        status_topics = unique_non_empty(status_group["topic_label_id"])
        if len(status_topics) == 1:
            return choose_best_metadata_row(status_group)

    final_group = group[group["source_group"].map(source_priority) == 1]
    final_topics = unique_non_empty(final_group["topic_label_id"])
    if len(final_topics) == 1:
        return choose_best_metadata_row(final_group)

    return None


def empty_normalized_labels() -> pd.DataFrame:
    return pd.DataFrame(columns=NORMALIZED_LABEL_COLUMNS)


def empty_conflicts() -> pd.DataFrame:
    return pd.DataFrame(columns=CONFLICT_COLUMNS)


def resolve_label_duplicates(labels: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if labels.empty:
        return empty_normalized_labels(), empty_conflicts()

    labels = labels.copy()
    labels["record_id"] = labels["record_id"].map(clean_value)
    conflicts: List[Dict[str, str]] = []

    missing_record_id = labels[labels["record_id"] == ""]
    for _, row in missing_record_id.iterrows():
        conflicts.append(
            make_conflict(
                "missing_record_id",
                pd.DataFrame([row]),
                f"Label row {row.get('label_row_number')} has blank record_id.",
            )
        )

    has_record = labels["record_id"] != ""
    missing_topic = labels[has_record & ~labels["label_has_any_topic_input"]]
    for _, row in missing_topic.iterrows():
        conflicts.append(
            make_conflict(
                "missing_topic_label",
                pd.DataFrame([row]),
                "Label row is missing both topic_label_final and topic_label_id.",
            )
        )

    invalid_label = labels[
        has_record
        & labels["label_has_any_topic_input"]
        & ~labels["is_valid_topic_label"]
        & (labels["label_status"].map(clean_value).str.lower() != "excluded")
    ]
    for _, row in invalid_label.iterrows():
        raw_candidates = pd.DataFrame(
            [
                {
                    **row.to_dict(),
                    "topic_label_id": row.get("raw_topic_label_id"),
                    "topic_label_final": row.get("raw_topic_label_final"),
                }
            ]
        )
        conflicts.append(
            make_conflict(
                "invalid_topic_label",
                raw_candidates,
                "Label cannot be normalized to one of T01-T18.",
            )
        )

    usable_for_join = labels[
        has_record
        & (
            labels["is_valid_topic_label"]
            | (labels["label_status"].map(clean_value).str.lower() == "excluded")
        )
    ].copy()
    if usable_for_join.empty:
        return empty_normalized_labels(), pd.DataFrame(conflicts, columns=CONFLICT_COLUMNS)

    resolved_rows: List[pd.Series] = []
    for record_id, group in usable_for_join.groupby("record_id", sort=False):
        if len(group) > 1:
            conflicts.append(
                make_conflict(
                    "duplicate_label",
                    group,
                    f"record_id appears {len(group)} times across label files.",
                )
            )

        topic_ids = unique_non_empty(group["topic_label_id"])
        if len(topic_ids) <= 1:
            resolved_rows.append(choose_best_metadata_row(group))
            continue

        conflicts.append(
            make_conflict(
                "duplicate_label_topic_conflict",
                group,
                "Duplicate record_id has conflicting topic_label_id values.",
            )
        )
        chosen = resolve_topic_conflict(group)
        if chosen is not None:
            resolved_rows.append(chosen)
        else:
            unresolved = group.copy()
            unresolved["topic_label_id"] = pd.NA
            unresolved["topic_label_final"] = pd.NA
            unresolved["label_status"] = "conflict_needs_review"
            conflicts.append(
                make_conflict(
                    "unresolved_duplicate_label_topic_conflict",
                    unresolved,
                    "Conflict could not be resolved by status or source priority; master keeps null label.",
                )
            )

    resolved = pd.DataFrame(resolved_rows)
    if resolved.empty:
        resolved = empty_normalized_labels()
    else:
        resolved = resolved[NORMALIZED_LABEL_COLUMNS].drop_duplicates(subset=["record_id"], keep="first")

    return resolved, pd.DataFrame(conflicts, columns=CONFLICT_COLUMNS)


def join_labels_to_master(master: pd.DataFrame, labels: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, int]:
    df = master.copy()
    ensure_columns(df, LABEL_UPDATE_COLUMNS)
    if labels.empty:
        return df, empty_conflicts(), 0

    if labels["record_id"].duplicated().any():
        duplicated = labels[labels["record_id"].duplicated(keep=False)]["record_id"].tolist()
        raise ValueError(f"Resolved labels still contain duplicate record_id values: {duplicated[:10]}")

    master_ids = set(df["record_id"].astype(str))
    labels = labels.copy()
    labels["record_id"] = labels["record_id"].map(clean_value)

    not_found = labels[~labels["record_id"].isin(master_ids)]
    conflicts = []
    for _, row in not_found.iterrows():
        conflicts.append(
            make_conflict(
                "label_record_id_not_found_in_master",
                pd.DataFrame([row]),
                "Label record_id does not exist in master after dedup.",
            )
        )

    joinable = labels[labels["record_id"].isin(master_ids)].copy()
    if joinable.empty:
        return df, pd.DataFrame(conflicts, columns=CONFLICT_COLUMNS), 0

    label_cols = ["record_id", *LABEL_UPDATE_COLUMNS]
    merged = df.merge(
        joinable[label_cols],
        on="record_id",
        how="left",
        suffixes=("", "__label"),
        validate="one_to_one",
    )
    for col in LABEL_UPDATE_COLUMNS:
        if col in merged.columns:
            merged[col] = merged[col].astype("object")
    for col in LABEL_UPDATE_COLUMNS:
        label_col = f"{col}__label"
        if label_col not in merged.columns:
            continue
        mask = ~blank_mask(merged[label_col])
        merged.loc[mask, col] = merged.loc[mask, label_col]
        merged = merged.drop(columns=[label_col])

    return merged, pd.DataFrame(conflicts, columns=CONFLICT_COLUMNS), len(joinable)


def update_topic_flags(df: pd.DataFrame) -> pd.DataFrame:
    ensure_columns(
        df,
        [
            "post_content_for_labeling",
            "topic_label_final",
            "topic_label_id",
            "label_status",
            "label_source",
            "annotation_round",
        ],
    )
    standardized = [
        standardize_topic_fields(topic_id_value, topic_final_value)
        for topic_id_value, topic_final_value in zip(df["topic_label_id"], df["topic_label_final"])
    ]
    df["topic_label_id"] = [item[0] if item[0] else pd.NA for item in standardized]
    df["topic_label_final"] = [item[1] for item in standardized]

    df["label_status"] = df["label_status"].map(clean_value)
    df.loc[df["label_status"] == "", "label_status"] = "unlabeled"

    excluded = df["label_status"].str.lower() == "excluded"
    caption_present = ~blank_mask(df["post_content_for_labeling"])
    valid_topic = df["topic_label_id"].isin(VALID_TOPIC_IDS)
    has_topic_label = valid_topic & ~blank_mask(df["topic_label_final"])
    status_needs_fix = has_topic_label & df["label_status"].str.lower().isin({"", "unlabeled"}) & ~excluded
    verified_source = (
        df["annotation_round"].map(clean_value).str.lower().str.contains("pilot|adjudication|adjudicated", regex=True)
        | (df["label_source"].map(clean_value).str.lower() == "manual_adjudicated")
    )
    df.loc[status_needs_fix & verified_source, "label_status"] = "human_verified"
    df.loc[status_needs_fix & ~verified_source, "label_status"] = "human_labeled"
    df.attrs["unlabeled_with_valid_label_fixed_count"] = int(status_needs_fix.sum())
    excluded = df["label_status"].str.lower() == "excluded"

    df["usable_for_topic_classification"] = (caption_present & valid_topic & ~excluded).astype(int)
    df["needs_topic_label"] = (caption_present & ~valid_topic & ~excluded).astype(int)
    df.loc[excluded, "needs_topic_label"] = 0
    return df


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    valid_denominator = denominator.where(denominator.notna() & (denominator != 0))
    return numerator / valid_denominator


def normalize_url_for_match(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.rstrip("/").str.lower()


def apply_manual_page_follower_overrides(df: pd.DataFrame) -> pd.DataFrame:
    ensure_columns(df, ["page_name", "page_handle", "page_url", "page_followers", "page_followers_raw"])
    handle_key = df["page_handle"].astype("string").str.strip().str.lower()
    url_key = normalize_url_for_match(df["page_url"])

    override_count = 0
    for handle, config in MANUAL_PAGE_FOLLOWER_OVERRIDES.items():
        expected_url = str(config["page_url"]).rstrip("/").lower()
        mask = (handle_key == handle) | (url_key == expected_url)
        override_count += int(mask.sum())
        df.loc[mask, "page_followers"] = int(config["page_followers"])
        df.loc[mask, "page_followers_raw"] = int(config["page_followers"])

    df.attrs["manual_page_follower_overrides_applied"] = override_count
    return df


def append_reason_series(reasons: pd.Series, mask: pd.Series, reason: str) -> pd.Series:
    updated = reasons.copy()
    updated.loc[mask & (updated == "")] = reason
    updated.loc[mask & (updated != "") & ~updated.str.contains(re.escape(reason), regex=True)] = (
        updated.loc[mask & (updated != "") & ~updated.str.contains(re.escape(reason), regex=True)] + "; " + reason
    )
    return updated


def update_metadata_outlier_flags(df: pd.DataFrame) -> pd.DataFrame:
    ensure_columns(df, ["has_metadata_outlier", "metadata_outlier_reason", "usable_for_engagement_analysis_strict"])
    reasons = pd.Series("", index=df.index, dtype="object")

    outlier_rules = [
        (df["comment_count"] >= 100000, "comment_count >= 100000"),
        (df["share_count"] >= 100000, "share_count >= 100000"),
        (df["total_reactions"] >= 100000, "total_reactions >= 100000"),
        (df["engagement_per_follower"] > 0.2, "engagement_per_follower > 0.2"),
        (
            (df["comment_count"] > df["total_reactions"].fillna(0) * 20) & (df["comment_count"] >= 10000),
            "comment_count > total_reactions * 20 and comment_count >= 10000",
        ),
        (
            (df["share_count"] > df["total_reactions"].fillna(0) * 20) & (df["share_count"] >= 10000),
            "share_count > total_reactions * 20 and share_count >= 10000",
        ),
    ]
    for mask, reason in outlier_rules:
        reasons = append_reason_series(reasons, mask.fillna(False), reason)

    df["has_metadata_outlier"] = (reasons != "").astype(int)
    df["metadata_outlier_reason"] = reasons
    return df


def update_reaction_flags_and_metrics(df: pd.DataFrame) -> pd.DataFrame:
    ensure_columns(df, NUMERIC_COLUMNS)
    df = apply_manual_page_follower_overrides(df)
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["sorry_count"] = df["sorry_count"].fillna(0)
    df["has_page_followers"] = ((df["page_followers"].notna()) & (df["page_followers"] > 0)).astype(int)
    df["has_reaction_total"] = ((df["total_reactions"].notna()) & (df["total_reactions"] >= 0)).astype(int)

    detail_main_not_null = pd.Series(True, index=df.index)
    for col in REACTION_DETAIL_MAIN_COLUMNS:
        detail_main_not_null &= df[col].notna()
    df["has_reaction_details"] = detail_main_not_null.astype(int)

    detail_cols = [*REACTION_DETAIL_MAIN_COLUMNS, "sorry_count"]
    df["reaction_detail_sum"] = df[detail_cols].fillna(0).sum(axis=1)
    df["reaction_detail_coverage_ratio"] = safe_divide(df["reaction_detail_sum"], df["total_reactions"])

    detail_diff = (df["reaction_detail_sum"] - df["total_reactions"]).abs()
    status = pd.Series("missing_details", index=df.index, dtype="object")
    status.loc[df["total_reactions"] == 0] = "no_reactions"
    ok_mask = (df["has_reaction_details"] == 1) & (df["total_reactions"] > 0) & (detail_diff <= 1)
    mismatch_mask = (df["has_reaction_details"] == 1) & (df["total_reactions"] > 0) & (detail_diff > 1)
    status.loc[ok_mask] = "ok"
    status.loc[mismatch_mask] = "sum_mismatch"
    df["reaction_details_status"] = status

    df["has_share_count"] = ((df["share_count"].notna()) & (df["share_count"] >= 0)).astype(int)
    df["has_comment_count"] = ((df["comment_count"].notna()) & (df["comment_count"] >= 0)).astype(int)
    df["has_engagement_basic"] = (
        (df["has_reaction_total"] == 1)
        & (df["has_share_count"] == 1)
        & (df["has_comment_count"] == 1)
    ).astype(int)

    counts = {col: df[col].fillna(0) for col in NUMERIC_COLUMNS}
    df["positive_reaction_total"] = counts["love_count"] + counts["care_count"]
    df["negative_reaction_total"] = (
        counts["haha_count"] + counts["angry_count"] + counts["sad_count"] + counts["wow_count"]
    )
    df["special_reaction_total"] = df["positive_reaction_total"] + df["negative_reaction_total"]
    df["all_reaction_total_for_formula"] = df["special_reaction_total"] + counts["like_count"]
    formula_denominator = df["all_reaction_total_for_formula"]

    df["reaction_intensity"] = safe_divide(df["special_reaction_total"], formula_denominator)
    df["reaction_valence"] = 0
    df.loc[df["positive_reaction_total"] > df["negative_reaction_total"], "reaction_valence"] = 1
    df.loc[df["positive_reaction_total"] < df["negative_reaction_total"], "reaction_valence"] = -1
    df["polarity_score"] = df["reaction_intensity"] * df["reaction_valence"]

    df["outrage_reaction_index"] = safe_divide(counts["angry_count"], formula_denominator)
    df["amusement_reaction_index"] = safe_divide(counts["haha_count"], formula_denominator)
    df["empathy_reaction_index"] = safe_divide(counts["sad_count"] + counts["care_count"], formula_denominator)
    df["approval_reaction_index"] = safe_divide(counts["like_count"] + counts["love_count"], formula_denominator)

    df["love_ratio"] = safe_divide(counts["love_count"], formula_denominator)
    df["care_ratio"] = safe_divide(counts["care_count"], formula_denominator)
    df["haha_ratio"] = safe_divide(counts["haha_count"], formula_denominator)
    df["wow_ratio"] = safe_divide(counts["wow_count"], formula_denominator)
    df["sad_ratio"] = safe_divide(counts["sad_count"], formula_denominator)
    df["angry_ratio"] = safe_divide(counts["angry_count"], formula_denominator)

    df["approval_index"] = df["approval_reaction_index"]
    df["outrage_index"] = df["outrage_reaction_index"]
    df["amusement_index"] = df["amusement_reaction_index"]
    df["empathy_index"] = df["empathy_reaction_index"]

    df["engagement_total"] = counts["total_reactions"] + counts["comment_count"] + counts["share_count"]
    follower_denominator = df["page_followers"].where(df["page_followers"].notna() & (df["page_followers"] > 0))
    df["reaction_per_follower"] = df["total_reactions"] / follower_denominator
    df["share_per_follower"] = df["share_count"] / follower_denominator
    df["comment_per_follower"] = df["comment_count"] / follower_denominator
    df["engagement_per_follower"] = df["engagement_total"] / follower_denominator
    df = update_metadata_outlier_flags(df)

    formula_metric_columns = [
        "reaction_intensity",
        "reaction_valence",
        "polarity_score",
        "love_ratio",
        "care_ratio",
        "haha_ratio",
        "wow_ratio",
        "sad_ratio",
        "angry_ratio",
        "approval_reaction_index",
        "outrage_reaction_index",
        "amusement_reaction_index",
        "empathy_reaction_index",
        "approval_index",
        "outrage_index",
        "amusement_index",
        "empathy_index",
    ]
    reaction_not_ok = df["reaction_details_status"] != "ok"
    df.loc[reaction_not_ok, formula_metric_columns] = pd.NA

    valid_topic = df["topic_label_id"].isin(VALID_TOPIC_IDS)
    not_excluded = df["label_status"].map(clean_value).str.lower() != "excluded"
    df["usable_for_reaction_analysis"] = (
        (df["has_reaction_total"] == 1)
        & (df["has_reaction_details"] == 1)
        & (df["reaction_details_status"] == "ok")
        & valid_topic
        & not_excluded
        & df["reaction_intensity"].notna()
    ).astype(int)
    df["usable_for_engagement_analysis"] = (
        (df["usable_for_reaction_analysis"] == 1)
        & (df["has_share_count"] == 1)
        & (df["has_comment_count"] == 1)
        & (df["has_page_followers"] == 1)
        & (df["page_followers"] > 0)
        & (df["has_metadata_outlier"] == 0)
    ).astype(int)
    df["usable_for_engagement_analysis_strict"] = df["usable_for_engagement_analysis"]

    return df


def parse_unix_datetime(value: object) -> Tuple[pd.Timestamp, str]:
    text = clean_value(value)
    if not text:
        return pd.NaT, ""
    number = pd.to_numeric(pd.Series([text]), errors="coerce").iloc[0]
    if pd.isna(number) or number <= 0:
        return pd.NaT, ""
    unit = "ms" if number > 10_000_000_000 else "s"
    parsed = pd.to_datetime(number, unit=unit, errors="coerce")
    return parsed, "post_created_time_unix" if pd.notna(parsed) else ""


def parse_text_datetime(value: object, source_name: str) -> Tuple[pd.Timestamp, str]:
    text = clean_value(value)
    if not text:
        return pd.NaT, ""
    parsed = pd.to_datetime(text, errors="coerce")
    return parsed, source_name if pd.notna(parsed) else ""


def choose_post_datetime(row: pd.Series) -> Tuple[pd.Timestamp, str, bool]:
    candidates = [
        ("post_created_time_unix", row.get("post_created_time_unix")),
        ("post_created_time_human", row.get("post_created_time_human")),
        ("post_created_date", row.get("post_created_date")),
    ]
    has_any_input = any(clean_value(value) for _, value in candidates)

    parsed, source = parse_unix_datetime(row.get("post_created_time_unix"))
    if pd.notna(parsed):
        return parsed, source, has_any_input

    for source_name in ["post_created_time_human", "post_created_date"]:
        parsed, source = parse_text_datetime(row.get(source_name), source_name)
        if pd.notna(parsed):
            return parsed, source, has_any_input

    return pd.NaT, "", has_any_input


def update_timestamp_flags(df: pd.DataFrame) -> pd.DataFrame:
    ensure_columns(
        df,
        [
            "post_created_time_raw",
            "post_created_time_unix",
            "post_created_time_human",
            "post_created_date",
            "post_created_hour",
            "post_created_weekday",
            "timestamp_source",
            "timestamp_status",
            "has_post_created_time",
        ],
    )

    parsed_rows = df.apply(choose_post_datetime, axis=1)
    parsed_datetimes = [item[0] for item in parsed_rows]
    parsed_sources = [item[1] for item in parsed_rows]
    has_any_inputs = [item[2] for item in parsed_rows]
    parsed_series = pd.Series(parsed_datetimes, index=df.index)

    ok_mask = parsed_series.notna()
    df["has_post_created_time"] = ok_mask.astype(int)
    df["timestamp_status"] = "missing"
    df.loc[ok_mask, "timestamp_status"] = "ok"
    invalid_mask = (~ok_mask) & pd.Series(has_any_inputs, index=df.index)
    df.loc[invalid_mask, "timestamp_status"] = "invalid"

    df.loc[ok_mask, "post_created_date"] = parsed_series.loc[ok_mask].dt.strftime("%Y-%m-%d")
    df.loc[ok_mask, "post_created_hour"] = parsed_series.loc[ok_mask].dt.hour.astype("Int64")
    df.loc[ok_mask, "post_created_weekday"] = parsed_series.loc[ok_mask].dt.day_name()
    df.loc[ok_mask, "post_created_time_human"] = parsed_series.loc[ok_mask].dt.strftime("%Y-%m-%d %H:%M:%S")

    source_series = pd.Series(parsed_sources, index=df.index)
    df.loc[ok_mask & ~blank_mask(source_series), "timestamp_source"] = source_series.loc[
        ok_mask & ~blank_mask(source_series)
    ]
    return df


def create_model_dataset(df: pd.DataFrame) -> pd.DataFrame:
    caption = df["post_content_for_labeling"]
    mask = (
        (df["usable_for_topic_classification"] == 1)
        & df["topic_label_id"].isin(VALID_MODEL_TOPIC_IDS)
        & (df["label_status"].map(clean_value).str.lower() != "excluded")
        & ~blank_mask(caption)
    )
    model_df = df.loc[mask, ["record_id", "post_content_for_labeling", "topic_label_final", "topic_label_id"]].copy()
    model_df = model_df.rename(columns={"post_content_for_labeling": "caption"})
    model_df["caption"] = model_df["caption"].map(clean_value)
    model_df = model_df.drop_duplicates(subset=["record_id"], keep="first")
    model_df = model_df.drop_duplicates(subset=["caption"], keep="first")
    return model_df


def create_streamlit_enriched(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["caption"] = df["post_content_for_labeling"].map(clean_value)
    ensure_columns(df, STREAMLIT_COLUMNS)
    label_status = df["label_status"].map(clean_value).str.lower()
    mask = (
        df["topic_label_id"].isin(VALID_MODEL_TOPIC_IDS)
        & (label_status != "excluded")
        & (label_status != "unlabeled")
        & ~blank_mask(df["caption"])
    )
    return df.loc[mask, STREAMLIT_COLUMNS].copy()


def create_pilot_exclude_list(labels: pd.DataFrame) -> pd.DataFrame:
    if labels.empty:
        return pd.DataFrame(
            columns=[
                "record_id",
                "exclude_from_test",
                "reason",
                "label_file_source",
                "topic_label_id",
                "topic_label_final",
            ]
        )

    annotation_round = labels["annotation_round"].map(clean_value).str.lower()
    mask = (labels["source_group"] == "Final_Pilot_Labeled") | annotation_round.str.contains(
        "pilot|calibration|adjudication", regex=True, na=False
    )
    pilot = labels[mask & (labels["record_id"].map(clean_value) != "")].copy()
    rows = []
    for record_id, group in pilot.groupby("record_id", sort=False):
        best = choose_best_metadata_row(group)
        rows.append(
            {
                "record_id": record_id,
                "exclude_from_test": 1,
                "reason": "pilot_or_guideline_calibration_sample",
                "label_file_source": join_unique(group["label_file_source"]),
                "topic_label_id": clean_value(best.get("topic_label_id")),
                "topic_label_final": clean_value(best.get("topic_label_final")),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "record_id",
            "exclude_from_test",
            "reason",
            "label_file_source",
            "topic_label_id",
            "topic_label_final",
        ],
    )


def first_non_empty_value(values: pd.Series) -> str:
    values = unique_non_empty(values)
    return values[0] if values else ""


def create_missing_followers_report(df: pd.DataFrame) -> pd.DataFrame:
    temp = df.copy()
    for col in ["page_name", "page_handle", "page_url", "post_url"]:
        ensure_columns(temp, [col])
    temp["_missing_page_followers"] = (temp["has_page_followers"] != 1).astype(int)
    temp["_has_page_followers_count"] = (temp["has_page_followers"] == 1).astype(int)

    grouped = temp.groupby(["page_name", "page_handle", "page_url"], dropna=False)
    report = grouped.agg(
        total_posts=("record_id", "size"),
        missing_page_followers_count=("_missing_page_followers", "sum"),
        has_page_followers_count=("_has_page_followers_count", "sum"),
        usable_for_reaction_analysis_count=("usable_for_reaction_analysis", "sum"),
        usable_for_engagement_analysis_count=("usable_for_engagement_analysis", "sum"),
        example_post_url=("post_url", first_non_empty_value),
    ).reset_index()
    report["missing_page_followers_rate"] = report["missing_page_followers_count"] / report["total_posts"]
    report = report[
        [
            "page_name",
            "page_handle",
            "page_url",
            "total_posts",
            "missing_page_followers_count",
            "has_page_followers_count",
            "missing_page_followers_rate",
            "usable_for_reaction_analysis_count",
            "usable_for_engagement_analysis_count",
            "example_post_url",
        ]
    ]
    report = report.sort_values(
        ["missing_page_followers_count", "usable_for_reaction_analysis_count"],
        ascending=[False, False],
    )
    return report


def create_metadata_outlier_report(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "record_id",
        "page_name",
        "post_url",
        "caption",
        "column_name",
        "value",
        "total_reactions",
        "comment_count",
        "share_count",
        "page_followers",
        "engagement_total",
        "engagement_per_follower",
        "reason",
    ]
    rows: List[Dict[str, object]] = []
    rule_specs = [
        ("comment_count", df["comment_count"] >= 100000, "comment_count >= 100000"),
        ("share_count", df["share_count"] >= 100000, "share_count >= 100000"),
        ("total_reactions", df["total_reactions"] >= 100000, "total_reactions >= 100000"),
        ("engagement_per_follower", df["engagement_per_follower"] > 0.2, "engagement_per_follower > 0.2"),
        (
            "comment_count",
            (df["comment_count"] > df["total_reactions"].fillna(0) * 20) & (df["comment_count"] >= 10000),
            "comment_count > total_reactions * 20 and comment_count >= 10000",
        ),
        (
            "share_count",
            (df["share_count"] > df["total_reactions"].fillna(0) * 20) & (df["share_count"] >= 10000),
            "share_count > total_reactions * 20 and share_count >= 10000",
        ),
    ]
    for column_name, mask, reason in rule_specs:
        for _, row in df[mask.fillna(False)].iterrows():
            rows.append(
                {
                    "record_id": row.get("record_id"),
                    "page_name": row.get("page_name"),
                    "post_url": row.get("post_url"),
                    "caption": clean_value(row.get("post_content_for_labeling")),
                    "column_name": column_name,
                    "value": row.get(column_name),
                    "total_reactions": row.get("total_reactions"),
                    "comment_count": row.get("comment_count"),
                    "share_count": row.get("share_count"),
                    "page_followers": row.get("page_followers"),
                    "engagement_total": row.get("engagement_total"),
                    "engagement_per_follower": row.get("engagement_per_follower"),
                    "reason": reason,
                }
            )
    return pd.DataFrame(rows, columns=columns)


def create_taxonomy_mapping_used() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "topic_label_id": topic_id,
                "topic_label_final": topic_label,
                "source_design_note": TAXONOMY_SOURCE_NOTES[topic_id],
            }
            for topic_id, topic_label in TOPIC_ID_TO_LABEL.items()
        ]
    )


def create_label_distribution(
    master_labeled: pd.DataFrame, model_df: pd.DataFrame, streamlit_df: pd.DataFrame
) -> pd.DataFrame:
    rows = []
    for topic_id, topic_label in TOPIC_ID_TO_LABEL.items():
        master_mask = master_labeled["topic_label_id"] == topic_id
        model_mask = model_df["topic_label_id"] == topic_id if not model_df.empty else pd.Series([], dtype=bool)
        streamlit_mask = (
            streamlit_df["topic_label_id"] == topic_id if not streamlit_df.empty else pd.Series([], dtype=bool)
        )
        uncertain = master_mask & (master_labeled["is_uncertain_label"].map(to_flag) == 1)
        excluded = master_mask & (master_labeled["label_status"].map(clean_value).str.lower() == "excluded")
        rows.append(
            {
                "topic_label_id": topic_id,
                "topic_label_final": topic_label,
                "count_in_master_labeled": int(master_mask.sum()),
                "count_in_model_dataset": int(model_mask.sum()) if len(model_mask) else 0,
                "count_in_streamlit_enriched": int(streamlit_mask.sum()) if len(streamlit_mask) else 0,
                "uncertain_count": int(uncertain.sum()),
                "excluded_count": int(excluded.sum()),
            }
        )
    return pd.DataFrame(rows)


def percentage(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(count / total * 100, 4)


def create_metadata_coverage_summary(
    df: pd.DataFrame, pilot_df: pd.DataFrame, model_df: pd.DataFrame, streamlit_df: pd.DataFrame
) -> pd.DataFrame:
    total = len(df)
    valid_topic = df["topic_label_id"].isin(VALID_TOPIC_IDS)
    excluded = df["label_status"].map(clean_value).str.lower() == "excluded"
    uncertain = df["is_uncertain_label"].map(to_flag) == 1
    t18_master = df["topic_label_id"] == "T18"
    metrics = [
        ("total_master_rows", total),
        ("labeled_rows", int(valid_topic.sum())),
        ("unlabeled_rows", int((~valid_topic & ~excluded).sum())),
        ("valid_topic_label_rows", int(valid_topic.sum())),
        ("excluded_rows", int(excluded.sum())),
        ("uncertain_rows", int(uncertain.sum())),
        (
            "master_usable_for_topic_classification_rows_including_t18",
            int((df["usable_for_topic_classification"] == 1).sum()),
        ),
        ("usable_for_topic_classification_rows", len(model_df)),
        ("usable_for_reaction_analysis_rows", int((df["usable_for_reaction_analysis"] == 1).sum())),
        ("usable_for_engagement_analysis_rows", int((df["usable_for_engagement_analysis"] == 1).sum())),
        (
            "usable_for_engagement_analysis_strict_rows",
            int((df["usable_for_engagement_analysis_strict"] == 1).sum()),
        ),
        ("metadata_outlier_rows", int((df["has_metadata_outlier"] == 1).sum())),
        ("has_page_followers_rows", int((df["has_page_followers"] == 1).sum())),
        ("missing_page_followers_rows", int((df["has_page_followers"] != 1).sum())),
        ("has_reaction_total_rows", int((df["has_reaction_total"] == 1).sum())),
        ("has_reaction_details_rows", int((df["has_reaction_details"] == 1).sum())),
        ("reaction_sum_mismatch_rows", int((df["reaction_details_status"] == "sum_mismatch").sum())),
        ("has_share_count_rows", int((df["has_share_count"] == 1).sum())),
        ("has_comment_count_rows", int((df["has_comment_count"] == 1).sum())),
        ("has_post_created_time_rows", int((df["has_post_created_time"] == 1).sum())),
        ("timestamp_ok_rows", int((df["timestamp_status"] == "ok").sum())),
        ("timestamp_missing_rows", int((df["timestamp_status"] == "missing").sum())),
        ("timestamp_invalid_rows", int((df["timestamp_status"] == "invalid").sum())),
        ("pilot_exclude_from_test_rows", len(pilot_df)),
        ("t18_rows_in_master", int(t18_master.sum())),
        ("t18_excluded_rows", int((t18_master & excluded).sum())),
        ("t18_removed_from_model_dataset", int(t18_master.sum() - (model_df["topic_label_id"] == "T18").sum())),
        (
            "t18_removed_from_streamlit_enriched",
            int(t18_master.sum() - (streamlit_df["topic_label_id"] == "T18").sum()),
        ),
    ]
    return pd.DataFrame(
        [{"metric": metric, "count": int(count), "percentage": percentage(int(count), total)} for metric, count in metrics]
    )


def dataframe_to_markdown(df: pd.DataFrame, max_rows: Optional[int] = None) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    if df.empty:
        return "_Không có dữ liệu._"
    display_df = df.copy()
    display_df = display_df.where(pd.notna(display_df), "")
    headers = [str(col) for col in display_df.columns]
    rows = display_df.astype(str).values.tolist()

    def esc(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")

    lines = [
        "| " + " | ".join(esc(header) for header in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(esc(value) for value in row) + " |")
    return "\n".join(lines)


def write_technical_report(
    path: Path,
    output_file_summary: pd.DataFrame,
    taxonomy_mapping: pd.DataFrame,
    label_distribution: pd.DataFrame,
    metadata_coverage_summary: pd.DataFrame,
    conflicts: pd.DataFrame,
    missing_followers: pd.DataFrame,
    metadata_outlier_report: pd.DataFrame,
    master_labeled: pd.DataFrame,
    model_df: pd.DataFrame,
    streamlit_df: pd.DataFrame,
    pilot_df: pd.DataFrame,
    label_status_fixed_count: int,
    manual_follower_override_count: int,
    created_columns: Sequence[str],
    warnings: Sequence[str],
) -> None:
    coverage_metrics = metadata_coverage_summary[
        metadata_coverage_summary["metric"].isin(
            [
                "master_usable_for_topic_classification_rows_including_t18",
                "usable_for_topic_classification_rows",
                "usable_for_reaction_analysis_rows",
                "usable_for_engagement_analysis_rows",
                "usable_for_engagement_analysis_strict_rows",
                "has_page_followers_rows",
                "has_post_created_time_rows",
                "metadata_outlier_rows",
            ]
        )
    ]
    issue_counts = conflicts["issue_type"].value_counts().to_dict() if not conflicts.empty else {}
    true_conflicts = conflicts[conflicts["issue_type"].isin(TRUE_CONFLICT_TYPES)] if not conflicts.empty else conflicts
    caption_empty_count = int(blank_mask(master_labeled["post_content_for_labeling"]).sum())
    label_null_count = int((~master_labeled["topic_label_id"].isin(VALID_TOPIC_IDS)).sum())
    t18_count = int((master_labeled["topic_label_id"] == "T18").sum())
    t18_excluded_count = int(
        ((master_labeled["topic_label_id"] == "T18") & (master_labeled["label_status"].map(clean_value).str.lower() == "excluded")).sum()
    )
    t18_removed_from_model = int(t18_count - (model_df["topic_label_id"] == "T18").sum())
    t18_removed_from_streamlit = int(t18_count - (streamlit_df["topic_label_id"] == "T18").sum())
    uncertain_count = int((master_labeled["is_uncertain_label"].map(to_flag) == 1).sum())
    reaction_mismatch_count = int((master_labeled["reaction_details_status"] == "sum_mismatch").sum())
    timestamp_missing_count = int((master_labeled["timestamp_status"] == "missing").sum())
    timestamp_invalid_count = int((master_labeled["timestamp_status"] == "invalid").sum())
    missing_follower_pages = int((missing_followers["missing_page_followers_count"] > 0).sum())
    metadata_outlier_rows = int((master_labeled["has_metadata_outlier"] == 1).sum())

    report = f"""# Technical Report: Final Master Data Generation

## 1. Mục tiêu
Tạo lại final datasets của DS107 sau khi fix logic label mapping, label status, T18 handling, reaction mismatch và metadata outlier. Các output chính gồm Master labeled, model dataset cho topic classification, Streamlit enriched dataset và pilot exclude list.

## 2. Input
- Master: `{rel_path(MASTER_PATH)}`
- Label final: `{rel_path(LABEL_DIRS[0])}`
- Label pilot: `{rel_path(LABEL_DIRS[1])}`

## 3. Quy trình thực hiện
- Đọc master after dedup
- Đọc và chuẩn hóa label
- Kiểm tra duplicate/conflict label
- Join label vào master
- Cập nhật needs_topic_label và usable flags
- Tính reaction/public response metrics
- Tạo model dataset
- Tạo Streamlit enriched dataset
- Tạo pilot exclude list
- Tạo các báo cáo thống kê

## 4. Output files
{dataframe_to_markdown(output_file_summary)}

## 5. Taxonomy mapping used
Mapping dưới đây là taxonomy chính thức đã dùng khi xuất file. `topic_label_final` luôn được chuẩn hóa theo mapping này, kể cả khi label name trong input có biến thể khác.

{dataframe_to_markdown(taxonomy_mapping)}

## 6. Thống kê nhãn
{dataframe_to_markdown(label_distribution)}

## 7. Thống kê usable theo tác vụ
{dataframe_to_markdown(coverage_metrics)}

## 8. T18 handling
- T18 được giữ trong Master để truy vết: `{t18_count}` dòng.
- T18 có `label_status = excluded`: `{t18_excluded_count}` dòng.
- T18 removed from model dataset: `{t18_removed_from_model}` dòng.
- T18 removed from Streamlit enriched: `{t18_removed_from_streamlit}` dòng.
- Master có `{t18_count + len(model_df)}` dòng usable_for_topic_classification nếu tính cả T18; model dataset chính chỉ còn `{len(model_df)}` dòng dữ liệu sau khi loại T18. Khi mở CSV có thể thấy `{len(model_df) + 1}` dòng nếu tính cả header.

## 9. Label status fix
- Số dòng có label hợp lệ nhưng status rỗng hoặc `unlabeled` đã được sửa: `{label_status_fixed_count}` dòng.
- Sau fix, `unlabeled` chỉ còn dùng cho dòng thật sự chưa có `topic_label_id` hợp lệ T01-T18.
- Streamlit enriched không giữ dòng `label_status = unlabeled`.

## 10. Metadata outlier handling
- Số dòng metadata outlier: `{metadata_outlier_rows}` dòng.
- Số dòng outlier-rule trong `metadata_outlier_report.csv`: `{len(metadata_outlier_report)}` dòng.
- Rule dùng để flag: `comment_count >= 100000`, `share_count >= 100000`, `total_reactions >= 100000`, `engagement_per_follower > 0.2`, `comment_count > total_reactions * 20 and comment_count >= 10000`, `share_count > total_reactions * 20 and share_count >= 10000`.
- Dòng outlier không bị sửa giá trị gốc, nhưng được set `usable_for_engagement_analysis = 0` và `usable_for_engagement_analysis_strict = 0`.

## 11. Reaction mismatch handling
- Reaction detail sum mismatch: `{reaction_mismatch_count}` dòng.
- Nếu `reaction_details_status != ok`, dòng đó có `usable_for_reaction_analysis = 0`.
- Các chỉ số reaction-based như `polarity_score`, `reaction_intensity`, `approval_reaction_index`, `outrage_reaction_index`, `amusement_reaction_index`, `empathy_reaction_index` được để null khi reaction details không `ok`.

## 12. Pilot/calibration
- `{len(pilot_df)}` record trong `Pilot_Record_IDs_Exclude_From_Test.csv` không nên đưa vào test set.
- Các record này có thể dùng cho train nếu nhóm muốn tận dụng nhãn đã adjudicate, nhưng cần loại khỏi test để tránh đánh giá quá lạc quan.

## 13. Vấn đề còn cần quan tâm
- Tổng issue trong `label_join_conflicts.csv`: `{len(conflicts)}` dòng.
- True label conflicts: `{len(true_conflicts)}` dòng.
- Chi tiết issue theo loại: `{json.dumps(issue_counts, ensure_ascii=False)}`.
- Manual page follower override đã áp dụng: `{manual_follower_override_count}` dòng post.
- Page thiếu followers: `{missing_follower_pages}` page có ít nhất một post thiếu follower.
- Timestamp missing: `{timestamp_missing_count}` dòng; timestamp invalid: `{timestamp_invalid_count}` dòng.
- Caption rỗng: `{caption_empty_count}` dòng.
- Label null hoặc chưa hợp lệ T01-T18: `{label_null_count}` dòng.
- T18 count: `{t18_count}` dòng.
- Uncertain count: `{uncertain_count}` dòng.
- Metadata outlier: `{metadata_outlier_rows}` dòng.
- Cột master được tạo mới do thiếu schema: `{", ".join(created_columns) if created_columns else "Không có"}`.
- Warnings: `{", ".join(warnings) if warnings else "Không có"}`.
"""
    path.write_text(report, encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding=CSV_ENCODING)


def dataframe_records(df: pd.DataFrame) -> List[Dict[str, object]]:
    return json.loads(df.to_json(orient="records", force_ascii=False))


def validate_outputs(
    master_labeled: pd.DataFrame,
    master_input: pd.DataFrame,
    model_df: pd.DataFrame,
    streamlit_df: pd.DataFrame,
    pilot_df: pd.DataFrame,
) -> None:
    assert len(master_labeled) == len(master_input), "Master labeled row count changed."
    assert master_labeled["record_id"].is_unique, "Master labeled record_id contains duplicates."
    assert model_df["record_id"].is_unique, "Model dataset record_id contains duplicates."
    assert streamlit_df["record_id"].is_unique, "Streamlit enriched record_id contains duplicates."
    assert not blank_mask(model_df["caption"]).any(), "Model dataset contains null/blank caption."
    assert not blank_mask(streamlit_df["caption"]).any(), "Streamlit enriched contains null/blank caption."
    assert model_df["topic_label_id"].isin(VALID_MODEL_TOPIC_IDS).all(), "Model dataset contains invalid topic_label_id."
    assert streamlit_df["topic_label_id"].isin(VALID_MODEL_TOPIC_IDS).all(), "Streamlit contains invalid topic_label_id."
    assert "T18" not in set(model_df["topic_label_id"]), "Model dataset still contains T18."
    assert "T18" not in set(streamlit_df["topic_label_id"]), "Streamlit enriched still contains T18."
    assert "unlabeled" not in set(streamlit_df["label_status"].dropna().map(clean_value).str.lower()), (
        "Streamlit enriched contains label_status=unlabeled."
    )
    assert streamlit_df["has_metadata_outlier"].isin([0, 1]).all(), "Invalid has_metadata_outlier values."
    assert model_df["caption"].is_unique, "Model dataset contains duplicate exact caption."

    master_status_by_id = master_labeled.set_index("record_id")["label_status"].map(clean_value).str.lower()
    model_status = master_status_by_id.loc[model_df["record_id"]]
    assert "unlabeled" not in set(model_status.dropna()), "Model dataset includes unlabeled rows from Master."

    missing_streamlit_cols = [col for col in STREAMLIT_COLUMNS if col not in streamlit_df.columns]
    assert not missing_streamlit_cols, f"Streamlit enriched missing required columns: {missing_streamlit_cols}"
    assert not blank_mask(pilot_df["record_id"]).any(), "Pilot exclude list contains null/blank record_id."


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_timestamp = datetime.now().isoformat(timespec="seconds")
    warnings: List[str] = []

    master_input = read_master(MASTER_PATH)
    master_input_rows = len(master_input)
    master_input_columns = len(master_input.columns)
    created_columns = ensure_columns(master_input, MASTER_EXPECTED_COLUMNS)
    master_output_columns = [col for col in master_input.columns if col != "split"]

    label_file_entries = discover_label_files(LABEL_DIRS)
    label_frames = []
    label_file_summaries = []
    for label_path, source_group in label_file_entries:
        raw_label = read_label_file(label_path)
        label_file_summaries.append(
            {
                "file": rel_path(label_path),
                "source_group": source_group,
                "rows": len(raw_label),
                "columns": len(raw_label.columns),
                "extra_columns": [
                    col
                    for col in raw_label.columns
                    if col
                    not in {
                        "record_id",
                        "topic_label_final",
                        "topic_label_id",
                        "label_status",
                        "label_source",
                        "annotator_1",
                        "annotator_2",
                        "annotation_round",
                        "annotation_note",
                        "is_uncertain_label",
                        "exclude_reason",
                        "quality_note",
                    }
                ],
            }
        )
        label_frames.append(normalize_label_dataframe(raw_label, label_path, source_group))

    all_labels = pd.concat(label_frames, ignore_index=True) if label_frames else empty_normalized_labels()
    raw_label_rows = len(all_labels)
    resolved_labels, duplicate_conflicts = resolve_label_duplicates(all_labels)

    master_labeled, join_conflicts, labels_joined = join_labels_to_master(master_input, resolved_labels)
    master_labeled = update_topic_flags(master_labeled)
    label_status_fixed_count = int(master_labeled.attrs.get("unlabeled_with_valid_label_fixed_count", 0))
    master_labeled = update_reaction_flags_and_metrics(master_labeled)
    manual_follower_override_count = int(master_labeled.attrs.get("manual_page_follower_overrides_applied", 0))
    master_labeled = update_timestamp_flags(master_labeled)

    model_df = create_model_dataset(master_labeled)
    streamlit_df = create_streamlit_enriched(master_labeled)
    pilot_df = create_pilot_exclude_list(all_labels)
    missing_followers = create_missing_followers_report(master_labeled)
    metadata_outlier_report = create_metadata_outlier_report(master_labeled)
    taxonomy_mapping = create_taxonomy_mapping_used()
    label_distribution = create_label_distribution(master_labeled, model_df, streamlit_df)
    metadata_coverage_summary = create_metadata_coverage_summary(master_labeled, pilot_df, model_df, streamlit_df)
    conflicts = pd.concat([duplicate_conflicts, join_conflicts], ignore_index=True)
    if conflicts.empty:
        conflicts = empty_conflicts()
    true_conflicts = conflicts[conflicts["issue_type"].isin(TRUE_CONFLICT_TYPES)] if not conflicts.empty else conflicts

    output_paths = {
        "master_labeled": OUTPUT_DIR / "Master_Facebook_News_Posts_TeamCrawl_Labeled.csv",
        "model_dataset": OUTPUT_DIR / "Topic_Classification_Model_Dataset.csv",
        "streamlit_enriched": OUTPUT_DIR / "Public_Response_Streamlit_Enriched.csv",
        "pilot_exclude": OUTPUT_DIR / "Pilot_Record_IDs_Exclude_From_Test.csv",
        "technical_report": OUTPUT_DIR / "Final_Master_Data_Technical_Report.md",
        "statistics_json": OUTPUT_DIR / "Final_Master_Data_Statistics.json",
        "missing_followers": OUTPUT_DIR / "missing_followers_by_page.csv",
        "metadata_outlier_report": OUTPUT_DIR / "metadata_outlier_report.csv",
        "label_join_conflicts": OUTPUT_DIR / "label_join_conflicts.csv",
        "label_distribution": OUTPUT_DIR / "label_distribution.csv",
        "metadata_coverage_summary": OUTPUT_DIR / "metadata_coverage_summary.csv",
        "taxonomy_mapping_used": OUTPUT_DIR / "taxonomy_mapping_used.csv",
    }

    master_to_write = master_labeled[master_output_columns].copy()

    output_file_summary = pd.DataFrame(
        [
            {
                "File": path.name,
                "Mục đích": purpose,
                "Số dòng dữ liệu": rows,
                "Số dòng file nếu tính header": rows + 1 if path.suffix.lower() == ".csv" else "N/A",
                "Số cột": cols,
            }
            for path, purpose, rows, cols in [
                (
                    output_paths["master_labeled"],
                    "Master giữ schema gốc, đã join label và cập nhật flags/metrics",
                    len(master_to_write),
                    len(master_to_write.columns),
                ),
                (
                    output_paths["model_dataset"],
                    "Dataset train topic classification cho Hân",
                    len(model_df),
                    len(model_df.columns),
                ),
                (
                    output_paths["streamlit_enriched"],
                    "Dataset enriched cho Streamlit dashboard của Yến",
                    len(streamlit_df),
                    len(streamlit_df.columns),
                ),
                (
                    output_paths["pilot_exclude"],
                    "Danh sách record pilot/calibration loại khỏi test",
                    len(pilot_df),
                    len(pilot_df.columns),
                ),
                (
                    output_paths["missing_followers"],
                    "Report page thiếu follower",
                    len(missing_followers),
                    len(missing_followers.columns),
                ),
                (
                    output_paths["metadata_outlier_report"],
                    "Report metadata outlier theo từng rule",
                    len(metadata_outlier_report),
                    len(metadata_outlier_report.columns),
                ),
                (
                    output_paths["label_join_conflicts"],
                    "Report conflict/invalid label/join issue",
                    len(conflicts),
                    len(conflicts.columns),
                ),
                (
                    output_paths["label_distribution"],
                    "Phân phối nhãn theo topic",
                    len(label_distribution),
                    len(label_distribution.columns),
                ),
                (
                    output_paths["metadata_coverage_summary"],
                    "Coverage metadata và usable flags",
                    len(metadata_coverage_summary),
                    len(metadata_coverage_summary.columns),
                ),
                (
                    output_paths["taxonomy_mapping_used"],
                    "Mapping taxonomy chính thức đã dùng",
                    len(taxonomy_mapping),
                    len(taxonomy_mapping.columns),
                ),
                (
                    output_paths["statistics_json"],
                    "Thống kê kỹ thuật dạng JSON",
                    1,
                    1,
                ),
                (
                    output_paths["technical_report"],
                    "Báo cáo kỹ thuật tiếng Việt",
                    1,
                    1,
                ),
            ]
        ]
    )

    statistics = {
        "input_paths": {
            "master": rel_path(MASTER_PATH),
            "label_dirs": [rel_path(path) for path in LABEL_DIRS],
        },
        "output_paths": {key: rel_path(path) for key, path in output_paths.items()},
        "run_timestamp": run_timestamp,
        "master_input_rows": int(master_input_rows),
        "master_input_columns": int(master_input_columns),
        "master_labeled_rows": int(len(master_to_write)),
        "master_labeled_columns": int(len(master_to_write.columns)),
        "number_of_label_files_loaded": int(len(label_file_entries)),
        "label_file_summaries": label_file_summaries,
        "number_of_raw_label_rows": int(raw_label_rows),
        "number_of_unique_labeled_record_id": int(resolved_labels["record_id"].nunique()) if not resolved_labels.empty else 0,
        "number_of_labels_joined_successfully": int(labels_joined),
        "number_of_labels_not_found_in_master": int(
            (conflicts["issue_type"] == "label_record_id_not_found_in_master").sum()
        )
        if not conflicts.empty
        else 0,
        "number_of_conflicts": int(len(conflicts)),
        "number_of_true_label_conflicts": int(len(true_conflicts)),
        "model_dataset_rows": int(len(model_df)),
        "streamlit_enriched_rows": int(len(streamlit_df)),
        "pilot_exclude_rows": int(len(pilot_df)),
        "unlabeled_with_valid_label_fixed": int(label_status_fixed_count),
        "t18_rows_in_master": int((master_to_write["topic_label_id"] == "T18").sum()),
        "t18_excluded_rows": int(
            (
                (master_to_write["topic_label_id"] == "T18")
                & (master_to_write["label_status"].map(clean_value).str.lower() == "excluded")
            ).sum()
        ),
        "t18_removed_from_model_dataset": int((master_to_write["topic_label_id"] == "T18").sum()),
        "t18_removed_from_streamlit_enriched": int((master_to_write["topic_label_id"] == "T18").sum()),
        "master_usable_for_topic_classification_rows_including_t18": int(
            (master_to_write["usable_for_topic_classification"] == 1).sum()
        ),
        "usable_for_topic_classification_rows_after_t18_removal": int(len(model_df)),
        "metadata_outlier_rows": int((master_to_write["has_metadata_outlier"] == 1).sum()),
        "metadata_outlier_report_rows": int(len(metadata_outlier_report)),
        "manual_page_follower_overrides_applied_rows": int(manual_follower_override_count),
        "manual_page_follower_overrides": MANUAL_PAGE_FOLLOWER_OVERRIDES,
        "usable_reaction_analysis_rows": int((master_to_write["usable_for_reaction_analysis"] == 1).sum()),
        "usable_engagement_analysis_rows": int((master_to_write["usable_for_engagement_analysis"] == 1).sum()),
        "usable_engagement_strict_rows": int(
            (master_to_write["usable_for_engagement_analysis_strict"] == 1).sum()
        ),
        "label_distribution": dataframe_records(label_distribution),
        "taxonomy_mapping_used": dataframe_records(taxonomy_mapping),
        "metadata_coverage_summary": dataframe_records(metadata_coverage_summary),
        "output_file_row_counts": dataframe_records(output_file_summary),
        "missing_followers_by_page_top_20": dataframe_records(missing_followers.head(20)),
        "metadata_outlier_report_top_20": dataframe_records(metadata_outlier_report.head(20)),
        "created_columns": list(created_columns),
        "warnings": warnings,
    }

    try:
        validate_outputs(master_to_write, master_input, model_df, streamlit_df, pilot_df)
        for path in output_paths.values():
            assert path.parent == OUTPUT_DIR, f"Output path is outside output folder: {path}"
    except AssertionError as exc:
        debug_dir = OUTPUT_DIR / "_debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_path = debug_dir / f"final_dataset_validation_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        debug_path.write_text(str(exc), encoding="utf-8")
        print(f"VALIDATION FAILED: {exc}")
        print(f"Debug error written to: {rel_path(debug_path)}")
        raise

    write_csv(master_to_write, output_paths["master_labeled"])
    write_csv(model_df, output_paths["model_dataset"])
    write_csv(streamlit_df, output_paths["streamlit_enriched"])
    write_csv(pilot_df, output_paths["pilot_exclude"])
    write_csv(missing_followers, output_paths["missing_followers"])
    write_csv(metadata_outlier_report, output_paths["metadata_outlier_report"])
    write_csv(conflicts[CONFLICT_COLUMNS], output_paths["label_join_conflicts"])
    write_csv(label_distribution, output_paths["label_distribution"])
    write_csv(metadata_coverage_summary, output_paths["metadata_coverage_summary"])
    write_csv(taxonomy_mapping, output_paths["taxonomy_mapping_used"])
    output_paths["statistics_json"].write_text(
        json.dumps(statistics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    write_technical_report(
        output_paths["technical_report"],
        output_file_summary,
        taxonomy_mapping,
        label_distribution,
        metadata_coverage_summary,
        conflicts,
        missing_followers,
        metadata_outlier_report,
        master_to_write,
        model_df,
        streamlit_df,
        pilot_df,
        label_status_fixed_count,
        manual_follower_override_count,
        created_columns,
        warnings,
    )

    t18_rows_in_master = int((master_to_write["topic_label_id"] == "T18").sum())
    print("=== FINAL DATASET FIX SUMMARY ===")
    print(f"Master input rows: {master_input_rows}")
    print(f"Master labeled rows: {len(master_to_write)}")
    print(f"Model dataset rows: {len(model_df)}")
    print(f"Streamlit enriched rows: {len(streamlit_df)}")
    print(f"Pilot exclude rows: {len(pilot_df)}")
    print(f"Unlabeled-with-valid-label fixed: {label_status_fixed_count}")
    print(f"T18 rows in master: {t18_rows_in_master}")
    print(f"T18 removed from model: {t18_rows_in_master}")
    print(f"T18 removed from streamlit: {t18_rows_in_master}")
    print(f"Metadata outlier rows: {(master_to_write['has_metadata_outlier'] == 1).sum()}")
    print(f"Manual follower override rows: {manual_follower_override_count}")
    print(f"Usable reaction analysis rows: {(master_to_write['usable_for_reaction_analysis'] == 1).sum()}")
    print(f"Usable engagement analysis rows: {(master_to_write['usable_for_engagement_analysis'] == 1).sum()}")
    print(
        "Usable engagement strict rows: "
        f"{(master_to_write['usable_for_engagement_analysis_strict'] == 1).sum()}"
    )
    print(f"True label conflicts: {len(true_conflicts)}")
    print(f"Missing followers pages: {(missing_followers['missing_page_followers_count'] > 0).sum()}")
    print(f"Timestamp missing rows: {(master_to_write['timestamp_status'] == 'missing').sum()}")
    print(f"Output folder: {rel_path(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()

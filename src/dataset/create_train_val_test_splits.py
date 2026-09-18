#!/usr/bin/env python3
"""Create reproducible train/validation/test splits for DS107.

The split excludes T18 from model data and prevents pilot/calibration records
from entering the test set. It writes CSV splits and a validation report.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import pandas as pd
from sklearn.model_selection import train_test_split


RANDOM_STATE = 42
DEFAULT_INPUT = Path("data_outputs/06_final_master_data/Topic_Classification_Model_Dataset.csv")
DEFAULT_PILOT_IDS = Path("data_outputs/06_final_master_data/Pilot_Record_IDs_Exclude_From_Test.csv")
DEFAULT_OUTPUT_DIR = Path("data_outputs/07_cleaned_splits/generated_raw")
LABEL_COL = "topic_label_id"
RECORD_ID_COL = "record_id"
INVALID_LABEL = "T18"


def read_pilot_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    df = pd.read_csv(path, low_memory=False)
    if RECORD_ID_COL not in df.columns:
        return set()
    return set(df[RECORD_ID_COL].dropna().astype(str))


def can_stratify(labels: Iterable[object]) -> bool:
    counts = pd.Series(labels).astype(str).value_counts()
    return len(counts) > 1 and bool((counts >= 2).all())


def stratified_sample(
    df: pd.DataFrame,
    n_sample: int,
    label_col: str,
    random_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if n_sample <= 0:
        return df.iloc[0:0].copy(), df.copy()
    if n_sample >= len(df):
        return df.copy(), df.iloc[0:0].copy()

    stratify = df[label_col].astype(str) if can_stratify(df[label_col]) else None
    keep, sample = train_test_split(
        df,
        test_size=n_sample,
        random_state=random_state,
        shuffle=True,
        stratify=stratify,
    )
    return sample.reset_index(drop=True), keep.reset_index(drop=True)


def distribution_rows(df: pd.DataFrame, split: str, label_col: str) -> list[dict[str, object]]:
    counts = df[label_col].astype(str).value_counts().sort_index()
    total = len(df)
    return [
        {
            "split": split,
            "topic_label_id": label,
            "count": int(count),
            "ratio": float(count / total) if total else 0.0,
        }
        for label, count in counts.items()
    ]


def write_report(
    output_dir: Path,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    pilot_ids: set[str],
    label_col: str,
    source_path: Path,
    random_state: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for split, df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        ids = set(df[RECORD_ID_COL].dropna().astype(str)) if RECORD_ID_COL in df.columns else set()
        rows.append(
            {
                "split": split,
                "rows": len(df),
                "unique_record_ids": len(ids),
                "duplicate_record_ids": len(df) - len(ids),
                "t18_rows": int(df[label_col].astype(str).eq(INVALID_LABEL).sum()),
                "pilot_or_calibration_rows": len(ids & pilot_ids),
            }
        )
    pd.DataFrame(rows).to_csv(output_dir / "split_validation_report.csv", index=False)

    distribution = []
    for split, df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        distribution.extend(distribution_rows(df, split, label_col))
    pd.DataFrame(distribution).to_csv(output_dir / "label_distribution_by_split.csv", index=False)

    manifest = {
        "source_path": str(source_path),
        "random_state": random_state,
        "invalid_label_removed": INVALID_LABEL,
        "pilot_ids_excluded_from_test": len(pilot_ids),
        "outputs": ["train.csv", "val.csv", "test.csv", "split_validation_report.csv"],
    }
    (output_dir / "split_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create DS107 train/val/test splits.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--pilot-ids", type=Path, default=DEFAULT_PILOT_IDS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--label-col", default=LABEL_COL)
    parser.add_argument("--test-size", type=float, default=0.10)
    parser.add_argument("--val-size", type=float, default=0.10)
    parser.add_argument("--random-state", type=int, default=RANDOM_STATE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    df = pd.read_csv(args.input, low_memory=False)

    required = {RECORD_ID_COL, args.label_col}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Input missing required columns: {sorted(missing)}")

    df = df.copy()
    df[RECORD_ID_COL] = df[RECORD_ID_COL].astype(str)
    df[args.label_col] = df[args.label_col].astype(str)
    df = df.loc[~df[args.label_col].eq(INVALID_LABEL)].reset_index(drop=True)

    pilot_ids = read_pilot_ids(args.pilot_ids)
    non_pilot_df = df.loc[~df[RECORD_ID_COL].isin(pilot_ids)].reset_index(drop=True)
    pilot_df = df.loc[df[RECORD_ID_COL].isin(pilot_ids)].reset_index(drop=True)

    n_total = len(df)
    n_test = round(n_total * args.test_size)
    n_val = round(n_total * args.val_size)

    test_df, non_test_df = stratified_sample(
        non_pilot_df,
        n_test,
        args.label_col,
        args.random_state,
    )
    train_val_df = pd.concat([non_test_df, pilot_df], ignore_index=True)
    val_df, train_df = stratified_sample(
        train_val_df,
        n_val,
        args.label_col,
        args.random_state + 1,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(args.output_dir / "train.csv", index=False)
    val_df.to_csv(args.output_dir / "val.csv", index=False)
    test_df.to_csv(args.output_dir / "test.csv", index=False)
    write_report(
        args.output_dir,
        train_df,
        val_df,
        test_df,
        pilot_ids,
        args.label_col,
        args.input,
        args.random_state,
    )

    pilot_in_test = set(test_df[RECORD_ID_COL].astype(str)) & pilot_ids
    if pilot_in_test:
        raise RuntimeError(f"Pilot/calibration leakage into test set: {len(pilot_in_test)} records")
    if any(split[args.label_col].astype(str).eq(INVALID_LABEL).any() for split in [train_df, val_df, test_df]):
        raise RuntimeError(f"{INVALID_LABEL} found in one of the output splits")

    print(f"Wrote train/val/test splits to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

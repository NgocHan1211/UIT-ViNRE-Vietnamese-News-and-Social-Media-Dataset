#!/usr/bin/env python3
"""Train traditional ML baselines for Vietnamese Facebook topic classification.

The benchmark trains on train, tunes on validation, and reports test metrics only
after hyperparameters are selected by validation Macro-F1.
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
import re
import shutil
import sys
import time
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

DEFAULT_DATA_DIR = Path("data/07_Cleaned_Data")
DEFAULT_OUTPUT_DIR = Path("data/08_Modeling_Results/traditional_ml")

DEFAULT_SCENARIO_ORDER = [
    "01_Raw_Data",
    "02_Basic_Clean",
    "03_Full_Clean",
    "04_No_Stopwords",
    "05_Balanced",
]
MODELS = ["LogisticRegression", "RandomForest", "XGBoost", "LinearSVC"]
SPLITS = ["train", "val", "test"]
ALL_LABELS = [f"T{i:02d}" for i in range(1, 18)]
INVALID_REMOVED_LABEL = "T18"

BASE_TEXT_COLUMNS = [
    "post_content_for_labeling",
    "caption",
    "text",
    "content",
    "raw_text",
    "text_raw",
    "basic_clean_text",
    "text_basic_clean",
    "full_clean_text",
    "text_full_clean",
    "no_stopwords_text",
    "text_no_stopwords",
    "balanced_text",
    "text_balanced",
]

SCENARIO_TEXT_PREFERENCES = {
    "raw": ["raw_text", "text_raw", "caption", "post_content_for_labeling"],
    "basic": ["basic_clean_text", "text_basic_clean", "caption", "post_content_for_labeling"],
    "full": ["full_clean_text", "text_full_clean", "caption", "post_content_for_labeling"],
    "stopwords": [
        "no_stopwords_text",
        "text_no_stopwords",
        "caption",
        "post_content_for_labeling",
    ],
    "balanced": ["balanced_text", "text_balanced", "caption", "post_content_for_labeling"],
}

TFIDF_PARAM_GRID_FAST = [
    {
        "max_features": 30000,
        "ngram_range": (1, 1),
        "min_df": 2,
        "max_df": 0.95,
        "sublinear_tf": True,
    },
    {
        "max_features": 50000,
        "ngram_range": (1, 1),
        "min_df": 2,
        "max_df": 0.95,
        "sublinear_tf": True,
    },
    {
        "max_features": 30000,
        "ngram_range": (1, 2),
        "min_df": 2,
        "max_df": 0.95,
        "sublinear_tf": True,
    },
    {
        "max_features": 50000,
        "ngram_range": (1, 2),
        "min_df": 2,
        "max_df": 0.95,
        "sublinear_tf": True,
    },
]

TFIDF_PARAM_GRID_FULL_EXTRA = [
    {
        "max_features": 70000,
        "ngram_range": (1, 2),
        "min_df": 1,
        "max_df": 0.95,
        "sublinear_tf": True,
    },
    {
        "max_features": 50000,
        "ngram_range": (1, 3),
        "min_df": 2,
        "max_df": 0.95,
        "sublinear_tf": True,
    },
]

TFIDF_DEEP_PARAMS = [
    {"analyzer": "word", "max_features": 10000, "ngram_range": (1, 1), "min_df": 2, "max_df": 0.95, "sublinear_tf": True},
    {"analyzer": "word", "max_features": 20000, "ngram_range": (1, 1), "min_df": 2, "max_df": 0.95, "sublinear_tf": True},
    {"analyzer": "word", "max_features": 30000, "ngram_range": (1, 1), "min_df": 2, "max_df": 0.95, "sublinear_tf": True},
    {"analyzer": "word", "max_features": 50000, "ngram_range": (1, 1), "min_df": 2, "max_df": 0.95, "sublinear_tf": True},
    {"analyzer": "word", "max_features": 30000, "ngram_range": (1, 2), "min_df": 2, "max_df": 0.95, "sublinear_tf": True},
    {"analyzer": "word", "max_features": 50000, "ngram_range": (1, 2), "min_df": 2, "max_df": 0.95, "sublinear_tf": True},
    {"analyzer": "word", "max_features": 70000, "ngram_range": (1, 2), "min_df": 2, "max_df": 0.95, "sublinear_tf": True},
    {"analyzer": "word", "max_features": 50000, "ngram_range": (1, 3), "min_df": 2, "max_df": 0.95, "sublinear_tf": True},
    {"analyzer": "word", "max_features": 50000, "ngram_range": (1, 2), "min_df": 1, "max_df": 0.95, "sublinear_tf": True},
    {"analyzer": "word", "max_features": 50000, "ngram_range": (1, 2), "min_df": 3, "max_df": 0.95, "sublinear_tf": True},
]

CHAR_TFIDF_DEEP_PARAMS = [
    {"analyzer": "char_wb", "max_features": 30000, "ngram_range": (3, 5), "min_df": 2, "max_df": 0.95, "sublinear_tf": True},
    {"analyzer": "char_wb", "max_features": 50000, "ngram_range": (3, 5), "min_df": 2, "max_df": 0.95, "sublinear_tf": True},
    {"analyzer": "char_wb", "max_features": 50000, "ngram_range": (4, 6), "min_df": 2, "max_df": 0.95, "sublinear_tf": True},
]

LOGREG_PARAM_GRID_FAST = [
    {"C": 0.5, "solver": "saga", "class_weight": "balanced"},
    {"C": 1.0, "solver": "saga", "class_weight": "balanced"},
    {"C": 2.0, "solver": "saga", "class_weight": "balanced"},
    {"C": 5.0, "solver": "saga", "class_weight": "balanced"},
]

LOGREG_PARAM_GRID_FULL_EXTRA = [
    {"C": 0.1, "solver": "saga", "class_weight": "balanced"},
    {"C": 10.0, "solver": "saga", "class_weight": "balanced"},
    {"C": 1.0, "solver": "lbfgs", "class_weight": "balanced"},
    {"C": 2.0, "solver": "lbfgs", "class_weight": "balanced"},
]

LOGREG_DEEP_PARAMS = [
    {"C": 0.05, "solver": "lbfgs"},
    {"C": 0.1, "solver": "lbfgs"},
    {"C": 0.3, "solver": "lbfgs"},
    {"C": 0.5, "solver": "lbfgs"},
    {"C": 1.0, "solver": "lbfgs"},
    {"C": 2.0, "solver": "lbfgs"},
    {"C": 5.0, "solver": "lbfgs"},
    {"C": 10.0, "solver": "lbfgs"},
    {"C": 1.0, "solver": "saga"},
    {"C": 2.0, "solver": "saga"},
]

LINEARSVC_PARAM_GRID_FAST = [
    {"C": 0.1, "class_weight": "balanced"},
    {"C": 0.5, "class_weight": "balanced"},
    {"C": 1.0, "class_weight": "balanced"},
    {"C": 2.0, "class_weight": "balanced"},
    {"C": 5.0, "class_weight": "balanced"},
]

LINEARSVC_PARAM_GRID_FULL_EXTRA = [
    {"C": 10.0, "class_weight": "balanced"},
    {"C": 1.0, "class_weight": None},
    {"C": 2.0, "class_weight": None},
]

LINEARSVC_DEEP_PARAMS = [
    {"C": 0.03, "class_weight": "balanced"},
    {"C": 0.05, "class_weight": "balanced"},
    {"C": 0.1, "class_weight": "balanced"},
    {"C": 0.3, "class_weight": "balanced"},
    {"C": 0.5, "class_weight": "balanced"},
    {"C": 1.0, "class_weight": "balanced"},
    {"C": 2.0, "class_weight": "balanced"},
    {"C": 5.0, "class_weight": "balanced"},
    {"C": 10.0, "class_weight": "balanced"},
    {"C": 1.0, "class_weight": None},
    {"C": 2.0, "class_weight": None},
]

RF_PARAM_GRID_FAST = [
    {"n_estimators": 100, "max_depth": None, "max_features": "sqrt", "min_samples_leaf": 1},
    {"n_estimators": 200, "max_depth": None, "max_features": "sqrt", "min_samples_leaf": 1},
    {"n_estimators": 100, "max_depth": 50, "max_features": "sqrt", "min_samples_leaf": 1},
    {"n_estimators": 100, "max_depth": 100, "max_features": "sqrt", "min_samples_leaf": 2},
]

RF_PARAM_GRID_FULL_EXTRA = [
    {"n_estimators": 300, "max_depth": None, "max_features": "sqrt", "min_samples_leaf": 1},
    {"n_estimators": 300, "max_depth": 100, "max_features": "sqrt", "min_samples_leaf": 2},
    {"n_estimators": 200, "max_depth": None, "max_features": "log2", "min_samples_leaf": 1},
]

RF_DEEP_PARAMS = [
    {"n_estimators": 100, "max_depth": None, "max_features": "sqrt", "min_samples_leaf": 1},
    {"n_estimators": 200, "max_depth": None, "max_features": "sqrt", "min_samples_leaf": 1},
    {"n_estimators": 300, "max_depth": None, "max_features": "sqrt", "min_samples_leaf": 1},
    {"n_estimators": 200, "max_depth": 50, "max_features": "sqrt", "min_samples_leaf": 1},
    {"n_estimators": 200, "max_depth": 100, "max_features": "sqrt", "min_samples_leaf": 1},
    {"n_estimators": 200, "max_depth": None, "max_features": "sqrt", "min_samples_leaf": 2},
    {"n_estimators": 300, "max_depth": 100, "max_features": "log2", "min_samples_leaf": 1},
]

XGB_PARAM_GRID_FAST = [
    {
        "n_estimators": 100,
        "max_depth": 4,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
    },
    {
        "n_estimators": 200,
        "max_depth": 4,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
    },
    {
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
    },
    {
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
    },
]

XGB_PARAM_GRID_FULL_EXTRA = [
    {
        "n_estimators": 300,
        "max_depth": 4,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
    },
    {
        "n_estimators": 300,
        "max_depth": 6,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
    },
    {
        "n_estimators": 200,
        "max_depth": 4,
        "learning_rate": 0.1,
        "subsample": 1.0,
        "colsample_bytree": 1.0,
    },
]

XGB_DEEP_PARAMS = [
    {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.1, "subsample": 0.8, "colsample_bytree": 0.8, "reg_lambda": 1.0, "reg_alpha": 0.0},
    {"n_estimators": 200, "max_depth": 3, "learning_rate": 0.05, "subsample": 0.8, "colsample_bytree": 0.8, "reg_lambda": 1.0, "reg_alpha": 0.0},
    {"n_estimators": 300, "max_depth": 3, "learning_rate": 0.03, "subsample": 0.8, "colsample_bytree": 0.8, "reg_lambda": 1.0, "reg_alpha": 0.0},
    {"n_estimators": 200, "max_depth": 4, "learning_rate": 0.05, "subsample": 0.8, "colsample_bytree": 0.8, "reg_lambda": 1.0, "reg_alpha": 0.0},
    {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.03, "subsample": 0.8, "colsample_bytree": 0.8, "reg_lambda": 2.0, "reg_alpha": 0.0},
    {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.05, "subsample": 0.9, "colsample_bytree": 0.9, "reg_lambda": 2.0, "reg_alpha": 0.1},
    {"n_estimators": 300, "max_depth": 5, "learning_rate": 0.03, "subsample": 0.9, "colsample_bytree": 0.9, "reg_lambda": 2.0, "reg_alpha": 0.1},
]

MODEL_PARAM_GRIDS_FAST = {
    "LogisticRegression": LOGREG_PARAM_GRID_FAST,
    "LinearSVC": LINEARSVC_PARAM_GRID_FAST,
    "RandomForest": RF_PARAM_GRID_FAST,
    "XGBoost": XGB_PARAM_GRID_FAST,
}

MODEL_PARAM_GRIDS_FULL_EXTRA = {
    "LogisticRegression": LOGREG_PARAM_GRID_FULL_EXTRA,
    "LinearSVC": LINEARSVC_PARAM_GRID_FULL_EXTRA,
    "RandomForest": RF_PARAM_GRID_FULL_EXTRA,
    "XGBoost": XGB_PARAM_GRID_FULL_EXTRA,
}

MODEL_PARAM_GRIDS_DEEP = {
    "LogisticRegression": LOGREG_DEEP_PARAMS,
    "LinearSVC": LINEARSVC_DEEP_PARAMS,
    "RandomForest": RF_DEEP_PARAMS,
    "XGBoost": XGB_DEEP_PARAMS,
}

MAX_CANDIDATES = {
    "LogisticRegression": 12,
    "LinearSVC": 12,
    "RandomForest": 6,
    "XGBoost": 6,
}

MAX_CANDIDATES_DEEP = {
    "LogisticRegression": 40,
    "LinearSVC": 45,
    "RandomForest": 18,
    "XGBoost": 18,
}

DEEP_DEFAULT_OUTPUT_DIR = Path("data/08_Modeling_Results/traditional_ml_hpo_deep")
FAST_RESULTS_DIR = Path("data/08_Modeling_Results/traditional_ml")
SIMPLICITY_MACRO_F1_TOLERANCE = 0.003


class DataValidationError(RuntimeError):
    """Raised when input data cannot safely be used for benchmark training."""


@dataclass
class ScenarioData:
    scenario: str
    text_column: str
    split_paths: dict[str, Path]
    splits: dict[str, pd.DataFrame]
    label_name_map: dict[str, str]
    validation_rows: list[dict[str, Any]]
    notes: list[str]
    severe_errors: list[str]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    return value


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(data), ensure_ascii=False, indent=2), encoding="utf-8")


def setup_logging(output_dir: Path) -> logging.Logger:
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("traditional_ml")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_dir / "train_traditional_models.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train traditional ML baselines for DS107 topic classification."
    )
    parser.add_argument("--data_dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output_dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=None,
        help="Scenario folder names to run. Defaults to auto-discovering all valid scenarios.",
    )
    parser.add_argument("--models", nargs="+", default=MODELS)
    parser.add_argument("--tuning_mode", choices=["fast", "full", "deep"], default="fast")
    parser.add_argument(
        "--validate_only",
        action="store_true",
        help="Only validate input data and write run/split validation reports.",
    )
    parser.add_argument(
        "--repair_failed_final",
        action="store_true",
        help=(
            "Repair failed final experiments from an existing deep HPO output directory. "
            "This reuses saved best hyperparameters and does not rerun HPO trials."
        ),
    )
    args = parser.parse_args()
    if args.tuning_mode == "deep" and "--output_dir" not in sys.argv:
        args.output_dir = DEEP_DEFAULT_OUTPUT_DIR
    return args


def normalize_requested_names(values: list[str], allowed: list[str], kind: str) -> list[str]:
    lower_to_name = {name.lower(): name for name in allowed}
    normalized = []
    for value in values:
        key = value.lower()
        if key not in lower_to_name:
            raise ValueError(f"Unknown {kind}: {value}. Allowed values: {allowed}")
        normalized.append(lower_to_name[key])
    return normalized


def split_name_from_path(path: Path) -> str | None:
    stem = path.stem.lower()
    for split in SPLITS:
        if re.search(rf"(^|[_\-.]){split}([_\-.]|$)", stem):
            return split
    return None


def find_split_paths_in_scenario_dir(
    scenario_dir: Path,
) -> tuple[dict[str, Path] | None, list[str]]:
    notes = []
    candidates: dict[str, list[Path]] = {split: [] for split in SPLITS}
    for csv_path in sorted(scenario_dir.rglob("*.csv")):
        split = split_name_from_path(csv_path)
        if split is not None:
            candidates[split].append(csv_path)

    if not all(candidates[split] for split in SPLITS):
        return None, notes

    split_paths = {}
    for split in SPLITS:
        split_candidates = sorted(
            candidates[split],
            key=lambda path: (len(path.relative_to(scenario_dir).parts), str(path)),
        )
        split_paths[split] = split_candidates[0]
        if len(split_candidates) > 1:
            notes.append(
                f"{scenario_dir.name}/{split}: found {len(split_candidates)} files; "
                f"using {split_candidates[0]}"
            )
    return split_paths, notes


def discover_scenario_split_paths(
    data_dir: Path,
    requested_scenarios: list[str] | None,
    logger: logging.Logger,
) -> tuple[list[str], dict[str, dict[str, Path]], dict[str, list[str]]]:
    if not data_dir.exists():
        raise DataValidationError(f"Data directory does not exist: {data_dir}")

    discovered_paths: dict[str, dict[str, Path]] = {}
    discovery_notes: dict[str, list[str]] = {}
    for scenario_dir in sorted(path for path in data_dir.iterdir() if path.is_dir()):
        split_paths, notes = find_split_paths_in_scenario_dir(scenario_dir)
        if split_paths is None:
            continue
        scenario = scenario_dir.name
        discovered_paths[scenario] = split_paths
        discovery_notes[scenario] = notes

    if not discovered_paths:
        raise DataValidationError(
            f"No valid scenarios found under {data_dir}. Expected folders containing train/val/test CSV files."
        )

    if requested_scenarios:
        lower_to_name = {name.lower(): name for name in discovered_paths}
        missing = [
            scenario for scenario in requested_scenarios if scenario.lower() not in lower_to_name
        ]
        if missing:
            raise DataValidationError(
                "Requested scenarios were not discovered: "
                f"{missing}. Discovered scenarios: {sorted(discovered_paths)}"
            )
        scenarios = [lower_to_name[scenario.lower()] for scenario in requested_scenarios]
    else:
        ordered = [scenario for scenario in DEFAULT_SCENARIO_ORDER if scenario in discovered_paths]
        extras = sorted(scenario for scenario in discovered_paths if scenario not in ordered)
        scenarios = ordered + extras

    for scenario in scenarios:
        split_paths = discovered_paths[scenario]
        logger.info("[SCENARIO FOUND] %s", scenario)
        logger.info("  train = %s", split_paths["train"])
        logger.info("  val   = %s", split_paths["val"])
        logger.info("  test  = %s", split_paths["test"])

    return scenarios, discovered_paths, discovery_notes


def get_tfidf_grid(model_name: str, tuning_mode: str) -> list[dict[str, Any]]:
    if tuning_mode == "deep":
        grid = [dict(params) for params in TFIDF_DEEP_PARAMS]
        if model_name in {"LogisticRegression", "LinearSVC"}:
            grid.extend(dict(params) for params in CHAR_TFIDF_DEEP_PARAMS)
        return grid
    grid = [dict(params) for params in TFIDF_PARAM_GRID_FAST]
    if tuning_mode == "full":
        grid.extend(dict(params) for params in TFIDF_PARAM_GRID_FULL_EXTRA)
    return grid


def get_model_grid(model_name: str, tuning_mode: str) -> list[dict[str, Any]]:
    if tuning_mode == "deep":
        return [dict(params) for params in MODEL_PARAM_GRIDS_DEEP[model_name]]
    grid = [dict(params) for params in MODEL_PARAM_GRIDS_FAST[model_name]]
    if tuning_mode == "full":
        grid.extend(dict(params) for params in MODEL_PARAM_GRIDS_FULL_EXTRA[model_name])
    return grid


def build_candidates(
    model_name: str, tuning_mode: str, logger: logging.Logger
) -> list[dict[str, Any]]:
    tfidf_grid = get_tfidf_grid(model_name, tuning_mode)
    model_grid = get_model_grid(model_name, tuning_mode)
    combinations = [
        {"tfidf_params": dict(tfidf_params), "model_params": dict(model_params)}
        for model_params, tfidf_params in itertools.product(model_grid, tfidf_grid)
    ]
    if tuning_mode == "deep":
        max_candidates = MAX_CANDIDATES_DEEP[model_name]
        total_candidates = len(combinations)
        if total_candidates > max_candidates:
            rng = np.random.default_rng(RANDOM_STATE)
            sampled_indices = sorted(
                rng.choice(total_candidates, size=max_candidates, replace=False).tolist()
            )
            combinations = [combinations[index] for index in sampled_indices]
        logger.info(
            "[HPO-DEEP] Model=%s | Total candidate configs=%s | Sampled trials=%s",
            model_name,
            total_candidates,
            len(combinations),
        )
        return combinations
    max_candidates = MAX_CANDIDATES[model_name]
    if len(combinations) > max_candidates:
        logger.info(
            "[TUNING] Model=%s generated %s configs; using first %s deterministic configs",
            model_name,
            len(combinations),
            max_candidates,
        )
        combinations = combinations[:max_candidates]
    else:
        logger.info("[TUNING] Model=%s using %s configs", model_name, len(combinations))
    return combinations


def read_split_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def text_column_candidates_for_scenario(scenario: str) -> list[str]:
    lower = scenario.lower()
    candidates: list[str] = []
    for keyword, columns in SCENARIO_TEXT_PREFERENCES.items():
        if keyword in lower:
            candidates.extend(columns)
    candidates.extend(BASE_TEXT_COLUMNS)
    deduped = []
    for column in candidates:
        if column not in deduped:
            deduped.append(column)
    return deduped


def pick_text_column(
    scenario: str, split_frames: dict[str, pd.DataFrame], logger: logging.Logger
) -> str:
    candidate_columns = text_column_candidates_for_scenario(scenario)
    for column in candidate_columns:
        if all(column in frame.columns for frame in split_frames.values()):
            logger.info("[TEXT COLUMN] Scenario=%s uses text_column=%s", scenario, column)
            return column
    available = {
        split: list(frame.columns)
        for split, frame in split_frames.items()
    }
    raise DataValidationError(
        f"No usable text column found for scenario {scenario}. "
        f"Expected one of {candidate_columns}. Available columns: {available}"
    )


def normalize_label_series(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def is_balanced_label_distribution(labels: pd.Series) -> bool:
    counts = labels.astype(str).value_counts()
    if counts.empty:
        return False
    return int(counts.max() - counts.min()) <= 1


def validate_and_clean_scenario(
    scenario: str,
    split_paths: dict[str, Path],
    path_notes: list[str],
    raw_test_record_ids: set[str] | None,
    logger: logging.Logger,
) -> ScenarioData:
    split_frames = {split: read_split_csv(path) for split, path in split_paths.items()}
    text_column = pick_text_column(scenario, split_frames, logger)

    required_columns = ["record_id", "topic_label_id", "topic_label_final", text_column]
    cleaned_splits: dict[str, pd.DataFrame] = {}
    split_stats: dict[str, dict[str, Any]] = {}
    severe_errors = []
    notes = list(path_notes)

    record_id_sets: dict[str, set[str]] = {}
    overlap_counts = {"train_val": 0, "train_test": 0, "val_test": 0}

    for split, frame in split_frames.items():
        missing_columns = [column for column in required_columns if column not in frame.columns]
        if missing_columns:
            severe_errors.append(f"{scenario}/{split} missing columns: {missing_columns}")
            continue

        df = frame.copy()
        n_rows = len(df)
        record_ids = df["record_id"].astype("string").str.strip()
        labels = normalize_label_series(df["topic_label_id"])
        text_values = df[text_column]
        text_stripped = text_values.fillna("").astype(str).str.strip()

        n_null_record_id = int(record_ids.fillna("").eq("").sum())
        n_duplicate_record_id = int(record_ids.duplicated().sum())
        n_null_text = int(text_values.isna().sum())
        n_empty_text = int(text_stripped.eq("").sum())
        n_null_label = int(labels.fillna("").eq("").sum())
        n_t18 = int(labels.eq(INVALID_REMOVED_LABEL).sum())
        valid_or_empty = set(ALL_LABELS + [INVALID_REMOVED_LABEL, ""])
        n_invalid_label = int((~labels.fillna("").isin(valid_or_empty)).sum())

        label_distribution = labels.value_counts(dropna=False).to_dict()

        if n_null_record_id > 0:
            severe_errors.append(f"{scenario}/{split} has {n_null_record_id} null/empty record_id")
        if n_duplicate_record_id > 0:
            if "balanced" in scenario.lower() and split == "train":
                duplicate_rows = df.loc[record_ids.duplicated(keep=False)].copy()
                duplicate_rows["_record_id_check"] = record_ids[record_ids.duplicated(keep=False)]
                duplicate_rows["_text_check"] = text_stripped[record_ids.duplicated(keep=False)]
                conflicting_duplicates = 0
                for _, group in duplicate_rows.groupby("_record_id_check", dropna=False):
                    if (
                        group["topic_label_id"].astype(str).str.strip().nunique() > 1
                        or group["_text_check"].nunique() > 1
                    ):
                        conflicting_duplicates += 1
                if conflicting_duplicates > 0:
                    severe_errors.append(
                        f"{scenario}/{split} has {conflicting_duplicates} duplicate record_id "
                        "groups with conflicting label/text values"
                    )
                else:
                    notes.append(
                        f"{scenario}/{split}: allowed {n_duplicate_record_id} duplicate "
                        "record_id rows because balanced train appears oversampled without "
                        "label/text conflicts"
                    )
            else:
                severe_errors.append(
                    f"{scenario}/{split} has {n_duplicate_record_id} duplicate record_id values"
                )
        if n_null_label > 0:
            severe_errors.append(f"{scenario}/{split} has {n_null_label} null/empty labels")
        if n_t18 > 0:
            severe_errors.append(f"{scenario}/{split} still contains {n_t18} T18 rows")
        if n_invalid_label > 0:
            severe_errors.append(f"{scenario}/{split} has {n_invalid_label} invalid labels")

        keep_mask = text_stripped.ne("")
        dropped_text_rows = int((~keep_mask).sum())
        if dropped_text_rows > 0:
            note = f"{scenario}/{split}: dropped {dropped_text_rows} rows with null/empty text"
            notes.append(note)
            logger.warning("[DATA CLEAN] %s", note)

        df = df.loc[keep_mask].copy()
        df["record_id"] = df["record_id"].astype(str).str.strip()
        df["topic_label_id"] = df["topic_label_id"].astype(str).str.strip()
        df["topic_label_final"] = df["topic_label_final"].astype(str).str.strip()
        df["_text"] = df[text_column].astype(str).str.strip()

        record_id_sets[split] = set(df["record_id"])
        cleaned_splits[split] = df
        split_stats[split] = {
            "n_rows": n_rows,
            "n_unique_record_id": int(record_ids.nunique(dropna=True)),
            "n_null_text": n_null_text,
            "n_empty_text": n_empty_text,
            "n_null_label": n_null_label,
            "n_t18": n_t18,
            "n_invalid_label": n_invalid_label,
            "dropped_empty_text_rows": dropped_text_rows,
            "label_distribution": label_distribution,
            "is_balanced_distribution": is_balanced_label_distribution(labels),
        }

    if len(cleaned_splits) != len(SPLITS):
        raise DataValidationError("\n".join(severe_errors))

    if all(split in record_id_sets for split in SPLITS):
        overlap_counts = {
            "train_val": len(record_id_sets["train"] & record_id_sets["val"]),
            "train_test": len(record_id_sets["train"] & record_id_sets["test"]),
            "val_test": len(record_id_sets["val"] & record_id_sets["test"]),
        }
        if overlap_counts["train_val"] > 0:
            severe_errors.append(
                f"{scenario} has {overlap_counts['train_val']} record_id overlaps between train and val"
            )
        if overlap_counts["train_test"] > 0:
            severe_errors.append(
                f"{scenario} has {overlap_counts['train_test']} record_id overlaps between train and test"
            )
        if overlap_counts["val_test"] > 0:
            severe_errors.append(
                f"{scenario} has {overlap_counts['val_test']} record_id overlaps between val and test"
            )

    train_label_set = set(cleaned_splits["train"]["topic_label_id"].unique())
    missing_train_labels = sorted(set(ALL_LABELS) - train_label_set)
    if missing_train_labels:
        severe_errors.append(
            f"{scenario}/train is missing labels required for 17-class training: "
            f"{missing_train_labels}"
        )

    label_name_map = {}
    for split_df in cleaned_splits.values():
        for label_id, label_name in zip(
            split_df["topic_label_id"].astype(str), split_df["topic_label_final"].astype(str)
        ):
            if label_id in ALL_LABELS and label_id not in label_name_map and label_name.strip():
                label_name_map[label_id] = label_name.strip()
    for label_id in ALL_LABELS:
        label_name_map.setdefault(label_id, label_id)

    if raw_test_record_ids is None:
        test_record_id_consistency = "reference"
    else:
        current_test_ids = record_id_sets["test"]
        missing_from_current = len(raw_test_record_ids - current_test_ids)
        extra_in_current = len(current_test_ids - raw_test_record_ids)
        if missing_from_current == 0 and extra_in_current == 0:
            test_record_id_consistency = "same"
        else:
            test_record_id_consistency = (
                f"different(missing_from_current={missing_from_current}, "
                f"extra_in_current={extra_in_current})"
            )
            notes.append(
                f"{scenario}: test record_id set differs from raw reference "
                f"(missing={missing_from_current}, extra={extra_in_current})"
            )

    if "balanced" in scenario.lower():
        notes.append("05_Balanced is an auxiliary balanced-data scenario.")
        if split_stats["train"]["is_balanced_distribution"]:
            notes.append("05_Balanced train split appears label-balanced.")
        if split_stats["val"]["is_balanced_distribution"] or split_stats["test"]["is_balanced_distribution"]:
            notes.append(
                "WARNING: 05_Balanced val/test appears balanced; metrics are auxiliary and "
                "not directly comparable with natural-distribution test results."
            )
        else:
            notes.append(
                "05_Balanced val/test do not appear perfectly balanced; if only train is balanced, "
                "this is a reasonable benchmark setting."
            )

    validation_row = {
        "scenario": scenario,
        "train_path": split_paths["train"],
        "val_path": split_paths["val"],
        "test_path": split_paths["test"],
        "n_train": len(cleaned_splits["train"]),
        "n_val": len(cleaned_splits["val"]),
        "n_test": len(cleaned_splits["test"]),
        "n_t18_train": split_stats["train"]["n_t18"],
        "n_t18_val": split_stats["val"]["n_t18"],
        "n_t18_test": split_stats["test"]["n_t18"],
        "n_invalid_label_train": split_stats["train"]["n_invalid_label"],
        "n_invalid_label_val": split_stats["val"]["n_invalid_label"],
        "n_invalid_label_test": split_stats["test"]["n_invalid_label"],
        "train_val_overlap": overlap_counts["train_val"],
        "train_test_overlap": overlap_counts["train_test"],
        "val_test_overlap": overlap_counts["val_test"],
        "test_record_id_consistency_with_raw": test_record_id_consistency,
        "status": "failed" if severe_errors else "ok",
        "notes": "; ".join(
            filter(
                None,
                notes
                + [
                    f"n_null_text_train={split_stats['train']['n_null_text']}",
                    f"n_empty_text_train={split_stats['train']['n_empty_text']}",
                    f"n_null_label_train={split_stats['train']['n_null_label']}",
                    f"n_duplicate_record_id_train={split_stats['train']['n_rows'] - split_stats['train']['n_unique_record_id']}",
                    f"label_distribution_train={json.dumps(to_jsonable(split_stats['train']['label_distribution']), ensure_ascii=False)}",
                    f"label_distribution_val={json.dumps(to_jsonable(split_stats['val']['label_distribution']), ensure_ascii=False)}",
                    f"label_distribution_test={json.dumps(to_jsonable(split_stats['test']['label_distribution']), ensure_ascii=False)}",
                ],
            )
        ),
    }
    if severe_errors:
        validation_row["notes"] = (
            validation_row["notes"] + f"; severe_errors={len(severe_errors)}"
        ).strip("; ")

    return ScenarioData(
        scenario=scenario,
        text_column=text_column,
        split_paths=split_paths,
        splits=cleaned_splits,
        label_name_map=label_name_map,
        validation_rows=[validation_row],
        notes=notes,
        severe_errors=severe_errors,
    )


def fit_label_encoder(train_labels: pd.Series) -> LabelEncoder:
    from sklearn.preprocessing import LabelEncoder

    label_encoder = LabelEncoder()
    label_encoder.fit(train_labels.astype(str).tolist())
    if list(label_encoder.classes_) != ALL_LABELS:
        raise DataValidationError(
            "LabelEncoder classes from train do not match T01-T17: "
            f"{list(label_encoder.classes_)}"
        )
    return label_encoder


def transform_labels(label_encoder: LabelEncoder, labels: pd.Series) -> np.ndarray:
    return label_encoder.transform(labels.astype(str).tolist())


def decode_labels(label_encoder: LabelEncoder, values: Any) -> np.ndarray:
    array = np.asarray(values)
    if array.dtype.kind in {"i", "u"}:
        return label_encoder.inverse_transform(array.astype(int))
    if array.dtype.kind == "f" and np.all(np.isfinite(array)) and np.all(array == array.astype(int)):
        int_array = array.astype(int)
        if int_array.min(initial=0) >= 0 and int_array.max(initial=0) < len(label_encoder.classes_):
            return label_encoder.inverse_transform(int_array)
    return array.astype(str)


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support

    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
    }
    for average in ["macro", "weighted", "micro"]:
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true,
            y_pred,
            labels=ALL_LABELS,
            average=average,
            zero_division=0,
        )
        metrics[f"{average}_precision"] = float(precision)
        metrics[f"{average}_recall"] = float(recall)
        metrics[f"{average}_f1"] = float(f1)
    return metrics


def classification_report_frame(y_true: np.ndarray, y_pred: np.ndarray) -> pd.DataFrame:
    from sklearn.metrics import classification_report

    report = classification_report(
        y_true,
        y_pred,
        labels=ALL_LABELS,
        output_dict=True,
        zero_division=0,
    )
    return pd.DataFrame(report).transpose()


def create_model(model_name: str, model_params: dict[str, Any]) -> Any:
    if model_name == "LogisticRegression":
        from sklearn.linear_model import LogisticRegression

        params = {
            "max_iter": 5000,
            "class_weight": "balanced",
            "random_state": RANDOM_STATE,
            "n_jobs": -1,
        }
        params.update(model_params)
        return LogisticRegression(**params)
    if model_name == "LinearSVC":
        from sklearn.svm import LinearSVC

        params = {
            "random_state": RANDOM_STATE,
            "max_iter": 10000,
        }
        params.update(model_params)
        return LinearSVC(**params)
    if model_name == "RandomForest":
        from sklearn.ensemble import RandomForestClassifier

        params = {
            "class_weight": "balanced",
            "random_state": RANDOM_STATE,
            "n_jobs": -1,
        }
        params.update(model_params)
        return RandomForestClassifier(**params)
    if model_name == "XGBoost":
        try:
            from xgboost import XGBClassifier
        except ImportError as exc:
            raise RuntimeError(
                "xgboost is not installed. Install requirements_modeling.txt first."
            ) from exc
        params = {
            "objective": "multi:softprob",
            "eval_metric": "mlogloss",
            "num_class": 17,
            "tree_method": "hist",
            "random_state": RANDOM_STATE,
            "n_jobs": -1,
            "verbosity": 0,
        }
        params.update(model_params)
        return XGBClassifier(**params)
    raise ValueError(f"Unknown model: {model_name}")


def fit_vectorizer(
    train_text: list[str], tfidf_params: dict[str, Any], logger: logging.Logger
) -> tuple[TfidfVectorizer, Any, dict[str, Any], list[str]]:
    from sklearn.feature_extraction.text import TfidfVectorizer

    used_params = dict(tfidf_params)
    notes = []
    try:
        vectorizer = TfidfVectorizer(**used_params)
        x_train = vectorizer.fit_transform(train_text)
        return vectorizer, x_train, used_params, notes
    except (MemoryError, ValueError) as exc:
        if used_params.get("max_features", 0) and used_params["max_features"] > 30000:
            original = used_params["max_features"]
            used_params["max_features"] = 30000
            notes.append(f"TF-IDF fallback max_features {original} -> 30000 after error: {exc}")
            logger.warning("[VECTORIZER] %s", notes[-1])
            vectorizer = TfidfVectorizer(**used_params)
            x_train = vectorizer.fit_transform(train_text)
            return vectorizer, x_train, used_params, notes
        raise


def fit_model(
    model_name: str,
    model_params: dict[str, Any],
    x_train: Any,
    y_train_encoded: np.ndarray,
    logger: logging.Logger,
    x_val: Any | None = None,
    y_val_encoded: np.ndarray | None = None,
    enable_xgb_early_stopping: bool = False,
) -> tuple[Any, dict[str, Any], list[str], dict[str, Any]]:
    from sklearn.exceptions import ConvergenceWarning

    used_params = dict(model_params)
    notes = []
    fit_info: dict[str, Any] = {
        "fallback_used": False,
        "warning_message": "",
        "early_stopping_used": False,
    }
    fit_kwargs = {}
    if model_name == "XGBoost":
        from sklearn.utils.class_weight import compute_sample_weight

        has_validation = x_val is not None and y_val_encoded is not None
        if "early_stopping_rounds" in used_params and not has_validation:
            removed_rounds = used_params.pop("early_stopping_rounds")
            notes.append(
                "XGBoost early_stopping_rounds removed for fit without validation set "
                f"(removed={removed_rounds}); using selected n_estimators instead"
            )
            fit_info["warning_message"] = notes[-1]

        model = create_model(model_name, used_params)
        fit_kwargs["sample_weight"] = compute_sample_weight(
            class_weight="balanced", y=y_train_encoded
        )
        if has_validation:
            fit_kwargs["eval_set"] = [(x_val, y_val_encoded)]
            fit_kwargs["verbose"] = False
            if "early_stopping_rounds" in used_params:
                fit_info["early_stopping_used"] = True
                notes.append("XGBoost early stopping enabled on validation set only")
            elif enable_xgb_early_stopping:
                try:
                    if "early_stopping_rounds" in model.get_params():
                        model.set_params(early_stopping_rounds=30)
                        used_params["early_stopping_rounds"] = 30
                        fit_info["early_stopping_used"] = True
                        notes.append("XGBoost early stopping enabled on validation set only")
                    else:
                        notes.append("XGBoost early stopping skipped: parameter not supported by installed version")
                except Exception as exc:  # noqa: BLE001
                    notes.append(f"XGBoost early stopping skipped: {exc}")
    else:
        model = create_model(model_name, used_params)

    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        try:
            model.fit(x_train, y_train_encoded, **fit_kwargs)
        except (TypeError, ValueError) as exc:
            if model_name == "XGBoost" and "early" in str(exc).lower():
                fit_info["early_stopping_used"] = False
                fit_info["fallback_used"] = True
                removed_rounds = used_params.pop("early_stopping_rounds", None)
                notes.append(
                    "XGBoost early stopping retry without early stopping after fit error "
                    f"(removed={removed_rounds}): {exc}"
                )
                fit_info["warning_message"] = "; ".join(
                    filter(None, [fit_info.get("warning_message", ""), notes[-1]])
                )
                model = create_model(model_name, used_params)
                model.fit(x_train, y_train_encoded, **fit_kwargs)
            else:
                raise
    convergence_warnings = [
        warning
        for warning in caught_warnings
        if issubclass(warning.category, ConvergenceWarning)
    ]
    if caught_warnings:
        fit_info["warning_message"] = "; ".join(
            filter(
                None,
                [
                    fit_info.get("warning_message", ""),
                    "; ".join(str(warning.message) for warning in caught_warnings[:3]),
                ],
            )
        )

    if (
        model_name == "LogisticRegression"
        and used_params.get("solver") == "saga"
        and convergence_warnings
    ):
        notes.append("LogisticRegression saga raised ConvergenceWarning; fallback to lbfgs")
        logger.warning("[MODEL FALLBACK] %s", notes[-1])
        fit_info["fallback_used"] = True
        fit_info["warning_message"] = "; ".join(
            filter(None, [fit_info.get("warning_message", ""), notes[-1]])
        )
        used_params["solver"] = "lbfgs"
        model = create_model(model_name, used_params)
        with warnings.catch_warnings(record=True) as fallback_warnings:
            warnings.simplefilter("always")
            model.fit(x_train, y_train_encoded)
        if fallback_warnings:
            fit_info["warning_message"] = "; ".join(
                filter(
                    None,
                    [
                        fit_info.get("warning_message", ""),
                        "; ".join(str(warning.message) for warning in fallback_warnings[:3]),
                    ],
                )
            )

    return model, used_params, notes, fit_info


def train_candidate(
    scenario_data: ScenarioData,
    model_name: str,
    trial_id: int,
    tfidf_params: dict[str, Any],
    model_params: dict[str, Any],
    label_encoder: LabelEncoder,
    logger: logging.Logger,
    run_id: str,
    tuning_mode: str,
) -> dict[str, Any]:
    train_df = scenario_data.splits["train"]
    val_df = scenario_data.splits["val"]
    y_train_encoded = transform_labels(label_encoder, train_df["topic_label_id"])
    y_val_encoded = transform_labels(label_encoder, val_df["topic_label_id"])
    y_val_ids = val_df["topic_label_id"].astype(str).to_numpy()
    notes = []
    started = time.perf_counter()
    try:
        vectorizer, x_train, used_tfidf_params, vectorizer_notes = fit_vectorizer(
            train_df["_text"].tolist(), tfidf_params, logger
        )
        notes.extend(vectorizer_notes)
        x_val = vectorizer.transform(val_df["_text"].tolist())
        model, used_model_params, model_notes, fit_info = fit_model(
            model_name,
            model_params,
            x_train,
            y_train_encoded,
            logger,
            x_val=x_val,
            y_val_encoded=y_val_encoded,
            enable_xgb_early_stopping=(tuning_mode == "deep"),
        )
        notes.extend(model_notes)
        train_time = time.perf_counter() - started

        val_started = time.perf_counter()
        y_val_pred_encoded = model.predict(x_val)
        val_predict_time = time.perf_counter() - val_started
        y_val_pred_ids = decode_labels(label_encoder, y_val_pred_encoded)
        metrics_val = calculate_metrics(y_val_ids, y_val_pred_ids)

        return {
            "run_id": run_id,
            "scenario": scenario_data.scenario,
            "model_name": model_name,
            "trial_id": trial_id,
            "text_column": scenario_data.text_column,
            "tfidf_params": used_tfidf_params,
            "model_params": dict(model_params),
            "model_params_effective": used_model_params,
            "metrics_val": metrics_val,
            "train_time_sec": train_time,
            "val_predict_time_sec": val_predict_time,
            "fallback_used": fit_info.get("fallback_used", False),
            "warning_message": fit_info.get("warning_message", ""),
            "status": "success",
            "notes": "; ".join(notes),
        }
    except Exception as exc:  # noqa: BLE001 - keep failed trials in search report.
        logger.exception(
            "[TRIAL FAILED] Scenario=%s | Model=%s | Trial=%s | error=%s",
            scenario_data.scenario,
            model_name,
            trial_id,
            exc,
        )
        return {
            "run_id": run_id,
            "scenario": scenario_data.scenario,
            "model_name": model_name,
            "trial_id": trial_id,
            "text_column": scenario_data.text_column,
            "tfidf_params": dict(tfidf_params),
            "model_params": dict(model_params),
            "model_params_effective": dict(model_params),
            "metrics_val": {},
            "train_time_sec": time.perf_counter() - started,
            "val_predict_time_sec": 0.0,
            "fallback_used": False,
            "warning_message": str(exc),
            "status": "failed",
            "notes": str(exc),
        }


def flatten_trial_row(trial: dict[str, Any]) -> dict[str, Any]:
    metrics = trial.get("metrics_val", {})
    tfidf_params = trial.get("tfidf_params", {})
    model_params = trial.get("model_params", {})
    effective_params = trial.get("model_params_effective", model_params)
    return {
        "run_id": trial.get("run_id"),
        "scenario": trial["scenario"],
        "model_name": trial["model_name"],
        "trial_id": trial["trial_id"],
        "text_column": trial["text_column"],
        "tfidf_params_json": json.dumps(to_jsonable(tfidf_params)),
        "tfidf_analyzer": tfidf_params.get("analyzer", "word"),
        "tfidf_max_features": tfidf_params.get("max_features"),
        "tfidf_ngram_range": str(tuple(tfidf_params.get("ngram_range", ()))),
        "tfidf_min_df": tfidf_params.get("min_df"),
        "tfidf_max_df": tfidf_params.get("max_df"),
        "tfidf_sublinear_tf": tfidf_params.get("sublinear_tf"),
        "model_params_json": json.dumps(to_jsonable(model_params)),
        "model_params_effective_json": json.dumps(to_jsonable(effective_params)),
        "class_weight": effective_params.get("class_weight"),
        "solver": effective_params.get("solver"),
        "C": effective_params.get("C"),
        "n_estimators": effective_params.get("n_estimators"),
        "max_depth": effective_params.get("max_depth"),
        "learning_rate": effective_params.get("learning_rate"),
        "subsample": effective_params.get("subsample"),
        "colsample_bytree": effective_params.get("colsample_bytree"),
        "reg_lambda": effective_params.get("reg_lambda"),
        "reg_alpha": effective_params.get("reg_alpha"),
        "accuracy_val": metrics.get("accuracy"),
        "macro_precision_val": metrics.get("macro_precision"),
        "macro_recall_val": metrics.get("macro_recall"),
        "macro_f1_val": metrics.get("macro_f1"),
        "weighted_precision_val": metrics.get("weighted_precision"),
        "weighted_recall_val": metrics.get("weighted_recall"),
        "weighted_f1_val": metrics.get("weighted_f1"),
        "micro_precision_val": metrics.get("micro_precision"),
        "micro_recall_val": metrics.get("micro_recall"),
        "micro_f1_val": metrics.get("micro_f1"),
        "train_time_sec": trial.get("train_time_sec"),
        "val_predict_time_sec": trial.get("val_predict_time_sec"),
        "fallback_used": trial.get("fallback_used", False),
        "warning_message": trial.get("warning_message", ""),
        "status": trial.get("status"),
        "notes": trial.get("notes"),
    }


def ngram_complexity(ngram_range: Any) -> int:
    if isinstance(ngram_range, (list, tuple)) and len(ngram_range) == 2:
        return int(ngram_range[1])
    return 99


def trial_simplicity_key(trial: dict[str, Any]) -> tuple[Any, ...]:
    tfidf_params = trial.get("tfidf_params", {})
    analyzer_penalty = 0 if tfidf_params.get("analyzer", "word") == "word" else 1
    return (
        tfidf_params.get("max_features") or 10**9,
        ngram_complexity(tfidf_params.get("ngram_range")),
        analyzer_penalty,
        trial.get("train_time_sec") or 10**9,
    )


def choose_best_trial(trials: list[dict[str, Any]]) -> dict[str, Any] | None:
    successful = [trial for trial in trials if trial.get("status") == "success"]
    if not successful:
        return None
    top_macro_f1 = max(trial["metrics_val"]["macro_f1"] for trial in successful)
    close_trials = [
        trial
        for trial in successful
        if trial["metrics_val"]["macro_f1"] >= top_macro_f1 - SIMPLICITY_MACRO_F1_TOLERANCE
    ]
    return sorted(
        close_trials,
        key=lambda trial: (
            trial["metrics_val"]["weighted_f1"],
            trial["metrics_val"]["accuracy"],
            tuple(-value if isinstance(value, (int, float)) else value for value in trial_simplicity_key(trial)),
            trial["metrics_val"]["macro_f1"],
        ),
        reverse=True,
    )[0]


def rank_trials_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    ranked = frame.copy()
    ranked["macro_f1_val"] = pd.to_numeric(ranked["macro_f1_val"], errors="coerce")
    ranked["weighted_f1_val"] = pd.to_numeric(ranked["weighted_f1_val"], errors="coerce")
    ranked["accuracy_val"] = pd.to_numeric(ranked["accuracy_val"], errors="coerce")
    ranked["train_time_sec"] = pd.to_numeric(ranked["train_time_sec"], errors="coerce")
    ranked = ranked.sort_values(
        by=["macro_f1_val", "weighted_f1_val", "accuracy_val", "train_time_sec"],
        ascending=[False, False, False, True],
        na_position="last",
    ).reset_index(drop=True)
    ranked["rank_global"] = np.arange(1, len(ranked) + 1)
    ranked["rank_within_scenario_model"] = (
        ranked.groupby(["scenario", "model_name"]).cumcount() + 1
    )
    ranked["is_best_for_scenario_model"] = ranked["rank_within_scenario_model"].eq(1)
    ranked["is_best_overall"] = ranked["rank_global"].eq(1)
    return ranked


def choose_best_experiment(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    successful = [result for result in results if result.get("status") == "success"]
    if not successful:
        return None
    top_macro_f1 = max(result["metrics_val"]["macro_f1"] for result in successful)
    close_results = [
        result
        for result in successful
        if result["metrics_val"]["macro_f1"] >= top_macro_f1 - SIMPLICITY_MACRO_F1_TOLERANCE
    ]
    return sorted(
        close_results,
        key=lambda trial: (
            trial["metrics_val"]["weighted_f1"],
            trial["metrics_val"].get("accuracy", 0),
            tuple(-value if isinstance(value, (int, float)) else value for value in trial_simplicity_key(trial)),
            trial["metrics_val"]["macro_f1"],
        ),
        reverse=True,
    )[0]


def prediction_probabilities(
    model: Any, x_matrix: Any, label_encoder: LabelEncoder
) -> list[dict[str, Any]]:
    if not hasattr(model, "predict_proba"):
        return [{} for _ in range(x_matrix.shape[0])]
    probabilities = model.predict_proba(x_matrix)
    model_classes = getattr(model, "classes_", np.arange(probabilities.shape[1]))
    if len(model_classes) != probabilities.shape[1]:
        model_classes = np.arange(probabilities.shape[1])

    rows = []
    for row in probabilities:
        top_indices = np.argsort(row)[::-1][:3]
        result: dict[str, Any] = {}
        for rank, column_index in enumerate(top_indices, start=1):
            encoded_label = np.asarray(model_classes)[column_index]
            label_id = decode_labels(label_encoder, np.asarray([encoded_label]))[0]
            score = float(row[column_index])
            result[f"top_{rank}_label"] = label_id
            result[f"top_{rank}_score"] = score
        result["confidence"] = result.get("top_1_score")
        rows.append(result)
    return rows


def build_predictions_frame(
    df: pd.DataFrame,
    y_pred_ids: np.ndarray,
    probability_rows: list[dict[str, Any]],
    scenario: str,
    model_name: str,
    label_name_map: dict[str, str],
) -> pd.DataFrame:
    y_true = df["topic_label_id"].astype(str).to_numpy()
    records = []
    for index, (_, row) in enumerate(df.iterrows()):
        y_true_id = str(y_true[index])
        y_pred_id = str(y_pred_ids[index])
        record = {
            "record_id": row["record_id"],
            "text": row["_text"],
            "y_true": y_true_id,
            "y_pred": y_pred_id,
            "y_true_label_name": label_name_map.get(y_true_id, y_true_id),
            "y_pred_label_name": label_name_map.get(y_pred_id, y_pred_id),
            "correct": y_true_id == y_pred_id,
            "scenario": scenario,
            "model_name": model_name,
        }
        probability_record = probability_rows[index] if index < len(probability_rows) else {}
        for column in [
            "confidence",
            "top_1_label",
            "top_1_score",
            "top_2_label",
            "top_2_score",
            "top_3_label",
            "top_3_score",
        ]:
            record[column] = probability_record.get(column)
        records.append(record)
    return pd.DataFrame(records)


def save_confusion_matrices(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    output_dir: Path,
    scenario: str,
    model_name: str,
) -> tuple[Path, Path, Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.metrics import confusion_matrix

    matrix = confusion_matrix(y_true, y_pred, labels=ALL_LABELS)
    matrix_df = pd.DataFrame(matrix, index=ALL_LABELS, columns=ALL_LABELS)
    csv_path = output_dir / "confusion_matrix_test.csv"
    matrix_df.to_csv(csv_path)

    png_path = output_dir / "confusion_matrix_test.png"
    normalized_png_path = output_dir / "confusion_matrix_test_normalized.png"

    plt.figure(figsize=(14, 12))
    sns.heatmap(matrix_df, annot=True, fmt="d", cmap="Blues", cbar=True)
    plt.title(f"Confusion Matrix - {scenario} - {model_name}")
    plt.xlabel("Predicted label")
    plt.ylabel("True label")
    plt.tight_layout()
    plt.savefig(png_path, dpi=300)
    plt.close()

    row_sums = matrix_df.sum(axis=1).replace(0, np.nan)
    normalized_df = matrix_df.div(row_sums, axis=0).fillna(0.0)
    plt.figure(figsize=(14, 12))
    sns.heatmap(normalized_df, annot=True, fmt=".2f", cmap="Blues", cbar=True, vmin=0, vmax=1)
    plt.title(f"Normalized Confusion Matrix - {scenario} - {model_name}")
    plt.xlabel("Predicted label")
    plt.ylabel("True label")
    plt.tight_layout()
    plt.savefig(normalized_png_path, dpi=300)
    plt.close()

    return csv_path, png_path, normalized_png_path


def train_final_experiment(
    scenario_data: ScenarioData,
    model_name: str,
    best_trial: dict[str, Any],
    label_encoder: LabelEncoder,
    experiment_dir: Path,
    logger: logging.Logger,
) -> dict[str, Any]:
    import joblib
    from sklearn.metrics import confusion_matrix

    experiment_dir.mkdir(parents=True, exist_ok=True)
    train_df = scenario_data.splits["train"]
    val_df = scenario_data.splits["val"]
    test_df = scenario_data.splits["test"]

    y_train_encoded = transform_labels(label_encoder, train_df["topic_label_id"])
    y_val_encoded = transform_labels(label_encoder, val_df["topic_label_id"])
    y_val_ids = val_df["topic_label_id"].astype(str).to_numpy()
    y_test_ids = test_df["topic_label_id"].astype(str).to_numpy()

    notes = []
    started = time.perf_counter()
    vectorizer, x_train, used_tfidf_params, vectorizer_notes = fit_vectorizer(
        train_df["_text"].tolist(), best_trial["tfidf_params"], logger
    )
    notes.extend(vectorizer_notes)
    x_val = vectorizer.transform(val_df["_text"].tolist())
    x_test = vectorizer.transform(test_df["_text"].tolist())

    best_model_params = best_trial.get("model_params_effective", best_trial["model_params"])
    fit_x_val = x_val if model_name == "XGBoost" else None
    fit_y_val = y_val_encoded if model_name == "XGBoost" else None
    model, used_model_params, model_notes, fit_info = fit_model(
        model_name,
        best_model_params,
        x_train,
        y_train_encoded,
        logger,
        x_val=fit_x_val,
        y_val_encoded=fit_y_val,
    )
    notes.extend(model_notes)
    train_time = time.perf_counter() - started

    val_started = time.perf_counter()
    y_val_pred_encoded = model.predict(x_val)
    val_predict_time = time.perf_counter() - val_started
    y_val_pred_ids = decode_labels(label_encoder, y_val_pred_encoded)

    test_started = time.perf_counter()
    y_test_pred_encoded = model.predict(x_test)
    test_predict_time = time.perf_counter() - test_started
    y_test_pred_ids = decode_labels(label_encoder, y_test_pred_encoded)

    metrics_val = calculate_metrics(y_val_ids, y_val_pred_ids)
    metrics_test = calculate_metrics(y_test_ids, y_test_pred_ids)

    model_path = experiment_dir / "model.joblib"
    vectorizer_path = experiment_dir / "vectorizer.joblib"
    label_encoder_path = experiment_dir / "label_encoder.joblib"
    joblib.dump(model, model_path)
    joblib.dump(vectorizer, vectorizer_path)
    joblib.dump(label_encoder, label_encoder_path)

    write_json(experiment_dir / "metrics_val.json", metrics_val)
    write_json(experiment_dir / "metrics_test.json", metrics_test)

    classification_report_frame(y_val_ids, y_val_pred_ids).to_csv(
        experiment_dir / "classification_report_val.csv"
    )
    classification_report_frame(y_test_ids, y_test_pred_ids).to_csv(
        experiment_dir / "classification_report_test.csv"
    )

    confusion_matrix(y_val_ids, y_val_pred_ids, labels=ALL_LABELS)
    pd.DataFrame(
        confusion_matrix(y_val_ids, y_val_pred_ids, labels=ALL_LABELS),
        index=ALL_LABELS,
        columns=ALL_LABELS,
    ).to_csv(experiment_dir / "confusion_matrix_val.csv")
    save_confusion_matrices(y_test_ids, y_test_pred_ids, experiment_dir, scenario_data.scenario, model_name)

    val_probability_rows = prediction_probabilities(model, x_val, label_encoder)
    test_probability_rows = prediction_probabilities(model, x_test, label_encoder)
    predictions_val = build_predictions_frame(
        val_df,
        y_val_pred_ids,
        val_probability_rows,
        scenario_data.scenario,
        model_name,
        scenario_data.label_name_map,
    )
    predictions_test = build_predictions_frame(
        test_df,
        y_test_pred_ids,
        test_probability_rows,
        scenario_data.scenario,
        model_name,
        scenario_data.label_name_map,
    )
    predictions_val.to_csv(experiment_dir / "predictions_val.csv", index=False)
    predictions_test.to_csv(experiment_dir / "predictions_test.csv", index=False)

    wrong_required_columns = [
        "record_id",
        "text",
        "y_true",
        "y_pred",
        "y_true_label_name",
        "y_pred_label_name",
        "scenario",
        "model_name",
    ]
    optional_confidence_columns = [
        "confidence",
        "top_1_label",
        "top_1_score",
        "top_2_label",
        "top_2_score",
        "top_3_label",
        "top_3_score",
    ]
    wrong_columns = wrong_required_columns + [
        column for column in optional_confidence_columns if column in predictions_test.columns
    ]
    predictions_val.loc[~predictions_val["correct"], wrong_columns].to_csv(
        experiment_dir / "wrong_predictions_val.csv", index=False
    )
    predictions_test.loc[~predictions_test["correct"], wrong_columns].to_csv(
        experiment_dir / "wrong_predictions_test.csv", index=False
    )

    experiment_config = {
        "scenario": scenario_data.scenario,
        "model_name": model_name,
        "text_column": scenario_data.text_column,
        "selected_trial_id": best_trial["trial_id"],
        "selection_metric": "validation_macro_f1",
        "tie_breakers": [
            "validation_weighted_f1",
            "validation_accuracy",
            f"model_simplicity_if_macro_f1_within_{SIMPLICITY_MACRO_F1_TOLERANCE}",
        ],
        "tfidf_params": used_tfidf_params,
        "model_params": best_trial["model_params"],
        "model_params_effective": used_model_params,
        "fallback_used": fit_info.get("fallback_used", False),
        "warning_message": fit_info.get("warning_message", ""),
        "train_rows": len(train_df),
        "val_rows": len(val_df),
        "test_rows": len(test_df),
        "split_paths": scenario_data.split_paths,
        "notes": "; ".join(filter(None, notes + scenario_data.notes)),
        "created_at": now_iso(),
    }
    write_json(experiment_dir / "experiment_config.json", experiment_config)

    return {
        "scenario": scenario_data.scenario,
        "model_name": model_name,
        "text_column": scenario_data.text_column,
        "n_train": len(train_df),
        "n_val": len(val_df),
        "n_test": len(test_df),
        "vectorizer_max_features": used_tfidf_params.get("max_features"),
        "vectorizer_ngram_range": str(tuple(used_tfidf_params.get("ngram_range", ()))),
        "metrics_val": metrics_val,
        "metrics_test": metrics_test,
        "train_time_sec": train_time,
        "val_predict_time_sec": val_predict_time,
        "test_predict_time_sec": test_predict_time,
        "model_path": str(model_path),
        "vectorizer_path": str(vectorizer_path),
        "label_encoder_path": str(label_encoder_path),
        "experiment_dir": str(experiment_dir),
        "tfidf_params": used_tfidf_params,
        "model_params": best_trial["model_params"],
        "model_params_effective": used_model_params,
        "selected_trial_id": best_trial["trial_id"],
        "fallback_used": fit_info.get("fallback_used", False),
        "warning_message": fit_info.get("warning_message", ""),
        "status": "success",
        "notes": "; ".join(filter(None, notes + scenario_data.notes)),
    }


def flatten_summary_row(result: dict[str, Any]) -> dict[str, Any]:
    val = result.get("metrics_val", {})
    test = result.get("metrics_test", {})
    return {
        "scenario": result.get("scenario"),
        "model_name": result.get("model_name"),
        "text_column": result.get("text_column"),
        "n_train": result.get("n_train"),
        "n_val": result.get("n_val"),
        "n_test": result.get("n_test"),
        "vectorizer_max_features": result.get("vectorizer_max_features"),
        "vectorizer_ngram_range": result.get("vectorizer_ngram_range"),
        "accuracy_val": val.get("accuracy"),
        "macro_precision_val": val.get("macro_precision"),
        "macro_recall_val": val.get("macro_recall"),
        "macro_f1_val": val.get("macro_f1"),
        "weighted_precision_val": val.get("weighted_precision"),
        "weighted_recall_val": val.get("weighted_recall"),
        "weighted_f1_val": val.get("weighted_f1"),
        "micro_precision_val": val.get("micro_precision"),
        "micro_recall_val": val.get("micro_recall"),
        "micro_f1_val": val.get("micro_f1"),
        "accuracy_test": test.get("accuracy"),
        "macro_precision_test": test.get("macro_precision"),
        "macro_recall_test": test.get("macro_recall"),
        "macro_f1_test": test.get("macro_f1"),
        "weighted_precision_test": test.get("weighted_precision"),
        "weighted_recall_test": test.get("weighted_recall"),
        "weighted_f1_test": test.get("weighted_f1"),
        "micro_precision_test": test.get("micro_precision"),
        "micro_recall_test": test.get("micro_recall"),
        "micro_f1_test": test.get("micro_f1"),
        "train_time_sec": result.get("train_time_sec"),
        "val_predict_time_sec": result.get("val_predict_time_sec"),
        "test_predict_time_sec": result.get("test_predict_time_sec"),
        "model_path": result.get("model_path"),
        "vectorizer_path": result.get("vectorizer_path"),
        "notes": result.get("notes"),
        "status": result.get("status"),
    }


def sort_summary_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    return frame.sort_values(
        by=["macro_f1_val", "weighted_f1_val"],
        ascending=[False, False],
        na_position="last",
    )


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int | None = None) -> str:
    if frame.empty:
        return "_Không có dữ liệu._"
    table = frame.loc[:, [column for column in columns if column in frame.columns]].copy()
    if max_rows is not None:
        table = table.head(max_rows)
    for column in table.columns:
        if pd.api.types.is_float_dtype(table[column]):
            table[column] = table[column].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    header = "| " + " | ".join(table.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(table.columns)) + " |"
    rows = [
        "| " + " | ".join(str(value) for value in row) + " |"
        for row in table.fillna("").to_numpy()
    ]
    return "\n".join([header, separator] + rows)


def write_summary_markdown(summary_frame: pd.DataFrame, output_dir: Path) -> None:
    columns = [
        "scenario",
        "model_name",
        "text_column",
        "accuracy_val",
        "macro_f1_val",
        "weighted_f1_val",
        "accuracy_test",
        "macro_f1_test",
        "weighted_f1_test",
        "train_time_sec",
        "status",
    ]
    content = [
        "# Traditional ML Results Summary",
        "",
        markdown_table(summary_frame, columns),
        "",
        "Sorted by validation Macro-F1, then validation Weighted-F1.",
        "",
    ]
    (output_dir / "all_model_results_summary.md").write_text(
        "\n".join(content), encoding="utf-8"
    )


def copy_best_model(best_result: dict[str, Any], output_dir: Path) -> None:
    import joblib

    best_dir = output_dir / "best_model"
    best_dir.mkdir(parents=True, exist_ok=True)
    source_dir = Path(best_result["experiment_dir"])
    for filename in ["model.joblib", "vectorizer.joblib", "label_encoder.joblib"]:
        shutil.copy2(source_dir / filename, best_dir / filename)

    label_encoder = joblib.load(best_dir / "label_encoder.joblib")
    model = joblib.load(best_dir / "model.joblib")
    vectorizer = joblib.load(best_dir / "vectorizer.joblib")

    metadata = {
        "scenario": best_result["scenario"],
        "model_name": best_result["model_name"],
        "text_column": best_result["text_column"],
        "label_classes": list(label_encoder.classes_),
        "vectorizer_config": best_result["tfidf_params"],
        "model_params": best_result["model_params"],
        "model_params_effective": best_result.get("model_params_effective", best_result["model_params"]),
        "preprocessing_scenario": best_result["scenario"],
        "validation_macro_f1": best_result["metrics_val"]["macro_f1"],
        "test_macro_f1": best_result["metrics_test"]["macro_f1"],
        "test_accuracy": best_result["metrics_test"]["accuracy"],
        "created_at": now_iso(),
    }
    write_json(best_dir / "metadata.json", metadata)

    predictions_path = source_dir / "predictions_test.csv"
    example_text = "Một caption ví dụ"
    predicted_topic_id = "Txx"
    predicted_topic_label = "Txx. ..."
    if predictions_path.exists():
        predictions = pd.read_csv(predictions_path)
        if not predictions.empty:
            example_text = str(predictions.iloc[0]["text"])
            predicted_topic_label = str(predictions.iloc[0].get("y_pred_label_name", predicted_topic_label))
    try:
        x_example = vectorizer.transform([example_text])
        pred = model.predict(x_example)
        predicted_topic_id = decode_labels(label_encoder, pred)[0]
        predicted_topic_label = predicted_topic_id
    except Exception:
        pass
    predict_example = {
        "input_text": example_text,
        "predicted_topic_id": predicted_topic_id,
        "predicted_topic_label": predicted_topic_label,
        "note": "Use vectorizer.transform([text]) before model.predict.",
    }
    write_json(best_dir / "predict_example.json", predict_example)


def refit_best_model_train_val(
    best_result: dict[str, Any],
    scenario_data: ScenarioData,
    output_dir: Path,
    logger: logging.Logger,
) -> None:
    import joblib

    refit_dir = output_dir / "best_model_refit_train_val"
    refit_dir.mkdir(parents=True, exist_ok=True)

    train_val_df = pd.concat(
        [scenario_data.splits["train"], scenario_data.splits["val"]],
        axis=0,
        ignore_index=True,
    )
    label_encoder = fit_label_encoder(train_val_df["topic_label_id"])
    y_train_val = transform_labels(label_encoder, train_val_df["topic_label_id"])

    vectorizer, x_train_val, used_tfidf_params, vectorizer_notes = fit_vectorizer(
        train_val_df["_text"].tolist(), best_result["tfidf_params"], logger
    )
    model, used_model_params, model_notes, fit_info = fit_model(
        best_result["model_name"],
        best_result.get("model_params_effective", best_result["model_params"]),
        x_train_val,
        y_train_val,
        logger,
    )

    joblib.dump(model, refit_dir / "model.joblib")
    joblib.dump(vectorizer, refit_dir / "vectorizer.joblib")
    joblib.dump(label_encoder, refit_dir / "label_encoder.joblib")

    metadata = {
        "scenario": best_result["scenario"],
        "model_name": best_result["model_name"],
        "text_column": best_result["text_column"],
        "label_classes": list(label_encoder.classes_),
        "vectorizer_config": used_tfidf_params,
        "model_params": best_result["model_params"],
        "model_params_effective": used_model_params,
        "fallback_used": fit_info.get("fallback_used", False),
        "warning_message": fit_info.get("warning_message", ""),
        "preprocessing_scenario": best_result["scenario"],
        "train_rows": len(scenario_data.splits["train"]),
        "val_rows": len(scenario_data.splits["val"]),
        "train_val_rows": len(train_val_df),
        "source_benchmark_validation_macro_f1": best_result["metrics_val"]["macro_f1"],
        "source_benchmark_test_macro_f1": best_result["metrics_test"]["macro_f1"],
        "source_benchmark_test_accuracy": best_result["metrics_test"]["accuracy"],
        "created_at": now_iso(),
        "notes": "; ".join(filter(None, vectorizer_notes + model_notes)),
    }
    write_json(refit_dir / "metadata.json", metadata)

    example_text = str(train_val_df.iloc[0]["_text"]) if not train_val_df.empty else "Một caption ví dụ"
    pred = model.predict(vectorizer.transform([example_text]))
    predicted_topic_id = decode_labels(label_encoder, pred)[0]
    predict_example = {
        "input_text": example_text,
        "predicted_topic_id": predicted_topic_id,
        "predicted_topic_label": scenario_data.label_name_map.get(predicted_topic_id, predicted_topic_id),
        "note": "Deployment model was refit on train + validation. Use vectorizer.transform([text]) before model.predict.",
    }
    write_json(refit_dir / "predict_example.json", predict_example)


def write_best_summary(best_result: dict[str, Any], output_dir: Path) -> None:
    best_summary = {
        "best_scenario": best_result["scenario"],
        "best_model_name": best_result["model_name"],
        "selection_metric": "validation_macro_f1",
        "validation_metrics": best_result["metrics_val"],
        "test_metrics": best_result["metrics_test"],
        "model_path": best_result["model_path"],
        "vectorizer_path": best_result["vectorizer_path"],
        "label_encoder_path": best_result["label_encoder_path"],
        "text_column": best_result["text_column"],
        "best_tfidf_params": best_result.get("tfidf_params", {}),
        "best_model_params": best_result.get("model_params", {}),
        "best_effective_model_params": best_result.get(
            "model_params_effective", best_result.get("model_params", {})
        ),
        "created_at": now_iso(),
        "notes": best_result.get("notes", ""),
    }
    write_json(output_dir / "best_model_summary.json", best_summary)


def top_confusions(confusion_csv: Path, top_n: int = 10) -> pd.DataFrame:
    matrix = pd.read_csv(confusion_csv, index_col=0)
    rows = []
    for true_label in matrix.index:
        for pred_label in matrix.columns:
            if true_label == pred_label:
                continue
            count = int(matrix.loc[true_label, pred_label])
            if count > 0:
                rows.append({"true_label": true_label, "pred_label": pred_label, "count": count})
    if not rows:
        return pd.DataFrame(columns=["true_label", "pred_label", "count"])
    return pd.DataFrame(rows).sort_values("count", ascending=False).head(top_n)


def write_technical_report(
    output_dir: Path,
    scenario_data_map: dict[str, ScenarioData],
    split_validation_frame: pd.DataFrame,
    summary_frame: pd.DataFrame,
    best_hyperparams_frame: pd.DataFrame,
    best_result: dict[str, Any] | None,
    tuning_mode: str,
) -> None:
    lines: list[str] = []
    lines.extend(
        [
            "# Traditional ML Technical Report",
            "",
            "## 1. Mục tiêu",
            "",
            "Benchmark này huấn luyện các mô hình Machine Learning truyền thống cho bài toán phân loại chủ đề bài đăng Facebook liên quan đến tin tức/sự kiện. Task chính là phân loại đơn nhãn 17 lớp từ T01 đến T17; nhãn T18 đã bị loại trước khi train.",
            "",
            "## 2. Input data",
            "",
            "Dữ liệu được đọc từ `data/07_Cleaned_Data` bằng cơ chế tự phát hiện scenario. Script quét từng top-level folder và tìm đủ ba file CSV có tên chứa train, val, test, bao gồm layout nested như `Scenario/Scenario/kb*_train.csv`.",
            "",
            "Các scenario benchmark hiện hỗ trợ gồm `01_Raw_Data`, `02_Basic_Clean`, `03_Full_Clean`, `04_No_Stopwords`, và `05_Balanced`. Mỗi kịch bản dùng ba split train/val/test có sẵn và không tự đổi split.",
            "",
            "## Scenario Discovery and Data Layout",
            "",
            markdown_table(
                pd.DataFrame(
                    [
                        {
                            "scenario": scenario_data.scenario,
                            "train_path": scenario_data.split_paths["train"],
                            "val_path": scenario_data.split_paths["val"],
                            "test_path": scenario_data.split_paths["test"],
                            "text_column": scenario_data.text_column,
                        }
                        for scenario_data in scenario_data_map.values()
                    ]
                ),
                ["scenario", "train_path", "val_path", "test_path", "text_column"],
            ),
            "",
            "## 05_Balanced Scenario",
            "",
            "`05_Balanced` là kịch bản dữ liệu cân bằng bổ sung. Nếu chỉ train set được balance thì đây là setting hợp lý để giảm bias do class imbalance. Nếu val/test cũng bị balance, kết quả của scenario này nên xem là auxiliary và không so sánh trực tiếp với test phân phối tự nhiên.",
            "",
        ]
    )
    layout_notes = []
    for scenario_data in scenario_data_map.values():
        layout_notes.extend(scenario_data.notes)
    if layout_notes:
        lines.extend(
            [
                "Assumption/layout note:",
                "",
                *[f"- {note}" for note in layout_notes],
                "",
            ]
        )

    lines.extend(
        [
            "## 3. Data validation",
            "",
            markdown_table(
                split_validation_frame,
                [
                    "scenario",
                    "train_path",
                    "val_path",
                    "test_path",
                    "n_train",
                    "n_val",
                    "n_test",
                    "n_t18_train",
                    "n_t18_val",
                    "n_t18_test",
                    "n_invalid_label_train",
                    "n_invalid_label_val",
                    "n_invalid_label_test",
                    "train_val_overlap",
                    "train_test_overlap",
                    "val_test_overlap",
                    "test_record_id_consistency_with_raw",
                    "status",
                ],
            ),
            "",
            "Validation kiểm tra file tồn tại, record_id, text column, topic_label_id, topic_label_final, null/rỗng, T18, nhãn ngoài T01-T17, duplicate record_id trong từng split, overlap record_id giữa train/val/test, và consistency của test record_id so với raw scenario nếu có thể.",
            "",
            "## 4. Experimental setup",
            "",
            f"- Random seed: {RANDOM_STATE}.",
            "- Feature extraction: TF-IDF word-level, fit chỉ trên train set rồi transform val/test.",
            "- Models: Logistic Regression, Random Forest, XGBoost, LinearSVC.",
            "- Metrics: accuracy, macro/weighted/micro precision, recall, F1; per-class report dùng `zero_division=0`.",
            "- Selection criterion: validation Macro-F1, tie-breaker validation Weighted-F1, sau đó validation Accuracy cho hyperparameter tuning.",
            "",
            "## Hyperparameter Optimization",
            "",
            "Tuning chỉ dùng train/validation. Test set không được dùng để chọn model hoặc hyperparameters; test chỉ được evaluate sau khi đã chọn best config theo validation Macro-F1.",
            "",
            f"- Tuning mode: `{tuning_mode}`.",
            "- TF-IDF fast grid: max_features 30000/50000, ngram_range (1,1)/(1,2), min_df=2, max_df=0.95, sublinear_tf=True.",
            "- TF-IDF full extra: max_features=70000 với min_df=1, và ngram_range=(1,3).",
            "- Deep mode dùng hold-out validation based HPO, validation curve analysis, controlled random sampling với random_state=42 khi số tổ hợp vượt cap.",
            "- Deep mode thử TF-IDF word n-gram và thêm char_wb n-gram cho LogisticRegression/LinearSVC để xử lý teencode, viết tắt, viết dính và từ né bộ lọc.",
            "- Logistic Regression grid: C, solver, class_weight; base max_iter=5000, random_state=42, n_jobs=-1, ưu tiên lbfgs trong deep mode.",
            "- LinearSVC grid: C và class_weight; base max_iter=10000, random_state=42.",
            "- Random Forest grid: n_estimators, max_depth, max_features, min_samples_leaf; class_weight balanced.",
            "- XGBoost grid: n_estimators, max_depth, learning_rate, subsample, colsample_bytree; sample_weight balanced.",
            "- Candidate cap fast/full: Logistic Regression 12, LinearSVC 12, Random Forest 6, XGBoost 6 configs cho mỗi scenario/model.",
            "- Candidate cap deep: Logistic Regression 40, LinearSVC 45, Random Forest 18, XGBoost 18 configs cho mỗi scenario/model.",
            f"- Nếu Macro-F1 validation nằm trong khoảng {SIMPLICITY_MACRO_F1_TOLERANCE}, tie-breaker cuối ưu tiên cấu hình đơn giản hơn.",
            "",
            "Best hyperparameters by scenario/model:",
            "",
            markdown_table(best_hyperparams_frame, list(best_hyperparams_frame.columns)),
            "",
            "## 5. Main results",
            "",
            markdown_table(
                summary_frame,
                [
                    "scenario",
                    "model_name",
                    "accuracy_test",
                    "macro_precision_test",
                    "macro_recall_test",
                    "macro_f1_test",
                    "weighted_f1_test",
                    "macro_f1_val",
                    "weighted_f1_val",
                ],
            ),
            "",
        ]
    )

    if best_result is None:
        lines.extend(["## 6. Best model", "", "Không có experiment thành công.", ""])
    else:
        lines.extend(
            [
                "## 6. Best model",
                "",
                f"- Best scenario: {best_result['scenario']}.",
                f"- Best model: {best_result['model_name']}.",
                f"- Validation Macro-F1: {best_result['metrics_val']['macro_f1']:.4f}.",
                f"- Validation Weighted-F1: {best_result['metrics_val']['weighted_f1']:.4f}.",
                f"- Test Macro-F1: {best_result['metrics_test']['macro_f1']:.4f}.",
                f"- Test Accuracy: {best_result['metrics_test']['accuracy']:.4f}.",
                f"- Benchmark model path: `{best_result['model_path']}`.",
                f"- Vectorizer path: `{best_result['vectorizer_path']}`.",
                "",
                "`best_model/` là benchmark model train trên train và chọn theo validation. `best_model_refit_train_val/` là deployment model refit trên train + validation để dùng cho Streamlit demo; test metrics vẫn lấy từ benchmark model.",
                "",
                "## 7. Error analysis summary",
                "",
            ]
        )
        experiment_dir = Path(best_result["experiment_dir"])
        confusion_path = experiment_dir / "confusion_matrix_test.csv"
        report_path = experiment_dir / "classification_report_test.csv"
        wrong_path = experiment_dir / "wrong_predictions_test.csv"
        predictions_path = experiment_dir / "predictions_test.csv"

        if confusion_path.exists():
            confusion_frame = top_confusions(confusion_path, top_n=10)
            lines.extend(["Top confused label pairs:", "", markdown_table(confusion_frame, list(confusion_frame.columns)), ""])
        if report_path.exists():
            class_report = pd.read_csv(report_path, index_col=0)
            low_f1 = (
                class_report.loc[class_report.index.intersection(ALL_LABELS)]
                .sort_values("f1-score")
                .head(5)
                .reset_index()
                .rename(columns={"index": "label"})
            )
            lines.extend(["Các nhãn có F1 thấp nhất:", "", markdown_table(low_f1, ["label", "precision", "recall", "f1-score", "support"]), ""])
        if wrong_path.exists():
            wrong_predictions = pd.read_csv(wrong_path)
            lines.extend([f"Số wrong predictions trên test: {len(wrong_predictions)}.", ""])
        if predictions_path.exists():
            predictions = pd.read_csv(predictions_path)
            wrong_examples = predictions.loc[~predictions["correct"]].head(5)
            example_columns = ["record_id", "y_true", "y_pred", "text"]
            lines.extend(["5 ví dụ sai tiêu biểu:", "", markdown_table(wrong_examples, example_columns), ""])

    lines.extend(
        [
            "## 8. Notes for Streamlit",
            "",
            "Load benchmark hoặc deployment model bằng `joblib`:",
            "",
            "```python",
            "import joblib",
            "",
            "model = joblib.load(\"model.joblib\")",
            "vectorizer = joblib.load(\"vectorizer.joblib\")",
            "label_encoder = joblib.load(\"label_encoder.joblib\")",
            "",
            "X = vectorizer.transform([input_text])",
            "pred = model.predict(X)",
            "topic_id = label_encoder.inverse_transform(pred)[0]",
            "```",
            "",
        ]
    )
    if best_result and best_result["model_name"] in {"LogisticRegression", "RandomForest", "XGBoost"}:
        lines.extend(
            [
                "Best model có `predict_proba`, có thể lấy confidence/top-3 bằng cách sort xác suất giảm dần theo `model.classes_` rồi inverse_transform class id về topic id.",
                "",
            ]
        )
    elif best_result and best_result["model_name"] == "LinearSVC":
        lines.extend(
            [
                "Best model là LinearSVC nên mặc định không có `predict_proba`; có thể dùng `decision_function` nếu cần score phụ, nhưng không nên diễn giải như xác suất.",
                "",
            ]
        )

    lines.extend(
        [
            "## 9. Limitations",
            "",
            "- Traditional ML dùng TF-IDF nên phụ thuộc surface words và khó hiểu ngữ cảnh sâu.",
            "- Random Forest/XGBoost có thể không tối ưu với sparse high-dimensional TF-IDF.",
            "- Macro-F1 quan trọng vì dữ liệu mất cân bằng nhãn.",
            "- Kết quả phụ thuộc split train/val/test đã chia sẵn.",
            "",
        ]
    )

    (output_dir / "traditional_ml_technical_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def save_run_config(args: argparse.Namespace, output_dir: Path, scenarios: list[str], models: list[str]) -> None:
    run_config = {
        "random_state": RANDOM_STATE,
        "scenarios": scenarios,
        "models": models,
        "data_dir": str(args.data_dir),
        "output_dir": str(args.output_dir),
        "tuning_mode": args.tuning_mode,
        "vectorizer_config": {
            "fast_grid": TFIDF_PARAM_GRID_FAST,
            "full_extra": TFIDF_PARAM_GRID_FULL_EXTRA,
            "deep_word_grid": TFIDF_DEEP_PARAMS,
            "deep_char_grid": CHAR_TFIDF_DEEP_PARAMS,
        },
        "model_candidate_caps": MAX_CANDIDATES,
        "model_candidate_caps_deep": MAX_CANDIDATES_DEEP,
        "deep_model_grids": MODEL_PARAM_GRIDS_DEEP,
        "created_at": now_iso(),
    }
    write_json(output_dir / "run_config.json", run_config)


def write_best_hyperparams(
    rows: list[dict[str, Any]], output_dir: Path
) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    output_path = output_dir / "best_hyperparameters_by_model.csv"
    frame.to_csv(output_path, index=False)
    return frame


def build_hpo_best_frame(experiment_results: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for result in experiment_results:
        if result.get("status") != "success":
            continue
        val = result.get("metrics_val", {})
        test = result.get("metrics_test", {})
        rows.append(
            {
                "scenario": result.get("scenario"),
                "model_name": result.get("model_name"),
                "best_trial_id": result.get("selected_trial_id"),
                "best_validation_macro_f1": val.get("macro_f1"),
                "best_validation_weighted_f1": val.get("weighted_f1"),
                "best_validation_accuracy": val.get("accuracy"),
                "best_tfidf_params_json": json.dumps(to_jsonable(result.get("tfidf_params", {}))),
                "best_model_params_json": json.dumps(to_jsonable(result.get("model_params", {}))),
                "best_effective_model_params_json": json.dumps(
                    to_jsonable(result.get("model_params_effective", result.get("model_params", {})))
                ),
                "test_accuracy": test.get("accuracy"),
                "test_macro_precision": test.get("macro_precision"),
                "test_macro_recall": test.get("macro_recall"),
                "test_macro_f1": test.get("macro_f1"),
                "test_weighted_f1": test.get("weighted_f1"),
                "model_path": result.get("model_path"),
                "vectorizer_path": result.get("vectorizer_path"),
                "label_encoder_path": result.get("label_encoder_path"),
            }
        )
    return pd.DataFrame(rows)


def build_parameter_effect_summary(trials_frame: pd.DataFrame) -> pd.DataFrame:
    if trials_frame.empty:
        return pd.DataFrame()
    success = trials_frame.loc[trials_frame["status"].eq("success")].copy()
    if success.empty:
        return pd.DataFrame()
    success["macro_f1_val"] = pd.to_numeric(success["macro_f1_val"], errors="coerce")
    success["train_time_sec"] = pd.to_numeric(success["train_time_sec"], errors="coerce")
    parameter_columns = [
        ("tfidf_analyzer", "tfidf_analyzer"),
        ("tfidf_ngram_range", "tfidf_ngram_range"),
        ("tfidf_max_features", "tfidf_max_features"),
        ("C", "C"),
        ("max_depth", "max_depth"),
        ("n_estimators", "n_estimators"),
        ("learning_rate", "learning_rate"),
    ]
    rows = []
    for model_name, model_frame in success.groupby("model_name"):
        for parameter_name, column in parameter_columns:
            if column not in model_frame.columns:
                continue
            values = model_frame[column].dropna()
            if values.empty:
                continue
            for parameter_value, value_frame in model_frame.loc[model_frame[column].notna()].groupby(column):
                rows.append(
                    {
                        "model_name": model_name,
                        "parameter_name": parameter_name,
                        "parameter_value": parameter_value,
                        "n_trials": len(value_frame),
                        "mean_val_macro_f1": value_frame["macro_f1_val"].mean(),
                        "max_val_macro_f1": value_frame["macro_f1_val"].max(),
                        "std_val_macro_f1": value_frame["macro_f1_val"].std(ddof=0),
                        "mean_train_time_sec": value_frame["train_time_sec"].mean(),
                        "notes": "Aggregated over successful validation trials only.",
                    }
                )
    return pd.DataFrame(rows)


def build_validation_curve_points(trials_frame: pd.DataFrame) -> pd.DataFrame:
    if trials_frame.empty:
        return pd.DataFrame()
    success = trials_frame.loc[trials_frame["status"].eq("success")].copy()
    parameter_columns = [
        ("tfidf_max_features", "tfidf_max_features"),
        ("tfidf_ngram_range", "tfidf_ngram_range"),
        ("tfidf_analyzer", "tfidf_analyzer"),
        ("C", "C"),
        ("max_depth", "max_depth"),
        ("n_estimators", "n_estimators"),
        ("learning_rate", "learning_rate"),
    ]
    rows = []
    for _, row in success.iterrows():
        for parameter_name, column in parameter_columns:
            if column in success.columns and pd.notna(row.get(column)):
                rows.append(
                    {
                        "scenario": row.get("scenario"),
                        "model_name": row.get("model_name"),
                        "parameter_name": parameter_name,
                        "parameter_value": row.get(column),
                        "macro_f1_val": row.get("macro_f1_val"),
                        "weighted_f1_val": row.get("weighted_f1_val"),
                        "accuracy_val": row.get("accuracy_val"),
                        "trial_id": row.get("trial_id"),
                    }
                )
    return pd.DataFrame(rows)


def save_hpo_plots(
    output_dir: Path,
    trials_frame: pd.DataFrame,
    ranked_frame: pd.DataFrame,
    summary_frame: pd.DataFrame,
    fast_vs_deep_frame: pd.DataFrame,
) -> list[str]:
    skipped = []
    if trials_frame.empty and summary_frame.empty:
        return ["No HPO data available for plots."]
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    plot_dir = output_dir / "hpo_plots"
    plot_dir.mkdir(parents=True, exist_ok=True)

    def save_plot(filename: str) -> None:
        plt.tight_layout()
        plt.savefig(plot_dir / filename, dpi=200)
        plt.close()

    try:
        if not summary_frame.empty and {"scenario", "model_name", "macro_f1_val"}.issubset(summary_frame.columns):
            plt.figure(figsize=(12, 5))
            sns.barplot(data=summary_frame, x="scenario", y="macro_f1_val", hue="model_name")
            plt.title("Validation Macro-F1 by Model and Scenario")
            plt.xticks(rotation=30, ha="right")
            plt.ylim(0, 1)
            save_plot("val_macro_f1_by_model_scenario.png")
        else:
            skipped.append("val_macro_f1_by_model_scenario.png: missing summary data")

        if not ranked_frame.empty:
            top20 = ranked_frame.head(20).copy()
            top20["trial_label"] = (
                top20["scenario"].astype(str)
                + " | "
                + top20["model_name"].astype(str)
                + " | #"
                + top20["trial_id"].astype(str)
            )
            plt.figure(figsize=(12, 8))
            sns.barplot(data=top20, y="trial_label", x="macro_f1_val", hue="model_name", dodge=False)
            plt.title("Top 20 Trials by Validation Macro-F1")
            plt.xlim(0, 1)
            save_plot("top_20_trials_validation_macro_f1.png")
        else:
            skipped.append("top_20_trials_validation_macro_f1.png: missing ranked trials")

        plot_specs = [
            ("tfidf_max_features", "tfidf_max_features_curve.png", "TF-IDF max_features Validation Curve"),
            ("tfidf_ngram_range", "tfidf_ngram_range_comparison.png", "TF-IDF ngram_range Comparison"),
            ("tfidf_analyzer", "tfidf_analyzer_comparison.png", "TF-IDF Analyzer Comparison"),
        ]
        for column, filename, title in plot_specs:
            if not trials_frame.empty and column in trials_frame.columns and trials_frame[column].notna().any():
                plt.figure(figsize=(10, 5))
                sns.pointplot(data=trials_frame, x=column, y="macro_f1_val", hue="model_name", errorbar=None)
                plt.title(title)
                plt.xticks(rotation=30, ha="right")
                plt.ylim(0, 1)
                save_plot(filename)
            else:
                skipped.append(f"{filename}: missing {column}")

        for model_name, filename, title in [
            ("LogisticRegression", "logreg_C_validation_curve.png", "Logistic Regression C Validation Curve"),
            ("LinearSVC", "linearsvc_C_validation_curve.png", "LinearSVC C Validation Curve"),
        ]:
            model_frame = trials_frame.loc[trials_frame["model_name"].eq(model_name)] if not trials_frame.empty else pd.DataFrame()
            if not model_frame.empty and "C" in model_frame.columns and model_frame["C"].notna().any():
                plt.figure(figsize=(10, 5))
                sns.pointplot(data=model_frame, x="C", y="macro_f1_val", hue="scenario", errorbar=None)
                plt.title(title)
                plt.xticks(rotation=30, ha="right")
                plt.ylim(0, 1)
                save_plot(filename)
            else:
                skipped.append(f"{filename}: missing C data for {model_name}")

        rf_frame = trials_frame.loc[trials_frame["model_name"].eq("RandomForest")] if not trials_frame.empty else pd.DataFrame()
        if not rf_frame.empty and "max_depth" in rf_frame.columns and rf_frame["max_depth"].notna().any():
            plt.figure(figsize=(10, 5))
            sns.pointplot(data=rf_frame, x="max_depth", y="macro_f1_val", hue="scenario", errorbar=None)
            plt.title("Random Forest max_depth Comparison")
            plt.xticks(rotation=30, ha="right")
            plt.ylim(0, 1)
            save_plot("rf_max_depth_comparison.png")
        else:
            skipped.append("rf_max_depth_comparison.png: missing RandomForest max_depth data")

        xgb_frame = trials_frame.loc[trials_frame["model_name"].eq("XGBoost")] if not trials_frame.empty else pd.DataFrame()
        if not xgb_frame.empty and {"max_depth", "learning_rate"}.issubset(xgb_frame.columns):
            plt.figure(figsize=(10, 5))
            sns.scatterplot(
                data=xgb_frame,
                x="max_depth",
                y="learning_rate",
                size="macro_f1_val",
                hue="scenario",
                sizes=(50, 300),
            )
            plt.title("XGBoost Depth and Learning Rate vs Validation Macro-F1")
            save_plot("xgb_depth_learning_rate_comparison.png")
        else:
            skipped.append("xgb_depth_learning_rate_comparison.png: missing XGBoost data")

        if not fast_vs_deep_frame.empty:
            plt.figure(figsize=(12, 5))
            sns.barplot(data=fast_vs_deep_frame, x="scenario", y="delta_val_macro_f1", hue="model_name")
            plt.title("Fast vs Deep Delta Validation Macro-F1")
            plt.axhline(0, color="black", linewidth=1)
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            plt.savefig(plot_dir / "fast_vs_deep_comparison.png", dpi=200)
            plt.savefig(output_dir / "fast_vs_deep_comparison.png", dpi=200)
            plt.close()
        else:
            skipped.append("fast_vs_deep_comparison.png: fast result not available")
    except Exception as exc:  # noqa: BLE001
        skipped.append(f"Plot generation warning: {exc}")
        plt.close("all")
    return skipped


def compare_fast_vs_deep(
    output_dir: Path, summary_frame: pd.DataFrame, hpo_best_frame: pd.DataFrame
) -> pd.DataFrame:
    fast_summary_path = FAST_RESULTS_DIR / "all_model_results_summary.csv"
    fast_params_path = FAST_RESULTS_DIR / "best_hyperparameters_by_model.csv"
    if not fast_summary_path.exists() or summary_frame.empty:
        return pd.DataFrame()
    fast_summary = pd.read_csv(fast_summary_path)
    fast_params = pd.read_csv(fast_params_path) if fast_params_path.exists() else pd.DataFrame()
    fast_param_map = {}
    if not fast_params.empty:
        for _, row in fast_params.iterrows():
            fast_param_map[(row.get("scenario"), row.get("model_name"))] = row.get("best_model_params_json", "")
    deep_param_map = {}
    if not hpo_best_frame.empty:
        for _, row in hpo_best_frame.iterrows():
            tfidf_json = row.get("best_tfidf_params_json", "{}")
            model_json = row.get("best_effective_model_params_json", "{}")
            try:
                tfidf_params = json.loads(tfidf_json) if isinstance(tfidf_json, str) else {}
            except json.JSONDecodeError:
                tfidf_params = {}
            try:
                model_params = json.loads(model_json) if isinstance(model_json, str) else {}
            except json.JSONDecodeError:
                model_params = {}
            deep_param_map[(row.get("scenario"), row.get("model_name"))] = json.dumps(
                {
                    "tfidf": tfidf_params,
                    "model": model_params,
                },
                ensure_ascii=False,
            )
    rows = []
    for _, deep_row in summary_frame.iterrows():
        match = fast_summary.loc[
            fast_summary["scenario"].eq(deep_row.get("scenario"))
            & fast_summary["model_name"].eq(deep_row.get("model_name"))
        ]
        if match.empty:
            continue
        fast_row = match.iloc[0]
        key = (deep_row.get("scenario"), deep_row.get("model_name"))
        rows.append(
            {
                "scenario": deep_row.get("scenario"),
                "model_name": deep_row.get("model_name"),
                "fast_val_macro_f1": fast_row.get("macro_f1_val"),
                "deep_val_macro_f1": deep_row.get("macro_f1_val"),
                "delta_val_macro_f1": deep_row.get("macro_f1_val") - fast_row.get("macro_f1_val"),
                "fast_test_macro_f1": fast_row.get("macro_f1_test"),
                "deep_test_macro_f1": deep_row.get("macro_f1_test"),
                "delta_test_macro_f1": deep_row.get("macro_f1_test") - fast_row.get("macro_f1_test"),
                "fast_best_params_json": fast_param_map.get(key, ""),
                "deep_best_params_json": deep_param_map.get(key, ""),
            }
        )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame.to_csv(output_dir / "fast_vs_deep_comparison.csv", index=False)
    return frame


def write_hpo_diagnostics_json(
    output_dir: Path,
    trials_frame: pd.DataFrame,
    ranked_frame: pd.DataFrame,
    best_result: dict[str, Any] | None,
    skipped_plots: list[str],
) -> None:
    diagnostics = {
        "created_at": now_iso(),
        "n_trials_total": int(len(trials_frame)),
        "n_trials_success": int(trials_frame["status"].eq("success").sum()) if not trials_frame.empty else 0,
        "n_trials_failed": int(trials_frame["status"].eq("failed").sum()) if not trials_frame.empty else 0,
        "fallback_count": int(trials_frame["fallback_used"].fillna(False).astype(bool).sum()) if "fallback_used" in trials_frame else 0,
        "selection_metric": "validation_macro_f1",
        "tie_breakers": [
            "validation_weighted_f1",
            "validation_accuracy",
            f"model_simplicity_if_macro_f1_within_{SIMPLICITY_MACRO_F1_TOLERANCE}",
        ],
        "best_overall": {
            "scenario": best_result.get("scenario") if best_result else None,
            "model_name": best_result.get("model_name") if best_result else None,
            "validation_macro_f1": best_result.get("metrics_val", {}).get("macro_f1") if best_result else None,
            "test_macro_f1": best_result.get("metrics_test", {}).get("macro_f1") if best_result else None,
        },
        "skipped_plots": skipped_plots,
        "ranked_rows": int(len(ranked_frame)),
    }
    write_json(output_dir / "hpo_tuning_diagnostics.json", diagnostics)


def write_hpo_best_overall(output_dir: Path, best_result: dict[str, Any] | None) -> None:
    if best_result is None:
        write_json(output_dir / "hpo_best_overall.json", {"status": "no_successful_experiment"})
        return
    write_json(
        output_dir / "hpo_best_overall.json",
        {
            "selection_metric": "validation_macro_f1",
            "tie_breakers": [
                "validation_weighted_f1",
                "validation_accuracy",
                f"model_simplicity_if_macro_f1_within_{SIMPLICITY_MACRO_F1_TOLERANCE}",
            ],
            "best_scenario": best_result["scenario"],
            "best_model_name": best_result["model_name"],
            "best_trial_id": best_result.get("selected_trial_id"),
            "best_tfidf_params": best_result.get("tfidf_params", {}),
            "best_model_params": best_result.get("model_params", {}),
            "best_effective_model_params": best_result.get("model_params_effective", {}),
            "validation_metrics": best_result.get("metrics_val", {}),
            "test_metrics": best_result.get("metrics_test", {}),
            "model_path": best_result.get("model_path"),
            "vectorizer_path": best_result.get("vectorizer_path"),
            "label_encoder_path": best_result.get("label_encoder_path"),
            "created_at": now_iso(),
        },
    )


def write_fast_run_log_diagnostics(output_dir: Path) -> None:
    log_path = Path("logs/train_traditional_models_overnight.log")
    fast_summary_path = FAST_RESULTS_DIR / "all_model_results_summary.csv"
    lines = ["# Fast Run Log Diagnostics", ""]
    if log_path.exists():
        log_text = log_path.read_text(encoding="utf-8", errors="ignore")
        fallback_count = log_text.count("fallback")
        warning_count = log_text.lower().count("warning")
        train_done_count = log_text.count("[TRAIN DONE]")
        lines.extend(
            [
                f"- Log path: `{log_path}`",
                f"- Completed experiment markers: {train_done_count}",
                f"- Warning count: {warning_count}",
                f"- Fallback mentions: {fallback_count}",
            ]
        )
        summary_match = re.findall(r"=== TRADITIONAL ML TRAINING SUMMARY ===(.+)", log_text, flags=re.S)
        if summary_match:
            lines.extend(["", "## Log Summary Tail", "", "```text", summary_match[-1].strip()[-2000:], "```"])
    else:
        lines.append(f"- Fast overnight log not found at `{log_path}`.")

    if fast_summary_path.exists():
        fast_summary = pd.read_csv(fast_summary_path)
        lines.extend(["", "## Fast Result Summary", ""])
        lines.append(f"- Experiments in summary: {len(fast_summary)}")
        if not fast_summary.empty and "macro_f1_val" in fast_summary:
            best_val = fast_summary.sort_values(["macro_f1_val", "weighted_f1_val"], ascending=False).iloc[0]
            lines.append(
                f"- Best by validation: {best_val['scenario']} / {best_val['model_name']} "
                f"(val Macro-F1={best_val['macro_f1_val']:.4f})"
            )
        if not fast_summary.empty and "macro_f1_test" in fast_summary:
            best_test = fast_summary.sort_values("macro_f1_test", ascending=False).iloc[0]
            lines.append(
                f"- Best by test: {best_test['scenario']} / {best_test['model_name']} "
                f"(test Macro-F1={best_test['macro_f1_test']:.4f})"
            )
        lines.append("- Không chọn best theo test vì test set chỉ dùng để báo cáo final performance.")
        weak = fast_summary.sort_values("macro_f1_val").head(5)
        lines.extend(["", "## Models Weaker In Fast Run", "", markdown_table(weak, ["scenario", "model_name", "macro_f1_val", "macro_f1_test"])])
    else:
        lines.append(f"- Fast summary not found at `{fast_summary_path}`.")
    (output_dir / "fast_run_log_diagnostics.md").write_text("\n".join(lines), encoding="utf-8")


def write_hyperparameter_reasoning_report(
    output_dir: Path,
    ranked_trials: pd.DataFrame,
    hpo_best_frame: pd.DataFrame,
    parameter_effect_frame: pd.DataFrame,
    fast_vs_deep_frame: pd.DataFrame,
    best_result: dict[str, Any] | None,
    trials_frame: pd.DataFrame,
) -> None:
    lines = [
        "# Hyperparameter Reasoning Report",
        "",
        "## 1. Mục tiêu tuning",
        "",
        "Dataset có mất cân bằng nhãn, caption Facebook có độ dài không đều, nhiều teencode/từ viết tắt/từ né bộ lọc. Vì vậy tuning tập trung tối ưu Macro-F1 thay vì chỉ Accuracy để tránh mô hình thiên về lớp lớn.",
        "",
        "## 2. Phương pháp",
        "",
        "- Không có elbow method chuẩn cho supervised classification như K-Means.",
        "- Pipeline dùng hold-out validation để đo Macro-F1 theo từng cấu hình.",
        "- Validation curve được tạo từ toàn bộ trial để xem plateau/overfit theo từng tham số.",
        "- Test set không dùng để chọn tham số; chỉ evaluate sau khi đã chọn best config theo validation Macro-F1.",
        f"- Nếu nhiều cấu hình có Macro-F1 gần nhau trong {SIMPLICITY_MACRO_F1_TOLERANCE}, ưu tiên cấu hình đơn giản hơn: ít feature hơn, n-gram ngắn hơn, train nhanh hơn.",
        "",
        "## 3. Search space",
        "",
        "- TF-IDF: analyzer, max_features, ngram_range, min_df, max_df, sublinear_tf.",
        "- Word n-gram bắt từ/cụm từ trực tiếp; char n-gram có thể giúp với teencode, viết tắt, viết dính và từ né bộ lọc.",
        "- LogisticRegression: C, solver, class_weight; deep mode ưu tiên lbfgs và chỉ thử saga ở vài cấu hình.",
        "- LinearSVC: C và class_weight.",
        "- RandomForest: n_estimators, max_depth, max_features, min_samples_leaf.",
        "- XGBoost: n_estimators, max_depth, learning_rate, subsample, colsample_bytree, reg_lambda, reg_alpha.",
        "",
        "## 4. Kết quả tuning tổng quan",
        "",
        markdown_table(ranked_trials, ["rank_global", "scenario", "model_name", "trial_id", "tfidf_analyzer", "tfidf_max_features", "tfidf_ngram_range", "C", "n_estimators", "max_depth", "learning_rate", "macro_f1_val", "weighted_f1_val", "accuracy_val"], max_rows=10),
        "",
        "## 5. Best hyperparameters theo từng scenario/model",
        "",
        markdown_table(hpo_best_frame, ["scenario", "model_name", "best_trial_id", "best_validation_macro_f1", "best_validation_weighted_f1", "best_validation_accuracy", "test_macro_f1", "best_tfidf_params_json", "best_effective_model_params_json"]),
        "",
        "## 6. Phân tích validation curves",
        "",
    ]
    if not parameter_effect_frame.empty:
        for parameter_name in ["tfidf_max_features", "tfidf_ngram_range", "tfidf_analyzer", "C", "max_depth", "n_estimators"]:
            subset = parameter_effect_frame.loc[parameter_effect_frame["parameter_name"].eq(parameter_name)]
            if subset.empty:
                continue
            best_row = subset.sort_values("max_val_macro_f1", ascending=False).iloc[0]
            lines.append(
                f"- `{parameter_name}` tốt nhất theo max validation Macro-F1: "
                f"{best_row['parameter_value']} cho {best_row['model_name']} "
                f"(max={best_row['max_val_macro_f1']:.4f})."
            )
    else:
        lines.append("- Chưa có dữ liệu validation curve.")
    lines.extend(["", "## 7. So sánh fast vs deep", ""])
    if fast_vs_deep_frame.empty:
        lines.append("Không tìm thấy fast result cũ hoặc chưa đủ dữ liệu để so sánh.")
    else:
        lines.append(markdown_table(fast_vs_deep_frame, ["scenario", "model_name", "fast_val_macro_f1", "deep_val_macro_f1", "delta_val_macro_f1", "fast_test_macro_f1", "deep_test_macro_f1", "delta_test_macro_f1"]))
    lines.extend(["", "## 8. Best model cuối cùng", ""])
    if best_result is None:
        lines.append("Không có experiment thành công.")
    else:
        lines.extend(
            [
                f"- Best scenario: {best_result['scenario']}.",
                f"- Best model: {best_result['model_name']}.",
                f"- Best trial id: {best_result.get('selected_trial_id')}.",
                f"- Best TF-IDF params: `{json.dumps(to_jsonable(best_result.get('tfidf_params', {})), ensure_ascii=False)}`.",
                f"- Best effective model params: `{json.dumps(to_jsonable(best_result.get('model_params_effective', {})), ensure_ascii=False)}`.",
                f"- Validation Macro-F1: {best_result['metrics_val']['macro_f1']:.4f}.",
                f"- Test Macro-F1: {best_result['metrics_test']['macro_f1']:.4f}.",
                f"- Model path: `{best_result['model_path']}`.",
                f"- Vectorizer path: `{best_result['vectorizer_path']}`.",
                f"- Label encoder path: `{best_result['label_encoder_path']}`.",
            ]
        )
    lines.extend(["", "## 9. Nhận xét bất thường", ""])
    fallback_count = int(trials_frame["fallback_used"].fillna(False).astype(bool).sum()) if "fallback_used" in trials_frame else 0
    lines.append(f"- Số fallback/convergence warning được ghi nhận: {fallback_count}.")
    if hpo_best_frame.empty:
        lines.append("- Chưa đủ best-result rows để phân tích validation-test gap.")
    else:
        for _, row in hpo_best_frame.iterrows():
            gap = row.get("test_macro_f1") - row.get("best_validation_macro_f1")
            if pd.notna(gap) and abs(gap) > 0.04:
                lines.append(
                    f"- Gap validation-test lớn ở {row['scenario']} / {row['model_name']}: {gap:.4f}."
                )
        tree_rows = hpo_best_frame.loc[hpo_best_frame["model_name"].isin(["RandomForest", "XGBoost"])]
        linear_rows = hpo_best_frame.loc[hpo_best_frame["model_name"].isin(["LogisticRegression", "LinearSVC"])]
        if not tree_rows.empty and not linear_rows.empty:
            if tree_rows["best_validation_macro_f1"].mean() < linear_rows["best_validation_macro_f1"].mean():
                lines.append("- Tree-based models thấp hơn mô hình tuyến tính, phù hợp kỳ vọng với sparse high-dimensional TF-IDF.")
        if hpo_best_frame["scenario"].astype(str).str.contains("Balanced", case=False).any():
            lines.append("- Balanced scenario có duplicate train do oversampling; validation/test vẫn được kiểm tra consistency với raw.")
    lines.extend(
        [
            "",
            "## 10. Kết luận",
            "",
            "Nhóm đã tiến hành HPO có kiểm soát bằng hold-out validation và chọn mô hình theo validation Macro-F1. Logistic Regression/LinearSVC với TF-IDF là baseline mạnh cho sparse text features; tree-based models thường kém hơn trên không gian TF-IDF chiều cao. Deep HPO được dùng để kiểm tra liệu search space rộng hơn, char n-gram và tuning C/regularization có cải thiện so với fast mode hay không.",
            "",
        ]
    )
    (output_dir / "hyperparameter_reasoning_report.md").write_text("\n".join(lines), encoding="utf-8")


def finalize_deep_hpo_outputs(
    output_dir: Path,
    trials_frame: pd.DataFrame,
    experiment_results: list[dict[str, Any]],
    summary_frame: pd.DataFrame,
    best_result: dict[str, Any] | None,
) -> None:
    if trials_frame.empty:
        return
    trials_frame.to_csv(output_dir / "hpo_all_trials.csv", index=False)
    ranked_frame = rank_trials_frame(trials_frame)
    ranked_frame.to_csv(output_dir / "hpo_all_trials_ranked.csv", index=False)
    hpo_best_frame = build_hpo_best_frame(experiment_results)
    hpo_best_frame.to_csv(output_dir / "hpo_best_by_scenario_model.csv", index=False)
    write_hpo_best_overall(output_dir, best_result)
    parameter_effect_frame = build_parameter_effect_summary(trials_frame)
    parameter_effect_frame.to_csv(output_dir / "hpo_parameter_effect_summary.csv", index=False)
    validation_curve_frame = build_validation_curve_points(trials_frame)
    validation_curve_frame.to_csv(output_dir / "hpo_validation_curve_points.csv", index=False)
    fast_vs_deep_frame = compare_fast_vs_deep(output_dir, summary_frame, hpo_best_frame)
    skipped_plots = save_hpo_plots(
        output_dir,
        trials_frame,
        ranked_frame,
        summary_frame,
        fast_vs_deep_frame,
    )
    write_hpo_diagnostics_json(output_dir, trials_frame, ranked_frame, best_result, skipped_plots)
    write_fast_run_log_diagnostics(output_dir)
    write_hyperparameter_reasoning_report(
        output_dir,
        ranked_frame,
        hpo_best_frame,
        parameter_effect_frame,
        fast_vs_deep_frame,
        best_result,
        trials_frame,
    )


REPAIR_BACKUP_FILENAMES = [
    "all_model_results_summary.csv",
    "best_hyperparameters_by_model.csv",
    "hpo_tuning_diagnostics.json",
    "hyperparameter_reasoning_report.md",
    "traditional_ml_technical_report.md",
]


def json_loads_field(value: Any, default: Any | None = None) -> Any:
    if default is None:
        default = {}
    if isinstance(value, dict):
        return value
    if isinstance(value, float) and pd.isna(value):
        return default
    if value is None:
        return default
    if not isinstance(value, str):
        return default
    text = value.strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def normalize_tfidf_params(params: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(params)
    if isinstance(normalized.get("ngram_range"), list):
        normalized["ngram_range"] = tuple(normalized["ngram_range"])
    return normalized


def backup_outputs_before_repair(output_dir: Path, logger: logging.Logger) -> Path:
    backup_dir = output_dir / "backup_before_xgboost_repair"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for filename in REPAIR_BACKUP_FILENAMES:
        source = output_dir / filename
        if source.exists():
            shutil.copy2(source, backup_dir / filename)
            logger.info("[REPAIR BACKUP] %s -> %s", source, backup_dir / filename)
        else:
            logger.warning("[REPAIR BACKUP] skipped missing file: %s", source)
    return backup_dir


def metric_value(row: pd.Series, column: str) -> float | None:
    value = row.get(column)
    if pd.isna(value):
        return None
    return float(value)


def metrics_from_summary_row(row: pd.Series, suffix: str) -> dict[str, float]:
    mapping = {
        "accuracy": f"accuracy_{suffix}",
        "macro_precision": f"macro_precision_{suffix}",
        "macro_recall": f"macro_recall_{suffix}",
        "macro_f1": f"macro_f1_{suffix}",
        "weighted_precision": f"weighted_precision_{suffix}",
        "weighted_recall": f"weighted_recall_{suffix}",
        "weighted_f1": f"weighted_f1_{suffix}",
        "micro_precision": f"micro_precision_{suffix}",
        "micro_recall": f"micro_recall_{suffix}",
        "micro_f1": f"micro_f1_{suffix}",
    }
    metrics = {}
    for metric_name, column in mapping.items():
        value = metric_value(row, column)
        if value is not None:
            metrics[metric_name] = value
    return metrics


def safe_path_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value)


def result_from_summary_row(row: pd.Series, output_dir: Path) -> dict[str, Any]:
    scenario = str(row.get("scenario"))
    model_name = str(row.get("model_name"))
    experiment_dir = output_dir / scenario / model_name
    model_path = safe_path_text(row.get("model_path"))
    if model_path:
        experiment_dir = Path(model_path).parent
    config_path = experiment_dir / "experiment_config.json"
    config = json_loads_field(config_path.read_text(encoding="utf-8"), {}) if config_path.exists() else {}
    status = str(row.get("status", "failed"))
    result: dict[str, Any] = {
        "scenario": scenario,
        "model_name": model_name,
        "text_column": row.get("text_column"),
        "n_train": metric_value(row, "n_train"),
        "n_val": metric_value(row, "n_val"),
        "n_test": metric_value(row, "n_test"),
        "vectorizer_max_features": metric_value(row, "vectorizer_max_features"),
        "vectorizer_ngram_range": row.get("vectorizer_ngram_range"),
        "metrics_val": metrics_from_summary_row(row, "val"),
        "metrics_test": metrics_from_summary_row(row, "test"),
        "train_time_sec": metric_value(row, "train_time_sec"),
        "val_predict_time_sec": metric_value(row, "val_predict_time_sec"),
        "test_predict_time_sec": metric_value(row, "test_predict_time_sec"),
        "model_path": model_path,
        "vectorizer_path": safe_path_text(row.get("vectorizer_path")),
        "label_encoder_path": str(experiment_dir / "label_encoder.joblib"),
        "experiment_dir": str(experiment_dir),
        "tfidf_params": config.get("tfidf_params", {}),
        "model_params": config.get("model_params", {}),
        "model_params_effective": config.get("model_params_effective", config.get("model_params", {})),
        "selected_trial_id": config.get("selected_trial_id"),
        "fallback_used": config.get("fallback_used", False),
        "warning_message": config.get("warning_message", ""),
        "status": status,
        "notes": row.get("notes", ""),
    }
    return result


def load_trials_frame_for_repair(output_dir: Path) -> pd.DataFrame:
    for filename in ["hpo_all_trials.csv", "hyperparameter_search_results.csv"]:
        path = output_dir / filename
        if path.exists():
            return pd.read_csv(path)
    return pd.DataFrame()


def load_best_trial_for_repair(
    output_dir: Path, scenario: str, model_name: str
) -> dict[str, Any]:
    best_path = output_dir / "best_hyperparameters_by_model.csv"
    if best_path.exists():
        best_frame = pd.read_csv(best_path)
        match = best_frame.loc[
            best_frame["scenario"].eq(scenario) & best_frame["model_name"].eq(model_name)
        ]
        if not match.empty:
            row = match.iloc[0]
            return {
                "trial_id": int(row["best_trial_id"]),
                "tfidf_params": normalize_tfidf_params(
                    json_loads_field(row.get("best_tfidf_params_json"), {})
                ),
                "model_params": json_loads_field(row.get("best_model_params_json"), {}),
                "model_params_effective": json_loads_field(
                    row.get("best_effective_model_params_json"),
                    json_loads_field(row.get("best_model_params_json"), {}),
                ),
                "metrics_val": {
                    "macro_f1": float(row.get("best_validation_macro_f1")),
                    "weighted_f1": float(row.get("best_validation_weighted_f1")),
                    "accuracy": float(row.get("best_validation_accuracy")),
                },
            }

    ranked_path = output_dir / "hpo_all_trials_ranked.csv"
    if ranked_path.exists():
        ranked_frame = pd.read_csv(ranked_path)
        match = ranked_frame.loc[
            ranked_frame["scenario"].eq(scenario)
            & ranked_frame["model_name"].eq(model_name)
            & ranked_frame["status"].eq("success")
        ].copy()
        if not match.empty:
            match["macro_f1_val"] = pd.to_numeric(match["macro_f1_val"], errors="coerce")
            match["weighted_f1_val"] = pd.to_numeric(match["weighted_f1_val"], errors="coerce")
            match["accuracy_val"] = pd.to_numeric(match["accuracy_val"], errors="coerce")
            row = match.sort_values(
                ["macro_f1_val", "weighted_f1_val", "accuracy_val"],
                ascending=[False, False, False],
            ).iloc[0]
            return {
                "trial_id": int(row["trial_id"]),
                "tfidf_params": normalize_tfidf_params(json_loads_field(row.get("tfidf_params_json"), {})),
                "model_params": json_loads_field(row.get("model_params_json"), {}),
                "model_params_effective": json_loads_field(
                    row.get("model_params_effective_json"),
                    json_loads_field(row.get("model_params_json"), {}),
                ),
                "metrics_val": {
                    "macro_f1": float(row.get("macro_f1_val")),
                    "weighted_f1": float(row.get("weighted_f1_val")),
                    "accuracy": float(row.get("accuracy_val")),
                },
            }

    raise RuntimeError(
        f"Cannot find saved best hyperparameters for repair: {scenario} / {model_name}"
    )


def write_validation_test_gap_analysis(summary_frame: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    rows = []
    if summary_frame.empty:
        frame = pd.DataFrame()
        frame.to_csv(output_dir / "validation_test_gap_analysis.csv", index=False)
        return frame
    success = summary_frame.loc[summary_frame["status"].eq("success")].copy()
    for _, row in success.iterrows():
        macro_val = row.get("macro_f1_val")
        macro_test = row.get("macro_f1_test")
        accuracy_val = row.get("accuracy_val")
        accuracy_test = row.get("accuracy_test")
        weighted_val = row.get("weighted_f1_val")
        weighted_test = row.get("weighted_f1_test")
        macro_delta = macro_test - macro_val if pd.notna(macro_val) and pd.notna(macro_test) else np.nan
        notes = []
        if pd.notna(macro_delta) and abs(macro_delta) > 0.04:
            notes.append("warning_abs_macro_f1_gap_gt_0.04")
        rows.append(
            {
                "scenario": row.get("scenario"),
                "model_name": row.get("model_name"),
                "macro_f1_val": macro_val,
                "macro_f1_test": macro_test,
                "delta_test_minus_val": macro_delta,
                "accuracy_val": accuracy_val,
                "accuracy_test": accuracy_test,
                "delta_accuracy_test_minus_val": (
                    accuracy_test - accuracy_val
                    if pd.notna(accuracy_val) and pd.notna(accuracy_test)
                    else np.nan
                ),
                "weighted_f1_val": weighted_val,
                "weighted_f1_test": weighted_test,
                "delta_weighted_f1_test_minus_val": (
                    weighted_test - weighted_val
                    if pd.notna(weighted_val) and pd.notna(weighted_test)
                    else np.nan
                ),
                "notes": "; ".join(notes),
            }
        )
    frame = pd.DataFrame(rows)
    frame.to_csv(output_dir / "validation_test_gap_analysis.csv", index=False)
    return frame


def append_repair_report_sections(
    output_dir: Path,
    summary_frame: pd.DataFrame,
    gap_frame: pd.DataFrame,
    repaired_scenarios: list[str],
) -> None:
    success_count = int(summary_frame["status"].eq("success").sum()) if "status" in summary_frame else 0
    failed_count = int(len(summary_frame) - success_count)
    sections = [
        "",
        "## XGBoost Final Repair",
        "",
        "- Nguyên nhân lỗi ban đầu: `early_stopping_rounds` cần `eval_set` trong final fit.",
        "- HPO trials của XGBoost không bị chạy lại và không bị mất; repair chỉ refit final XGBoost bằng best hyperparameters đã chọn từ validation.",
        "- Benchmark final fit dùng validation set cho XGBoost early stopping; test set vẫn không dùng để chọn hyperparameters.",
        "- Deployment refit train+val không dùng early stopping vì không có validation set riêng; nếu best deployment là XGBoost thì `early_stopping_rounds` được bỏ an toàn.",
        f"- Repaired XGBoost scenarios: {len(repaired_scenarios)} ({', '.join(repaired_scenarios) if repaired_scenarios else 'none'}).",
        f"- Final experiments after repair: {len(summary_frame)} total, {success_count} success, {failed_count} failed.",
        "",
        "## Validation-Test Gap Analysis",
        "",
        "- Best model được chọn theo validation Macro-F1; test set chỉ dùng để báo cáo final performance.",
        "- Test Macro-F1 có thể cao/thấp hơn validation do phân phối val/test khác nhau, độ khó split khác nhau hoặc support từng lớp khác nhau.",
        "- Không chọn lại model theo test Macro-F1, kể cả khi test của fast/deep khác nhau.",
        "- Cần xem thêm per-class F1/confusion matrix trong error analysis sau khi chốt final.",
        "",
        markdown_table(
            gap_frame,
            [
                "scenario",
                "model_name",
                "macro_f1_val",
                "macro_f1_test",
                "delta_test_minus_val",
                "accuracy_val",
                "accuracy_test",
                "delta_accuracy_test_minus_val",
                "weighted_f1_val",
                "weighted_f1_test",
                "delta_weighted_f1_test_minus_val",
                "notes",
            ],
        ),
        "",
    ]
    text = "\n".join(sections)
    for filename in ["hyperparameter_reasoning_report.md", "traditional_ml_technical_report.md"]:
        path = output_dir / filename
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        path.write_text(current.rstrip() + "\n" + text, encoding="utf-8")


def update_repair_diagnostics(
    output_dir: Path,
    summary_frame: pd.DataFrame,
    repaired_scenarios: list[str],
) -> None:
    diagnostics_path = output_dir / "hpo_tuning_diagnostics.json"
    diagnostics = {}
    if diagnostics_path.exists():
        diagnostics = json_loads_field(diagnostics_path.read_text(encoding="utf-8"), {})
    success_count = int(summary_frame["status"].eq("success").sum()) if "status" in summary_frame else 0
    diagnostics.update(
        {
            "final_experiments_total": int(len(summary_frame)),
            "final_experiments_success": success_count,
            "final_experiments_failed": int(len(summary_frame) - success_count),
            "xgboost_repaired": bool(repaired_scenarios),
            "xgboost_repaired_scenarios": int(len(repaired_scenarios)),
            "xgboost_repaired_scenario_names": repaired_scenarios,
            "repair_created_at": now_iso(),
            "selection_metric": "validation_macro_f1",
        }
    )
    write_json(diagnostics_path, diagnostics)


def repair_failed_final_experiments(
    args: argparse.Namespace,
    output_dir: Path,
    logger: logging.Logger,
    scenario_data_map: dict[str, ScenarioData],
    split_validation_frame: pd.DataFrame,
) -> int:
    summary_path = output_dir / "all_model_results_summary.csv"
    if not summary_path.exists():
        raise RuntimeError(f"Cannot repair without existing summary: {summary_path}")

    existing_summary = pd.read_csv(summary_path)
    failed_rows = existing_summary.loc[~existing_summary["status"].eq("success")].copy()
    xgb_failed_rows = failed_rows.loc[failed_rows["model_name"].eq("XGBoost")].copy()
    logger.info("Repair failed final experiments: %s", len(failed_rows))
    logger.info("XGBoost failed final experiments selected for repair: %s", len(xgb_failed_rows))

    backup_outputs_before_repair(output_dir, logger)
    split_validation_frame.to_csv(output_dir / "split_validation_report.csv", index=False)

    results_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for _, row in existing_summary.iterrows():
        result = result_from_summary_row(row, output_dir)
        results_by_key[(result["scenario"], result["model_name"])] = result

    repaired_scenarios: list[str] = []
    for _, row in xgb_failed_rows.iterrows():
        scenario = str(row["scenario"])
        model_name = "XGBoost"
        if scenario not in scenario_data_map:
            logger.error("[REPAIR FAILED] Scenario not loaded: %s", scenario)
            results_by_key[(scenario, model_name)] = {
                "scenario": scenario,
                "model_name": model_name,
                "text_column": row.get("text_column"),
                "status": "failed",
                "notes": "Scenario not available during repair",
            }
            continue

        scenario_data = scenario_data_map[scenario]
        label_encoder = fit_label_encoder(scenario_data.splits["train"]["topic_label_id"])
        experiment_dir = output_dir / scenario / model_name
        best_trial = load_best_trial_for_repair(output_dir, scenario, model_name)
        logger.info(
            "[REPAIR START] Scenario=%s | Model=%s | Best trial=%s",
            scenario,
            model_name,
            best_trial["trial_id"],
        )
        try:
            result = train_final_experiment(
                scenario_data,
                model_name,
                best_trial,
                label_encoder,
                experiment_dir,
                logger,
            )
            result["notes"] = "; ".join(
                filter(
                    None,
                    [
                        result.get("notes", ""),
                        "Repaired final XGBoost from saved deep HPO best hyperparameters; HPO trials were not rerun.",
                    ],
                )
            )
            results_by_key[(scenario, model_name)] = result
            repaired_scenarios.append(scenario)
            write_json(
                experiment_dir / "best_hyperparameters.json",
                {
                    "best_trial_id": best_trial["trial_id"],
                    "selection_metric": "validation_macro_f1",
                    "tie_breakers": [
                        "validation_weighted_f1",
                        "validation_accuracy",
                        f"model_simplicity_if_macro_f1_within_{SIMPLICITY_MACRO_F1_TOLERANCE}",
                    ],
                    "best_validation_metrics_from_hpo": best_trial.get("metrics_val", {}),
                    "best_tfidf_params": best_trial["tfidf_params"],
                    "best_model_params": best_trial["model_params"],
                    "best_effective_model_params": best_trial.get(
                        "model_params_effective", best_trial["model_params"]
                    ),
                    "repair_note": "Final XGBoost refit reused saved HPO best hyperparameters; HPO trials were not rerun.",
                    "created_at": now_iso(),
                },
            )
            logger.info(
                "[REPAIR DONE] Scenario=%s | val_macro_f1=%.4f | test_macro_f1=%.4f",
                scenario,
                result["metrics_val"]["macro_f1"],
                result["metrics_test"]["macro_f1"],
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("[REPAIR FAILED] Scenario=%s | error=%s", scenario, exc)
            results_by_key[(scenario, model_name)] = {
                "scenario": scenario,
                "model_name": model_name,
                "text_column": scenario_data.text_column,
                "status": "failed",
                "notes": str(exc),
            }

    experiment_results = list(results_by_key.values())
    summary_frame = sort_summary_frame(
        pd.DataFrame([flatten_summary_row(result) for result in experiment_results])
    )
    summary_frame.to_csv(summary_path, index=False)
    write_summary_markdown(summary_frame, output_dir)

    best_hyperparams_path = output_dir / "best_hyperparameters_by_model.csv"
    best_hyperparams_frame = (
        pd.read_csv(best_hyperparams_path) if best_hyperparams_path.exists() else pd.DataFrame()
    )

    best_result = choose_best_experiment(experiment_results)
    previous_best = {}
    best_summary_path = output_dir / "best_model_summary.json"
    if best_summary_path.exists():
        previous_best = json_loads_field(best_summary_path.read_text(encoding="utf-8"), {})
    previous_best_key = (
        previous_best.get("best_scenario"),
        previous_best.get("best_model_name"),
    )
    current_best_key = (
        best_result.get("scenario") if best_result else None,
        best_result.get("model_name") if best_result else None,
    )
    if best_result is not None:
        write_best_summary(best_result, output_dir)
        if current_best_key != previous_best_key and best_result["model_name"] == "XGBoost":
            logger.info("[REPAIR BEST UPDATE] XGBoost became best overall; updating best_model folders.")
            copy_best_model(best_result, output_dir)
            refit_best_model_train_val(
                best_result,
                scenario_data_map[best_result["scenario"]],
                output_dir,
                logger,
            )
        else:
            logger.info("[REPAIR BEST UPDATE] Best overall unchanged or not XGBoost; best_model artifacts left in place.")

    write_technical_report(
        output_dir,
        scenario_data_map,
        split_validation_frame,
        summary_frame,
        best_hyperparams_frame,
        best_result,
        "deep",
    )

    trials_frame = load_trials_frame_for_repair(output_dir)
    if not trials_frame.empty:
        finalize_deep_hpo_outputs(
            output_dir,
            trials_frame,
            experiment_results,
            summary_frame,
            best_result,
        )

    gap_frame = write_validation_test_gap_analysis(summary_frame, output_dir)
    append_repair_report_sections(output_dir, summary_frame, gap_frame, repaired_scenarios)
    update_repair_diagnostics(output_dir, summary_frame, repaired_scenarios)

    successful_experiments = int(summary_frame["status"].eq("success").sum())
    failed_experiments = int(len(summary_frame) - successful_experiments)
    logger.info("Repaired XGBoost scenarios: %s", len(repaired_scenarios))
    logger.info("Final experiments: %s", len(summary_frame))
    logger.info("Successful experiments: %s", successful_experiments)
    logger.info("Failed experiments: %s", failed_experiments)
    logger.info("Output folder: %s", output_dir)
    return 0 if failed_experiments == 0 else 1


def run_training(args: argparse.Namespace) -> int:
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logging(output_dir)

    scenarios, discovered_split_paths, discovery_notes = discover_scenario_split_paths(
        args.data_dir, args.scenarios, logger
    )
    models = normalize_requested_names(args.models, MODELS, "model")
    if not args.repair_failed_final:
        save_run_config(args, output_dir, scenarios, models)

    logger.info("Starting DS107 traditional ML training")
    logger.info("data_dir=%s", args.data_dir)
    logger.info("output_dir=%s", output_dir)
    logger.info("scenarios=%s", scenarios)
    logger.info("models=%s", models)
    logger.info("tuning_mode=%s", args.tuning_mode)
    logger.info("repair_failed_final=%s", args.repair_failed_final)
    run_id = f"{args.tuning_mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    scenario_data_map: dict[str, ScenarioData] = {}
    split_validation_rows = []
    validation_errors: list[str] = []
    raw_test_record_ids: set[str] | None = None
    raw_reference_scenario = next(
        (scenario for scenario in scenarios if "raw" in scenario.lower()),
        scenarios[0] if scenarios else None,
    )
    if raw_reference_scenario is not None:
        raw_reference_df = read_split_csv(discovered_split_paths[raw_reference_scenario]["test"])
        if "record_id" in raw_reference_df.columns:
            raw_test_record_ids = set(
                raw_reference_df["record_id"].astype("string").str.strip().dropna()
            )
    for scenario in scenarios:
        scenario_data = validate_and_clean_scenario(
            scenario,
            discovered_split_paths[scenario],
            discovery_notes.get(scenario, []),
            None if scenario == raw_reference_scenario else raw_test_record_ids,
            logger,
        )
        scenario_data_map[scenario] = scenario_data
        split_validation_rows.extend(scenario_data.validation_rows)
        validation_errors.extend(scenario_data.severe_errors)

    split_validation_frame = pd.DataFrame(split_validation_rows)

    if validation_errors:
        logger.error("Input data validation failed with %s severe errors.", len(validation_errors))
        raise DataValidationError("\n".join(validation_errors))

    if args.validate_only:
        split_validation_frame.to_csv(output_dir / "split_validation_report.csv", index=False)
        logger.info("Validation-only mode complete.")
        return 0

    if args.repair_failed_final:
        return repair_failed_final_experiments(
            args,
            output_dir,
            logger,
            scenario_data_map,
            split_validation_frame,
        )

    split_validation_frame.to_csv(output_dir / "split_validation_report.csv", index=False)

    all_trial_rows: list[dict[str, Any]] = []
    best_hyperparameter_rows: list[dict[str, Any]] = []
    experiment_results: list[dict[str, Any]] = []

    for scenario in scenarios:
        scenario_data = scenario_data_map[scenario]
        label_encoder = fit_label_encoder(scenario_data.splits["train"]["topic_label_id"])
        for model_name in models:
            logger.info("[START] Scenario=%s | Model=%s", scenario, model_name)
            logger.info(
                "[DATA] train=%s, val=%s, test=%s",
                len(scenario_data.splits["train"]),
                len(scenario_data.splits["val"]),
                len(scenario_data.splits["test"]),
            )
            experiment_dir = output_dir / scenario / model_name
            experiment_dir.mkdir(parents=True, exist_ok=True)

            candidates = build_candidates(model_name, args.tuning_mode, logger)
            if args.tuning_mode == "deep":
                total_candidates = len(get_model_grid(model_name, args.tuning_mode)) * len(
                    get_tfidf_grid(model_name, args.tuning_mode)
                )
                logger.info(
                    "[HPO-DEEP] Scenario=%s | Model=%s | Total candidate configs=%s | Sampled trials=%s",
                    scenario,
                    model_name,
                    total_candidates,
                    len(candidates),
                )
            logger.info(
                "[HPO] Scenario=%s | Model=%s | Trials=%s",
                scenario,
                model_name,
                len(candidates),
            )
            trials = []
            for trial_index, candidate in enumerate(candidates, start=1):
                logger.info(
                    "[TUNING] Scenario=%s | Model=%s | Trial=%s/%s",
                    scenario,
                    model_name,
                    trial_index,
                    len(candidates),
                )
                trial = train_candidate(
                    scenario_data,
                    model_name,
                    trial_index,
                    candidate["tfidf_params"],
                    candidate["model_params"],
                    label_encoder,
                    logger,
                    run_id,
                    args.tuning_mode,
                )
                trials.append(trial)
                all_trial_rows.append(flatten_trial_row(trial))

            trials_frame = pd.DataFrame([flatten_trial_row(trial) for trial in trials])
            trials_frame.to_csv(experiment_dir / "hyperparameter_trials.csv", index=False)

            best_trial = choose_best_trial(trials)
            if best_trial is None:
                failed_result = {
                    "scenario": scenario,
                    "model_name": model_name,
                    "text_column": scenario_data.text_column,
                    "status": "failed",
                    "notes": "All hyperparameter trials failed",
                }
                experiment_results.append(failed_result)
                logger.error(
                    "[EXPERIMENT FAILED] Scenario=%s | Model=%s | all trials failed",
                    scenario,
                    model_name,
                )
                continue

            write_json(
                experiment_dir / "best_hyperparameters.json",
                {
                    "best_trial_id": best_trial["trial_id"],
                    "selection_metric": "validation_macro_f1",
                    "tie_breakers": [
                        "validation_weighted_f1",
                        "validation_accuracy",
                        f"model_simplicity_if_macro_f1_within_{SIMPLICITY_MACRO_F1_TOLERANCE}",
                    ],
                    "best_validation_metrics": best_trial["metrics_val"],
                    "best_tfidf_params": best_trial["tfidf_params"],
                    "best_model_params": best_trial["model_params"],
                    "best_effective_model_params": best_trial.get(
                        "model_params_effective", best_trial["model_params"]
                    ),
                    "created_at": now_iso(),
                },
            )
            best_hyperparameter_rows.append(
                {
                    "scenario": scenario,
                    "model_name": model_name,
                    "best_trial_id": best_trial["trial_id"],
                    "best_validation_macro_f1": best_trial["metrics_val"]["macro_f1"],
                    "best_validation_weighted_f1": best_trial["metrics_val"]["weighted_f1"],
                    "best_validation_accuracy": best_trial["metrics_val"]["accuracy"],
                    "best_tfidf_params_json": json.dumps(
                        to_jsonable(best_trial["tfidf_params"])
                    ),
                    "best_model_params_json": json.dumps(
                        to_jsonable(best_trial["model_params"])
                    ),
                    "best_effective_model_params_json": json.dumps(
                        to_jsonable(best_trial.get("model_params_effective", best_trial["model_params"]))
                    ),
                }
            )

            logger.info(
                "[VECTORIZER] max_features=%s, ngram_range=%s",
                best_trial["tfidf_params"].get("max_features"),
                best_trial["tfidf_params"].get("ngram_range"),
            )
            try:
                result = train_final_experiment(
                    scenario_data,
                    model_name,
                    best_trial,
                    label_encoder,
                    experiment_dir,
                    logger,
                )
                experiment_results.append(result)
                logger.info("[TRAIN DONE] train_time=%.2f", result["train_time_sec"])
                logger.info(
                    "[VAL] acc=%.4f, macro_precision=%.4f, macro_recall=%.4f, macro_f1=%.4f",
                    result["metrics_val"]["accuracy"],
                    result["metrics_val"]["macro_precision"],
                    result["metrics_val"]["macro_recall"],
                    result["metrics_val"]["macro_f1"],
                )
                logger.info(
                    "[TEST] acc=%.4f, macro_precision=%.4f, macro_recall=%.4f, macro_f1=%.4f",
                    result["metrics_test"]["accuracy"],
                    result["metrics_test"]["macro_precision"],
                    result["metrics_test"]["macro_recall"],
                    result["metrics_test"]["macro_f1"],
                )
                logger.info("[SAVED] output path=%s", experiment_dir)
            except Exception as exc:  # noqa: BLE001 - continue other experiments.
                logger.exception(
                    "[EXPERIMENT FAILED] Scenario=%s | Model=%s | error=%s",
                    scenario,
                    model_name,
                    exc,
                )
                experiment_results.append(
                    {
                        "scenario": scenario,
                        "model_name": model_name,
                        "text_column": scenario_data.text_column,
                        "status": "failed",
                        "notes": str(exc),
                    }
                )

    hyperparameter_search_frame = pd.DataFrame(all_trial_rows)
    hyperparameter_search_frame.to_csv(
        output_dir / "hyperparameter_search_results.csv", index=False
    )
    best_hyperparams_frame = write_best_hyperparams(best_hyperparameter_rows, output_dir)

    summary_frame = sort_summary_frame(
        pd.DataFrame([flatten_summary_row(result) for result in experiment_results])
    )
    summary_frame.to_csv(output_dir / "all_model_results_summary.csv", index=False)
    write_summary_markdown(summary_frame, output_dir)

    best_result = choose_best_experiment(experiment_results)
    if best_result is not None:
        write_best_summary(best_result, output_dir)
        copy_best_model(best_result, output_dir)
        refit_best_model_train_val(
            best_result,
            scenario_data_map[best_result["scenario"]],
            output_dir,
            logger,
        )

    write_technical_report(
        output_dir,
        scenario_data_map,
        split_validation_frame,
        summary_frame,
        best_hyperparams_frame,
        best_result,
        args.tuning_mode,
    )

    if args.tuning_mode == "deep":
        finalize_deep_hpo_outputs(
            output_dir,
            hyperparameter_search_frame,
            experiment_results,
            summary_frame,
            best_result,
        )

    total_experiments = len(scenarios) * len(models)
    successful_experiments = sum(
        1 for result in experiment_results if result.get("status") == "success"
    )
    failed_experiments = total_experiments - successful_experiments

    logger.info("=== TRADITIONAL ML TRAINING SUMMARY ===")
    logger.info("Total experiments: %s", total_experiments)
    logger.info("Successful experiments: %s", successful_experiments)
    logger.info("Failed experiments: %s", failed_experiments)
    if best_result is not None:
        logger.info("Best scenario: %s", best_result["scenario"])
        logger.info("Best model: %s", best_result["model_name"])
        logger.info("Best validation Macro-F1: %.4f", best_result["metrics_val"]["macro_f1"])
        logger.info("Best test Macro-F1: %.4f", best_result["metrics_test"]["macro_f1"])
        logger.info("Best test Accuracy: %.4f", best_result["metrics_test"]["accuracy"])
    else:
        logger.info("Best scenario: N/A")
        logger.info("Best model: N/A")
        logger.info("Best validation Macro-F1: N/A")
        logger.info("Best test Macro-F1: N/A")
        logger.info("Best test Accuracy: N/A")
    logger.info("Output folder: %s", output_dir)

    return 0 if successful_experiments > 0 else 1


def main() -> int:
    try:
        args = parse_args()
        return run_training(args)
    except DataValidationError as exc:
        print(f"[DATA VALIDATION ERROR]\n{exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

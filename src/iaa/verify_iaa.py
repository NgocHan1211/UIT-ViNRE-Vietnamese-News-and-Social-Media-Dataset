# -*- coding: utf-8 -*-
"""Final IAA verification for the first 100 labeled rows."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from itertools import combinations
from pathlib import Path
import math

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
LABELED_DIR = REPO_ROOT / "data" / "05_Labeling" / "Labeled"
REPORT_PATH = REPO_ROOT / "verify_iaa.md"
N_ROWS = 100

ANNOTATORS = ["Nhung", "Yen", "Han"]
ANNOTATOR_FILE_HINTS = {
    "Nhung": "Nhung",
    "Yen": "Yen",
    "Han": "Han",
}
LABEL_COL = "annotator_topic_label"


def normalize_label(value):
    if pd.isna(value):
        return None
    value = str(value).strip()
    return value if value else None


def fmt_num(value, digits=4):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    return f"{value:.{digits}f}"


def fmt_pct(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    return f"{value * 100:.1f}%"


def clean_cell(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).replace("\n", " ").replace("|", "\\|")


def md_table(rows, headers):
    if isinstance(rows, pd.DataFrame):
        headers = list(rows.columns)
        rows = rows.to_dict("records")
    if not rows:
        return "_Không có._"
    if isinstance(rows[0], dict):
        body = [[clean_cell(row.get(header, "")) for header in headers] for row in rows]
    else:
        body = [[clean_cell(value) for value in row] for row in rows]
    lines = [
        "| " + " | ".join(clean_cell(header) for header in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(lines)


def find_annotator_files():
    files = {}
    csv_files = sorted(LABELED_DIR.glob("*.csv"))
    for annotator, hint in ANNOTATOR_FILE_HINTS.items():
        matches = [path for path in csv_files if hint.lower() in path.name.lower()]
        if len(matches) != 1:
            raise FileNotFoundError(
                f"Expected exactly one CSV file for {annotator} in {LABELED_DIR}, found {len(matches)}."
            )
        files[annotator] = matches[0]
    return files


def load_first_rows():
    files = find_annotator_files()
    frames = {}
    for annotator, path in files.items():
        df = pd.read_csv(path).head(N_ROWS).copy()
        required = {"record_id", LABEL_COL}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"{path} missing required columns: {sorted(missing)}")
        frames[annotator] = df

    base_ids = frames[ANNOTATORS[0]]["record_id"].tolist()
    order_checks = []
    for annotator in ANNOTATORS[1:]:
        ids = frames[annotator]["record_id"].tolist()
        order_checks.append(
            {
                "comparison": f"{ANNOTATORS[0]} vs {annotator}",
                "same_order": ids == base_ids,
                "same_set": set(ids) == set(base_ids),
            }
        )
        if ids != base_ids:
            raise ValueError(
                f"First {N_ROWS} record_id order differs between {ANNOTATORS[0]} and {annotator}."
            )

    label_df = pd.DataFrame({"record_id": base_ids})
    for annotator in ANNOTATORS:
        label_df[annotator] = frames[annotator][LABEL_COL].map(normalize_label).tolist()
    return files, frames, pd.DataFrame(order_checks), label_df


def cohen_kappa(labels_a, labels_b, label_universe):
    pairs = [(a, b) for a, b in zip(labels_a, labels_b) if a is not None and b is not None]
    n = len(pairs)
    if n == 0:
        return {"n": 0, "observed_agreement": math.nan, "expected_agreement": math.nan, "kappa": math.nan}
    observed = sum(1 for a, b in pairs if a == b) / n
    counts_a = Counter(a for a, _ in pairs)
    counts_b = Counter(b for _, b in pairs)
    expected = sum((counts_a[label] / n) * (counts_b[label] / n) for label in label_universe)
    denom = 1 - expected
    kappa = 1.0 if denom == 0 and observed == 1 else ((observed - expected) / denom if denom else math.nan)
    return {"n": n, "observed_agreement": observed, "expected_agreement": expected, "kappa": kappa}


def fleiss_kappa(label_matrix, label_universe):
    valid = label_matrix.dropna()
    n_items = len(valid)
    n_raters = len(label_matrix.columns)
    if n_items == 0:
        return {"n_items": 0, "n_raters": n_raters, "observed_agreement": math.nan, "expected_agreement": math.nan, "kappa": math.nan}

    row_agreements = []
    label_totals = Counter()
    for row in valid.itertuples(index=False):
        counts = Counter(row)
        label_totals.update(counts)
        row_agreements.append(
            sum(count * (count - 1) for count in counts.values()) / (n_raters * (n_raters - 1))
        )

    observed = sum(row_agreements) / n_items
    total_assignments = n_items * n_raters
    expected = sum((label_totals[label] / total_assignments) ** 2 for label in label_universe)
    denom = 1 - expected
    kappa = 1.0 if denom == 0 and observed == 1 else ((observed - expected) / denom if denom else math.nan)
    return {
        "n_items": n_items,
        "n_raters": n_raters,
        "observed_agreement": observed,
        "expected_agreement": expected,
        "kappa": kappa,
    }


def agreement_type(row):
    values = [value for value in row if value is not None]
    if len(values) < len(ANNOTATORS):
        return "incomplete"
    unique_count = len(set(values))
    if unique_count == 1:
        return "full_agreement"
    if unique_count == 2:
        return "partial_disagreement"
    return "complete_disagreement"


def build_report(files, order_checks, label_df):
    label_matrix = label_df[ANNOTATORS]
    label_universe = sorted({value for col in ANNOTATORS for value in label_matrix[col].dropna().tolist()})
    valid_mask = label_matrix.notna().all(axis=1)
    missing_rows = label_df.loc[~valid_mask, ["record_id"] + ANNOTATORS].copy()
    if not missing_rows.empty:
        missing_rows["missing_annotators"] = missing_rows.apply(
            lambda row: ", ".join(annotator for annotator in ANNOTATORS if row[annotator] is None),
            axis=1,
        )

    fleiss = fleiss_kappa(label_matrix, label_universe)
    fleiss_rows = [
        {
            "n_items": fleiss["n_items"],
            "n_raters": fleiss["n_raters"],
            "observed_agreement": fmt_num(fleiss["observed_agreement"]),
            "expected_agreement": fmt_num(fleiss["expected_agreement"]),
            "fleiss_kappa": fmt_num(fleiss["kappa"]),
        }
    ]

    cohen_rows = []
    for a, b in combinations(ANNOTATORS, 2):
        metric = cohen_kappa(label_matrix[a].tolist(), label_matrix[b].tolist(), label_universe)
        cohen_rows.append(
            {
                "pair": f"{a} vs {b}",
                "n": metric["n"],
                "observed_agreement": fmt_num(metric["observed_agreement"]),
                "expected_agreement": fmt_num(metric["expected_agreement"]),
                "cohen_kappa": fmt_num(metric["kappa"]),
            }
        )

    types = label_matrix.apply(lambda row: agreement_type(row.tolist()), axis=1)
    agreement_counts = (
        types.value_counts()
        .reindex(["full_agreement", "partial_disagreement", "complete_disagreement", "incomplete"], fill_value=0)
        .rename_axis("agreement_type")
        .reset_index(name="rows")
    )
    agreement_counts["pct_all_100_rows"] = agreement_counts["rows"].map(lambda n: fmt_pct(n / len(label_df)))

    file_rows = [
        {
            "annotator": annotator,
            "file": str(path.relative_to(REPO_ROOT)),
            "rows_read": N_ROWS,
            "missing_topic_labels_in_first_100": int(label_df[annotator].isna().sum()),
        }
        for annotator, path in files.items()
    ]

    overview_rows = [
        {
            "scope": f"first_{N_ROWS}_rows",
            "total_rows": len(label_df),
            "valid_rows_for_fleiss": int(valid_mask.sum()),
            "rows_with_missing_label": int((~valid_mask).sum()),
            "labels_seen": len(label_universe),
            "fleiss_kappa": fmt_num(fleiss["kappa"]),
            "mean_cohen_kappa": fmt_num(
                sum(float(row["cohen_kappa"]) for row in cohen_rows if row["cohen_kappa"] != "NA") / len(cohen_rows)
            ),
        }
    ]

    parts = [
        "# Verify IAA Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "## Scope",
        f"Tính IAA trên {N_ROWS} dòng đầu tiên của 3 file trong `data/05_Labeling/Labeled`. Report này chỉ dùng để verify IAA lần cuối, không phân tích sâu và không đưa gợi ý cập nhật guideline.",
        "## Input Files",
        md_table(file_rows, ["annotator", "file", "rows_read", "missing_topic_labels_in_first_100"]),
        "## Record Order Check",
        md_table(order_checks, list(order_checks.columns)),
        "## Overview",
        md_table(overview_rows, list(overview_rows[0].keys())),
        "## Fleiss' Kappa",
        md_table(fleiss_rows, list(fleiss_rows[0].keys())),
        "## Cohen's Kappa",
        md_table(cohen_rows, list(cohen_rows[0].keys())),
        "## Agreement Counts",
        md_table(agreement_counts, list(agreement_counts.columns)),
        "## Missing Label Rows",
        md_table(missing_rows[["record_id", "missing_annotators"]], ["record_id", "missing_annotators"])
        if not missing_rows.empty
        else "_Không có dòng thiếu nhãn._",
    ]
    return "\n\n".join(parts) + "\n"


def main():
    files, _frames, order_checks, label_df = load_first_rows()
    report = build_report(files, order_checks, label_df)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()

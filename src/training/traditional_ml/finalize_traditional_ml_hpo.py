#!/usr/bin/env python3
"""Finalize DS107 traditional ML deep HPO outputs without retraining models."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


BASE_DIR = Path("data/08_Modeling_Results/traditional_ml_hpo_deep")
MODEL_ORDER = ["LogisticRegression", "RandomForest", "XGBoost", "LinearSVC"]
SCENARIO_ORDER = [
    "01_Raw_Data",
    "02_Basic_Clean",
    "03_Full_Clean",
    "04_No_Stopwords",
    "05_Balanced",
]
PROBA_MODELS = {"LogisticRegression", "RandomForest", "XGBoost"}
REQUIRED_METRIC_PREFIXES = [
    "accuracy",
    "macro_precision",
    "macro_recall",
    "macro_f1",
    "weighted_precision",
    "weighted_recall",
    "weighted_f1",
    "micro_precision",
    "micro_recall",
    "micro_f1",
]
FINAL_FULL_COLUMNS = [
    "model_name",
    "scenario",
    "accuracy_val",
    "macro_precision_val",
    "macro_recall_val",
    "macro_f1_val",
    "weighted_precision_val",
    "weighted_recall_val",
    "weighted_f1_val",
    "accuracy_test",
    "macro_precision_test",
    "macro_recall_test",
    "macro_f1_test",
    "weighted_precision_test",
    "weighted_recall_test",
    "weighted_f1_test",
    "selection_note",
]
FINAL_REPORT_COLUMNS = [
    "model_name",
    "best_scenario_by_val_macro_f1",
    "accuracy_val",
    "macro_precision_val",
    "macro_recall_val",
    "macro_f1_val",
    "accuracy_test",
    "macro_precision_test",
    "macro_recall_test",
    "macro_f1_test",
    "weighted_f1_test",
    "best_hyperparameters_summary",
    "notes",
]
NSW_TERMS = [
    "ko",
    "k",
    "khum",
    "hong",
    "hok",
    "nma",
    "j",
    "t",
    "mk",
    "tóp tóp",
    "toptop",
    "tiktok",
    "cđm",
    "cdm",
    "baohanh",
    "tuvong",
    "matuy",
    "b.ỏ",
    "r.ơi",
    "t.ử",
    "v.ong",
    "chấn động",
    "quay xe",
    "bế lên phường",
    "giải cứu",
    "ngầu đét",
    "cảm lạnh",
]
KEYWORD_GROUPS = {
    "politics": ["thủ tướng", "chính phủ", "bộ trưởng", "quốc hội", "chủ tịch nước", "tổng bí thư"],
    "crime": ["công an", "khởi tố", "bắt giữ", "điều tra", "ma túy", "ma tuý", "bạo hành"],
    "entertainment": ["ca sĩ", "diễn viên", "concert", "hoa hậu", "nghệ sĩ", "showbiz"],
    "disaster_accident": ["tai nạn", "cháy", "sạt lở", "mưa lớn", "thiệt mạng"],
    "economy": ["thuế", "giá vàng", "ngân hàng", "doanh nghiệp", "bất động sản"],
    "transport": ["cao tốc", "sân bay", "đường sắt", "xe buýt", "giao thông"],
}
SLANG_TERMS = ["quay xe", "bế lên phường", "giải cứu", "cảm lạnh", "ngầu đét", "chấn động", "sốc", "drama", "phốt"]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def json_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def json_read(path: Path, default: Any | None = None) -> Any:
    if default is None:
        default = {}
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def parse_json(value: Any, default: Any | None = None) -> Any:
    if default is None:
        default = {}
    if isinstance(value, dict):
        return value
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return default


def format_float(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value):
        return ""
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.4f}"
    return str(value)


def markdown_table(
    frame: pd.DataFrame,
    columns: list[str] | None = None,
    bold_rows: set[int] | None = None,
    max_rows: int | None = None,
) -> str:
    if frame.empty:
        return "_Không có dữ liệu._"
    table = frame.copy()
    if columns is not None:
        table = table[[column for column in columns if column in table.columns]]
    if max_rows is not None:
        table = table.head(max_rows)
    bold_rows = bold_rows or set()
    header = "| " + " | ".join(table.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(table.columns)) + " |"
    rows = []
    for index, row in table.iterrows():
        values = []
        for value in row.tolist():
            text = format_float(value)
            text = text.replace("\n", " ").replace("|", "\\|")
            if index in bold_rows:
                text = f"**{text}**"
            values.append(text)
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join([header, separator] + rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sheet_column_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def xlsx_cell_xml(row: int, col: int, value: Any, style: int = 0) -> str:
    ref = f"{sheet_column_name(col)}{row}"
    style_attr = f' s="{style}"' if style else ""
    if value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value):
        return f'<c r="{ref}"{style_attr}/>'
    if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool):
        return f'<c r="{ref}"{style_attr}><v>{float(value)}</v></c>'
    text = html.escape(str(value), quote=True)
    return f'<c r="{ref}" t="inlineStr"{style_attr}><is><t>{text}</t></is></c>'


def write_basic_xlsx(
    path: Path,
    frame: pd.DataFrame,
    sheet_name: str,
    row_styles: dict[int, int] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row_styles = row_styles or {}
    rows_xml = []
    header_cells = [
        xlsx_cell_xml(1, col_index, column, style=1)
        for col_index, column in enumerate(frame.columns, start=1)
    ]
    rows_xml.append(f'<row r="1">{"".join(header_cells)}</row>')
    for data_index, (_, row) in enumerate(frame.iterrows(), start=2):
        style = row_styles.get(data_index - 2, 0)
        cells = [
            xlsx_cell_xml(data_index, col_index, value, style=style)
            for col_index, value in enumerate(row.tolist(), start=1)
        ]
        rows_xml.append(f'<row r="{data_index}">{"".join(cells)}</row>')
    last_col = sheet_column_name(max(1, len(frame.columns)))
    last_row = max(1, len(frame) + 1)
    worksheet = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:{last_col}{last_row}"/>
  <sheetViews><sheetView workbookViewId="0"/></sheetViews>
  <sheetFormatPr defaultRowHeight="15"/>
  <sheetData>
    {''.join(rows_xml)}
  </sheetData>
  <autoFilter ref="A1:{last_col}{last_row}"/>
</worksheet>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><color theme="1"/><name val="Calibri"/><family val="2"/></font>
    <font><b/><sz val="11"/><color theme="1"/><name val="Calibri"/><family val="2"/></font>
  </fonts>
  <fills count="5">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFD9EAD3"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFD9EAF7"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="5">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
    <xf numFmtId="0" fontId="1" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
    <xf numFmtId="0" fontId="1" fillId="4" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
  </cellXfs>
</styleSheet>'''
    workbook = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="{html.escape(sheet_name, quote=True)}" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''
    workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
    root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>'''
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/styles.xml", styles)
        zf.writestr("xl/worksheets/sheet1.xml", worksheet)


def sorted_summary(summary: pd.DataFrame) -> pd.DataFrame:
    frame = summary.copy()
    frame["model_name"] = pd.Categorical(frame["model_name"], categories=MODEL_ORDER, ordered=True)
    frame["scenario"] = pd.Categorical(frame["scenario"], categories=SCENARIO_ORDER, ordered=True)
    return frame.sort_values(["model_name", "scenario"]).reset_index(drop=True)


def validate_inputs(base_dir: Path) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    summary_path = base_dir / "all_model_results_summary.csv"
    diagnostics_path = base_dir / "hpo_tuning_diagnostics.json"
    hyperparams_path = base_dir / "best_hyperparameters_by_model.csv"
    missing = [path for path in [summary_path, diagnostics_path, hyperparams_path] if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing required input files: {missing}")
    summary = pd.read_csv(summary_path)
    diagnostics = json_read(diagnostics_path)
    hyperparams = pd.read_csv(hyperparams_path)

    errors = []
    if len(summary) != 20:
        errors.append(f"all_model_results_summary.csv must have 20 rows, found {len(summary)}")
    if set(summary["model_name"]) != set(MODEL_ORDER):
        errors.append(f"Expected models {MODEL_ORDER}, found {sorted(summary['model_name'].unique())}")
    if set(summary["scenario"]) != set(SCENARIO_ORDER):
        errors.append(f"Expected scenarios {SCENARIO_ORDER}, found {sorted(summary['scenario'].unique())}")
    counts = summary.groupby("model_name")["scenario"].nunique().to_dict()
    for model_name in MODEL_ORDER:
        if counts.get(model_name) != 5:
            errors.append(f"{model_name} must have 5 scenarios, found {counts.get(model_name)}")
    if not summary["status"].eq("success").all():
        errors.append(f"Found failed statuses: {summary['status'].value_counts(dropna=False).to_dict()}")
    xgb = summary.loc[summary["model_name"].eq("XGBoost")]
    if len(xgb) != 5:
        errors.append(f"XGBoost must have 5 rows, found {len(xgb)}")
    for prefix in REQUIRED_METRIC_PREFIXES:
        for suffix in ["val", "test"]:
            column = f"{prefix}_{suffix}"
            if column not in summary.columns:
                errors.append(f"Missing metric column: {column}")
            elif summary[column].isna().any():
                errors.append(f"Metric column has null values: {column}")
    expected_diag = {
        "final_experiments_total": 20,
        "final_experiments_success": 20,
        "final_experiments_failed": 0,
        "xgboost_repaired": True,
    }
    for key, expected in expected_diag.items():
        actual = diagnostics.get(key)
        if actual != expected:
            errors.append(f"Diagnostics {key} expected {expected!r}, found {actual!r}")
    if len(hyperparams) != 20:
        errors.append(f"best_hyperparameters_by_model.csv must have 20 rows, found {len(hyperparams)}")
    if errors:
        raise RuntimeError("Input validation failed:\n- " + "\n- ".join(errors))
    return summary, diagnostics, hyperparams


def choose_best_rows(summary: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame, pd.Series]:
    ranked = summary.sort_values(
        ["macro_f1_val", "weighted_f1_val", "accuracy_val"],
        ascending=[False, False, False],
    )
    best_overall = ranked.iloc[0]
    best_by_model_rows = []
    for model_name in MODEL_ORDER:
        rows = summary.loc[summary["model_name"].eq(model_name)].sort_values(
            ["macro_f1_val", "weighted_f1_val", "accuracy_val"],
            ascending=[False, False, False],
        )
        best_by_model_rows.append(rows.iloc[0])
    best_by_model = pd.DataFrame(best_by_model_rows).reset_index(drop=True)
    best_test = summary.sort_values("macro_f1_test", ascending=False).iloc[0]
    return best_overall, best_by_model, best_test


def summarize_hyperparams(row: pd.Series, hyperparams: pd.DataFrame) -> str:
    match = hyperparams.loc[
        hyperparams["scenario"].eq(row["scenario"]) & hyperparams["model_name"].eq(row["model_name"])
    ]
    if match.empty:
        return ""
    hp = match.iloc[0]
    tfidf = parse_json(hp.get("best_tfidf_params_json"), {})
    model_params = parse_json(hp.get("best_effective_model_params_json"), {})
    tfidf_bits = [
        f"analyzer={tfidf.get('analyzer', 'word')}",
        f"max_features={tfidf.get('max_features')}",
        f"ngram={tuple(tfidf.get('ngram_range', []))}",
        f"min_df={tfidf.get('min_df')}",
    ]
    model_bits = [f"{key}={value}" for key, value in model_params.items()]
    return "TF-IDF(" + ", ".join(tfidf_bits) + "); Model(" + ", ".join(model_bits) + ")"


def create_evaluation_tables(
    base_dir: Path,
    summary: pd.DataFrame,
    hyperparams: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    final_dir = base_dir / "final_tables"
    final_dir.mkdir(parents=True, exist_ok=True)
    best_overall, best_by_model, best_test = choose_best_rows(summary)
    full = sorted_summary(summary)
    full["selection_note"] = ""
    for index, row in full.iterrows():
        notes = []
        if row["scenario"] == best_overall["scenario"] and row["model_name"] == best_overall["model_name"]:
            notes.append("Best overall by validation Macro-F1")
        model_best = best_by_model.loc[best_by_model["model_name"].eq(row["model_name"])].iloc[0]
        if row["scenario"] == model_best["scenario"]:
            notes.append("Best scenario for this model by validation Macro-F1")
        if row["scenario"] == best_test["scenario"] and row["model_name"] == best_test["model_name"]:
            notes.append("Best test Macro-F1 reference only; not used for selection")
        full.at[index, "selection_note"] = "; ".join(notes)
    full = full[FINAL_FULL_COLUMNS]
    full.to_csv(final_dir / "final_evaluation_table_full.csv", index=False)
    full_bold = set(
        full.index[
            full["selection_note"].str.contains("Best overall|Best scenario", regex=True, na=False)
        ].tolist()
    )
    write_text(
        final_dir / "final_evaluation_table_full.md",
        "\n".join(
            [
                "# Final Evaluation Table Full",
                "",
                "Best model is selected by validation Macro-F1. Test metrics are reported only for final evaluation.",
                "",
                markdown_table(full, FINAL_FULL_COLUMNS, bold_rows=full_bold),
                "",
            ]
        ),
    )
    row_styles = {}
    for index, row in full.iterrows():
        note = str(row["selection_note"])
        if "Best overall" in note:
            row_styles[index] = 2
        elif "Best scenario" in note:
            row_styles[index] = 3
        elif "Best test" in note:
            row_styles[index] = 4
    write_basic_xlsx(final_dir / "final_evaluation_table_full.xlsx", full, "Full Evaluation", row_styles)

    report_rows = []
    for _, row in best_by_model.iterrows():
        notes = ["Selected by validation Macro-F1 within model family."]
        if row["scenario"] == best_overall["scenario"] and row["model_name"] == best_overall["model_name"]:
            notes.append("Best overall model.")
        report_rows.append(
            {
                "model_name": row["model_name"],
                "best_scenario_by_val_macro_f1": row["scenario"],
                "accuracy_val": row["accuracy_val"],
                "macro_precision_val": row["macro_precision_val"],
                "macro_recall_val": row["macro_recall_val"],
                "macro_f1_val": row["macro_f1_val"],
                "accuracy_test": row["accuracy_test"],
                "macro_precision_test": row["macro_precision_test"],
                "macro_recall_test": row["macro_recall_test"],
                "macro_f1_test": row["macro_f1_test"],
                "weighted_f1_test": row["weighted_f1_test"],
                "best_hyperparameters_summary": summarize_hyperparams(row, hyperparams),
                "notes": " ".join(notes),
            }
        )
    report = pd.DataFrame(report_rows)
    report["model_name"] = pd.Categorical(report["model_name"], categories=MODEL_ORDER, ordered=True)
    report = report.sort_values("model_name").astype({"model_name": "string"}).reset_index(drop=True)
    report.to_csv(final_dir / "final_evaluation_table_report.csv", index=False)
    report_bold = set(report.index[report["notes"].str.contains("Best overall", na=False)].tolist())
    write_text(
        final_dir / "final_evaluation_table_report.md",
        "\n".join(
            [
                "# Report-Ready Compact Evaluation Table",
                "",
                "Each row is the best scenario of one model family, selected by validation Macro-F1.",
                "",
                markdown_table(report, FINAL_REPORT_COLUMNS, bold_rows=report_bold),
                "",
            ]
        ),
    )
    write_basic_xlsx(final_dir / "final_evaluation_table_report.xlsx", report, "Report Evaluation", {index: 2 for index in report_bold})
    return full, report


def source_experiment_dir(row: pd.Series, base_dir: Path) -> Path:
    model_path = row.get("model_path")
    if isinstance(model_path, str) and model_path:
        return Path(model_path).parent
    return base_dir / str(row["scenario"]) / str(row["model_name"])


def rel_symlink_or_copy(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        destination.unlink()
    try:
        relative_source = os.path.relpath(source, destination.parent)
        destination.symlink_to(relative_source)
        return "symlink"
    except OSError:
        shutil.copy2(source, destination)
        return "copy"


def prediction_example_from_source(source_dir: Path, scenario: str, model_name: str) -> dict[str, Any]:
    predictions_path = source_dir / "predictions_test.csv"
    if predictions_path.exists():
        predictions = pd.read_csv(predictions_path)
        if not predictions.empty:
            row = predictions.iloc[0]
            return {
                "input_text": str(row.get("text", "Một caption ví dụ")),
                "predicted_topic_id": str(row.get("y_pred", "Txx")),
                "predicted_topic_label": str(row.get("y_pred_label_name", row.get("y_pred", "Txx"))),
                "note": "Use vectorizer.transform([text]) before model.predict.",
            }
    return {
        "input_text": "Một caption ví dụ",
        "predicted_topic_id": "Txx",
        "predicted_topic_label": "Txx. ...",
        "note": f"Prediction example placeholder for {scenario}/{model_name}.",
    }


def create_model_zoo(base_dir: Path, summary: pd.DataFrame) -> pd.DataFrame:
    zoo_dir = base_dir / "model_zoo"
    best_overall, best_by_model, _ = choose_best_rows(summary)
    registry_rows = []

    def add_entry(row: pd.Series, group: str, target_dir: Path, recommended: bool) -> None:
        source_dir = source_experiment_dir(row, base_dir)
        modes = []
        for filename in ["model.joblib", "vectorizer.joblib", "label_encoder.joblib"]:
            mode = rel_symlink_or_copy(source_dir / filename, target_dir / filename)
            modes.append(mode)
        metadata = {
            "model_name": row["model_name"],
            "scenario": row["scenario"],
            "selection_rule": (
                "Best scenario within model by validation Macro-F1"
                if group == "best_by_model"
                else "Scenario/model artifact from final deep HPO benchmark"
            ),
            "validation_macro_f1": float(row["macro_f1_val"]),
            "validation_accuracy": float(row["accuracy_val"]),
            "test_macro_f1": float(row["macro_f1_test"]),
            "test_accuracy": float(row["accuracy_test"]),
            "supports_predict_proba": row["model_name"] in PROBA_MODELS,
            "source_artifact_dir": str(source_dir),
            "artifact_reference_mode": modes[0] if len(set(modes)) == 1 else ",".join(modes),
            "notes": "Test metrics are reported only for final evaluation; model selection used validation Macro-F1.",
            "created_at": now_iso(),
        }
        json_write(target_dir / "metadata.json", metadata)
        json_write(target_dir / "predict_example.json", prediction_example_from_source(source_dir, row["scenario"], row["model_name"]))
        registry_rows.append(
            {
                "registry_group": group,
                "display_name": f"{row['model_name']} - {row['scenario']}",
                "model_name": row["model_name"],
                "scenario": row["scenario"],
                "model_path": str(target_dir / "model.joblib"),
                "vectorizer_path": str(target_dir / "vectorizer.joblib"),
                "label_encoder_path": str(target_dir / "label_encoder.joblib"),
                "supports_predict_proba": row["model_name"] in PROBA_MODELS,
                "validation_macro_f1": float(row["macro_f1_val"]),
                "test_macro_f1": float(row["macro_f1_test"]),
                "test_accuracy": float(row["accuracy_test"]),
                "recommended_for_demo": bool(recommended),
                "notes": (
                    "Best overall and recommended for default Streamlit demo."
                    if row["scenario"] == best_overall["scenario"] and row["model_name"] == best_overall["model_name"]
                    else "Recommended model-family demo artifact."
                    if recommended
                    else "Additional scenario/model artifact."
                ),
            }
        )

    for _, row in best_by_model.iterrows():
        add_entry(row, "best_by_model", zoo_dir / "best_by_model" / str(row["model_name"]), True)
    ordered = sorted_summary(summary)
    for _, row in ordered.iterrows():
        add_entry(
            row,
            "by_scenario",
            zoo_dir / "by_scenario" / str(row["scenario"]) / str(row["model_name"]),
            False,
        )
    registry = pd.DataFrame(registry_rows)
    registry.to_csv(zoo_dir / "model_registry.csv", index=False)
    json_write(zoo_dir / "model_registry.json", registry.to_dict(orient="records"))
    readme = [
        "# Traditional ML Model Zoo",
        "",
        "Folder này gom artifacts để Streamlit có thể load nhiều model sau deep HPO finalization.",
        "",
        "## Groups",
        "",
        "- `best_by_model/`: 4 model, mỗi model là scenario tốt nhất theo validation Macro-F1 trong model family.",
        "- `by_scenario/`: đủ 5 scenarios x 4 models.",
        "",
        "Các file `model.joblib`, `vectorizer.joblib`, `label_encoder.joblib` được tạo bằng symlink tương đối tới artifact gốc để tránh nhân đôi dung lượng. Nếu hệ thống không hỗ trợ symlink, script fallback sang copy.",
        "",
        "Registry chính:",
        "",
        "- `model_registry.csv`",
        "- `model_registry.json`",
        "",
        "Streamlit nên đọc registry, chọn row `recommended_for_demo=true` cho demo nhanh hoặc cho phép user chọn mọi row trong `by_scenario`.",
        "",
    ]
    write_text(zoo_dir / "README.md", "\n".join(readme))
    return registry


def load_predictions(base_dir: Path, scenario: str, model_name: str, split: str) -> pd.DataFrame:
    path = base_dir / scenario / model_name / f"predictions_{split}.csv"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    frame["scenario"] = scenario
    frame["model_name"] = model_name
    frame["split"] = split
    return frame


def word_count(text: Any) -> int:
    return len(str(text).split())


def text_bucket(count: int) -> str:
    if count < 10:
        return "short"
    if count <= 50:
        return "medium"
    return "long"


def count_terms(text: Any, terms: list[str]) -> tuple[int, list[str]]:
    lowered = str(text).lower()
    found = [term for term in terms if term.lower() in lowered]
    return len(found), found


def matched_keyword_groups(text: Any) -> list[str]:
    lowered = str(text).lower()
    groups = []
    for group, terms in KEYWORD_GROUPS.items():
        if any(term in lowered for term in terms):
            groups.append(group)
    return groups


def reason_guess(text: Any, matched_slang: list[str], keyword_groups: list[str]) -> str:
    wc = word_count(text)
    if wc < 10:
        return "caption too short"
    if matched_slang:
        return "slang/metaphor"
    if len(keyword_groups) >= 2:
        return "multi-topic or keyword boundary ambiguity"
    if wc > 50:
        return "long/noisy caption"
    return "keyword overfitting or label boundary ambiguity"


def confusion_pairs_from_matrix(path: Path, model_name: str, scenario: str) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["gold_label", "predicted_label", "count", "model_name", "scenario"])
    matrix = pd.read_csv(path, index_col=0)
    rows = []
    for gold in matrix.index:
        for pred in matrix.columns:
            if gold == pred:
                continue
            count = int(matrix.loc[gold, pred])
            if count:
                rows.append(
                    {
                        "gold_label": gold,
                        "predicted_label": pred,
                        "count": count,
                        "model_name": model_name,
                        "scenario": scenario,
                    }
                )
    return pd.DataFrame(rows).sort_values("count", ascending=False) if rows else pd.DataFrame(rows)


def plot_simple_bar(frame: pd.DataFrame, path: Path, x: str, y: str, title: str, hue: str | None = None) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return plot_simple_bar_pillow(frame, path, x, y, title, hue)
    if frame.empty or x not in frame or y not in frame:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(10, 5))
    if hue and hue in frame:
        labels = sorted(frame[hue].astype(str).unique())
        x_values = list(frame[x].astype(str).unique())
        positions = np.arange(len(x_values))
        width = 0.8 / max(1, len(labels))
        for offset, label in enumerate(labels):
            subset = frame.loc[frame[hue].astype(str).eq(label)]
            values = []
            for x_value in x_values:
                match = subset.loc[subset[x].astype(str).eq(x_value)]
                values.append(float(match[y].iloc[0]) if not match.empty else 0.0)
            plt.bar(positions + offset * width, values, width=width, label=label)
        plt.xticks(positions + width * (len(labels) - 1) / 2, x_values, rotation=30, ha="right")
        plt.legend(fontsize=8)
    else:
        plt.bar(frame[x].astype(str), frame[y].astype(float))
        plt.xticks(rotation=30, ha="right")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()
    return True


def plot_simple_bar_pillow(
    frame: pd.DataFrame,
    path: Path,
    x: str,
    y: str,
    title: str,
    hue: str | None = None,
) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return False
    if frame.empty or x not in frame or y not in frame:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1200, 700
    margin_left, margin_right, margin_top, margin_bottom = 110, 40, 80, 150
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    colors = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2", "#B279A2"]
    draw.text((margin_left, 25), title, fill="black", font=font)
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    draw.line((margin_left, margin_top, margin_left, margin_top + plot_h), fill="black")
    draw.line((margin_left, margin_top + plot_h, margin_left + plot_w, margin_top + plot_h), fill="black")
    max_value = float(pd.to_numeric(frame[y], errors="coerce").max() or 1.0)
    max_value = max(max_value, 1e-9)
    x_values = list(dict.fromkeys(frame[x].astype(str).tolist()))
    labels = list(dict.fromkeys(frame[hue].astype(str).tolist())) if hue and hue in frame else [None]
    group_width = plot_w / max(1, len(x_values))
    bar_width = max(8, int(group_width * 0.75 / max(1, len(labels))))
    for x_index, x_value in enumerate(x_values):
        group_x = margin_left + x_index * group_width + group_width * 0.12
        for hue_index, label in enumerate(labels):
            subset = frame.loc[frame[x].astype(str).eq(x_value)]
            if label is not None:
                subset = subset.loc[subset[hue].astype(str).eq(label)]
            value = float(pd.to_numeric(subset[y], errors="coerce").mean()) if not subset.empty else 0.0
            bar_h = int((value / max_value) * (plot_h - 20))
            x0 = int(group_x + hue_index * bar_width)
            y0 = margin_top + plot_h - bar_h
            x1 = x0 + bar_width - 2
            y1 = margin_top + plot_h
            draw.rectangle((x0, y0, x1, y1), fill=colors[hue_index % len(colors)])
        draw.text((int(group_x), margin_top + plot_h + 8), x_value[:18], fill="black", font=font)
    for tick in range(6):
        value = max_value * tick / 5
        y_pos = margin_top + plot_h - int((value / max_value) * (plot_h - 20))
        draw.line((margin_left - 5, y_pos, margin_left, y_pos), fill="black")
        draw.text((10, y_pos - 6), f"{value:.2f}", fill="black", font=font)
    if labels != [None]:
        legend_x = margin_left + plot_w - 220
        legend_y = margin_top
        for index, label in enumerate(labels):
            y_pos = legend_y + index * 18
            draw.rectangle((legend_x, y_pos, legend_x + 12, y_pos + 12), fill=colors[index % len(colors)])
            draw.text((legend_x + 18, y_pos), str(label)[:30], fill="black", font=font)
    image.save(path)
    return True


def plot_confusion_matrices(matrix_specs: list[tuple[Path, str]], output_path: Path, title: str) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return plot_confusion_matrices_pillow(matrix_specs, output_path, title)
    specs = [(path, label) for path, label in matrix_specs if path.exists()]
    if not specs:
        return False
    n = len(specs)
    cols = 2 if n > 1 else 1
    rows = int(math.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(7 * cols, 6 * rows))
    axes_arr = np.atleast_1d(axes).reshape(rows, cols)
    for axis in axes_arr.ravel():
        axis.axis("off")
    for axis, (path, label) in zip(axes_arr.ravel(), specs):
        matrix = pd.read_csv(path, index_col=0)
        values = matrix.to_numpy(dtype=float)
        row_sums = values.sum(axis=1, keepdims=True)
        normalized = np.divide(values, row_sums, out=np.zeros_like(values), where=row_sums != 0)
        image = axis.imshow(normalized, cmap="Blues", vmin=0, vmax=1)
        axis.set_title(label)
        axis.set_xticks(range(len(matrix.columns)))
        axis.set_xticklabels(matrix.columns, rotation=90, fontsize=7)
        axis.set_yticks(range(len(matrix.index)))
        axis.set_yticklabels(matrix.index, fontsize=7)
        axis.set_xlabel("Predicted")
        axis.set_ylabel("True")
        fig.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    fig.suptitle(title)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200)
    plt.close()
    return True


def blue_gradient(value: float) -> tuple[int, int, int]:
    value = max(0.0, min(1.0, float(value)))
    r = int(247 - 220 * value)
    g = int(251 - 130 * value)
    b = int(255 - 20 * value)
    return r, g, b


def plot_confusion_matrices_pillow(
    matrix_specs: list[tuple[Path, str]],
    output_path: Path,
    title: str,
) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return False
    specs = [(path, label) for path, label in matrix_specs if path.exists()]
    if not specs:
        return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cell = 22
    label_space = 70
    panel_w = label_space + cell * 17 + 30
    panel_h = 95 + cell * 17 + 40
    cols = 2 if len(specs) > 1 else 1
    rows = int(math.ceil(len(specs) / cols))
    image = Image.new("RGB", (panel_w * cols, panel_h * rows + 40), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((20, 15), title, fill="black", font=font)
    for spec_index, (path, label) in enumerate(specs):
        matrix = pd.read_csv(path, index_col=0)
        values = matrix.to_numpy(dtype=float)
        row_sums = values.sum(axis=1, keepdims=True)
        normalized = np.divide(values, row_sums, out=np.zeros_like(values), where=row_sums != 0)
        col = spec_index % cols
        row = spec_index // cols
        x_origin = col * panel_w + label_space
        y_origin = row * panel_h + 80
        draw.text((col * panel_w + 20, row * panel_h + 50), label, fill="black", font=font)
        for i, gold in enumerate(matrix.index):
            draw.text((col * panel_w + 20, y_origin + i * cell + 6), str(gold), fill="black", font=font)
        for j, pred in enumerate(matrix.columns):
            draw.text((x_origin + j * cell + 3, y_origin - 18), str(pred), fill="black", font=font)
        for i in range(min(17, normalized.shape[0])):
            for j in range(min(17, normalized.shape[1])):
                x0 = x_origin + j * cell
                y0 = y_origin + i * cell
                draw.rectangle(
                    (x0, y0, x0 + cell - 1, y0 + cell - 1),
                    fill=blue_gradient(normalized[i, j]),
                    outline=(220, 220, 220),
                )
    image.save(output_path)
    return True


def create_error_analysis(base_dir: Path, summary: pd.DataFrame) -> None:
    error_dir = base_dir / "error_analysis"
    error_dir.mkdir(parents=True, exist_ok=True)
    best_overall, best_by_model, _ = choose_best_rows(summary)
    best_pairs = [(row["scenario"], row["model_name"]) for _, row in best_by_model.iterrows()]

    prediction_frames = []
    for scenario, model_name in best_pairs:
        for split in ["val", "test"]:
            frame = load_predictions(base_dir, scenario, model_name, split)
            if not frame.empty:
                prediction_frames.append(frame)
    predictions = pd.concat(prediction_frames, ignore_index=True) if prediction_frames else pd.DataFrame()

    if predictions.empty:
        for filename in [
            "error_by_text_length.csv",
            "nsw_density_correct_vs_wrong.csv",
            "keyword_error_analysis.csv",
            "slang_metaphor_error_cases.csv",
            "qualitative_error_examples.csv",
            "per_model_error_overview.csv",
            "top_confused_pairs.csv",
        ]:
            pd.DataFrame({"status": ["insufficient data"]}).to_csv(error_dir / filename, index=False)
        write_text(error_dir / "error_analysis_summary.md", "# Error Analysis Summary\n\nInsufficient prediction data.")
        return

    predictions["word_count"] = predictions["text"].map(word_count)
    predictions["length_bucket"] = predictions["word_count"].map(text_bucket)
    predictions["correct_bool"] = predictions["correct"].astype(str).str.lower().isin(["true", "1"])
    length_rows = []
    for keys, group in predictions.groupby(["split", "model_name", "scenario", "length_bucket"]):
        split, model_name, scenario, bucket = keys
        total = len(group)
        wrong = int((~group["correct_bool"]).sum())
        length_rows.append(
            {
                "split": split,
                "model_name": model_name,
                "scenario": scenario,
                "length_bucket": bucket,
                "total_samples": total,
                "wrong_predictions": wrong,
                "error_rate": wrong / total if total else np.nan,
            }
        )
    error_by_length = pd.DataFrame(length_rows)
    error_by_length.to_csv(error_dir / "error_by_text_length.csv", index=False)
    plot_simple_bar(
        error_by_length.loc[error_by_length["split"].eq("val")],
        error_dir / "error_by_text_length.png",
        "length_bucket",
        "error_rate",
        "Validation Error Rate by Text Length",
        "model_name",
    )

    nsw_counts = predictions["text"].map(lambda text: count_terms(text, NSW_TERMS))
    predictions["nsw_count"] = [item[0] for item in nsw_counts]
    predictions["matched_nsw_terms"] = [", ".join(item[1]) for item in nsw_counts]
    predictions["nsw_density"] = predictions["nsw_count"] / predictions["word_count"].replace(0, np.nan)
    nsw_summary = (
        predictions.groupby(["split", "model_name", "scenario", "correct_bool"], dropna=False)
        .agg(mean_nsw_density=("nsw_density", "mean"), mean_nsw_count=("nsw_count", "mean"), n_samples=("record_id", "count"))
        .reset_index()
    )
    nsw_summary.to_csv(error_dir / "nsw_density_correct_vs_wrong.csv", index=False)
    plot_simple_bar(
        nsw_summary.loc[nsw_summary["split"].eq("val")],
        error_dir / "nsw_density_correct_vs_wrong.png",
        "correct_bool",
        "mean_nsw_density",
        "Validation NSW Density: Correct vs Wrong",
        "model_name",
    )

    wrong_predictions = predictions.loc[~predictions["correct_bool"]].copy()
    keyword_rows = []
    slang_rows = []
    qualitative_rows = []
    for _, row in wrong_predictions.iterrows():
        groups = matched_keyword_groups(row["text"])
        slang_count, slang_terms = count_terms(row["text"], SLANG_TERMS)
        for group in groups:
            keyword_rows.append(
                {
                    "keyword_group": group,
                    "gold_label": row["y_true"],
                    "predicted_label": row["y_pred"],
                    "model_name": row["model_name"],
                    "scenario": row["scenario"],
                    "split": row["split"],
                    "count": 1,
                }
            )
        if slang_terms:
            slang_rows.append(
                {
                    "record_id": row["record_id"],
                    "text": row["text"],
                    "y_true": row["y_true"],
                    "y_pred": row["y_pred"],
                    "model_name": row["model_name"],
                    "scenario": row["scenario"],
                    "split": row["split"],
                    "matched_slang_terms": ", ".join(slang_terms),
                }
            )
        qualitative_rows.append(
            {
                "record_id": row["record_id"],
                "text": row["text"],
                "gold_label": row["y_true"],
                "predicted_label": row["y_pred"],
                "model_name": row["model_name"],
                "scenario": row["scenario"],
                "split": row["split"],
                "reason_guess": reason_guess(row["text"], slang_terms, groups),
            }
        )
    keyword_frame = pd.DataFrame(keyword_rows)
    if not keyword_frame.empty:
        keyword_frame = (
            keyword_frame.groupby(["keyword_group", "gold_label", "predicted_label", "model_name", "scenario", "split"])
            .agg(count=("count", "sum"))
            .reset_index()
            .sort_values("count", ascending=False)
        )
    keyword_frame.to_csv(error_dir / "keyword_error_analysis.csv", index=False)
    pd.DataFrame(slang_rows).to_csv(error_dir / "slang_metaphor_error_cases.csv", index=False)
    pd.DataFrame(qualitative_rows).head(10).to_csv(error_dir / "qualitative_error_examples.csv", index=False)

    overview_rows = []
    for _, row in best_by_model.iterrows():
        frame = load_predictions(base_dir, row["scenario"], row["model_name"], "test")
        total = len(frame)
        correct = frame["correct"].astype(str).str.lower().isin(["true", "1"]).sum() if total else 0
        overview_rows.append(
            {
                "model_name": row["model_name"],
                "scenario": row["scenario"],
                "test_samples": total,
                "test_wrong_predictions": int(total - correct),
                "test_error_rate": (total - correct) / total if total else np.nan,
                "validation_macro_f1": row["macro_f1_val"],
                "test_macro_f1": row["macro_f1_test"],
                "test_accuracy": row["accuracy_test"],
            }
        )
    overview = pd.DataFrame(overview_rows)
    overview.to_csv(error_dir / "per_model_error_overview.csv", index=False)

    confusion_frames = []
    for _, row in best_by_model.iterrows():
        confusion_frames.append(
            confusion_pairs_from_matrix(
                base_dir / row["scenario"] / row["model_name"] / "confusion_matrix_test.csv",
                row["model_name"],
                row["scenario"],
            )
        )
    top_confused = pd.concat(confusion_frames, ignore_index=True) if confusion_frames else pd.DataFrame()
    if not top_confused.empty:
        top_confused = top_confused.sort_values("count", ascending=False)
    top_confused.to_csv(error_dir / "top_confused_pairs.csv", index=False)

    plot_confusion_matrices(
        [
            (
                base_dir / best_overall["scenario"] / best_overall["model_name"] / "confusion_matrix_test.csv",
                f"{best_overall['model_name']} / {best_overall['scenario']}",
            )
        ],
        error_dir / "confusion_matrix_best_overall.png",
        "Best Overall Normalized Confusion Matrix",
    )
    plot_confusion_matrices(
        [
            (
                base_dir / row["scenario"] / row["model_name"] / "confusion_matrix_test.csv",
                f"{row['model_name']} / {row['scenario']}",
            )
            for _, row in best_by_model.iterrows()
        ],
        error_dir / "confusion_matrix_best_by_model.png",
        "Best By Model Normalized Confusion Matrices",
    )

    top_nsw_terms = {}
    for terms in wrong_predictions.get("matched_nsw_terms", pd.Series(dtype=str)).dropna():
        for term in [item.strip() for item in str(terms).split(",") if item.strip()]:
            top_nsw_terms[term] = top_nsw_terms.get(term, 0) + 1
    top_nsw_text = ", ".join(
        f"{term} ({count})" for term, count in sorted(top_nsw_terms.items(), key=lambda item: item[1], reverse=True)[:10]
    ) or "Không có NSW/slang term nổi bật trong wrong predictions đã phân tích."
    summary_lines = [
        "# Error Analysis Summary",
        "",
        "Phân tích này dùng predictions đã lưu sau deep HPO repair, không train lại model.",
        "",
        "## Scope",
        "",
        f"- Best overall: `{best_overall['scenario']} / {best_overall['model_name']}`.",
        "- Best-by-model models: " + ", ".join(f"`{row['model_name']} / {row['scenario']}`" for _, row in best_by_model.iterrows()) + ".",
        "- Split chính cho error buckets: validation; test được dùng để đối chiếu final performance.",
        "",
        "## Per Model Error Overview",
        "",
        markdown_table(overview),
        "",
        "## Text Length",
        "",
        markdown_table(error_by_length.loc[error_by_length["split"].eq("val")].head(20)),
        "",
        "## NSW / Teencode Density",
        "",
        markdown_table(nsw_summary.loc[nsw_summary["split"].eq("val")].head(20)),
        "",
        f"Top NSW terms trong wrong predictions: {top_nsw_text}.",
        "",
        "## Top Confused Pairs",
        "",
        markdown_table(top_confused.head(15)),
        "",
        "## Qualitative Examples",
        "",
        markdown_table(pd.DataFrame(qualitative_rows).head(10), ["record_id", "gold_label", "predicted_label", "model_name", "scenario", "reason_guess", "text"]),
        "",
    ]
    write_text(error_dir / "error_analysis_summary.md", "\n".join(summary_lines))


def write_error_analysis_notebook(notebook_path: Path) -> None:
    notebook_path.parent.mkdir(parents=True, exist_ok=True)
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Traditional ML Error Analysis\n",
                "\n",
                "Notebook này không train lại model. Các artifact phân tích đã được tạo bởi `src/finalize_traditional_ml_hpo.py` từ output sau XGBoost repair.\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from pathlib import Path\n",
                "import pandas as pd\n",
                "BASE = Path('data/08_Modeling_Results/traditional_ml_hpo_deep')\n",
                "summary = pd.read_csv(BASE / 'all_model_results_summary.csv')\n",
                "summary.head()\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## Load Final Artifacts\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "error_dir = BASE / 'error_analysis'\n",
                "files = sorted(p.name for p in error_dir.glob('*'))\n",
                "files\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## Model Comparison\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "cols = ['scenario','model_name','macro_f1_val','accuracy_val','weighted_f1_val','macro_f1_test','accuracy_test','weighted_f1_test']\n",
                "summary[cols].sort_values('macro_f1_val', ascending=False)\n",
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## Error Analysis Tables\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "for name in ['per_model_error_overview.csv', 'error_by_text_length.csv', 'nsw_density_correct_vs_wrong.csv', 'top_confused_pairs.csv', 'keyword_error_analysis.csv', 'slang_metaphor_error_cases.csv', 'qualitative_error_examples.csv']:\n",
                "    path = error_dir / name\n",
                "    print('\\n###', name)\n",
                "    display(pd.read_csv(path).head(10))\n",
            ],
        },
    ]
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    json_write(notebook_path, notebook)


def file_manifest(base_dir: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(base_dir.rglob("*")):
        if path.is_dir():
            kind = "dir"
            size = 0
        else:
            kind = "file"
            size = path.stat().st_size
        rows.append(
            {
                "path": str(path.relative_to(base_dir)),
                "kind": kind,
                "size_bytes": size,
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
            }
        )
    return pd.DataFrame(rows)


def cleanup_safe(base_dir: Path) -> list[str]:
    before = file_manifest(base_dir)
    before.to_csv(base_dir / "cleanup_manifest_before.csv", index=False)
    delete_candidates = [path for path in base_dir.rglob(".DS_Store")]
    plan_lines = [
        "# Cleanup Delete Plan",
        "",
        "Chỉ xoá file cache/tạm an toàn. Không xoá model artifacts, HPO tables, reports, plots, backup hoặc scenario folders.",
        "",
        "## Files selected for deletion",
        "",
    ]
    if delete_candidates:
        plan_lines.extend(f"- `{path.relative_to(base_dir)}`" for path in delete_candidates)
    else:
        plan_lines.append("- Không có file cache/tạm cần xoá.")
    write_text(base_dir / "cleanup_delete_plan.md", "\n".join(plan_lines))

    deleted = []
    for path in delete_candidates:
        path.unlink()
        deleted.append(str(path.relative_to(base_dir)))

    manual_review = [
        "# Cleanup Candidates Manual Review",
        "",
        "- `backup_before_xgboost_repair/`: giữ lại để audit vì đây là snapshot trước repair XGBoost. Không xoá tự động.",
        "- Base reports cũ (`hyperparameter_reasoning_report.md`, `traditional_ml_technical_report.md`) được giữ lại; bản final nằm trong `reports/`.",
        "- `hyperparameter_search_results.csv` và `hpo_all_trials.csv` cùng tồn tại để tương thích tên file cũ/mới; không xoá tự động.",
        "",
    ]
    write_text(base_dir / "cleanup_candidates_manual_review.md", "\n".join(manual_review))
    after = file_manifest(base_dir)
    after.to_csv(base_dir / "cleanup_manifest_after.csv", index=False)
    report = [
        "# Cleanup Report",
        "",
        f"- Created at: {now_iso()}",
        f"- Deleted files: {len(deleted)}",
        "",
    ]
    if deleted:
        report.extend(f"- `{item}`" for item in deleted)
    else:
        report.append("- Không xoá file nào.")
    report.extend(["", "Backup trước repair được giữ nguyên để audit.", ""])
    write_text(base_dir / "cleanup_report.md", "\n".join(report))
    return deleted


def write_folder_explanation(base_dir: Path) -> None:
    lines = [
        "# Traditional ML Deep HPO Folder Structure",
        "",
        "`data/08_Modeling_Results/traditional_ml_hpo_deep` là output chính sau deep HPO và XGBoost final repair.",
        "",
        "## Root Files",
        "",
        "- `all_model_results_summary.csv`: bảng metric validation/test của 20 final experiments, dùng để chọn best theo validation Macro-F1.",
        "- `best_hyperparameters_by_model.csv`: best hyperparameters đã chọn cho từng scenario/model bằng validation set.",
        "- `hpo_all_trials.csv` / `hyperparameter_search_results.csv`: toàn bộ 605 HPO trials, chỉ có validation metrics.",
        "- `hpo_all_trials_ranked.csv`: trial table đã rank theo validation Macro-F1, Weighted-F1, Accuracy và train time.",
        "- `hpo_tuning_diagnostics.json`: diagnostics của deep HPO và repair status, gồm final_experiments_success/failed.",
        "- `validation_test_gap_analysis.csv`: so sánh validation vs test metrics, dùng để phát hiện gap lớn.",
        "- `best_model_summary.json`: metadata của best benchmark model theo validation Macro-F1.",
        "",
        "## Main Folders",
        "",
        "- `reports/`: bản Markdown final để đưa vào báo cáo/slide/Word.",
        "- `final_tables/`: bảng evaluation full 20 rows và compact 4 rows ở CSV/MD/XLSX.",
        "- `error_analysis/`: bảng và hình phân tích lỗi, không train lại model.",
        "- `model_zoo/`: registry và artifacts để Streamlit demo nhiều model.",
        "- `hpo_plots/`: validation curves và HPO comparison plots.",
        "- `best_model/`: benchmark model tốt nhất, train trên train, chọn theo validation, test một lần để report.",
        "- `best_model_refit_train_val/`: deployment model refit trên train+val bằng best hyperparameters; dùng cho demo, không dùng để chọn model.",
        "- `backup_before_xgboost_repair/`: snapshot report/summary trước repair XGBoost, giữ để audit.",
        "",
        "## Scenario/Model Folders",
        "",
        "Mỗi folder `<scenario>/<model>/` chứa `model.joblib`, `vectorizer.joblib`, `label_encoder.joblib`, metrics JSON, classification reports, confusion matrices, predictions và wrong predictions.",
        "",
        "## Test Discipline",
        "",
        "Validation set được dùng để chọn hyperparameters và best model. Test set chỉ dùng để báo cáo final performance.",
        "",
    ]
    write_text(base_dir / "folder_structure_explanation.md", "\n".join(lines))
    write_text(base_dir / "README.md", "\n".join(lines))
    write_text(base_dir / "reports" / "folder_structure_explanation.md", "\n".join(lines))


def write_reports(
    base_dir: Path,
    summary: pd.DataFrame,
    diagnostics: dict[str, Any],
    hyperparams: pd.DataFrame,
    full_table: pd.DataFrame,
    report_table: pd.DataFrame,
) -> None:
    reports_dir = base_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    best_overall, best_by_model, best_test = choose_best_rows(summary)
    gap_path = base_dir / "validation_test_gap_analysis.csv"
    gap_frame = pd.read_csv(gap_path) if gap_path.exists() else pd.DataFrame()
    error_summary_path = base_dir / "error_analysis" / "error_analysis_summary.md"
    error_summary = error_summary_path.read_text(encoding="utf-8") if error_summary_path.exists() else "Chưa có error analysis summary."

    traditional = [
        "# Traditional ML Technical Report Final",
        "",
        "## Dataset/Split Validation",
        "",
        "Pipeline sử dụng 5 preprocessing scenarios và split train/val/test đã chia sẵn. Validation kiểm tra T18, label T01-T17, duplicate/overlap record_id và consistency test ids giữa scenarios.",
        "",
        f"- Final experiments total: {diagnostics.get('final_experiments_total')}.",
        f"- Final experiments success: {diagnostics.get('final_experiments_success')}.",
        f"- Final experiments failed: {diagnostics.get('final_experiments_failed')}.",
        "",
        "## 5 Preprocessing Scenarios",
        "",
        ", ".join(f"`{scenario}`" for scenario in SCENARIO_ORDER),
        "",
        "## 4 Model Families",
        "",
        ", ".join(f"`{model}`" for model in MODEL_ORDER),
        "",
        "## Deep HPO Setup",
        "",
        "- TF-IDF word/char search space tùy model.",
        "- Hold-out validation based HPO.",
        "- Primary metric: validation Macro-F1.",
        "- Tie-breakers: validation Weighted-F1, validation Accuracy, model simplicity nếu Macro-F1 gần nhau.",
        "- Test set không dùng để chọn hyperparameters.",
        "",
        "## XGBoost Repair Note",
        "",
        "XGBoost final fit ban đầu lỗi do `early_stopping_rounds` cần `eval_set`. Repair chỉ refit final XGBoost bằng best hyperparameters đã có từ HPO, không chạy lại 605 trials và không dùng test set để chọn tham số.",
        "",
        "## Full Evaluation Result",
        "",
        markdown_table(full_table, FINAL_FULL_COLUMNS),
        "",
        "## Compact Report-Ready Result",
        "",
        markdown_table(report_table, FINAL_REPORT_COLUMNS),
        "",
        "## Best Model Selection",
        "",
        f"Best overall theo validation Macro-F1 là `{best_overall['scenario']} / {best_overall['model_name']}` với validation Macro-F1 `{best_overall['macro_f1_val']:.4f}`, test Macro-F1 `{best_overall['macro_f1_test']:.4f}`, test Accuracy `{best_overall['accuracy_test']:.4f}`.",
        "",
        f"Best test Macro-F1 reference là `{best_test['scenario']} / {best_test['model_name']}` với test Macro-F1 `{best_test['macro_f1_test']:.4f}`. Không chọn theo test.",
        "",
        "## Validation-Test Gap",
        "",
        markdown_table(gap_frame.head(20)),
        "",
        "## Error Analysis Summary",
        "",
        error_summary,
        "",
        "## Streamlit Model Zoo Note",
        "",
        "Dùng `model_zoo/model_registry.json` hoặc `.csv` để load 4 model recommended hoặc toàn bộ 20 scenario/model artifacts. Các artifact trong model_zoo là symlink/copy tới model gốc.",
        "",
        "## Limitations",
        "",
        "- TF-IDF phụ thuộc surface words.",
        "- Tree-based models kém hơn mô hình tuyến tính trên sparse high-dimensional text features.",
        "- Macro-F1 quan trọng do imbalance.",
        "- Kết quả phụ thuộc split đã chia sẵn.",
        "",
    ]
    write_text(reports_dir / "traditional_ml_technical_report_final.md", "\n".join(traditional))

    hp_rows = []
    for model_name in MODEL_ORDER:
        row = report_table.loc[report_table["model_name"].astype(str).eq(model_name)].iloc[0]
        hp_rows.append(
            {
                "model_name": model_name,
                "best_scenario": row["best_scenario_by_val_macro_f1"],
                "validation_macro_f1": row["macro_f1_val"],
                "test_macro_f1": row["macro_f1_test"],
                "best_hyperparameters_summary": row["best_hyperparameters_summary"],
            }
        )
    hp_best_table = pd.DataFrame(hp_rows)
    reasoning = [
        "# Hyperparameter Reasoning Report Final",
        "",
        "## 1. Mục tiêu tuning",
        "",
        "Tối ưu baseline traditional ML cho bài toán phân loại 17 chủ đề bài đăng Facebook, ưu tiên Macro-F1 vì dữ liệu mất cân bằng.",
        "",
        "## 2. Vì sao không dùng elbow method như K-Means",
        "",
        "Đây là supervised classification, không phải clustering. Không có elbow method chuẩn để chọn tham số; thay vào đó dùng validation set để đo chất lượng từng cấu hình.",
        "",
        "## 3. Phương pháp hold-out validation + validation curve",
        "",
        "Mỗi trial fit TF-IDF và model trên train, đánh giá trên validation. Test chỉ dùng sau khi chọn best config. Validation curves và parameter effect summary dùng để giải thích xu hướng tham số.",
        "",
        "## 4. Search space TF-IDF",
        "",
        "Word TF-IDF thử max_features, ngram_range, min_df, max_df, sublinear_tf. LogisticRegression và LinearSVC có thêm char_wb TF-IDF để xử lý teencode, viết tắt, viết dính và từ né bộ lọc.",
        "",
        "## 5. Search space từng model",
        "",
        "1. LogisticRegression: C, solver, class_weight; deep ưu tiên lbfgs.",
        "2. RandomForest: n_estimators, max_depth, max_features, min_samples_leaf.",
        "3. XGBoost: n_estimators, max_depth, learning_rate, subsample, colsample_bytree, reg_lambda, reg_alpha.",
        "4. LinearSVC: C, class_weight.",
        "",
        "## 6. Quá trình tuning theo model",
        "",
        "Deep HPO thử 605 successful validation trials. Candidate sampling dùng random_state=42 khi search space vượt cap để chạy được local.",
        "",
        "## 7. Nhận xét kết quả theo model",
        "",
        "- LogisticRegression là best overall và ổn định nhất.",
        "- LinearSVC rất gần LogisticRegression ở một số scenario.",
        "- RandomForest thấp hơn nhóm tuyến tính vì sparse TF-IDF không phù hợp với tree ensemble truyền thống.",
        "- XGBoost sau repair chạy đủ final experiments nhưng validation Macro-F1 vẫn thấp hơn nhóm tuyến tính.",
        "",
        "## 8. Best hyperparameters theo model",
        "",
        markdown_table(hp_best_table),
        "",
        "## 9. XGBoost final repair",
        "",
        "Repair chỉ xử lý final fit. HPO trials của XGBoost đã thành công trước đó và được reuse; benchmark final fit dùng validation set cho early stopping, deployment refit train+val không dùng early stopping vì không có validation riêng.",
        "",
        "## 10. Discussion / Limitation / Future work",
        "",
        "Traditional ML + TF-IDF là baseline mạnh, dễ giải thích và nhanh. Hướng tiếp theo là so sánh với PhoBERT/transformer, calibration probability, và phân tích sâu các label boundary ambiguity.",
        "",
    ]
    write_text(reports_dir / "hyperparameter_reasoning_report_final.md", "\n".join(reasoning))

    summary_report = [
        "# Modeling Results Summary Final",
        "",
        f"- Best overall: `{best_overall['scenario']} / {best_overall['model_name']}`.",
        f"- Validation Macro-F1: `{best_overall['macro_f1_val']:.4f}`.",
        f"- Test Macro-F1: `{best_overall['macro_f1_test']:.4f}`.",
        f"- Test Accuracy: `{best_overall['accuracy_test']:.4f}`.",
        "- Selection rule: validation Macro-F1. Test metrics are reference-only final evaluation.",
        "",
        "## Compact Table",
        "",
        markdown_table(report_table, FINAL_REPORT_COLUMNS),
        "",
        "## Full Table",
        "",
        markdown_table(full_table, FINAL_FULL_COLUMNS),
        "",
    ]
    write_text(reports_dir / "modeling_results_summary_final.md", "\n".join(summary_report))

    source = [
        "# Hyperparameter Optimization Report for Traditional ML Models",
        "",
        "## 1. Introduction",
        "",
        "This report summarizes deep hyperparameter optimization for traditional ML models on Vietnamese Facebook news-related topic classification.",
        "",
        "## 2. Experimental Setup",
        "",
        "Data contains 5 preprocessing scenarios and fixed train/validation/test splits. Model and hyperparameter selection use validation Macro-F1 only.",
        "",
        "## 3. Model Descriptions",
        "",
        "### 3.1 Logistic Regression",
        "Linear classifier with regularization over TF-IDF features.",
        "",
        "### 3.2 Random Forest",
        "Tree ensemble baseline over sparse TF-IDF features.",
        "",
        "### 3.3 XGBoost",
        "Gradient boosted tree baseline with balanced sample weights.",
        "",
        "### 3.4 LinearSVC",
        "Linear support vector classifier, strong for sparse high-dimensional text features.",
        "",
        "## 4. Hyperparameter Search Space",
        "",
        "### 4.1 TF-IDF",
        "Word and char_wb analyzers, max_features, ngram_range, min_df, max_df, sublinear_tf.",
        "",
        "### 4.2 Logistic Regression",
        "C and solver, with lbfgs prioritized in deep mode.",
        "",
        "### 4.3 Random Forest",
        "n_estimators, max_depth, max_features, min_samples_leaf.",
        "",
        "### 4.4 XGBoost",
        "n_estimators, max_depth, learning_rate, subsample, colsample_bytree, regularization.",
        "",
        "### 4.5 LinearSVC",
        "C and class_weight.",
        "",
        "## 5. Hyperparameter Optimization Process",
        "",
        "### 5.1 Method: Hold-out validation and validation curves",
        "Each trial fits on train and evaluates on validation.",
        "",
        "### 5.2 Trial sampling strategy",
        "Controlled random sampling with random_state=42 when candidate count exceeds local cap.",
        "",
        "### 5.3 Selection metric",
        "Primary metric is validation Macro-F1; test set is not used for selection.",
        "",
        "### 5.4 XGBoost repair note",
        "XGBoost final experiments were repaired by refitting final models with saved best hyperparameters and validation eval_set for early stopping; HPO trials were not rerun.",
        "",
        "## 6. Results",
        "",
        "### 6.1 Full 20-experiment evaluation table",
        "",
        markdown_table(full_table, FINAL_FULL_COLUMNS, bold_rows=set(full_table.index[full_table["selection_note"].str.contains("Best overall|Best scenario", regex=True, na=False)])),
        "",
        "### 6.2 Best scenario per model",
        "",
        markdown_table(report_table, FINAL_REPORT_COLUMNS, bold_rows=set(report_table.index[report_table["notes"].str.contains("Best overall", na=False)])),
        "",
        "### 6.3 Best overall model",
        "",
        f"**{best_overall['scenario']} / {best_overall['model_name']}** is selected by validation Macro-F1.",
        "",
        "## 7. Error Analysis Summary",
        "",
        "See `error_analysis/error_analysis_summary.md` and generated CSV/PNG artifacts.",
        "",
        "## 8. Discussion",
        "",
        "Linear models remain strongest for sparse TF-IDF. Tree-based models are useful baselines but weaker.",
        "",
        "## 9. Limitations",
        "",
        "TF-IDF relies on surface forms and may miss context, sarcasm, or implicit topics.",
        "",
        "## 10. Future Work",
        "",
        "Compare with transformer models, probability calibration, and richer error analysis by label taxonomy.",
        "",
        "## Appendix: Figures and Artifacts",
        "",
    ]
    for plot_name in [
        "hpo_plots/val_macro_f1_by_model_scenario.png",
        "hpo_plots/top_20_trials_validation_macro_f1.png",
        "hpo_plots/tfidf_max_features_curve.png",
        "hpo_plots/tfidf_ngram_range_comparison.png",
        "hpo_plots/tfidf_analyzer_comparison.png",
        "hpo_plots/logreg_C_validation_curve.png",
        "hpo_plots/linearsvc_C_validation_curve.png",
        "hpo_plots/rf_max_depth_comparison.png",
        "hpo_plots/xgb_depth_learning_rate_comparison.png",
        "error_analysis/confusion_matrix_best_overall.png",
        "error_analysis/confusion_matrix_best_by_model.png",
    ]:
        if (base_dir / plot_name).exists():
            source.append(f"- `{plot_name}`")
        else:
            source.append(f"- [PLACEHOLDER: insert {plot_name} plot]")
    source.append("")
    write_text(reports_dir / "DS107_HPO_Deep_Report_Final_SOURCE.md", "\n".join(source))


def create_finalization_summary(base_dir: Path, deleted: list[str], word_created: bool) -> None:
    lines = [
        "# Finalization Summary",
        "",
        f"- Created at: {now_iso()}",
        "- Training rerun: no.",
        "- Deep HPO rerun: no.",
        "- XGBoost repair rerun: no.",
        f"- Word draft created: {'yes' if word_created else 'no'}",
        "",
        "## Key outputs",
        "",
        "- `final_tables/final_evaluation_table_full.csv`",
        "- `final_tables/final_evaluation_table_report.csv`",
        "- `reports/DS107_HPO_Deep_Report_Final_SOURCE.md`",
        "- `model_zoo/model_registry.json`",
        "- `error_analysis/error_analysis_summary.md`",
        "- `folder_structure_explanation.md`",
        "",
        "## Cleanup",
        "",
    ]
    if deleted:
        lines.extend(f"- Deleted `{item}`" for item in deleted)
    else:
        lines.append("- No files deleted.")
    if not word_created:
        lines.extend(
            [
                "",
                "Không tạo Word trong môi trường agent; đã chuẩn bị đầy đủ Markdown/CSV/XLSX để Phúc gửi ChatGPT tạo Word.",
            ]
        )
    write_text(base_dir / "finalization_summary.md", "\n".join(lines))


def final_checks(base_dir: Path) -> None:
    summary = pd.read_csv(base_dir / "all_model_results_summary.csv")
    full = pd.read_csv(base_dir / "final_tables" / "final_evaluation_table_full.csv")
    report = pd.read_csv(base_dir / "final_tables" / "final_evaluation_table_report.csv")
    registry_path = base_dir / "model_zoo" / "model_registry.json"
    registry = json_read(registry_path, [])
    errors = []
    if len(summary) != 20:
        errors.append("all_model_results_summary.csv does not have 20 rows")
    if len(summary.loc[summary["model_name"].eq("XGBoost")]) != 5:
        errors.append("XGBoost does not have 5 rows")
    if not summary["status"].eq("success").all():
        errors.append("Found failed status in summary")
    if len(full) != 20:
        errors.append("final_evaluation_table_full.csv does not have 20 rows")
    if len(report) != 4:
        errors.append("final_evaluation_table_report.csv does not have 4 rows")
    if not registry:
        errors.append("model_registry.json is missing or empty")
    for model_name in MODEL_ORDER:
        if not (base_dir / "model_zoo" / "best_by_model" / model_name).exists():
            errors.append(f"Missing model_zoo/best_by_model/{model_name}")
    for scenario in SCENARIO_ORDER:
        for model_name in MODEL_ORDER:
            if not (base_dir / "model_zoo" / "by_scenario" / scenario / model_name).exists():
                errors.append(f"Missing model_zoo/by_scenario/{scenario}/{model_name}")
    required_paths = [
        base_dir / "reports" / "traditional_ml_technical_report_final.md",
        base_dir / "reports" / "hyperparameter_reasoning_report_final.md",
        base_dir / "reports" / "modeling_results_summary_final.md",
        base_dir / "reports" / "DS107_HPO_Deep_Report_Final_SOURCE.md",
        base_dir / "README.md",
        base_dir / "folder_structure_explanation.md",
        base_dir / "error_analysis" / "error_analysis_summary.md",
    ]
    for path in required_paths:
        if not path.exists():
            errors.append(f"Missing final artifact: {path}")
    if errors:
        raise RuntimeError("Final checks failed:\n- " + "\n- ".join(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize DS107 traditional ML deep HPO outputs.")
    parser.add_argument("--output_dir", type=Path, default=BASE_DIR)
    args = parser.parse_args()
    base_dir = args.output_dir

    print(f"[FINALIZE] output_dir={base_dir}")
    summary, diagnostics, hyperparams = validate_inputs(base_dir)
    print("[VALIDATE] repaired deep HPO outputs are complete: 20/20 success")

    full_table, report_table = create_evaluation_tables(base_dir, summary, hyperparams)
    print("[TABLES] final evaluation tables written")

    registry = create_model_zoo(base_dir, summary)
    print(f"[MODEL ZOO] registry rows={len(registry)}")

    create_error_analysis(base_dir, summary)
    write_error_analysis_notebook(Path("notebooks/error_analysis_traditional_ml.ipynb"))
    print("[ERROR ANALYSIS] artifacts and notebook source written")

    write_folder_explanation(base_dir)
    write_reports(base_dir, summary, diagnostics, hyperparams, full_table, report_table)
    print("[REPORTS] final markdown reports written")

    deleted = cleanup_safe(base_dir)
    print(f"[CLEANUP] deleted={deleted}")

    # python-docx is not a required dependency for this repo; keep Word generation optional.
    word_created = False
    create_finalization_summary(base_dir, deleted, word_created)
    final_checks(base_dir)
    print("[FINAL CHECKS] passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

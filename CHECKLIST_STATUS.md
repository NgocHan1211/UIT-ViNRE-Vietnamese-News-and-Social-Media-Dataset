# DS107 Submission Checklist Status

This file maps the provided checklist to the files in this submission package.

## A. Crawl Data

- Present: `src/crawl/`
- Main crawler: `src/crawl/facebook_crawler_multipage_v9_3_2_team_pages.py`
- Example config: `configs/crawl_config.example.json`
- Run guide: `docs/crawl/`
- Sample output: `data_samples/crawl_sample/sample_post_sanitized.json`
- Secrets: no token, cookie, `.env`, or login credential is included.

## B. Master Dataset

- Master build scripts:
  - `src/dataset/build_master_facebook_posts.py`
  - `src/dataset/build_master_teamcrawl_posts.py`
  - `src/dataset/build_master_bao_chi_posts.py`
- Deduped master output:
  - `data_outputs/02_master_dataset/Master_Facebook_News_Posts_TeamCrawl_After_Dedup.csv`
- Reports/docs:
  - `docs/dataset/master_data_pipeline.md`
  - `docs/dataset/README_02_Processed_Data.md`

## C. Label Merge And Final Dataset

- Script: `src/dataset/create_final_master_datasets.py`
- Outputs:
  - `data_outputs/06_final_master_data/Master_Facebook_News_Posts_TeamCrawl_Labeled.csv`
  - `data_outputs/06_final_master_data/Topic_Classification_Model_Dataset.csv`
  - `data_outputs/06_final_master_data/Public_Response_Streamlit_Enriched.csv`
  - `data_outputs/06_final_master_data/taxonomy_mapping_used.csv`
  - `data_outputs/06_final_master_data/metadata_outlier_report.csv`
  - `data_outputs/06_final_master_data/Final_Master_Data_Technical_Report.md`

## D. Train/Validation/Test Split

- Existing cleaned splits: `data_outputs/07_cleaned_splits/07_Cleaned_Data/`
- Reproducible split script: `src/dataset/create_train_val_test_splits.py`
- Validation output:
  - `data_outputs/08_modeling_results/traditional_ml_hpo_deep/split_validation_report.csv`
- The script also writes a fresh split report under `data_outputs/07_cleaned_splits/generated_raw/`
  when it is run from the package root.

## E. Traditional ML

- Training script: `src/training/traditional_ml/train_traditional_models.py`
- Finalization/error script: `src/training/traditional_ml/finalize_traditional_ml_hpo.py`
- Models covered in code: Logistic Regression, LinearSVC, Random Forest, XGBoost.
- Outputs:
  - `data_outputs/08_modeling_results/traditional_ml_hpo_deep/model_results.csv`
  - `data_outputs/08_modeling_results/traditional_ml_hpo_deep/run_config.json`
  - `data_outputs/08_modeling_results/traditional_ml_hpo_deep/best_overall_LogisticRegression/`
  - `logs/train_traditional_models.log`

## F. Pre-trained Models

- mBERT notebook: `src/training/pretrained/notebooks/mbert.ipynb`
- PhoBERT notebook: `src/training/pretrained/notebooks/phobert-social-media-topic-classifier.ipynb`
- XLM-R notebook: `src/training/pretrained/notebooks/xlm-roberta.ipynb`
- Large checkpoints and full transformer outputs are not included.

## G. Error Analysis

- Notebook: `src/error_analysis/error_analysis_traditional_ml.ipynb`
- Extracted/package outputs:
  - `data_outputs/08_modeling_results/han_error_analysis_package_extracted/`
  - `data_outputs/08_modeling_results/han_error_analysis_package.zip`
- Included analyses: text length, NSW density, confusion pairs, qualitative examples,
  confusion matrices, and report-ready tables.

## H. Streamlit Dashboard

- Dashboard folder: `src/dashboard/`
- App: `src/dashboard/app.py`
- Theme utils: `src/dashboard/viz_theme.py`
- Dataset: `src/dashboard/Public_Response_Streamlit_Enriched.csv`
- README and requirements: `src/dashboard/README.md`, `src/dashboard/requirements.txt`
- Model registry metadata is included; `.joblib` weights are excluded.

## I. Documentation

- Root README: `README.md`
- Requirements: `requirements.txt`, `requirements_modeling.txt`
- Git ignore: `.gitignore`
- Configs: `configs/`
- Project docs: `docs/`
- PDF slides/report files were not found in the current workspace, so they are not included.

## J. Final Checks

- Python compile checks pass for copied `.py` files.
- Notebook JSON parse checks pass for copied notebooks.
- No `.env`, `__pycache__`, `.DS_Store`, `.joblib`, `.pt`, `.bin`, `.h5`, cookie, or token file is included.
- No absolute local path is required to run the package.

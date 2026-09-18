# Traditional ML Deep HPO Folder Structure

`data/08_Modeling_Results/traditional_ml_hpo_deep` là output chính sau deep HPO và XGBoost final repair.

## Root Files

- `all_model_results_summary.csv`: bảng metric validation/test của 20 final experiments, dùng để chọn best theo validation Macro-F1.
- `best_hyperparameters_by_model.csv`: best hyperparameters đã chọn cho từng scenario/model bằng validation set.
- `hpo_all_trials.csv` / `hyperparameter_search_results.csv`: toàn bộ 605 HPO trials, chỉ có validation metrics.
- `hpo_all_trials_ranked.csv`: trial table đã rank theo validation Macro-F1, Weighted-F1, Accuracy và train time.
- `hpo_tuning_diagnostics.json`: diagnostics của deep HPO và repair status, gồm final_experiments_success/failed.
- `validation_test_gap_analysis.csv`: so sánh validation vs test metrics, dùng để phát hiện gap lớn.
- `best_model_summary.json`: metadata của best benchmark model theo validation Macro-F1.

## Main Folders

- `reports/`: bản Markdown final để đưa vào báo cáo/slide/Word.
- `final_tables/`: bảng evaluation full 20 rows và compact 4 rows ở CSV/MD/XLSX.
- `error_analysis/`: bảng và hình phân tích lỗi, không train lại model.
- `model_zoo/`: registry và artifacts để Streamlit demo nhiều model.
- `hpo_plots/`: validation curves và HPO comparison plots.
- `best_model/`: benchmark model tốt nhất, train trên train, chọn theo validation, test một lần để report.
- `best_model_refit_train_val/`: deployment model refit trên train+val bằng best hyperparameters; dùng cho demo, không dùng để chọn model.
- `backup_before_xgboost_repair/`: snapshot report/summary trước repair XGBoost, giữ để audit.

## Scenario/Model Folders

Mỗi folder `<scenario>/<model>/` chứa `model.joblib`, `vectorizer.joblib`, `label_encoder.joblib`, metrics JSON, classification reports, confusion matrices, predictions và wrong predictions.

## Test Discipline

Validation set được dùng để chọn hyperparameters và best model. Test set chỉ dùng để báo cáo final performance.

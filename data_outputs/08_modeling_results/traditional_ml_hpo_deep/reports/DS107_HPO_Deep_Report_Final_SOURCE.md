# Hyperparameter Optimization Report for Traditional ML Models

## 1. Introduction

This report summarizes deep hyperparameter optimization for traditional ML models on Vietnamese Facebook news-related topic classification.

## 2. Experimental Setup

Data contains 5 preprocessing scenarios and fixed train/validation/test splits. Model and hyperparameter selection use validation Macro-F1 only.

## 3. Model Descriptions

### 3.1 Logistic Regression
Linear classifier with regularization over TF-IDF features.

### 3.2 Random Forest
Tree ensemble baseline over sparse TF-IDF features.

### 3.3 XGBoost
Gradient boosted tree baseline with balanced sample weights.

### 3.4 LinearSVC
Linear support vector classifier, strong for sparse high-dimensional text features.

## 4. Hyperparameter Search Space

### 4.1 TF-IDF
Word and char_wb analyzers, max_features, ngram_range, min_df, max_df, sublinear_tf.

### 4.2 Logistic Regression
C and solver, with lbfgs prioritized in deep mode.

### 4.3 Random Forest
n_estimators, max_depth, max_features, min_samples_leaf.

### 4.4 XGBoost
n_estimators, max_depth, learning_rate, subsample, colsample_bytree, regularization.

### 4.5 LinearSVC
C and class_weight.

## 5. Hyperparameter Optimization Process

### 5.1 Method: Hold-out validation and validation curves
Each trial fits on train and evaluates on validation.

### 5.2 Trial sampling strategy
Controlled random sampling with random_state=42 when candidate count exceeds local cap.

### 5.3 Selection metric
Primary metric is validation Macro-F1; test set is not used for selection.

### 5.4 XGBoost repair note
XGBoost final experiments were repaired by refitting final models with saved best hyperparameters and validation eval_set for early stopping; HPO trials were not rerun.

## 6. Results

### 6.1 Full 20-experiment evaluation table

| model_name | scenario | accuracy_val | macro_precision_val | macro_recall_val | macro_f1_val | weighted_precision_val | weighted_recall_val | weighted_f1_val | accuracy_test | macro_precision_test | macro_recall_test | macro_f1_test | weighted_precision_test | weighted_recall_test | weighted_f1_test | selection_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **LogisticRegression** | **01_Raw_Data** | **0.7252** | **0.6826** | **0.6455** | **0.6492** | **0.7357** | **0.7252** | **0.7244** | **0.7601** | **0.7061** | **0.6979** | **0.6954** | **0.7609** | **0.7601** | **0.7578** | **Best overall by validation Macro-F1; Best scenario for this model by validation Macro-F1** |
| LogisticRegression | 02_Basic_Clean | 0.7192 | 0.6666 | 0.6380 | 0.6391 | 0.7301 | 0.7192 | 0.7190 | 0.7613 | 0.7095 | 0.7033 | 0.7014 | 0.7629 | 0.7613 | 0.7596 | Best test Macro-F1 reference only; not used for selection |
| LogisticRegression | 03_Full_Clean | 0.7204 | 0.6592 | 0.6363 | 0.6366 | 0.7296 | 0.7204 | 0.7203 | 0.7601 | 0.7011 | 0.7059 | 0.6996 | 0.7612 | 0.7601 | 0.7587 |  |
| LogisticRegression | 04_No_Stopwords | 0.7168 | 0.6668 | 0.6282 | 0.6314 | 0.7264 | 0.7168 | 0.7153 | 0.7625 | 0.7025 | 0.7019 | 0.6971 | 0.7629 | 0.7625 | 0.7604 |  |
| LogisticRegression | 05_Balanced | 0.7204 | 0.6721 | 0.6381 | 0.6407 | 0.7224 | 0.7204 | 0.7147 | 0.7530 | 0.6971 | 0.6827 | 0.6841 | 0.7507 | 0.7530 | 0.7488 |  |
| RandomForest | 01_Raw_Data | 0.6440 | 0.7048 | 0.5508 | 0.5698 | 0.6656 | 0.6440 | 0.6286 | 0.6766 | 0.6625 | 0.5682 | 0.5860 | 0.6720 | 0.6766 | 0.6593 |  |
| RandomForest | 02_Basic_Clean | 0.6141 | 0.5695 | 0.5969 | 0.5600 | 0.6196 | 0.6141 | 0.6054 | 0.6718 | 0.6068 | 0.6596 | 0.6142 | 0.6778 | 0.6718 | 0.6670 |  |
| RandomForest | 03_Full_Clean | 0.6177 | 0.5604 | 0.6017 | 0.5624 | 0.6245 | 0.6177 | 0.6101 | 0.6706 | 0.6070 | 0.6581 | 0.6128 | 0.6778 | 0.6706 | 0.6651 |  |
| RandomForest | 04_No_Stopwords | 0.6762 | 0.7115 | 0.5507 | 0.5788 | 0.6860 | 0.6762 | 0.6520 | 0.6957 | 0.7424 | 0.5653 | 0.5956 | 0.7223 | 0.6957 | 0.6752 |  |
| **RandomForest** | **05_Balanced** | **0.6714** | **0.6784** | **0.5686** | **0.5796** | **0.6775** | **0.6714** | **0.6542** | **0.7088** | **0.6910** | **0.5988** | **0.6139** | **0.7128** | **0.7088** | **0.6923** | **Best scenario for this model by validation Macro-F1** |
| XGBoost | 01_Raw_Data | 0.5938 | 0.5332 | 0.5602 | 0.5358 | 0.6190 | 0.5938 | 0.5993 | 0.6516 | 0.5877 | 0.6717 | 0.6178 | 0.6847 | 0.6516 | 0.6603 |  |
| XGBoost | 02_Basic_Clean | 0.5938 | 0.5288 | 0.5655 | 0.5369 | 0.6199 | 0.5938 | 0.6000 | 0.6599 | 0.5892 | 0.6627 | 0.6145 | 0.6902 | 0.6599 | 0.6685 |  |
| **XGBoost** | **03_Full_Clean** | **0.5986** | **0.5391** | **0.5756** | **0.5458** | **0.6268** | **0.5986** | **0.6053** | **0.6575** | **0.5945** | **0.6707** | **0.6189** | **0.6923** | **0.6575** | **0.6671** | **Best scenario for this model by validation Macro-F1** |
| XGBoost | 04_No_Stopwords | 0.5962 | 0.5244 | 0.5678 | 0.5345 | 0.6219 | 0.5962 | 0.6004 | 0.6575 | 0.5805 | 0.6612 | 0.6078 | 0.6952 | 0.6575 | 0.6680 |  |
| XGBoost | 05_Balanced | 0.6033 | 0.5461 | 0.5491 | 0.5379 | 0.6088 | 0.6033 | 0.6010 | 0.6647 | 0.6015 | 0.6384 | 0.6137 | 0.6748 | 0.6647 | 0.6664 |  |
| **LinearSVC** | **01_Raw_Data** | **0.7300** | **0.7039** | **0.6294** | **0.6455** | **0.7251** | **0.7300** | **0.7201** | **0.7589** | **0.7201** | **0.6745** | **0.6867** | **0.7545** | **0.7589** | **0.7522** | **Best scenario for this model by validation Macro-F1** |
| LinearSVC | 02_Basic_Clean | 0.7312 | 0.7074 | 0.6311 | 0.6453 | 0.7281 | 0.7312 | 0.7209 | 0.7578 | 0.7278 | 0.6800 | 0.6938 | 0.7548 | 0.7578 | 0.7520 |  |
| LinearSVC | 03_Full_Clean | 0.7240 | 0.6562 | 0.6324 | 0.6358 | 0.7203 | 0.7240 | 0.7187 | 0.7542 | 0.6843 | 0.6644 | 0.6698 | 0.7476 | 0.7542 | 0.7489 |  |
| LinearSVC | 04_No_Stopwords | 0.7264 | 0.6630 | 0.6472 | 0.6452 | 0.7291 | 0.7264 | 0.7242 | 0.7506 | 0.6746 | 0.6654 | 0.6672 | 0.7488 | 0.7506 | 0.7480 |  |
| LinearSVC | 05_Balanced | 0.7204 | 0.6991 | 0.6323 | 0.6390 | 0.7221 | 0.7204 | 0.7109 | 0.7494 | 0.7065 | 0.6861 | 0.6876 | 0.7466 | 0.7494 | 0.7435 |  |

### 6.2 Best scenario per model

| model_name | best_scenario_by_val_macro_f1 | accuracy_val | macro_precision_val | macro_recall_val | macro_f1_val | accuracy_test | macro_precision_test | macro_recall_test | macro_f1_test | weighted_f1_test | best_hyperparameters_summary | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **LogisticRegression** | **01_Raw_Data** | **0.7252** | **0.6826** | **0.6455** | **0.6492** | **0.7601** | **0.7061** | **0.6979** | **0.6954** | **0.7578** | **TF-IDF(analyzer=word, max_features=50000, ngram=(1, 2), min_df=1); Model(C=10.0, solver=lbfgs)** | **Selected by validation Macro-F1 within model family. Best overall model.** |
| RandomForest | 05_Balanced | 0.6714 | 0.6784 | 0.5686 | 0.5796 | 0.7088 | 0.6910 | 0.5988 | 0.6139 | 0.6923 | TF-IDF(analyzer=word, max_features=20000, ngram=(1, 1), min_df=2); Model(n_estimators=300, max_depth=100, max_features=log2, min_samples_leaf=1) | Selected by validation Macro-F1 within model family. |
| XGBoost | 03_Full_Clean | 0.5986 | 0.5391 | 0.5756 | 0.5458 | 0.6575 | 0.5945 | 0.6707 | 0.6189 | 0.6671 | TF-IDF(analyzer=word, max_features=50000, ngram=(1, 2), min_df=3); Model(n_estimators=200, max_depth=5, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9, reg_lambda=2.0, reg_alpha=0.1, early_stopping_rounds=30) | Selected by validation Macro-F1 within model family. |
| LinearSVC | 01_Raw_Data | 0.7300 | 0.7039 | 0.6294 | 0.6455 | 0.7589 | 0.7201 | 0.6745 | 0.6867 | 0.7522 | TF-IDF(analyzer=word, max_features=50000, ngram=(1, 2), min_df=1); Model(C=2.0, class_weight=None) | Selected by validation Macro-F1 within model family. |

### 6.3 Best overall model

**01_Raw_Data / LogisticRegression** is selected by validation Macro-F1.

## 7. Error Analysis Summary

See `error_analysis/error_analysis_summary.md` and generated CSV/PNG artifacts.

## 8. Discussion

Linear models remain strongest for sparse TF-IDF. Tree-based models are useful baselines but weaker.

## 9. Limitations

TF-IDF relies on surface forms and may miss context, sarcasm, or implicit topics.

## 10. Future Work

Compare with transformer models, probability calibration, and richer error analysis by label taxonomy.

## Appendix: Figures and Artifacts

- `hpo_plots/val_macro_f1_by_model_scenario.png`
- `hpo_plots/top_20_trials_validation_macro_f1.png`
- `hpo_plots/tfidf_max_features_curve.png`
- `hpo_plots/tfidf_ngram_range_comparison.png`
- `hpo_plots/tfidf_analyzer_comparison.png`
- `hpo_plots/logreg_C_validation_curve.png`
- `hpo_plots/linearsvc_C_validation_curve.png`
- `hpo_plots/rf_max_depth_comparison.png`
- `hpo_plots/xgb_depth_learning_rate_comparison.png`
- `error_analysis/confusion_matrix_best_overall.png`
- `error_analysis/confusion_matrix_best_by_model.png`

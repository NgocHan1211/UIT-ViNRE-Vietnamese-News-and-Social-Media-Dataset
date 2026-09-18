# Report-Ready Compact Evaluation Table

Each row is the best scenario of one model family, selected by validation Macro-F1.

| model_name | best_scenario_by_val_macro_f1 | accuracy_val | macro_precision_val | macro_recall_val | macro_f1_val | accuracy_test | macro_precision_test | macro_recall_test | macro_f1_test | weighted_f1_test | best_hyperparameters_summary | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **LogisticRegression** | **01_Raw_Data** | **0.7252** | **0.6826** | **0.6455** | **0.6492** | **0.7601** | **0.7061** | **0.6979** | **0.6954** | **0.7578** | **TF-IDF(analyzer=word, max_features=50000, ngram=(1, 2), min_df=1); Model(C=10.0, solver=lbfgs)** | **Selected by validation Macro-F1 within model family. Best overall model.** |
| RandomForest | 05_Balanced | 0.6714 | 0.6784 | 0.5686 | 0.5796 | 0.7088 | 0.6910 | 0.5988 | 0.6139 | 0.6923 | TF-IDF(analyzer=word, max_features=20000, ngram=(1, 1), min_df=2); Model(n_estimators=300, max_depth=100, max_features=log2, min_samples_leaf=1) | Selected by validation Macro-F1 within model family. |
| XGBoost | 03_Full_Clean | 0.5986 | 0.5391 | 0.5756 | 0.5458 | 0.6575 | 0.5945 | 0.6707 | 0.6189 | 0.6671 | TF-IDF(analyzer=word, max_features=50000, ngram=(1, 2), min_df=3); Model(n_estimators=200, max_depth=5, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9, reg_lambda=2.0, reg_alpha=0.1, early_stopping_rounds=30) | Selected by validation Macro-F1 within model family. |
| LinearSVC | 01_Raw_Data | 0.7300 | 0.7039 | 0.6294 | 0.6455 | 0.7589 | 0.7201 | 0.6745 | 0.6867 | 0.7522 | TF-IDF(analyzer=word, max_features=50000, ngram=(1, 2), min_df=1); Model(C=2.0, class_weight=None) | Selected by validation Macro-F1 within model family. |

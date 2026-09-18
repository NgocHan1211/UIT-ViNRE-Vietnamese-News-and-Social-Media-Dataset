# Hyperparameter Reasoning Report Final

## 1. Mục tiêu tuning

Tối ưu baseline traditional ML cho bài toán phân loại 17 chủ đề bài đăng Facebook, ưu tiên Macro-F1 vì dữ liệu mất cân bằng.

## 2. Vì sao không dùng elbow method như K-Means

Đây là supervised classification, không phải clustering. Không có elbow method chuẩn để chọn tham số; thay vào đó dùng validation set để đo chất lượng từng cấu hình.

## 3. Phương pháp hold-out validation + validation curve

Mỗi trial fit TF-IDF và model trên train, đánh giá trên validation. Test chỉ dùng sau khi chọn best config. Validation curves và parameter effect summary dùng để giải thích xu hướng tham số.

## 4. Search space TF-IDF

Word TF-IDF thử max_features, ngram_range, min_df, max_df, sublinear_tf. LogisticRegression và LinearSVC có thêm char_wb TF-IDF để xử lý teencode, viết tắt, viết dính và từ né bộ lọc.

## 5. Search space từng model

1. LogisticRegression: C, solver, class_weight; deep ưu tiên lbfgs.
2. RandomForest: n_estimators, max_depth, max_features, min_samples_leaf.
3. XGBoost: n_estimators, max_depth, learning_rate, subsample, colsample_bytree, reg_lambda, reg_alpha.
4. LinearSVC: C, class_weight.

## 6. Quá trình tuning theo model

Deep HPO thử 605 successful validation trials. Candidate sampling dùng random_state=42 khi search space vượt cap để chạy được local.

## 7. Nhận xét kết quả theo model

- LogisticRegression là best overall và ổn định nhất.
- LinearSVC rất gần LogisticRegression ở một số scenario.
- RandomForest thấp hơn nhóm tuyến tính vì sparse TF-IDF không phù hợp với tree ensemble truyền thống.
- XGBoost sau repair chạy đủ final experiments nhưng validation Macro-F1 vẫn thấp hơn nhóm tuyến tính.

## 8. Best hyperparameters theo model

| model_name | best_scenario | validation_macro_f1 | test_macro_f1 | best_hyperparameters_summary |
| --- | --- | --- | --- | --- |
| LogisticRegression | 01_Raw_Data | 0.6492 | 0.6954 | TF-IDF(analyzer=word, max_features=50000, ngram=(1, 2), min_df=1); Model(C=10.0, solver=lbfgs) |
| RandomForest | 05_Balanced | 0.5796 | 0.6139 | TF-IDF(analyzer=word, max_features=20000, ngram=(1, 1), min_df=2); Model(n_estimators=300, max_depth=100, max_features=log2, min_samples_leaf=1) |
| XGBoost | 03_Full_Clean | 0.5458 | 0.6189 | TF-IDF(analyzer=word, max_features=50000, ngram=(1, 2), min_df=3); Model(n_estimators=200, max_depth=5, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9, reg_lambda=2.0, reg_alpha=0.1, early_stopping_rounds=30) |
| LinearSVC | 01_Raw_Data | 0.6455 | 0.6867 | TF-IDF(analyzer=word, max_features=50000, ngram=(1, 2), min_df=1); Model(C=2.0, class_weight=None) |

## 9. XGBoost final repair

Repair chỉ xử lý final fit. HPO trials của XGBoost đã thành công trước đó và được reuse; benchmark final fit dùng validation set cho early stopping, deployment refit train+val không dùng early stopping vì không có validation riêng.

## 10. Discussion / Limitation / Future work

Traditional ML + TF-IDF là baseline mạnh, dễ giải thích và nhanh. Hướng tiếp theo là so sánh với PhoBERT/transformer, calibration probability, và phân tích sâu các label boundary ambiguity.

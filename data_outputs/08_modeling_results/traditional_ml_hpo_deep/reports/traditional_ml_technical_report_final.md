# Traditional ML Technical Report Final

## Dataset/Split Validation

Pipeline sử dụng 5 preprocessing scenarios và split train/val/test đã chia sẵn. Validation kiểm tra T18, label T01-T17, duplicate/overlap record_id và consistency test ids giữa scenarios.

- Final experiments total: 20.
- Final experiments success: 20.
- Final experiments failed: 0.

## 5 Preprocessing Scenarios

`01_Raw_Data`, `02_Basic_Clean`, `03_Full_Clean`, `04_No_Stopwords`, `05_Balanced`

## 4 Model Families

`LogisticRegression`, `RandomForest`, `XGBoost`, `LinearSVC`

## Deep HPO Setup

- TF-IDF word/char search space tùy model.
- Hold-out validation based HPO.
- Primary metric: validation Macro-F1.
- Tie-breakers: validation Weighted-F1, validation Accuracy, model simplicity nếu Macro-F1 gần nhau.
- Test set không dùng để chọn hyperparameters.

## XGBoost Repair Note

XGBoost final fit ban đầu lỗi do `early_stopping_rounds` cần `eval_set`. Repair chỉ refit final XGBoost bằng best hyperparameters đã có từ HPO, không chạy lại 605 trials và không dùng test set để chọn tham số.

## Full Evaluation Result

| model_name | scenario | accuracy_val | macro_precision_val | macro_recall_val | macro_f1_val | weighted_precision_val | weighted_recall_val | weighted_f1_val | accuracy_test | macro_precision_test | macro_recall_test | macro_f1_test | weighted_precision_test | weighted_recall_test | weighted_f1_test | selection_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LogisticRegression | 01_Raw_Data | 0.7252 | 0.6826 | 0.6455 | 0.6492 | 0.7357 | 0.7252 | 0.7244 | 0.7601 | 0.7061 | 0.6979 | 0.6954 | 0.7609 | 0.7601 | 0.7578 | Best overall by validation Macro-F1; Best scenario for this model by validation Macro-F1 |
| LogisticRegression | 02_Basic_Clean | 0.7192 | 0.6666 | 0.6380 | 0.6391 | 0.7301 | 0.7192 | 0.7190 | 0.7613 | 0.7095 | 0.7033 | 0.7014 | 0.7629 | 0.7613 | 0.7596 | Best test Macro-F1 reference only; not used for selection |
| LogisticRegression | 03_Full_Clean | 0.7204 | 0.6592 | 0.6363 | 0.6366 | 0.7296 | 0.7204 | 0.7203 | 0.7601 | 0.7011 | 0.7059 | 0.6996 | 0.7612 | 0.7601 | 0.7587 |  |
| LogisticRegression | 04_No_Stopwords | 0.7168 | 0.6668 | 0.6282 | 0.6314 | 0.7264 | 0.7168 | 0.7153 | 0.7625 | 0.7025 | 0.7019 | 0.6971 | 0.7629 | 0.7625 | 0.7604 |  |
| LogisticRegression | 05_Balanced | 0.7204 | 0.6721 | 0.6381 | 0.6407 | 0.7224 | 0.7204 | 0.7147 | 0.7530 | 0.6971 | 0.6827 | 0.6841 | 0.7507 | 0.7530 | 0.7488 |  |
| RandomForest | 01_Raw_Data | 0.6440 | 0.7048 | 0.5508 | 0.5698 | 0.6656 | 0.6440 | 0.6286 | 0.6766 | 0.6625 | 0.5682 | 0.5860 | 0.6720 | 0.6766 | 0.6593 |  |
| RandomForest | 02_Basic_Clean | 0.6141 | 0.5695 | 0.5969 | 0.5600 | 0.6196 | 0.6141 | 0.6054 | 0.6718 | 0.6068 | 0.6596 | 0.6142 | 0.6778 | 0.6718 | 0.6670 |  |
| RandomForest | 03_Full_Clean | 0.6177 | 0.5604 | 0.6017 | 0.5624 | 0.6245 | 0.6177 | 0.6101 | 0.6706 | 0.6070 | 0.6581 | 0.6128 | 0.6778 | 0.6706 | 0.6651 |  |
| RandomForest | 04_No_Stopwords | 0.6762 | 0.7115 | 0.5507 | 0.5788 | 0.6860 | 0.6762 | 0.6520 | 0.6957 | 0.7424 | 0.5653 | 0.5956 | 0.7223 | 0.6957 | 0.6752 |  |
| RandomForest | 05_Balanced | 0.6714 | 0.6784 | 0.5686 | 0.5796 | 0.6775 | 0.6714 | 0.6542 | 0.7088 | 0.6910 | 0.5988 | 0.6139 | 0.7128 | 0.7088 | 0.6923 | Best scenario for this model by validation Macro-F1 |
| XGBoost | 01_Raw_Data | 0.5938 | 0.5332 | 0.5602 | 0.5358 | 0.6190 | 0.5938 | 0.5993 | 0.6516 | 0.5877 | 0.6717 | 0.6178 | 0.6847 | 0.6516 | 0.6603 |  |
| XGBoost | 02_Basic_Clean | 0.5938 | 0.5288 | 0.5655 | 0.5369 | 0.6199 | 0.5938 | 0.6000 | 0.6599 | 0.5892 | 0.6627 | 0.6145 | 0.6902 | 0.6599 | 0.6685 |  |
| XGBoost | 03_Full_Clean | 0.5986 | 0.5391 | 0.5756 | 0.5458 | 0.6268 | 0.5986 | 0.6053 | 0.6575 | 0.5945 | 0.6707 | 0.6189 | 0.6923 | 0.6575 | 0.6671 | Best scenario for this model by validation Macro-F1 |
| XGBoost | 04_No_Stopwords | 0.5962 | 0.5244 | 0.5678 | 0.5345 | 0.6219 | 0.5962 | 0.6004 | 0.6575 | 0.5805 | 0.6612 | 0.6078 | 0.6952 | 0.6575 | 0.6680 |  |
| XGBoost | 05_Balanced | 0.6033 | 0.5461 | 0.5491 | 0.5379 | 0.6088 | 0.6033 | 0.6010 | 0.6647 | 0.6015 | 0.6384 | 0.6137 | 0.6748 | 0.6647 | 0.6664 |  |
| LinearSVC | 01_Raw_Data | 0.7300 | 0.7039 | 0.6294 | 0.6455 | 0.7251 | 0.7300 | 0.7201 | 0.7589 | 0.7201 | 0.6745 | 0.6867 | 0.7545 | 0.7589 | 0.7522 | Best scenario for this model by validation Macro-F1 |
| LinearSVC | 02_Basic_Clean | 0.7312 | 0.7074 | 0.6311 | 0.6453 | 0.7281 | 0.7312 | 0.7209 | 0.7578 | 0.7278 | 0.6800 | 0.6938 | 0.7548 | 0.7578 | 0.7520 |  |
| LinearSVC | 03_Full_Clean | 0.7240 | 0.6562 | 0.6324 | 0.6358 | 0.7203 | 0.7240 | 0.7187 | 0.7542 | 0.6843 | 0.6644 | 0.6698 | 0.7476 | 0.7542 | 0.7489 |  |
| LinearSVC | 04_No_Stopwords | 0.7264 | 0.6630 | 0.6472 | 0.6452 | 0.7291 | 0.7264 | 0.7242 | 0.7506 | 0.6746 | 0.6654 | 0.6672 | 0.7488 | 0.7506 | 0.7480 |  |
| LinearSVC | 05_Balanced | 0.7204 | 0.6991 | 0.6323 | 0.6390 | 0.7221 | 0.7204 | 0.7109 | 0.7494 | 0.7065 | 0.6861 | 0.6876 | 0.7466 | 0.7494 | 0.7435 |  |

## Compact Report-Ready Result

| model_name | best_scenario_by_val_macro_f1 | accuracy_val | macro_precision_val | macro_recall_val | macro_f1_val | accuracy_test | macro_precision_test | macro_recall_test | macro_f1_test | weighted_f1_test | best_hyperparameters_summary | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LogisticRegression | 01_Raw_Data | 0.7252 | 0.6826 | 0.6455 | 0.6492 | 0.7601 | 0.7061 | 0.6979 | 0.6954 | 0.7578 | TF-IDF(analyzer=word, max_features=50000, ngram=(1, 2), min_df=1); Model(C=10.0, solver=lbfgs) | Selected by validation Macro-F1 within model family. Best overall model. |
| RandomForest | 05_Balanced | 0.6714 | 0.6784 | 0.5686 | 0.5796 | 0.7088 | 0.6910 | 0.5988 | 0.6139 | 0.6923 | TF-IDF(analyzer=word, max_features=20000, ngram=(1, 1), min_df=2); Model(n_estimators=300, max_depth=100, max_features=log2, min_samples_leaf=1) | Selected by validation Macro-F1 within model family. |
| XGBoost | 03_Full_Clean | 0.5986 | 0.5391 | 0.5756 | 0.5458 | 0.6575 | 0.5945 | 0.6707 | 0.6189 | 0.6671 | TF-IDF(analyzer=word, max_features=50000, ngram=(1, 2), min_df=3); Model(n_estimators=200, max_depth=5, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9, reg_lambda=2.0, reg_alpha=0.1, early_stopping_rounds=30) | Selected by validation Macro-F1 within model family. |
| LinearSVC | 01_Raw_Data | 0.7300 | 0.7039 | 0.6294 | 0.6455 | 0.7589 | 0.7201 | 0.6745 | 0.6867 | 0.7522 | TF-IDF(analyzer=word, max_features=50000, ngram=(1, 2), min_df=1); Model(C=2.0, class_weight=None) | Selected by validation Macro-F1 within model family. |

## Best Model Selection

Best overall theo validation Macro-F1 là `01_Raw_Data / LogisticRegression` với validation Macro-F1 `0.6492`, test Macro-F1 `0.6954`, test Accuracy `0.7601`.

Best test Macro-F1 reference là `02_Basic_Clean / LogisticRegression` với test Macro-F1 `0.7014`. Không chọn theo test.

## Validation-Test Gap

| scenario | model_name | macro_f1_val | macro_f1_test | delta_test_minus_val | accuracy_val | accuracy_test | delta_accuracy_test_minus_val | weighted_f1_val | weighted_f1_test | delta_weighted_f1_test_minus_val | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01_Raw_Data | LogisticRegression | 0.6492 | 0.6954 | 0.0461 | 0.7252 | 0.7601 | 0.0349 | 0.7244 | 0.7578 | 0.0334 | warning_abs_macro_f1_gap_gt_0.04 |
| 01_Raw_Data | LinearSVC | 0.6455 | 0.6867 | 0.0412 | 0.7300 | 0.7589 | 0.0290 | 0.7201 | 0.7522 | 0.0321 | warning_abs_macro_f1_gap_gt_0.04 |
| 02_Basic_Clean | LinearSVC | 0.6453 | 0.6938 | 0.0485 | 0.7312 | 0.7578 | 0.0266 | 0.7209 | 0.7520 | 0.0311 | warning_abs_macro_f1_gap_gt_0.04 |
| 04_No_Stopwords | LinearSVC | 0.6452 | 0.6672 | 0.0220 | 0.7264 | 0.7506 | 0.0242 | 0.7242 | 0.7480 | 0.0239 |  |
| 05_Balanced | LogisticRegression | 0.6407 | 0.6841 | 0.0434 | 0.7204 | 0.7530 | 0.0326 | 0.7147 | 0.7488 | 0.0341 | warning_abs_macro_f1_gap_gt_0.04 |
| 02_Basic_Clean | LogisticRegression | 0.6391 | 0.7014 | 0.0623 | 0.7192 | 0.7613 | 0.0421 | 0.7190 | 0.7596 | 0.0407 | warning_abs_macro_f1_gap_gt_0.04 |
| 05_Balanced | LinearSVC | 0.6390 | 0.6876 | 0.0486 | 0.7204 | 0.7494 | 0.0290 | 0.7109 | 0.7435 | 0.0326 | warning_abs_macro_f1_gap_gt_0.04 |
| 03_Full_Clean | LogisticRegression | 0.6366 | 0.6996 | 0.0630 | 0.7204 | 0.7601 | 0.0397 | 0.7203 | 0.7587 | 0.0384 | warning_abs_macro_f1_gap_gt_0.04 |
| 03_Full_Clean | LinearSVC | 0.6358 | 0.6698 | 0.0340 | 0.7240 | 0.7542 | 0.0302 | 0.7187 | 0.7489 | 0.0302 |  |
| 04_No_Stopwords | LogisticRegression | 0.6314 | 0.6971 | 0.0657 | 0.7168 | 0.7625 | 0.0457 | 0.7153 | 0.7604 | 0.0451 | warning_abs_macro_f1_gap_gt_0.04 |
| 05_Balanced | RandomForest | 0.5796 | 0.6139 | 0.0343 | 0.6714 | 0.7088 | 0.0374 | 0.6542 | 0.6923 | 0.0381 |  |
| 04_No_Stopwords | RandomForest | 0.5788 | 0.5956 | 0.0167 | 0.6762 | 0.6957 | 0.0195 | 0.6520 | 0.6752 | 0.0232 |  |
| 01_Raw_Data | RandomForest | 0.5698 | 0.5860 | 0.0162 | 0.6440 | 0.6766 | 0.0326 | 0.6286 | 0.6593 | 0.0308 |  |
| 03_Full_Clean | RandomForest | 0.5624 | 0.6128 | 0.0504 | 0.6177 | 0.6706 | 0.0530 | 0.6101 | 0.6651 | 0.0550 | warning_abs_macro_f1_gap_gt_0.04 |
| 02_Basic_Clean | RandomForest | 0.5600 | 0.6142 | 0.0543 | 0.6141 | 0.6718 | 0.0577 | 0.6054 | 0.6670 | 0.0616 | warning_abs_macro_f1_gap_gt_0.04 |
| 03_Full_Clean | XGBoost | 0.5458 | 0.6189 | 0.0731 | 0.5986 | 0.6575 | 0.0590 | 0.6053 | 0.6671 | 0.0619 | warning_abs_macro_f1_gap_gt_0.04 |
| 05_Balanced | XGBoost | 0.5379 | 0.6137 | 0.0758 | 0.6033 | 0.6647 | 0.0613 | 0.6010 | 0.6664 | 0.0654 | warning_abs_macro_f1_gap_gt_0.04 |
| 02_Basic_Clean | XGBoost | 0.5369 | 0.6145 | 0.0776 | 0.5938 | 0.6599 | 0.0661 | 0.6000 | 0.6685 | 0.0685 | warning_abs_macro_f1_gap_gt_0.04 |
| 01_Raw_Data | XGBoost | 0.5358 | 0.6178 | 0.0820 | 0.5938 | 0.6516 | 0.0578 | 0.5993 | 0.6603 | 0.0610 | warning_abs_macro_f1_gap_gt_0.04 |
| 04_No_Stopwords | XGBoost | 0.5345 | 0.6078 | 0.0733 | 0.5962 | 0.6575 | 0.0613 | 0.6004 | 0.6680 | 0.0676 | warning_abs_macro_f1_gap_gt_0.04 |

## Error Analysis Summary

# Error Analysis Summary

Phân tích này dùng predictions đã lưu sau deep HPO repair, không train lại model.

## Scope

- Best overall: `01_Raw_Data / LogisticRegression`.
- Best-by-model models: `LogisticRegression / 01_Raw_Data`, `RandomForest / 05_Balanced`, `XGBoost / 03_Full_Clean`, `LinearSVC / 01_Raw_Data`.
- Split chính cho error buckets: validation; test được dùng để đối chiếu final performance.

## Per Model Error Overview

| model_name | scenario | test_samples | test_wrong_predictions | test_error_rate | validation_macro_f1 | test_macro_f1 | test_accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LogisticRegression | 01_Raw_Data | 838 | 201 | 0.2399 | 0.6492 | 0.6954 | 0.7601 |
| RandomForest | 05_Balanced | 838 | 244 | 0.2912 | 0.5796 | 0.6139 | 0.7088 |
| XGBoost | 03_Full_Clean | 838 | 287 | 0.3425 | 0.5458 | 0.6189 | 0.6575 |
| LinearSVC | 01_Raw_Data | 838 | 202 | 0.2411 | 0.6455 | 0.6867 | 0.7589 |

## Text Length

| split | model_name | scenario | length_bucket | total_samples | wrong_predictions | error_rate |
| --- | --- | --- | --- | --- | --- | --- |
| val | LinearSVC | 01_Raw_Data | long | 168 | 54 | 0.3214 |
| val | LinearSVC | 01_Raw_Data | medium | 646 | 168 | 0.2601 |
| val | LinearSVC | 01_Raw_Data | short | 23 | 4 | 0.1739 |
| val | LogisticRegression | 01_Raw_Data | long | 168 | 54 | 0.3214 |
| val | LogisticRegression | 01_Raw_Data | medium | 646 | 174 | 0.2693 |
| val | LogisticRegression | 01_Raw_Data | short | 23 | 2 | 0.0870 |
| val | RandomForest | 05_Balanced | long | 166 | 67 | 0.4036 |
| val | RandomForest | 05_Balanced | medium | 641 | 199 | 0.3105 |
| val | RandomForest | 05_Balanced | short | 30 | 9 | 0.3000 |
| val | XGBoost | 03_Full_Clean | long | 166 | 63 | 0.3795 |
| val | XGBoost | 03_Full_Clean | medium | 641 | 259 | 0.4041 |
| val | XGBoost | 03_Full_Clean | short | 30 | 14 | 0.4667 |

## NSW / Teencode Density

| split | model_name | scenario | correct_bool | mean_nsw_density | mean_nsw_count | n_samples |
| --- | --- | --- | --- | --- | --- | --- |
| val | LinearSVC | 01_Raw_Data | 0 | 0.0680 | 1.6903 | 226 |
| val | LinearSVC | 01_Raw_Data | 1 | 0.0785 | 1.7250 | 611 |
| val | LogisticRegression | 01_Raw_Data | 0 | 0.0665 | 1.6739 | 230 |
| val | LogisticRegression | 01_Raw_Data | 1 | 0.0792 | 1.7315 | 607 |
| val | RandomForest | 05_Balanced | 0 | 0.0723 | 1.7345 | 275 |
| val | RandomForest | 05_Balanced | 1 | 0.0786 | 1.6815 | 562 |
| val | XGBoost | 03_Full_Clean | 0 | 0.0761 | 1.6667 | 336 |
| val | XGBoost | 03_Full_Clean | 1 | 0.0768 | 1.7206 | 501 |

Top NSW terms trong wrong predictions: t (1982), k (1227), j (48), hong (36), cđm (20), matuy (14), giải cứu (14), tiktok (13), chấn động (11), ko (8).

## Top Confused Pairs

| gold_label | predicted_label | count | model_name | scenario |
| --- | --- | --- | --- | --- |
| T13 | T10 | 30 | RandomForest | 05_Balanced |
| T10 | T13 | 18 | XGBoost | 03_Full_Clean |
| T10 | T13 | 15 | LogisticRegression | 01_Raw_Data |
| T13 | T10 | 15 | LinearSVC | 01_Raw_Data |
| T10 | T13 | 13 | LinearSVC | 01_Raw_Data |
| T13 | T10 | 13 | LogisticRegression | 01_Raw_Data |
| T03 | T10 | 13 | RandomForest | 05_Balanced |
| T02 | T10 | 10 | RandomForest | 05_Balanced |
| T10 | T13 | 9 | RandomForest | 05_Balanced |
| T02 | T03 | 8 | RandomForest | 05_Balanced |
| T06 | T10 | 8 | RandomForest | 05_Balanced |
| T10 | T15 | 8 | XGBoost | 03_Full_Clean |
| T12 | T10 | 8 | RandomForest | 05_Balanced |
| T03 | T17 | 8 | XGBoost | 03_Full_Clean |
| T03 | T02 | 7 | LogisticRegression | 01_Raw_Data |

## Qualitative Examples

| record_id | gold_label | predicted_label | model_name | scenario | reason_guess | text |
| --- | --- | --- | --- | --- | --- | --- |
| REC_002424 | T12 | T17 | LogisticRegression | 01_Raw_Data | keyword overfitting or label boundary ambiguity | Siết sát hạch lái xe, tỷ lệ đỗ đường trường giảm sâu #VnExpress |
| REC_011028 | T10 | T13 | LogisticRegression | 01_Raw_Data | keyword overfitting or label boundary ambiguity | Noo Phước Thịnh lộ tin nhắn riêng tư với chàng trai người Trung Quốc |
| REC_008844 | T13 | T09 | LogisticRegression | 01_Raw_Data | keyword overfitting or label boundary ambiguity | Nữ tài xế dừng đèn đỏ bị xe buýt tông, hơn 10 người hợp sức nâng xe cứu nạn. #Vietnamnet #Thờisự #PT |
| REC_008668 | T13 | T04 | LogisticRegression | 01_Raw_Data | long/noisy caption | BÉ TRAI 9 TUỔI NGƯỜI TÀY NGUY KỊCH VÌ VIÊM NÃO NHẬT BẢN, CHA MẸ NGHÈO KIỆT QUỆ Ngày nào cũng vậy, mỗi khi ngồi bên giường bệnh của con, anh Lê Văn Hiếu (SN 1991, thôn Đo, xã Bình Xa, tỉnh Tuyên Quang) lặng lẽ dõi theo từng nhịp thở phát ra từ máy móc. Bệnh tình của bé Hưng ngày càng nặng khiến anh không dám rời mắt, bởi chỉ một phút lơ là cũng có thể đe dọa đến tính mạng của con. Trước đó, vào tháng 6/2025, bé Hưng bất ngờ sốt cao kéo dài. Gia đình đưa con đến Bệnh viện Đa khoa huyện Hàm Yên thăm khám và chuyển lên Bệnh viện Đa khoa tỉnh Tuyên Quang điều trị. Sau một thời gian, tình trạng của bé vẫn diễn biến xấu. Rạng sáng ngày 29/6, Hưng lên cơn co giật, tình trạng bất thường nên bác sĩ chuyển bé lên cấp cứu tại Bệnh viện Nhi Trung ương. Tại đây, kết quả xét nghiệm khiến cả gia đình suy sụp: bé Hưng mắc viêm não Nhật Bản. Sau 9 ngày cấp cứu tại Bệnh viện Nhi Trung ương, Hưng được chuyển sang Bệnh viện Bệnh Nhiệt đới Trung ương để tiếp tục điều trị chuyên sâu. “Giữa tháng 7/2025, các bác sĩ buộc phải mở nội khí quản vì con không thể tự thở. Hưng rơi vào hôn mê sâu gần một tháng, mọi sinh hoạt đều phụ thuộc vào ống xông dạ dày. Đó là quãng thời gian khó khăn nhất khiến vợ chồng tôi suy sụp tinh thần. Có lúc chúng tôi nghĩ con sẽ không qua khỏi”, anh Hiếu nghẹn ngào kể. Biến chứng liên tục khiến bé Hưng nhiều lần phải cấp cứu, đe doạ tính mạng. Cứ như vậy, vòng tròn cấp cứu từ các bệnh viện ở Hà Nội rồi quay về tỉnh diễn ra liên tục trong gần một năm qua. Hiện tại, bé Hưng đang điều trị tại Bệnh viện Đa khoa tỉnh Tuyên Quang trong tình trạng hoàn toàn phụ thuộc vào máy thở và ống xông. Theo anh Hiếu, gần một năm qua, chi phí điều trị cho Hưng đã vượt quá 500 triệu đồng. Gia đình phải vay ngân hàng 100 triệu đồng, số còn lại nhờ anh em, bạn bè và người thân hỗ trợ. “Bác sĩ nói, hành trình chữa bệnh cho con còn rất dài do tổn thương phổi nặng, khả năng phục hồi khó khăn. Để duy trì sự sống, Hưng phải sử dụng nhiều loại kháng sinh và thuốc đặc trị đắt tiền, trong đó có nhiều loại nằm ngoài danh mục bảo hiểm y tế chi trả”, anh Hiếu nghẹn ngào. Lúc này, vòng tay hỗ trợ từ cộng đồng sẽ giúp cháu Hưng có cơ hội hồi phục, giúp gia đình anh Hiếu vượt qua giai đoạn khó khăn. #Vietnamnet #Bạnđọc #Gócsẻchia #PT |
| REC_010402 | T03 | T10 | LogisticRegression | 01_Raw_Data | caption too short | Tình hình mới nhất của Miu Lê |
| REC_002582 | T01 | T12 | LogisticRegression | 01_Raw_Data | long/noisy caption | '40 năm sau Đổi Mới, điệp khúc cũ "Đưa luật vào cuộc sống" vẫn như một khẩu hiệu mới, phản ánh nhu cầu bức thiết của xã hội. Đáp lại nhu cầu này là tình trạng "lỗi tại thực thi". Nhiều bộ luật vẫn phải chờ nghị định, thông tư "lắp chân" để đi vào cuộc sống', góc nhìn của PGS. TS Võ Trí Hảo #VnExpress #Góc_nhìn |
| REC_002925 | T10 | T11 | LogisticRegression | 01_Raw_Data | keyword overfitting or label boundary ambiguity | Miss World lần đầu tổ chức tại Việt Nam #VnExpress |
| REC_005899 | T14 | T13 | LogisticRegression | 01_Raw_Data | keyword overfitting or label boundary ambiguity | Gần 9.000 nhân viên tại một tập đoàn công nghệ vừa bị 'mời' nghỉ hưu sớm, có người đã gắn bó hàng thập kỷ cũng trong diện tinh giản |
| REC_005841 | T04 | T12 | LogisticRegression | 01_Raw_Data | keyword overfitting or label boundary ambiguity | Loạt “đặc quyền y tế” miễn phí, thông minh tại Trạm Công Dân Số dành cho người dân |
| REC_004814 | T15 | T13 | LogisticRegression | 01_Raw_Data | keyword overfitting or label boundary ambiguity | Học hỏi menu của người phụ nữ làm mâm cơm chưa đến 100k cho gia đình 5 người ăn vô tư |


## Streamlit Model Zoo Note

Dùng `model_zoo/model_registry.json` hoặc `.csv` để load 4 model recommended hoặc toàn bộ 20 scenario/model artifacts. Các artifact trong model_zoo là symlink/copy tới model gốc.

## Limitations

- TF-IDF phụ thuộc surface words.
- Tree-based models kém hơn mô hình tuyến tính trên sparse high-dimensional text features.
- Macro-F1 quan trọng do imbalance.
- Kết quả phụ thuộc split đã chia sẵn.

# Traditional ML Results Summary

| scenario | model_name | text_column | accuracy_val | macro_f1_val | weighted_f1_val | accuracy_test | macro_f1_test | weighted_f1_test | train_time_sec | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01_Raw_Data | LogisticRegression | post_content_for_labeling | 0.7252 | 0.6492 | 0.7244 | 0.7601 | 0.6954 | 0.7578 | 5.2955 | success |
| 01_Raw_Data | LinearSVC | post_content_for_labeling | 0.7300 | 0.6455 | 0.7201 | 0.7589 | 0.6867 | 0.7522 | 0.7775 | success |
| 02_Basic_Clean | LinearSVC | post_content_for_labeling | 0.7312 | 0.6453 | 0.7209 | 0.7578 | 0.6938 | 0.7520 | 0.7627 | success |
| 04_No_Stopwords | LinearSVC | post_content_for_labeling | 0.7264 | 0.6452 | 0.7242 | 0.7506 | 0.6672 | 0.7480 | 0.6752 | success |
| 05_Balanced | LogisticRegression | post_content_for_labeling | 0.7204 | 0.6407 | 0.7147 | 0.7530 | 0.6841 | 0.7488 | 6.1702 | success |
| 02_Basic_Clean | LogisticRegression | post_content_for_labeling | 0.7192 | 0.6391 | 0.7190 | 0.7613 | 0.7014 | 0.7596 | 5.1832 | success |
| 05_Balanced | LinearSVC | post_content_for_labeling | 0.7204 | 0.6390 | 0.7109 | 0.7494 | 0.6876 | 0.7435 | 2.8838 | success |
| 03_Full_Clean | LogisticRegression | post_content_for_labeling | 0.7204 | 0.6366 | 0.7203 | 0.7601 | 0.6996 | 0.7587 | 5.0297 | success |
| 03_Full_Clean | LinearSVC | post_content_for_labeling | 0.7240 | 0.6358 | 0.7187 | 0.7542 | 0.6698 | 0.7489 | 1.6304 | success |
| 04_No_Stopwords | LogisticRegression | post_content_for_labeling | 0.7168 | 0.6314 | 0.7153 | 0.7625 | 0.6971 | 0.7604 | 6.3428 | success |
| 05_Balanced | RandomForest | post_content_for_labeling | 0.6714 | 0.5796 | 0.6542 | 0.7088 | 0.6139 | 0.6923 | 2.6626 | success |
| 04_No_Stopwords | RandomForest | post_content_for_labeling | 0.6762 | 0.5788 | 0.6520 | 0.6957 | 0.5956 | 0.6752 | 0.9285 | success |
| 01_Raw_Data | RandomForest | post_content_for_labeling | 0.6440 | 0.5698 | 0.6286 | 0.6766 | 0.5860 | 0.6593 | 2.5223 | success |
| 03_Full_Clean | RandomForest | post_content_for_labeling | 0.6177 | 0.5624 | 0.6101 | 0.6706 | 0.6128 | 0.6651 | 1.2818 | success |
| 02_Basic_Clean | RandomForest | post_content_for_labeling | 0.6141 | 0.5600 | 0.6054 | 0.6718 | 0.6142 | 0.6670 | 1.6660 | success |
| 03_Full_Clean | XGBoost | post_content_for_labeling | 0.5986 | 0.5458 | 0.6053 | 0.6575 | 0.6189 | 0.6671 | 67.3779 | success |
| 05_Balanced | XGBoost | post_content_for_labeling | 0.6033 | 0.5379 | 0.6010 | 0.6647 | 0.6137 | 0.6664 | 108.3053 | success |
| 02_Basic_Clean | XGBoost | post_content_for_labeling | 0.5938 | 0.5369 | 0.6000 | 0.6599 | 0.6145 | 0.6685 | 66.9806 | success |
| 01_Raw_Data | XGBoost | post_content_for_labeling | 0.5938 | 0.5358 | 0.5993 | 0.6516 | 0.6178 | 0.6603 | 79.1631 | success |
| 04_No_Stopwords | XGBoost | post_content_for_labeling | 0.5962 | 0.5345 | 0.6004 | 0.6575 | 0.6078 | 0.6680 | 81.6302 | success |

Sorted by validation Macro-F1, then validation Weighted-F1.

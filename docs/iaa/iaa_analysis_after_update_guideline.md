# IAA Analysis After Guideline Update

Generated: 2026-06-08 15:00:45

## Mục tiêu

Phân tích mức nhất quán gán nhãn topic của 3 annotator (Nhung, Yen, Han) cho vòng pilot sau khi cập nhật guideline. Report này chỉ trình bày metric và phân tích phân phối/bất đồng, không bao gồm phần gợi ý cập nhật guideline.

## Dữ liệu

Nguồn: `data/04_Labeling_Pilot/Topic Annotation Pilot Set 100 [2] - IAA_Merge.csv`. File có 100 dòng, trong đó 98 dòng đủ cả 3 nhãn annotator và 2 dòng thiếu ít nhất 1 nhãn annotator.

## Phương pháp

- Fleiss' kappa được tính trên các dòng đủ cả 3 nhãn annotator.
- Cohen's kappa được tính từng cặp annotator trên các dòng mà cả hai người trong cặp đều có nhãn.
- `full_agreement` nghĩa là 3 người gán cùng một nhãn; `partial_disagreement` nghĩa là 2 người cùng nhãn và 1 người khác; `complete_disagreement` nghĩa là 3 người gán 3 nhãn khác nhau; `incomplete` nghĩa là thiếu ít nhất 1 nhãn annotator.
- Universe nhãn gồm 18 topic labels của guideline để xác định nhãn chưa được dùng trong tập này.

## Universe nhãn

| label_id | label |
| --- | --- |
| T01 | POLITICS |
| T02 | ECONOMY_BUSINESS_AND_FINANCE |
| T03 | CRIME_LAW_AND_JUSTICE |
| T04 | HEALTH |
| T05 | EDUCATION |
| T06 | SCIENCE_AND_TECHNOLOGY |
| T07 | ENVIRONMENT |
| T08 | WEATHER |
| T09 | DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT |
| T10 | ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA |
| T11 | SPORT |
| T12 | SOCIETY |
| T13 | HUMAN_INTEREST |
| T14 | LABOR |
| T15 | LIFESTYLE_AND_LEISURE |
| T16 | WORLD_INTERNATIONAL |
| T17 | TRANSPORT_INFRASTRUCTURE |
| T18 | OTHER_UNCLEAR |

## Tổng quan chỉ số

| dataset | rows | valid_rows | incomplete | fleiss_kappa | mean_cohen_kappa | used_labels | unused_labels | full | partial | complete |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pilot after guideline update - Set 100 [2] | 100 | 98 | 2 | 0.8514 | 0.8523 | 15 | 3 | 79 | 19 | 0 |

## Insight chính

- Fleiss' kappa của vòng sau cập nhật guideline là 0.8514; Cohen's kappa trung bình từng cặp là 0.8523.
- Tỷ lệ dòng có bất đồng là 19.0%: 19 dòng khác 1 phần và 0 dòng khác hoàn toàn; có 2 dòng thiếu nhãn.
- Các nhãn majority phổ biến nhất là ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA (24 dòng), CRIME_LAW_AND_JUSTICE (18 dòng), HUMAN_INTEREST (14 dòng).
- Các nhãn phát sinh bất đồng nhiều nhất là HUMAN_INTEREST (10 dòng), CRIME_LAW_AND_JUSTICE (7 dòng), OTHER_UNCLEAR (5 dòng); cặp bất đồng nhiều nhất là HUMAN_INTEREST vs LIFESTYLE_AND_LEISURE (3 dòng).
- Annotator giống trung bình nhóm nhất là Yen (Cohen trung bình 0.8712, khớp majority của 2 người còn lại 96.3%); annotator khác biệt nhất là Nhung (Cohen trung bình 0.8191, lệch khỏi majority của 2 người còn lại 13.2%).

## Pilot after guideline update - Set 100 [2]

Phạm vi dòng: Toàn bộ file sau cập nhật guideline (100 dòng). Tổng dòng: 100; dòng đủ 3 nhãn: 98; dòng thiếu nhãn: 2.

Nhãn được dùng: 15/18. Nhãn không được dùng: 3 (HEALTH, EDUCATION, LABOR).

### Fleiss' kappa

| n_items | n_raters | observed_agreement | expected_agreement | fleiss_kappa |
| --- | --- | --- | --- | --- |
| 98 | 3 | 0.8707 | 0.1303 | 0.8514 |

### Cohen's kappa từng cặp

| pair | n | observed_agreement | expected_agreement | cohen_kappa |
| --- | --- | --- | --- | --- |
| Nhung vs Yen | 98 | 0.8469 | 0.1318 | 0.8237 |
| Nhung vs Han | 99 | 0.8384 | 0.1287 | 0.8145 |
| Yen vs Han | 99 | 0.9293 | 0.1299 | 0.9187 |

### Annotator giống trung bình nhóm / khác biệt so với nhóm

| average_similarity_rank | outlier_rank | annotator | avg_pairwise_cohen | avg_pairwise_agreement | avg_pairwise_disagreement_rate | other2_consensus_rows | match_other2_consensus_rows | match_other2_consensus_rate | minority_when_other2_agree_rows | minority_when_other2_agree_rate | label_distribution_l1_to_group_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 3 | Yen | 0.8712 | 88.8% | 11.2% | 82 | 79 | 96.3% | 3 | 3.7% | 0.0713 |
| 2 | 2 | Han | 0.8666 | 88.4% | 11.6% | 83 | 79 | 95.2% | 4 | 4.8% | 0.0624 |
| 3 | 1 | Nhung | 0.8191 | 84.3% | 15.7% | 91 | 79 | 86.8% | 12 | 13.2% | 0.1050 |

### Tần suất đồng thuận/bất đồng

| agreement_type | rows | pct_all_rows |
| --- | --- | --- |
| full_agreement | 79 | 79.0% |
| partial_disagreement | 19 | 19.0% |
| complete_disagreement | 0 | 0.0% |
| incomplete | 2 | 2.0% |

### Phân phối nhãn cấp dòng theo majority vote

| label | rows | pct_valid_rows |
| --- | --- | --- |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 24 | 24.5% |
| CRIME_LAW_AND_JUSTICE | 18 | 18.4% |
| HUMAN_INTEREST | 14 | 14.3% |
| TRANSPORT_INFRASTRUCTURE | 7 | 7.1% |
| WORLD_INTERNATIONAL | 5 | 5.1% |
| SCIENCE_AND_TECHNOLOGY | 5 | 5.1% |
| DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | 5 | 5.1% |
| ECONOMY_BUSINESS_AND_FINANCE | 4 | 4.1% |
| WEATHER | 3 | 3.1% |
| SOCIETY | 3 | 3.1% |
| SPORT | 3 | 3.1% |
| OTHER_UNCLEAR | 3 | 3.1% |
| ENVIRONMENT | 2 | 2.0% |
| POLITICS | 1 | 1.0% |
| LIFESTYLE_AND_LEISURE | 1 | 1.0% |
| INCOMPLETE_MISSING_LABELS | 2 | NA |

### Phân phối nhãn theo toàn bộ lượt gán

| label | total_assignments | Nhung | Yen | Han | assignment_pct |
| --- | --- | --- | --- | --- | --- |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 73 | 23 | 25 | 25 | 24.5% |
| CRIME_LAW_AND_JUSTICE | 55 | 20 | 18 | 17 | 18.5% |
| HUMAN_INTEREST | 40 | 15 | 12 | 13 | 13.4% |
| TRANSPORT_INFRASTRUCTURE | 19 | 5 | 8 | 6 | 6.4% |
| DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | 15 | 5 | 5 | 5 | 5.0% |
| WORLD_INTERNATIONAL | 15 | 5 | 5 | 5 | 5.0% |
| SCIENCE_AND_TECHNOLOGY | 14 | 5 | 5 | 4 | 4.7% |
| ECONOMY_BUSINESS_AND_FINANCE | 13 | 4 | 4 | 5 | 4.4% |
| OTHER_UNCLEAR | 12 | 5 | 3 | 4 | 4.0% |
| SOCIETY | 9 | 3 | 3 | 3 | 3.0% |
| SPORT | 9 | 3 | 3 | 3 | 3.0% |
| WEATHER | 9 | 3 | 3 | 3 | 3.0% |
| ENVIRONMENT | 6 | 1 | 2 | 3 | 2.0% |
| POLITICS | 5 | 2 | 1 | 2 | 1.7% |
| LIFESTYLE_AND_LEISURE | 4 | 0 | 2 | 2 | 1.3% |
| EDUCATION | 0 | 0 | 0 | 0 | 0.0% |
| HEALTH | 0 | 0 | 0 | 0 | 0.0% |
| LABOR | 0 | 0 | 0 | 0 | 0.0% |

### Nhãn không hề phát sinh bất đồng khi xuất hiện

| label_id | label | rows_with_label | assignment_count_valid |
| --- | --- | --- | --- |
| T08 | WEATHER | 3 | 9 |
| T09 | DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | 5 | 15 |
| T11 | SPORT | 3 | 9 |
| T12 | SOCIETY | 3 | 9 |
| T16 | WORLD_INTERNATIONAL | 5 | 15 |

### Nhãn hay phát sinh bất đồng

| label_id | label | rows_with_label | disagreement_rows_with_label | disagreement_rate_when_label_appears | disagreement_assignment_count |
| --- | --- | --- | --- | --- | --- |
| T13 | HUMAN_INTEREST | 18 | 10 | 55.6% | 16 |
| T03 | CRIME_LAW_AND_JUSTICE | 22 | 7 | 31.8% | 10 |
| T18 | OTHER_UNCLEAR | 6 | 5 | 83.3% | 7 |
| T17 | TRANSPORT_INFRASTRUCTURE | 8 | 4 | 50.0% | 7 |
| T15 | LIFESTYLE_AND_LEISURE | 3 | 3 | 100.0% | 4 |
| T10 | ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 25 | 3 | 12.0% | 5 |
| T07 | ENVIRONMENT | 3 | 2 | 66.7% | 3 |
| T01 | POLITICS | 3 | 2 | 66.7% | 2 |
| T06 | SCIENCE_AND_TECHNOLOGY | 5 | 1 | 20.0% | 2 |
| T02 | ECONOMY_BUSINESS_AND_FINANCE | 5 | 1 | 20.0% | 1 |

### Cặp nhãn hay bị bất đồng với nhau

| label_a | label_b | disagreement_rows | pct_of_disagreement_rows |
| --- | --- | --- | --- |
| HUMAN_INTEREST | LIFESTYLE_AND_LEISURE | 3 | 15.8% |
| CRIME_LAW_AND_JUSTICE | TRANSPORT_INFRASTRUCTURE | 3 | 15.8% |
| HUMAN_INTEREST | OTHER_UNCLEAR | 3 | 15.8% |
| CRIME_LAW_AND_JUSTICE | HUMAN_INTEREST | 2 | 10.5% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | HUMAN_INTEREST | 2 | 10.5% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | OTHER_UNCLEAR | 1 | 5.3% |
| ENVIRONMENT | OTHER_UNCLEAR | 1 | 5.3% |
| CRIME_LAW_AND_JUSTICE | ENVIRONMENT | 1 | 5.3% |
| POLITICS | TRANSPORT_INFRASTRUCTURE | 1 | 5.3% |
| CRIME_LAW_AND_JUSTICE | POLITICS | 1 | 5.3% |
| ECONOMY_BUSINESS_AND_FINANCE | SCIENCE_AND_TECHNOLOGY | 1 | 5.3% |

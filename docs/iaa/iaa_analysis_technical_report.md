# IAA Analysis Technical Report

Generated: 2026-06-07 13:13:26

## Mục tiêu

Phân tích mức nhất quán gán nhãn topic của 3 annotator (Nhung, Yen, Han) cho 2 vòng pilot: set 100, set 400, và 4 batch 100 dòng trong set 400.

## Phương pháp

- Fleiss' kappa được tính trên các dòng đủ cả 3 nhãn annotator.
- Cohen's kappa được tính từng cặp annotator trên các dòng mà cả hai người trong cặp đều có nhãn.
- `full_agreement` nghĩa là 3 người gán cùng một nhãn; `partial_disagreement` nghĩa là 2 người cùng nhãn và 1 người khác; `complete_disagreement` nghĩa là 3 người gán 3 nhãn khác nhau; `incomplete` nghĩa là thiếu ít nhất 1 nhãn annotator.
- Universe nhãn gồm 18 topic labels xuất hiện trong toàn bộ pilot/final-train, dùng để xác định nhãn chưa được dùng ở từng tập.

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
| Pilot set 100 + 400 (500 rows) | 500 | 497 | 3 | 0.7905 | 0.7906 | 18 | 0 | 368 | 104 | 25 |
| Pilot set 100 | 100 | 100 | 0 | 0.7717 | 0.7724 | 17 | 1 | 70 | 27 | 3 |
| Pilot set 400 | 400 | 397 | 3 | 0.7949 | 0.7950 | 18 | 0 | 298 | 77 | 22 |
| Pilot set 400 - Batch 1 | 100 | 98 | 2 | 0.7917 | 0.7921 | 17 | 1 | 74 | 17 | 7 |
| Pilot set 400 - Batch 2 | 100 | 100 | 0 | 0.8016 | 0.8017 | 18 | 0 | 76 | 19 | 5 |
| Pilot set 400 - Batch 3 | 100 | 100 | 0 | 0.8141 | 0.8144 | 17 | 1 | 78 | 16 | 6 |
| Pilot set 400 - Batch 4 | 100 | 99 | 1 | 0.7693 | 0.7694 | 18 | 0 | 70 | 25 | 4 |

## Tổng quan phân phối và bất đồng trong 500 dòng

Gộp pilot set 100 và pilot set 400 thành 500 dòng không trùng `record_id`. Phân phối cấp dòng dùng majority vote trên các dòng đủ 3 annotator; các dòng thiếu nhãn được ghi riêng là `INCOMPLETE_MISSING_LABELS`.

### Phân phối nhãn cấp dòng trong 500 dòng

| label | rows | pct_valid_rows | pct_all_500_rows |
| --- | --- | --- | --- |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 82 | 16.5% | 16.4% |
| CRIME_LAW_AND_JUSTICE | 79 | 15.9% | 15.8% |
| HUMAN_INTEREST | 46 | 9.3% | 9.2% |
| POLITICS | 45 | 9.1% | 9.0% |
| ECONOMY_BUSINESS_AND_FINANCE | 42 | 8.5% | 8.4% |
| NO_MAJORITY_TIE | 25 | 5.0% | 5.0% |
| SPORT | 21 | 4.2% | 4.2% |
| OTHER_UNCLEAR | 20 | 4.0% | 4.0% |
| EDUCATION | 19 | 3.8% | 3.8% |
| WORLD_INTERNATIONAL | 18 | 3.6% | 3.6% |
| HEALTH | 17 | 3.4% | 3.4% |
| DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | 16 | 3.2% | 3.2% |
| TRANSPORT_INFRASTRUCTURE | 16 | 3.2% | 3.2% |
| SCIENCE_AND_TECHNOLOGY | 14 | 2.8% | 2.8% |
| SOCIETY | 10 | 2.0% | 2.0% |
| LIFESTYLE_AND_LEISURE | 8 | 1.6% | 1.6% |
| WEATHER | 8 | 1.6% | 1.6% |
| LABOR | 7 | 1.4% | 1.4% |
| ENVIRONMENT | 4 | 0.8% | 0.8% |
| INCOMPLETE_MISSING_LABELS | 3 | NA | 0.6% |

### Phân phối nhãn theo lượt gán trong 500 dòng

| label | total_assignments | Nhung | Yen | Han | assignment_pct |
| --- | --- | --- | --- | --- | --- |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 249 | 72 | 89 | 88 | 16.7% |
| CRIME_LAW_AND_JUSTICE | 237 | 86 | 72 | 79 | 15.9% |
| HUMAN_INTEREST | 156 | 58 | 49 | 49 | 10.4% |
| POLITICS | 141 | 43 | 47 | 51 | 9.4% |
| ECONOMY_BUSINESS_AND_FINANCE | 126 | 43 | 36 | 47 | 8.4% |
| OTHER_UNCLEAR | 86 | 25 | 35 | 26 | 5.8% |
| SPORT | 63 | 21 | 21 | 21 | 4.2% |
| WORLD_INTERNATIONAL | 57 | 16 | 22 | 19 | 3.8% |
| EDUCATION | 56 | 22 | 17 | 17 | 3.7% |
| HEALTH | 54 | 17 | 20 | 17 | 3.6% |
| DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | 51 | 18 | 18 | 15 | 3.4% |
| TRANSPORT_INFRASTRUCTURE | 47 | 16 | 16 | 15 | 3.1% |
| SCIENCE_AND_TECHNOLOGY | 43 | 16 | 13 | 14 | 2.9% |
| SOCIETY | 38 | 9 | 11 | 18 | 2.5% |
| LIFESTYLE_AND_LEISURE | 35 | 16 | 10 | 9 | 2.3% |
| WEATHER | 25 | 8 | 10 | 7 | 1.7% |
| LABOR | 20 | 8 | 9 | 3 | 1.3% |
| ENVIRONMENT | 10 | 3 | 2 | 5 | 0.7% |

### Nhãn phát sinh bất đồng trong 500 dòng

| label_id | label | rows_with_label | disagreement_rows_with_label | disagreement_rate_when_label_appears | disagreement_assignment_count |
| --- | --- | --- | --- | --- | --- |
| T13 | HUMAN_INTEREST | 78 | 46 | 59.0% | 60 |
| T10 | ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 101 | 35 | 34.7% | 51 |
| T18 | OTHER_UNCLEAR | 46 | 29 | 63.0% | 32 |
| T01 | POLITICS | 61 | 26 | 42.6% | 36 |
| T03 | CRIME_LAW_AND_JUSTICE | 91 | 24 | 26.4% | 36 |
| T15 | LIFESTYLE_AND_LEISURE | 25 | 23 | 92.0% | 29 |
| T02 | ECONOMY_BUSINESS_AND_FINANCE | 53 | 22 | 41.5% | 33 |
| T12 | SOCIETY | 23 | 18 | 78.3% | 23 |
| T16 | WORLD_INTERNATIONAL | 25 | 11 | 44.0% | 15 |
| T05 | EDUCATION | 23 | 9 | 39.1% | 14 |
| T04 | HEALTH | 23 | 9 | 39.1% | 12 |
| T14 | LABOR | 10 | 7 | 70.0% | 11 |
| T06 | SCIENCE_AND_TECHNOLOGY | 18 | 7 | 38.9% | 10 |
| T17 | TRANSPORT_INFRASTRUCTURE | 18 | 5 | 27.8% | 8 |
| T09 | DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | 20 | 5 | 25.0% | 6 |
| T07 | ENVIRONMENT | 5 | 4 | 80.0% | 7 |
| T08 | WEATHER | 10 | 3 | 30.0% | 4 |

### Cặp nhãn bất đồng trong 500 dòng (top 20)

| label_a | label_b | disagreement_rows | pct_of_disagreement_rows |
| --- | --- | --- | --- |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | HUMAN_INTEREST | 19 | 14.7% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | OTHER_UNCLEAR | 9 | 7.0% |
| HUMAN_INTEREST | LIFESTYLE_AND_LEISURE | 9 | 7.0% |
| LIFESTYLE_AND_LEISURE | OTHER_UNCLEAR | 8 | 6.2% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | LIFESTYLE_AND_LEISURE | 8 | 6.2% |
| HUMAN_INTEREST | SOCIETY | 7 | 5.4% |
| CRIME_LAW_AND_JUSTICE | POLITICS | 7 | 5.4% |
| HUMAN_INTEREST | OTHER_UNCLEAR | 7 | 5.4% |
| POLITICS | WORLD_INTERNATIONAL | 6 | 4.7% |
| CRIME_LAW_AND_JUSTICE | OTHER_UNCLEAR | 5 | 3.9% |
| ECONOMY_BUSINESS_AND_FINANCE | OTHER_UNCLEAR | 5 | 3.9% |
| POLITICS | SOCIETY | 5 | 3.9% |
| HEALTH | HUMAN_INTEREST | 5 | 3.9% |
| ECONOMY_BUSINESS_AND_FINANCE | HUMAN_INTEREST | 4 | 3.1% |
| ECONOMY_BUSINESS_AND_FINANCE | POLITICS | 4 | 3.1% |
| CRIME_LAW_AND_JUSTICE | HUMAN_INTEREST | 3 | 2.3% |
| CRIME_LAW_AND_JUSTICE | SOCIETY | 3 | 2.3% |
| ECONOMY_BUSINESS_AND_FINANCE | LIFESTYLE_AND_LEISURE | 3 | 2.3% |
| DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | HUMAN_INTEREST | 3 | 2.3% |
| CRIME_LAW_AND_JUSTICE | WORLD_INTERNATIONAL | 3 | 2.3% |

## Insight chính

- Fleiss' kappa tăng từ 0.7717 ở pilot 100 lên 0.7949 ở pilot 400 (delta 0.0232), cho thấy mức nhất quán 3 người tốt hơn ở vòng 2.
- Tỷ lệ dòng có bất đồng giảm từ 30.0% ở pilot 100 xuống 24.8% ở pilot 400. Pilot 400 còn 3 dòng thiếu nhãn của Nhung/Yen nên bị loại khỏi phép tính IAA 3 người.
- Batch ổn định nhất trong file 400 là Pilot set 400 - Batch 3 với Fleiss 0.8141; batch yếu nhất là Pilot set 400 - Batch 4 với Fleiss 0.7693.
- Trong pilot 400, nhãn phát sinh bất đồng nhiều nhất là HUMAN_INTEREST (38 dòng có bất đồng khi nhãn này xuất hiện).
- Cặp nhãn hay bị đặt cạnh nhau trong các dòng bất đồng nhất của pilot 400 là ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA vs HUMAN_INTEREST (17 dòng).
- Ở pilot 400, các nhãn được dùng nhưng không phát sinh bất đồng là: SPORT.
- Trong 500 dòng gộp, các nhãn majority phổ biến nhất là ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA (82 dòng), CRIME_LAW_AND_JUSTICE (79 dòng), HUMAN_INTEREST (46 dòng); các nhãn phát sinh bất đồng nhiều nhất là HUMAN_INTEREST (46 dòng), ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA (35 dòng), OTHER_UNCLEAR (29 dòng); cặp bất đồng nhiều nhất là ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA vs HUMAN_INTEREST (19 dòng).
- Về annotator, trong pilot 400 người giống trung bình nhóm nhất là Han (Cohen trung bình 0.7984, khớp majority của 2 người còn lại 92.8%); người khác biệt nhất là Yen (Cohen trung bình 0.7889, lệch khỏi majority của 2 người còn lại 9.1%).

## Annotator giống trung bình nhóm / khác biệt so với nhóm

- `most_average_annotator` được xếp theo Cohen's kappa trung bình với 2 annotator còn lại, sau đó xét tỷ lệ khớp với majority của 2 người còn lại và độ lệch phân phối nhãn so với trung bình nhóm.
- `outlier_annotator` là chiều ngược lại: Cohen trung bình thấp hơn, ít khớp với majority của 2 người còn lại hơn, hoặc có phân phối nhãn lệch hơn.
- `match_other2_consensus` chỉ tính trên các dòng mà 2 annotator còn lại đồng thuận; đây là thước đo trực quan xem annotator đó có hay là người thứ ba khác ý kiến không.
- `label_dist_l1` càng thấp thì phân phối nhãn của annotator càng gần phân phối trung bình nhóm; chỉ số này hỗ trợ phát hiện bias dùng nhãn, không thay thế Cohen/majority agreement.

| dataset | most_average_annotator | most_average_avg_cohen | most_average_match_other2_consensus | outlier_annotator | outlier_avg_cohen | outlier_minority_when_other2_agree | outlier_label_dist_l1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Pilot set 100 + 400 (500 rows) | Nhung | 0.7971 | 92.7% | Yen | 0.7781 | 11.1% | 0.0933 |
| Pilot set 100 | Nhung | 0.7936 | 93.3% | Yen | 0.7349 | 18.6% | 0.2200 |
| Pilot set 400 | Han | 0.7984 | 92.8% | Yen | 0.7889 | 9.1% | 0.0846 |
| Pilot set 400 - Batch 1 | Nhung | 0.8014 | 94.9% | Yen | 0.7791 | 9.8% | 0.1633 |
| Pilot set 400 - Batch 2 | Nhung | 0.8151 | 95.0% | Yen | 0.7868 | 10.6% | 0.1467 |
| Pilot set 400 - Batch 3 | Yen | 0.8272 | 96.3% | Nhung | 0.7999 | 9.3% | 0.1333 |
| Pilot set 400 - Batch 4 | Han | 0.7767 | 90.9% | Yen | 0.7600 | 12.5% | 0.1032 |

## Gợi ý những chỉnh sửa cho phiên bản guideline tiếp theo

- Gợi ý ưu tiên chỉnh sửa các nhãn/cụm nhãn gây bất đồng nhiều nhất trong pilot 400: `HUMAN_INTEREST`, `ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA`, `LIFESTYLE_AND_LEISURE`, `OTHER_UNCLEAR`, `ECONOMY_BUSINESS_AND_FINANCE`, `CRIME_LAW_AND_JUSTICE`, `SOCIETY`.
- Với các nhãn có tỷ lệ bất đồng cao khi xuất hiện như `LIFESTYLE_AND_LEISURE` (90.9%), `SOCIETY` (77.8%), `HUMAN_INTEREST` (58.5%) và `OTHER_UNCLEAR` (58.1%), phiên bản guideline tiếp theo nên bổ sung ví dụ hoặc hướng dẫn cụ thể.
- Nên thêm decision tree phân biệt ranh giới cho annotator: xác định topic chính trước, sau đó kiểm tra các cặp ranh giới dễ nhầm, cuối cùng mới dùng `OTHER_UNCLEAR` nếu không đủ bằng chứng.
- Nên tạo một phụ lục guideline riêng cho các case giáp ranh, có thể lấy trực tiếp từ những dòng bất đồng trong pilot 400 và ghi rõ nhãn đúng sau adjudication cùng lý do chọn nhãn.
- Sau khi cập nhật guideline, nên chạy một mini-calibration 50-100 dòng tập trung vào các cặp nhãn dưới đây trước khi bước sang batch gán nhãn lớn hơn.

### Gợi ý các ranh giới nên làm rõ

| suggested_boundary | pilot400_rows | suggested_revision |
| --- | --- | --- |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA vs HUMAN_INTEREST | 17 | Làm rõ khi nào bài về nhân vật/câu chuyện đời sống của người nổi tiếng vẫn là ARTS/MEDIA, và khi nào trọng tâm chuyển sang câu chuyện con người/cảm xúc nên là HUMAN_INTEREST. |
| HUMAN_INTEREST vs LIFESTYLE_AND_LEISURE | 9 | Tách nội dung trải nghiệm/câu chuyện cá nhân khỏi nội dung hướng dẫn thói quen, tiêu dùng, giải trí, du lịch, ăn uống hoặc phong cách sống. |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA vs LIFESTYLE_AND_LEISURE | 8 | Quy định ưu tiên ARTS/MEDIA khi trọng tâm là sản phẩm/hoạt động giải trí, văn hóa, showbiz, truyền thông; ưu tiên LIFESTYLE khi trọng tâm là hành vi sống, leisure hoặc lựa chọn cá nhân. |
| LIFESTYLE_AND_LEISURE vs OTHER_UNCLEAR | 7 | Nêu rõ nội dung ngắn về ăn chơi, du lịch, thời trang, giải trí cá nhân vẫn có thể là LIFESTYLE nếu có tín hiệu chủ đề đủ rõ; không đẩy sang OTHER_UNCLEAR chỉ vì thiếu văn cảnh rộng. |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA vs OTHER_UNCLEAR | 6 | Bổ sung tiêu chí nhận diện nội dung media/giải trí từ tên người, chương trình, phim, nhạc, sự kiện văn hóa; OTHER_UNCLEAR chỉ khi không xác định được thực thể hoặc sự kiện chính. |
| HUMAN_INTEREST vs OTHER_UNCLEAR | 5 | Nếu bài có câu chuyện con người, cảm xúc, hoàn cảnh cá nhân/cộng đồng đủ nhận diện thì ưu tiên HUMAN_INTEREST; nếu chỉ là caption/bình luận không có sự kiện hoặc chủ thể rõ thì mới OTHER_UNCLEAR. |
| HUMAN_INTEREST vs SOCIETY | 5 | Tách câu chuyện con người đơn lẻ khỏi vấn đề xã hội có phạm vi cộng đồng, chính sách, phúc lợi, dịch vụ công hoặc tác động xã hội rộng. |
| CRIME_LAW_AND_JUSTICE vs POLITICS | 5 | Ưu tiên CRIME/LAW khi trọng tâm là điều tra, xét xử, vi phạm, bắt giữ, án phạt; ưu tiên POLITICS khi trọng tâm là hoạt động nhà nước, đảng, bầu cử, ngoại giao hoặc quyết sách. |
| ECONOMY_BUSINESS_AND_FINANCE vs POLITICS | 4 | Làm rõ bài về chính sách kinh tế/tài chính: nếu trọng tâm là tác động thị trường, doanh nghiệp, ngân hàng, giá cả thì ECONOMY; nếu trọng tâm là quyết định/chủ thể quản trị nhà nước thì POLITICS. |

## Pilot set 100

Phạm vi dòng: Toàn bộ file set 100 (100 dòng). Tổng dòng: 100; dòng đủ 3 nhãn: 100; dòng thiếu nhãn: 0.

Nhãn được dùng: 17/18. Nhãn không được dùng: 1 (LABOR).

### Fleiss' kappa

| n_items | n_raters | observed_agreement | expected_agreement | fleiss_kappa |
| --- | --- | --- | --- | --- |
| 100 | 3 | 0.7900 | 0.0802 | 0.7717 |

### Cohen's kappa từng cặp

| pair | n | observed_agreement | expected_agreement | cohen_kappa |
| --- | --- | --- | --- | --- |
| Nhung vs Yen | 100 | 0.7600 | 0.0781 | 0.7397 |
| Nhung vs Han | 100 | 0.8600 | 0.0820 | 0.8475 |
| Yen vs Han | 100 | 0.7500 | 0.0739 | 0.7301 |

### Annotator giống trung bình nhóm / khác biệt so với nhóm

| average_similarity_rank | outlier_rank | annotator | avg_pairwise_cohen | avg_pairwise_agreement | avg_pairwise_disagreement_rate | other2_consensus_rows | match_other2_consensus_rows | match_other2_consensus_rate | minority_when_other2_agree_rows | minority_when_other2_agree_rate | label_distribution_l1_to_group_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 3 | Nhung | 0.7936 | 81.0% | 19.0% | 75 | 70 | 93.3% | 5 | 6.7% | 0.1533 |
| 2 | 2 | Han | 0.7888 | 80.5% | 19.5% | 76 | 70 | 92.1% | 6 | 7.9% | 0.1667 |
| 3 | 1 | Yen | 0.7349 | 75.5% | 24.5% | 86 | 70 | 81.4% | 16 | 18.6% | 0.2200 |

### Tần suất đồng thuận/bất đồng

| agreement_type | rows | pct_all_rows |
| --- | --- | --- |
| full_agreement | 70 | 70.0% |
| partial_disagreement | 27 | 27.0% |
| complete_disagreement | 3 | 3.0% |
| incomplete | 0 | 0.0% |

### Phân phối nhãn theo lượt gán

| label | total_assignments | Nhung | Yen | Han | assignment_pct |
| --- | --- | --- | --- | --- | --- |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 39 | 12 | 12 | 15 | 13.0% |
| CRIME_LAW_AND_JUSTICE | 35 | 14 | 9 | 12 | 11.7% |
| POLITICS | 30 | 11 | 9 | 10 | 10.0% |
| HUMAN_INTEREST | 27 | 10 | 10 | 7 | 9.0% |
| OTHER_UNCLEAR | 25 | 6 | 15 | 4 | 8.3% |
| ECONOMY_BUSINESS_AND_FINANCE | 24 | 10 | 5 | 9 | 8.0% |
| SPORT | 21 | 7 | 7 | 7 | 7.0% |
| EDUCATION | 18 | 6 | 6 | 6 | 6.0% |
| TRANSPORT_INFRASTRUCTURE | 18 | 6 | 6 | 6 | 6.0% |
| WORLD_INTERNATIONAL | 11 | 2 | 6 | 3 | 3.7% |
| DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | 10 | 3 | 4 | 3 | 3.3% |
| HEALTH | 10 | 3 | 2 | 5 | 3.3% |
| SOCIETY | 9 | 2 | 2 | 5 | 3.0% |
| SCIENCE_AND_TECHNOLOGY | 8 | 3 | 2 | 3 | 2.7% |
| WEATHER | 8 | 3 | 3 | 2 | 2.7% |
| LIFESTYLE_AND_LEISURE | 4 | 2 | 1 | 1 | 1.3% |
| ENVIRONMENT | 3 | 0 | 1 | 2 | 1.0% |
| LABOR | 0 | 0 | 0 | 0 | 0.0% |

### Nhãn không hề phát sinh bất đồng khi xuất hiện

| label_id | label | rows_with_label | assignment_count_valid |
| --- | --- | --- | --- |
| T05 | EDUCATION | 6 | 18 |
| T11 | SPORT | 7 | 21 |
| T17 | TRANSPORT_INFRASTRUCTURE | 6 | 18 |

### Nhãn hay phát sinh bất đồng

| label_id | label | rows_with_label | disagreement_rows_with_label | disagreement_rate_when_label_appears | disagreement_assignment_count |
| --- | --- | --- | --- | --- | --- |
| T18 | OTHER_UNCLEAR | 15 | 11 | 73.3% | 13 |
| T03 | CRIME_LAW_AND_JUSTICE | 16 | 9 | 56.2% | 14 |
| T13 | HUMAN_INTEREST | 13 | 8 | 61.5% | 12 |
| T01 | POLITICS | 13 | 6 | 46.2% | 9 |
| T02 | ECONOMY_BUSINESS_AND_FINANCE | 10 | 5 | 50.0% | 9 |
| T12 | SOCIETY | 5 | 4 | 80.0% | 6 |
| T16 | WORLD_INTERNATIONAL | 6 | 4 | 66.7% | 5 |
| T10 | ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 15 | 4 | 26.7% | 6 |
| T15 | LIFESTYLE_AND_LEISURE | 3 | 3 | 100.0% | 4 |
| T04 | HEALTH | 5 | 3 | 60.0% | 4 |
| T07 | ENVIRONMENT | 2 | 2 | 100.0% | 3 |
| T06 | SCIENCE_AND_TECHNOLOGY | 4 | 2 | 50.0% | 2 |
| T08 | WEATHER | 3 | 1 | 33.3% | 2 |
| T09 | DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | 4 | 1 | 25.0% | 1 |

### Cặp nhãn hay bị bất đồng với nhau

| label_a | label_b | disagreement_rows | pct_of_disagreement_rows |
| --- | --- | --- | --- |
| POLITICS | WORLD_INTERNATIONAL | 4 | 13.3% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | OTHER_UNCLEAR | 3 | 10.0% |
| CRIME_LAW_AND_JUSTICE | OTHER_UNCLEAR | 3 | 10.0% |
| ECONOMY_BUSINESS_AND_FINANCE | OTHER_UNCLEAR | 3 | 10.0% |
| HUMAN_INTEREST | SOCIETY | 2 | 6.7% |
| CRIME_LAW_AND_JUSTICE | POLITICS | 2 | 6.7% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | HUMAN_INTEREST | 2 | 6.7% |
| HUMAN_INTEREST | OTHER_UNCLEAR | 2 | 6.7% |
| SCIENCE_AND_TECHNOLOGY | SOCIETY | 1 | 3.3% |
| ENVIRONMENT | LIFESTYLE_AND_LEISURE | 1 | 3.3% |
| CRIME_LAW_AND_JUSTICE | HUMAN_INTEREST | 1 | 3.3% |
| LIFESTYLE_AND_LEISURE | OTHER_UNCLEAR | 1 | 3.3% |
| CRIME_LAW_AND_JUSTICE | SOCIETY | 1 | 3.3% |
| POLITICS | SOCIETY | 1 | 3.3% |
| HEALTH | HUMAN_INTEREST | 1 | 3.3% |

## Pilot set 400

Phạm vi dòng: Toàn bộ file set 400 (400 dòng). Tổng dòng: 400; dòng đủ 3 nhãn: 397; dòng thiếu nhãn: 3.

Nhãn được dùng: 18/18. Nhãn không được dùng: 0.

### Fleiss' kappa

| n_items | n_raters | observed_agreement | expected_agreement | fleiss_kappa |
| --- | --- | --- | --- | --- |
| 397 | 3 | 0.8153 | 0.0995 | 0.7949 |

### Cohen's kappa từng cặp

| pair | n | observed_agreement | expected_agreement | cohen_kappa |
| --- | --- | --- | --- | --- |
| Nhung vs Yen | 397 | 0.8086 | 0.0967 | 0.7881 |
| Nhung vs Han | 397 | 0.8262 | 0.0989 | 0.8071 |
| Yen vs Han | 397 | 0.8111 | 0.1016 | 0.7897 |

### Annotator giống trung bình nhóm / khác biệt so với nhóm

| average_similarity_rank | outlier_rank | annotator | avg_pairwise_cohen | avg_pairwise_agreement | avg_pairwise_disagreement_rate | other2_consensus_rows | match_other2_consensus_rows | match_other2_consensus_rate | minority_when_other2_agree_rows | minority_when_other2_agree_rate | label_distribution_l1_to_group_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 3 | Han | 0.7984 | 81.9% | 18.1% | 321 | 298 | 92.8% | 23 | 7.2% | 0.0821 |
| 2 | 2 | Nhung | 0.7976 | 81.7% | 18.3% | 322 | 298 | 92.5% | 24 | 7.5% | 0.1114 |
| 3 | 1 | Yen | 0.7889 | 81.0% | 19.0% | 328 | 298 | 90.9% | 30 | 9.1% | 0.0846 |

### Tần suất đồng thuận/bất đồng

| agreement_type | rows | pct_all_rows |
| --- | --- | --- |
| full_agreement | 298 | 74.5% |
| partial_disagreement | 77 | 19.2% |
| complete_disagreement | 22 | 5.5% |
| incomplete | 3 | 0.8% |

### Phân phối nhãn theo lượt gán

| label | total_assignments | Nhung | Yen | Han | assignment_pct |
| --- | --- | --- | --- | --- | --- |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 210 | 60 | 77 | 73 | 17.6% |
| CRIME_LAW_AND_JUSTICE | 202 | 72 | 63 | 67 | 16.9% |
| HUMAN_INTEREST | 129 | 48 | 39 | 42 | 10.8% |
| POLITICS | 111 | 32 | 38 | 41 | 9.3% |
| ECONOMY_BUSINESS_AND_FINANCE | 102 | 33 | 31 | 38 | 8.5% |
| OTHER_UNCLEAR | 61 | 19 | 20 | 22 | 5.1% |
| WORLD_INTERNATIONAL | 46 | 14 | 16 | 16 | 3.9% |
| HEALTH | 44 | 14 | 18 | 12 | 3.7% |
| SPORT | 42 | 14 | 14 | 14 | 3.5% |
| DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | 41 | 15 | 14 | 12 | 3.4% |
| EDUCATION | 38 | 16 | 11 | 11 | 3.2% |
| SCIENCE_AND_TECHNOLOGY | 35 | 13 | 11 | 11 | 2.9% |
| LIFESTYLE_AND_LEISURE | 31 | 14 | 9 | 8 | 2.6% |
| SOCIETY | 29 | 7 | 9 | 13 | 2.4% |
| TRANSPORT_INFRASTRUCTURE | 29 | 10 | 10 | 9 | 2.4% |
| LABOR | 20 | 8 | 9 | 3 | 1.7% |
| WEATHER | 17 | 5 | 7 | 5 | 1.4% |
| ENVIRONMENT | 7 | 3 | 1 | 3 | 0.6% |

### Nhãn không hề phát sinh bất đồng khi xuất hiện

| label_id | label | rows_with_label | assignment_count_valid |
| --- | --- | --- | --- |
| T11 | SPORT | 14 | 42 |

### Nhãn hay phát sinh bất đồng

| label_id | label | rows_with_label | disagreement_rows_with_label | disagreement_rate_when_label_appears | disagreement_assignment_count |
| --- | --- | --- | --- | --- | --- |
| T13 | HUMAN_INTEREST | 65 | 38 | 58.5% | 48 |
| T10 | ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 86 | 31 | 36.0% | 45 |
| T15 | LIFESTYLE_AND_LEISURE | 22 | 20 | 90.9% | 25 |
| T01 | POLITICS | 48 | 20 | 41.7% | 27 |
| T18 | OTHER_UNCLEAR | 31 | 18 | 58.1% | 19 |
| T02 | ECONOMY_BUSINESS_AND_FINANCE | 43 | 17 | 39.5% | 24 |
| T03 | CRIME_LAW_AND_JUSTICE | 75 | 15 | 20.0% | 22 |
| T12 | SOCIETY | 18 | 14 | 77.8% | 17 |
| T05 | EDUCATION | 17 | 9 | 52.9% | 14 |
| T14 | LABOR | 10 | 7 | 70.0% | 11 |
| T16 | WORLD_INTERNATIONAL | 19 | 7 | 36.8% | 10 |
| T04 | HEALTH | 18 | 6 | 33.3% | 8 |
| T17 | TRANSPORT_INFRASTRUCTURE | 12 | 5 | 41.7% | 8 |
| T06 | SCIENCE_AND_TECHNOLOGY | 14 | 5 | 35.7% | 8 |
| T09 | DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | 16 | 4 | 25.0% | 5 |

### Cặp nhãn hay bị bất đồng với nhau

| label_a | label_b | disagreement_rows | pct_of_disagreement_rows |
| --- | --- | --- | --- |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | HUMAN_INTEREST | 17 | 17.2% |
| HUMAN_INTEREST | LIFESTYLE_AND_LEISURE | 9 | 9.1% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | LIFESTYLE_AND_LEISURE | 8 | 8.1% |
| LIFESTYLE_AND_LEISURE | OTHER_UNCLEAR | 7 | 7.1% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | OTHER_UNCLEAR | 6 | 6.1% |
| HUMAN_INTEREST | OTHER_UNCLEAR | 5 | 5.1% |
| HUMAN_INTEREST | SOCIETY | 5 | 5.1% |
| CRIME_LAW_AND_JUSTICE | POLITICS | 5 | 5.1% |
| HEALTH | HUMAN_INTEREST | 4 | 4.0% |
| POLITICS | SOCIETY | 4 | 4.0% |
| ECONOMY_BUSINESS_AND_FINANCE | POLITICS | 4 | 4.0% |
| ECONOMY_BUSINESS_AND_FINANCE | HUMAN_INTEREST | 3 | 3.0% |
| DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | HUMAN_INTEREST | 3 | 3.0% |
| CRIME_LAW_AND_JUSTICE | WORLD_INTERNATIONAL | 3 | 3.0% |
| LABOR | POLITICS | 3 | 3.0% |

## Pilot 400 theo từng batch 100 dòng

## Pilot set 400 - Batch 1

Phạm vi dòng: Dòng 1-100 trong file set 400. Tổng dòng: 100; dòng đủ 3 nhãn: 98; dòng thiếu nhãn: 2.

Nhãn được dùng: 17/18. Nhãn không được dùng: 1 (SPORT).

### Fleiss' kappa

| n_items | n_raters | observed_agreement | expected_agreement | fleiss_kappa |
| --- | --- | --- | --- | --- |
| 98 | 3 | 0.8129 | 0.1017 | 0.7917 |

### Cohen's kappa từng cặp

| pair | n | observed_agreement | expected_agreement | cohen_kappa |
| --- | --- | --- | --- | --- |
| Nhung vs Yen | 98 | 0.8061 | 0.0994 | 0.7847 |
| Nhung vs Han | 98 | 0.8367 | 0.1024 | 0.8181 |
| Yen vs Han | 98 | 0.7959 | 0.0992 | 0.7734 |

### Annotator giống trung bình nhóm / khác biệt so với nhóm

| average_similarity_rank | outlier_rank | annotator | avg_pairwise_cohen | avg_pairwise_agreement | avg_pairwise_disagreement_rate | other2_consensus_rows | match_other2_consensus_rows | match_other2_consensus_rate | minority_when_other2_agree_rows | minority_when_other2_agree_rate | label_distribution_l1_to_group_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 3 | Nhung | 0.8014 | 82.1% | 17.9% | 78 | 74 | 94.9% | 4 | 5.1% | 0.1555 |
| 2 | 2 | Han | 0.7958 | 81.6% | 18.4% | 79 | 74 | 93.7% | 5 | 6.3% | 0.1646 |
| 3 | 1 | Yen | 0.7791 | 80.1% | 19.9% | 82 | 74 | 90.2% | 8 | 9.8% | 0.1633 |

### Tần suất đồng thuận/bất đồng

| agreement_type | rows | pct_all_rows |
| --- | --- | --- |
| full_agreement | 74 | 74.0% |
| partial_disagreement | 17 | 17.0% |
| complete_disagreement | 7 | 7.0% |
| incomplete | 2 | 2.0% |

### Phân phối nhãn theo lượt gán

| label | total_assignments | Nhung | Yen | Han | assignment_pct |
| --- | --- | --- | --- | --- | --- |
| CRIME_LAW_AND_JUSTICE | 57 | 21 | 17 | 19 | 19.3% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 44 | 12 | 15 | 17 | 14.9% |
| HUMAN_INTEREST | 31 | 13 | 9 | 9 | 10.5% |
| ECONOMY_BUSINESS_AND_FINANCE | 25 | 8 | 7 | 10 | 8.4% |
| POLITICS | 24 | 7 | 11 | 6 | 8.1% |
| OTHER_UNCLEAR | 21 | 6 | 8 | 7 | 7.1% |
| WORLD_INTERNATIONAL | 17 | 5 | 6 | 6 | 5.7% |
| DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | 15 | 5 | 6 | 4 | 5.1% |
| HEALTH | 14 | 4 | 6 | 4 | 4.7% |
| EDUCATION | 10 | 4 | 2 | 4 | 3.4% |
| SOCIETY | 10 | 2 | 2 | 6 | 3.4% |
| LIFESTYLE_AND_LEISURE | 9 | 4 | 3 | 2 | 3.0% |
| SCIENCE_AND_TECHNOLOGY | 6 | 2 | 2 | 2 | 2.0% |
| WEATHER | 6 | 2 | 2 | 2 | 2.0% |
| LABOR | 4 | 2 | 2 | 0 | 1.4% |
| ENVIRONMENT | 2 | 1 | 0 | 1 | 0.7% |
| TRANSPORT_INFRASTRUCTURE | 1 | 0 | 0 | 1 | 0.3% |
| SPORT | 0 | 0 | 0 | 0 | 0.0% |

### Nhãn không hề phát sinh bất đồng khi xuất hiện

| label_id | label | rows_with_label | assignment_count_valid |
| --- | --- | --- | --- |
| T08 | WEATHER | 2 | 6 |

### Nhãn hay phát sinh bất đồng

| label_id | label | rows_with_label | disagreement_rows_with_label | disagreement_rate_when_label_appears | disagreement_assignment_count |
| --- | --- | --- | --- | --- | --- |
| T13 | HUMAN_INTEREST | 15 | 8 | 53.3% | 10 |
| T01 | POLITICS | 12 | 6 | 50.0% | 6 |
| T15 | LIFESTYLE_AND_LEISURE | 6 | 5 | 83.3% | 6 |
| T02 | ECONOMY_BUSINESS_AND_FINANCE | 11 | 5 | 45.5% | 7 |
| T10 | ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 17 | 5 | 29.4% | 8 |
| T12 | SOCIETY | 6 | 4 | 66.7% | 4 |
| T18 | OTHER_UNCLEAR | 9 | 4 | 44.4% | 4 |
| T03 | CRIME_LAW_AND_JUSTICE | 21 | 4 | 19.0% | 6 |
| T05 | EDUCATION | 5 | 3 | 60.0% | 4 |
| T14 | LABOR | 2 | 2 | 100.0% | 4 |

### Cặp nhãn hay bị bất đồng với nhau

| label_a | label_b | disagreement_rows | pct_of_disagreement_rows |
| --- | --- | --- | --- |
| ECONOMY_BUSINESS_AND_FINANCE | LABOR | 2 | 8.3% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | HUMAN_INTEREST | 2 | 8.3% |
| HUMAN_INTEREST | OTHER_UNCLEAR | 2 | 8.3% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | LIFESTYLE_AND_LEISURE | 2 | 8.3% |
| HUMAN_INTEREST | SOCIETY | 2 | 8.3% |
| POLITICS | SOCIETY | 2 | 8.3% |
| CRIME_LAW_AND_JUSTICE | POLITICS | 2 | 8.3% |
| CRIME_LAW_AND_JUSTICE | SOCIETY | 2 | 8.3% |
| LIFESTYLE_AND_LEISURE | OTHER_UNCLEAR | 2 | 8.3% |
| HUMAN_INTEREST | LIFESTYLE_AND_LEISURE | 2 | 8.3% |

## Pilot set 400 - Batch 2

Phạm vi dòng: Dòng 101-200 trong file set 400. Tổng dòng: 100; dòng đủ 3 nhãn: 100; dòng thiếu nhãn: 0.

Nhãn được dùng: 18/18. Nhãn không được dùng: 0.

### Fleiss' kappa

| n_items | n_raters | observed_agreement | expected_agreement | fleiss_kappa |
| --- | --- | --- | --- | --- |
| 100 | 3 | 0.8233 | 0.1098 | 0.8016 |

### Cohen's kappa từng cặp

| pair | n | observed_agreement | expected_agreement | cohen_kappa |
| --- | --- | --- | --- | --- |
| Nhung vs Yen | 100 | 0.8200 | 0.1059 | 0.7987 |
| Nhung vs Han | 100 | 0.8500 | 0.1100 | 0.8315 |
| Yen vs Han | 100 | 0.8000 | 0.1114 | 0.7749 |

### Annotator giống trung bình nhóm / khác biệt so với nhóm

| average_similarity_rank | outlier_rank | annotator | avg_pairwise_cohen | avg_pairwise_agreement | avg_pairwise_disagreement_rate | other2_consensus_rows | match_other2_consensus_rows | match_other2_consensus_rate | minority_when_other2_agree_rows | minority_when_other2_agree_rate | label_distribution_l1_to_group_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 3 | Nhung | 0.8151 | 83.5% | 16.5% | 80 | 76 | 95.0% | 4 | 5.0% | 0.0933 |
| 2 | 2 | Han | 0.8032 | 82.5% | 17.5% | 82 | 76 | 92.7% | 6 | 7.3% | 0.1267 |
| 3 | 1 | Yen | 0.7868 | 81.0% | 19.0% | 85 | 76 | 89.4% | 9 | 10.6% | 0.1467 |

### Tần suất đồng thuận/bất đồng

| agreement_type | rows | pct_all_rows |
| --- | --- | --- |
| full_agreement | 76 | 76.0% |
| partial_disagreement | 19 | 19.0% |
| complete_disagreement | 5 | 5.0% |
| incomplete | 0 | 0.0% |

### Phân phối nhãn theo lượt gán

| label | total_assignments | Nhung | Yen | Han | assignment_pct |
| --- | --- | --- | --- | --- | --- |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 58 | 17 | 21 | 20 | 19.3% |
| CRIME_LAW_AND_JUSTICE | 57 | 20 | 18 | 19 | 19.0% |
| HUMAN_INTEREST | 32 | 11 | 10 | 11 | 10.7% |
| POLITICS | 28 | 9 | 8 | 11 | 9.3% |
| ECONOMY_BUSINESS_AND_FINANCE | 20 | 6 | 6 | 8 | 6.7% |
| OTHER_UNCLEAR | 15 | 5 | 4 | 6 | 5.0% |
| TRANSPORT_INFRASTRUCTURE | 13 | 4 | 5 | 4 | 4.3% |
| SPORT | 12 | 4 | 4 | 4 | 4.0% |
| WORLD_INTERNATIONAL | 12 | 4 | 5 | 3 | 4.0% |
| DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | 10 | 4 | 3 | 3 | 3.3% |
| HEALTH | 9 | 3 | 4 | 2 | 3.0% |
| LABOR | 7 | 2 | 4 | 1 | 2.3% |
| SCIENCE_AND_TECHNOLOGY | 7 | 3 | 2 | 2 | 2.3% |
| EDUCATION | 6 | 3 | 2 | 1 | 2.0% |
| SOCIETY | 6 | 2 | 1 | 3 | 2.0% |
| LIFESTYLE_AND_LEISURE | 4 | 2 | 1 | 1 | 1.3% |
| ENVIRONMENT | 2 | 1 | 0 | 1 | 0.7% |
| WEATHER | 2 | 0 | 2 | 0 | 0.7% |

### Nhãn không hề phát sinh bất đồng khi xuất hiện

| label_id | label | rows_with_label | assignment_count_valid |
| --- | --- | --- | --- |
| T11 | SPORT | 4 | 12 |

### Nhãn hay phát sinh bất đồng

| label_id | label | rows_with_label | disagreement_rows_with_label | disagreement_rate_when_label_appears | disagreement_assignment_count |
| --- | --- | --- | --- | --- | --- |
| T13 | HUMAN_INTEREST | 15 | 8 | 53.3% | 11 |
| T18 | OTHER_UNCLEAR | 9 | 6 | 66.7% | 6 |
| T01 | POLITICS | 12 | 6 | 50.0% | 10 |
| T10 | ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 22 | 5 | 22.7% | 7 |
| T12 | SOCIETY | 4 | 4 | 100.0% | 6 |
| T03 | CRIME_LAW_AND_JUSTICE | 21 | 4 | 19.0% | 6 |
| T15 | LIFESTYLE_AND_LEISURE | 3 | 3 | 100.0% | 4 |
| T14 | LABOR | 4 | 3 | 75.0% | 4 |
| T08 | WEATHER | 2 | 2 | 100.0% | 2 |
| T05 | EDUCATION | 3 | 2 | 66.7% | 3 |

### Cặp nhãn hay bị bất đồng với nhau

| label_a | label_b | disagreement_rows | pct_of_disagreement_rows |
| --- | --- | --- | --- |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | OTHER_UNCLEAR | 4 | 16.7% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | HUMAN_INTEREST | 3 | 12.5% |
| HUMAN_INTEREST | OTHER_UNCLEAR | 2 | 8.3% |
| HEALTH | HUMAN_INTEREST | 2 | 8.3% |
| CRIME_LAW_AND_JUSTICE | WORLD_INTERNATIONAL | 2 | 8.3% |
| LABOR | POLITICS | 2 | 8.3% |
| POLITICS | SOCIETY | 2 | 8.3% |
| LIFESTYLE_AND_LEISURE | OTHER_UNCLEAR | 2 | 8.3% |
| EDUCATION | SOCIETY | 1 | 4.2% |
| EDUCATION | WEATHER | 1 | 4.2% |

## Pilot set 400 - Batch 3

Phạm vi dòng: Dòng 201-300 trong file set 400. Tổng dòng: 100; dòng đủ 3 nhãn: 100; dòng thiếu nhãn: 0.

Nhãn được dùng: 17/18. Nhãn không được dùng: 1 (ENVIRONMENT).

### Fleiss' kappa

| n_items | n_raters | observed_agreement | expected_agreement | fleiss_kappa |
| --- | --- | --- | --- | --- |
| 100 | 3 | 0.8333 | 0.1033 | 0.8141 |

### Cohen's kappa từng cặp

| pair | n | observed_agreement | expected_agreement | cohen_kappa |
| --- | --- | --- | --- | --- |
| Nhung vs Yen | 100 | 0.8300 | 0.1000 | 0.8111 |
| Nhung vs Han | 100 | 0.8100 | 0.1007 | 0.7887 |
| Yen vs Han | 100 | 0.8600 | 0.1070 | 0.8432 |

### Annotator giống trung bình nhóm / khác biệt so với nhóm

| average_similarity_rank | outlier_rank | annotator | avg_pairwise_cohen | avg_pairwise_agreement | avg_pairwise_disagreement_rate | other2_consensus_rows | match_other2_consensus_rows | match_other2_consensus_rate | minority_when_other2_agree_rows | minority_when_other2_agree_rate | label_distribution_l1_to_group_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 3 | Yen | 0.8272 | 84.5% | 15.5% | 81 | 78 | 96.3% | 3 | 3.7% | 0.0867 |
| 2 | 2 | Han | 0.8160 | 83.5% | 16.5% | 83 | 78 | 94.0% | 5 | 6.0% | 0.1000 |
| 3 | 1 | Nhung | 0.7999 | 82.0% | 18.0% | 86 | 78 | 90.7% | 8 | 9.3% | 0.1333 |

### Tần suất đồng thuận/bất đồng

| agreement_type | rows | pct_all_rows |
| --- | --- | --- |
| full_agreement | 78 | 78.0% |
| partial_disagreement | 16 | 16.0% |
| complete_disagreement | 6 | 6.0% |
| incomplete | 0 | 0.0% |

### Phân phối nhãn theo lượt gán

| label | total_assignments | Nhung | Yen | Han | assignment_pct |
| --- | --- | --- | --- | --- | --- |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 59 | 17 | 22 | 20 | 19.7% |
| CRIME_LAW_AND_JUSTICE | 45 | 17 | 14 | 14 | 15.0% |
| HUMAN_INTEREST | 35 | 12 | 10 | 13 | 11.7% |
| POLITICS | 28 | 7 | 9 | 12 | 9.3% |
| ECONOMY_BUSINESS_AND_FINANCE | 26 | 8 | 9 | 9 | 8.7% |
| HEALTH | 14 | 5 | 5 | 4 | 4.7% |
| OTHER_UNCLEAR | 14 | 4 | 5 | 5 | 4.7% |
| SPORT | 12 | 4 | 4 | 4 | 4.0% |
| DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | 10 | 4 | 3 | 3 | 3.3% |
| LIFESTYLE_AND_LEISURE | 10 | 5 | 3 | 2 | 3.3% |
| SOCIETY | 10 | 3 | 4 | 3 | 3.3% |
| TRANSPORT_INFRASTRUCTURE | 10 | 4 | 3 | 3 | 3.3% |
| EDUCATION | 8 | 3 | 3 | 2 | 2.7% |
| SCIENCE_AND_TECHNOLOGY | 6 | 2 | 2 | 2 | 2.0% |
| WEATHER | 6 | 2 | 2 | 2 | 2.0% |
| WORLD_INTERNATIONAL | 6 | 2 | 2 | 2 | 2.0% |
| LABOR | 1 | 1 | 0 | 0 | 0.3% |
| ENVIRONMENT | 0 | 0 | 0 | 0 | 0.0% |

### Nhãn không hề phát sinh bất đồng khi xuất hiện

| label_id | label | rows_with_label | assignment_count_valid |
| --- | --- | --- | --- |
| T06 | SCIENCE_AND_TECHNOLOGY | 2 | 6 |
| T08 | WEATHER | 2 | 6 |
| T11 | SPORT | 4 | 12 |

### Nhãn hay phát sinh bất đồng

| label_id | label | rows_with_label | disagreement_rows_with_label | disagreement_rate_when_label_appears | disagreement_assignment_count |
| --- | --- | --- | --- | --- | --- |
| T13 | HUMAN_INTEREST | 18 | 11 | 61.1% | 14 |
| T10 | ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 23 | 7 | 30.4% | 11 |
| T15 | LIFESTYLE_AND_LEISURE | 7 | 6 | 85.7% | 7 |
| T01 | POLITICS | 12 | 5 | 41.7% | 7 |
| T12 | SOCIETY | 6 | 4 | 66.7% | 4 |
| T02 | ECONOMY_BUSINESS_AND_FINANCE | 11 | 4 | 36.4% | 5 |
| T03 | CRIME_LAW_AND_JUSTICE | 17 | 3 | 17.6% | 3 |
| T16 | WORLD_INTERNATIONAL | 3 | 2 | 66.7% | 3 |
| T17 | TRANSPORT_INFRASTRUCTURE | 4 | 2 | 50.0% | 4 |
| T18 | OTHER_UNCLEAR | 6 | 2 | 33.3% | 2 |

### Cặp nhãn hay bị bất đồng với nhau

| label_a | label_b | disagreement_rows | pct_of_disagreement_rows |
| --- | --- | --- | --- |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | HUMAN_INTEREST | 5 | 22.7% |
| HUMAN_INTEREST | LIFESTYLE_AND_LEISURE | 4 | 18.2% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | LIFESTYLE_AND_LEISURE | 3 | 13.6% |
| HUMAN_INTEREST | SOCIETY | 2 | 9.1% |
| CRIME_LAW_AND_JUSTICE | POLITICS | 2 | 9.1% |
| LIFESTYLE_AND_LEISURE | SOCIETY | 1 | 4.5% |
| SOCIETY | TRANSPORT_INFRASTRUCTURE | 1 | 4.5% |
| ECONOMY_BUSINESS_AND_FINANCE | HUMAN_INTEREST | 1 | 4.5% |
| ECONOMY_BUSINESS_AND_FINANCE | LIFESTYLE_AND_LEISURE | 1 | 4.5% |
| DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | HUMAN_INTEREST | 1 | 4.5% |

## Pilot set 400 - Batch 4

Phạm vi dòng: Dòng 301-400 trong file set 400. Tổng dòng: 100; dòng đủ 3 nhãn: 99; dòng thiếu nhãn: 1.

Nhãn được dùng: 18/18. Nhãn không được dùng: 0.

### Fleiss' kappa

| n_items | n_raters | observed_agreement | expected_agreement | fleiss_kappa |
| --- | --- | --- | --- | --- |
| 99 | 3 | 0.7912 | 0.0952 | 0.7693 |

### Cohen's kappa từng cặp

| pair | n | observed_agreement | expected_agreement | cohen_kappa |
| --- | --- | --- | --- | --- |
| Nhung vs Yen | 99 | 0.7778 | 0.0932 | 0.7550 |
| Nhung vs Han | 99 | 0.8081 | 0.0934 | 0.7883 |
| Yen vs Han | 99 | 0.7879 | 0.0971 | 0.7651 |

### Annotator giống trung bình nhóm / khác biệt so với nhóm

| average_similarity_rank | outlier_rank | annotator | avg_pairwise_cohen | avg_pairwise_agreement | avg_pairwise_disagreement_rate | other2_consensus_rows | match_other2_consensus_rows | match_other2_consensus_rate | minority_when_other2_agree_rows | minority_when_other2_agree_rate | label_distribution_l1_to_group_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 3 | Han | 0.7767 | 79.8% | 20.2% | 77 | 70 | 90.9% | 7 | 9.1% | 0.0943 |
| 2 | 2 | Nhung | 0.7716 | 79.3% | 20.7% | 78 | 70 | 89.7% | 8 | 10.3% | 0.1178 |
| 3 | 1 | Yen | 0.7600 | 78.3% | 21.7% | 80 | 70 | 87.5% | 10 | 12.5% | 0.1032 |

### Tần suất đồng thuận/bất đồng

| agreement_type | rows | pct_all_rows |
| --- | --- | --- |
| full_agreement | 70 | 70.0% |
| partial_disagreement | 25 | 25.0% |
| complete_disagreement | 4 | 4.0% |
| incomplete | 1 | 1.0% |

### Phân phối nhãn theo lượt gán

| label | total_assignments | Nhung | Yen | Han | assignment_pct |
| --- | --- | --- | --- | --- | --- |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 49 | 14 | 19 | 16 | 16.4% |
| CRIME_LAW_AND_JUSTICE | 43 | 14 | 14 | 15 | 14.4% |
| ECONOMY_BUSINESS_AND_FINANCE | 31 | 11 | 9 | 11 | 10.4% |
| HUMAN_INTEREST | 31 | 12 | 10 | 9 | 10.4% |
| POLITICS | 31 | 9 | 10 | 12 | 10.4% |
| SPORT | 18 | 6 | 6 | 6 | 6.0% |
| SCIENCE_AND_TECHNOLOGY | 16 | 6 | 5 | 5 | 5.4% |
| EDUCATION | 14 | 6 | 4 | 4 | 4.7% |
| OTHER_UNCLEAR | 11 | 4 | 3 | 4 | 3.7% |
| WORLD_INTERNATIONAL | 11 | 3 | 3 | 5 | 3.7% |
| LABOR | 8 | 3 | 3 | 2 | 2.7% |
| LIFESTYLE_AND_LEISURE | 8 | 3 | 2 | 3 | 2.7% |
| HEALTH | 7 | 2 | 3 | 2 | 2.3% |
| DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | 6 | 2 | 2 | 2 | 2.0% |
| TRANSPORT_INFRASTRUCTURE | 5 | 2 | 2 | 1 | 1.7% |
| ENVIRONMENT | 3 | 1 | 1 | 1 | 1.0% |
| SOCIETY | 3 | 0 | 2 | 1 | 1.0% |
| WEATHER | 3 | 1 | 1 | 1 | 1.0% |

### Nhãn không hề phát sinh bất đồng khi xuất hiện

| label_id | label | rows_with_label | assignment_count_valid |
| --- | --- | --- | --- |
| T07 | ENVIRONMENT | 1 | 3 |
| T08 | WEATHER | 1 | 3 |
| T09 | DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | 2 | 6 |
| T11 | SPORT | 6 | 18 |

### Nhãn hay phát sinh bất đồng

| label_id | label | rows_with_label | disagreement_rows_with_label | disagreement_rate_when_label_appears | disagreement_assignment_count |
| --- | --- | --- | --- | --- | --- |
| T10 | ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 24 | 14 | 58.3% | 19 |
| T13 | HUMAN_INTEREST | 17 | 11 | 64.7% | 13 |
| T15 | LIFESTYLE_AND_LEISURE | 6 | 6 | 100.0% | 8 |
| T18 | OTHER_UNCLEAR | 7 | 6 | 85.7% | 7 |
| T02 | ECONOMY_BUSINESS_AND_FINANCE | 13 | 6 | 46.2% | 10 |
| T03 | CRIME_LAW_AND_JUSTICE | 16 | 4 | 25.0% | 7 |
| T05 | EDUCATION | 6 | 3 | 50.0% | 5 |
| T01 | POLITICS | 12 | 3 | 25.0% | 4 |
| T12 | SOCIETY | 2 | 2 | 100.0% | 3 |
| T16 | WORLD_INTERNATIONAL | 5 | 2 | 40.0% | 2 |

### Cặp nhãn hay bị bất đồng với nhau

| label_a | label_b | disagreement_rows | pct_of_disagreement_rows |
| --- | --- | --- | --- |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | HUMAN_INTEREST | 7 | 24.1% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | LIFESTYLE_AND_LEISURE | 3 | 10.3% |
| HUMAN_INTEREST | LIFESTYLE_AND_LEISURE | 2 | 6.9% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | CRIME_LAW_AND_JUSTICE | 2 | 6.9% |
| LIFESTYLE_AND_LEISURE | OTHER_UNCLEAR | 2 | 6.9% |
| ECONOMY_BUSINESS_AND_FINANCE | POLITICS | 2 | 6.9% |
| ECONOMY_BUSINESS_AND_FINANCE | OTHER_UNCLEAR | 1 | 3.4% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | SCIENCE_AND_TECHNOLOGY | 1 | 3.4% |
| ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | ECONOMY_BUSINESS_AND_FINANCE | 1 | 3.4% |
| ECONOMY_BUSINESS_AND_FINANCE | LIFESTYLE_AND_LEISURE | 1 | 3.4% |

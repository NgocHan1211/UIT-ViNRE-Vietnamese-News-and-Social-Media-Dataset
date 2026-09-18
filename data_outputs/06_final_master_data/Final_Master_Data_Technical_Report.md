# Technical Report: Final Master Data Generation

## 1. Mục tiêu
Tạo lại final datasets của DS107 sau khi fix logic label mapping, label status, T18 handling, reaction mismatch và metadata outlier. Các output chính gồm Master labeled, model dataset cho topic classification, Streamlit enriched dataset và pilot exclude list.

## 2. Input
- Master: `data/02_Processed_Data/Master_Facebook_News_Posts_TeamCrawl_After_Dedup.csv`
- Label final: `data/05_Labeling/Final_Labeled`
- Label pilot: `data/05_Labeling/Final_Pilot_Labeled`

## 3. Quy trình thực hiện
- Đọc master after dedup
- Đọc và chuẩn hóa label
- Kiểm tra duplicate/conflict label
- Join label vào master
- Cập nhật needs_topic_label và usable flags
- Tính reaction/public response metrics
- Tạo model dataset
- Tạo Streamlit enriched dataset
- Tạo pilot exclude list
- Tạo các báo cáo thống kê

## 4. Output files
| File | Mục đích | Số dòng dữ liệu | Số dòng file nếu tính header | Số cột |
| --- | --- | --- | --- | --- |
| Master_Facebook_News_Posts_TeamCrawl_Labeled.csv | Master giữ schema gốc, đã join label và cập nhật flags/metrics | 11786 | 11787 | 92 |
| Topic_Classification_Model_Dataset.csv | Dataset train topic classification cho Hân | 8922 | 8923 | 4 |
| Public_Response_Streamlit_Enriched.csv | Dataset enriched cho Streamlit dashboard của Yến | 8922 | 8923 | 71 |
| Pilot_Record_IDs_Exclude_From_Test.csv | Danh sách record pilot/calibration loại khỏi test | 600 | 601 | 6 |
| missing_followers_by_page.csv | Report page thiếu follower | 17 | 18 | 10 |
| metadata_outlier_report.csv | Report metadata outlier theo từng rule | 63 | 64 | 13 |
| label_join_conflicts.csv | Report conflict/invalid label/join issue | 2715 | 2716 | 6 |
| label_distribution.csv | Phân phối nhãn theo topic | 18 | 19 | 7 |
| metadata_coverage_summary.csv | Coverage metadata và usable flags | 28 | 29 | 3 |
| taxonomy_mapping_used.csv | Mapping taxonomy chính thức đã dùng | 18 | 19 | 3 |
| Final_Master_Data_Statistics.json | Thống kê kỹ thuật dạng JSON | 1 | N/A | 1 |
| Final_Master_Data_Technical_Report.md | Báo cáo kỹ thuật tiếng Việt | 1 | N/A | 1 |

## 5. Taxonomy mapping used
Mapping dưới đây là taxonomy chính thức đã dùng khi xuất file. `topic_label_final` luôn được chuẩn hóa theo mapping này, kể cả khi label name trong input có biến thể khác.

| topic_label_id | topic_label_final | source_design_note |
| --- | --- | --- |
| T01 | T01. POLITICS | IPTC |
| T02 | T02. ECONOMY_BUSINESS_AND_FINANCE | IPTC |
| T03 | T03. CRIME_LAW_AND_JUSTICE | IPTC |
| T04 | T04. HEALTH | IPTC |
| T05 | T05. EDUCATION | IPTC |
| T06 | T06. SCIENCE_AND_TECHNOLOGY | IPTC |
| T07 | T07. ENVIRONMENT | IPTC |
| T08 | T08. WEATHER | IPTC |
| T09 | T09. DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | IPTC |
| T10 | T10. ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | IPTC |
| T11 | T11. SPORT | IPTC |
| T12 | T12. SOCIETY | IPTC |
| T13 | T13. HUMAN_INTEREST | IPTC |
| T14 | T14. LABOR | IPTC |
| T15 | T15. LIFESTYLE_AND_LEISURE | IPTC |
| T16 | T16. WORLD_INTERNATIONAL | bổ sung theo VNTC/Việt Nam |
| T17 | T17. TRANSPORT_INFRASTRUCTURE | bổ sung theo đặc thù Việt Nam/Đông Nam Á |
| T18 | T18. OTHER_UNCLEAR | nhãn kỹ thuật cho caption Facebook |

## 6. Thống kê nhãn
| topic_label_id | topic_label_final | count_in_master_labeled | count_in_model_dataset | count_in_streamlit_enriched | uncertain_count | excluded_count |
| --- | --- | --- | --- | --- | --- | --- |
| T01 | T01. POLITICS | 621 | 621 | 621 | 4 | 0 |
| T02 | T02. ECONOMY_BUSINESS_AND_FINANCE | 713 | 713 | 713 | 1 | 0 |
| T03 | T03. CRIME_LAW_AND_JUSTICE | 1635 | 1635 | 1635 | 4 | 0 |
| T04 | T04. HEALTH | 348 | 348 | 348 | 2 | 0 |
| T05 | T05. EDUCATION | 203 | 203 | 203 | 0 | 0 |
| T06 | T06. SCIENCE_AND_TECHNOLOGY | 194 | 194 | 194 | 3 | 0 |
| T07 | T07. ENVIRONMENT | 82 | 82 | 82 | 1 | 0 |
| T08 | T08. WEATHER | 151 | 151 | 151 | 0 | 0 |
| T09 | T09. DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT | 401 | 401 | 401 | 0 | 0 |
| T10 | T10. ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA | 1875 | 1875 | 1875 | 5 | 0 |
| T11 | T11. SPORT | 291 | 291 | 291 | 0 | 0 |
| T12 | T12. SOCIETY | 215 | 215 | 215 | 3 | 0 |
| T13 | T13. HUMAN_INTEREST | 1131 | 1131 | 1131 | 11 | 0 |
| T14 | T14. LABOR | 103 | 103 | 103 | 1 | 0 |
| T15 | T15. LIFESTYLE_AND_LEISURE | 172 | 172 | 172 | 2 | 0 |
| T16 | T16. WORLD_INTERNATIONAL | 468 | 468 | 468 | 0 | 0 |
| T17 | T17. TRANSPORT_INFRASTRUCTURE | 319 | 319 | 319 | 0 | 0 |
| T18 | T18. OTHER_UNCLEAR | 280 | 0 | 0 | 8 | 0 |

## 7. Thống kê usable theo tác vụ
| metric | count | percentage |
| --- | --- | --- |
| master_usable_for_topic_classification_rows_including_t18 | 9202 | 78.0757 |
| usable_for_topic_classification_rows | 8922 | 75.7 |
| usable_for_reaction_analysis_rows | 8008 | 67.945 |
| usable_for_engagement_analysis_rows | 7985 | 67.7499 |
| usable_for_engagement_analysis_strict_rows | 7985 | 67.7499 |
| metadata_outlier_rows | 38 | 0.3224 |
| has_page_followers_rows | 11786 | 100.0 |
| has_post_created_time_rows | 8560 | 72.6285 |

## 8. T18 handling
- T18 được giữ trong Master để truy vết: `280` dòng.
- T18 có `label_status = excluded`: `0` dòng.
- T18 removed from model dataset: `280` dòng.
- T18 removed from Streamlit enriched: `280` dòng.
- Master có `9202` dòng usable_for_topic_classification nếu tính cả T18; model dataset chính chỉ còn `8922` dòng dữ liệu sau khi loại T18. Khi mở CSV có thể thấy `8923` dòng nếu tính cả header.

## 9. Label status fix
- Số dòng có label hợp lệ nhưng status rỗng hoặc `unlabeled` đã được sửa: `0` dòng.
- Sau fix, `unlabeled` chỉ còn dùng cho dòng thật sự chưa có `topic_label_id` hợp lệ T01-T18.
- Streamlit enriched không giữ dòng `label_status = unlabeled`.

## 10. Metadata outlier handling
- Số dòng metadata outlier: `38` dòng.
- Số dòng outlier-rule trong `metadata_outlier_report.csv`: `63` dòng.
- Rule dùng để flag: `comment_count >= 100000`, `share_count >= 100000`, `total_reactions >= 100000`, `engagement_per_follower > 0.2`, `comment_count > total_reactions * 20 and comment_count >= 10000`, `share_count > total_reactions * 20 and share_count >= 10000`.
- Dòng outlier không bị sửa giá trị gốc, nhưng được set `usable_for_engagement_analysis = 0` và `usable_for_engagement_analysis_strict = 0`.

## 11. Reaction mismatch handling
- Reaction detail sum mismatch: `1945` dòng.
- Nếu `reaction_details_status != ok`, dòng đó có `usable_for_reaction_analysis = 0`.
- Các chỉ số reaction-based như `polarity_score`, `reaction_intensity`, `approval_reaction_index`, `outrage_reaction_index`, `amusement_reaction_index`, `empathy_reaction_index` được để null khi reaction details không `ok`.

## 12. Pilot/calibration
- `600` record trong `Pilot_Record_IDs_Exclude_From_Test.csv` không nên đưa vào test set.
- Các record này có thể dùng cho train nếu nhóm muốn tận dụng nhãn đã adjudicate, nhưng cần loại khỏi test để tránh đánh giá quá lạc quan.

## 13. Vấn đề còn cần quan tâm
- Tổng issue trong `label_join_conflicts.csv`: `2715` dòng.
- True label conflicts: `67` dòng.
- Chi tiết issue theo loại: `{"missing_topic_label": 2547, "duplicate_label": 101, "duplicate_label_topic_conflict": 24, "unresolved_duplicate_label_topic_conflict": 23, "label_record_id_not_found_in_master": 19, "invalid_topic_label": 1}`.
- Manual page follower override đã áp dụng: `657` dòng post.
- Page thiếu followers: `0` page có ít nhất một post thiếu follower.
- Timestamp missing: `3226` dòng; timestamp invalid: `0` dòng.
- Caption rỗng: `0` dòng.
- Label null hoặc chưa hợp lệ T01-T18: `2584` dòng.
- T18 count: `280` dòng.
- Uncertain count: `45` dòng.
- Metadata outlier: `38` dòng.
- Cột master được tạo mới do thiếu schema: `has_metadata_outlier, metadata_outlier_reason, usable_for_engagement_analysis_strict`.
- Warnings: `Không có`.

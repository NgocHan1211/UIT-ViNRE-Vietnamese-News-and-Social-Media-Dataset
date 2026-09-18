# Checklist và pipeline tạo Master Data

Tài liệu này mô tả pipeline hiện tại sau khi chuyển Master chính sang **TeamCrawl only**.

## Master chính hiện tại

Output chính:

```text
data/02_Processed_Data/Master_Facebook_News_Posts_TeamCrawl.csv
data/02_Processed_Data/Master_Facebook_News_Posts_TeamCrawl_After_Dedup.csv
data/02_Processed_Data/Annotation_Template_TeamCrawl.csv
```

Script build:

```text
src/build_master_teamcrawl_posts.py
```

Điều kiện lấy dữ liệu:

```text
raw_file_path thuộc data/01_Raw_Data/02_Team_Crawled_Raw/
page_name không rỗng
không lấy ViTrend
không lấy Archive
không lấy comment-level rows
```

Master 14K cũ có cả ViTrend đã được lưu tại:

```text
data/02_Processed_Data/_archive/master_14K_before_teamcrawl_20260603_202533/
```

## Checklist

- [x] Chỉ lấy team-crawled raw.
- [x] Bỏ ViTrend khỏi Master chính.
- [x] Chỉ giữ record có `page_name`.
- [x] Dedup theo pipeline build và tạo thêm bản after dedup theo `post_content_for_labeling`.
- [x] Bỏ các cột old label vì không dùng ViTrend/targeted label.
- [x] Bỏ các cột hằng số hoặc trùng lặp trong schema TeamCrawl.
- [x] Tạo annotation template gọn hơn.
- [x] Kiểm tra `has_page_followers = 1` chỉ khi `page_followers > 0`.
- [x] Kiểm tra `usable_for_reaction_analysis = 1` chỉ khi tổng reaction detail bằng `total_reactions`.
- [x] Kiểm tra `usable_for_engagement_analysis = 1` chỉ khi full reaction details và `comment_count > 0` hoặc `share_count > 0`.
- [ ] Gán nhãn cuối vào `topic_label_final`.
- [ ] Build lại Master sau khi có annotation.

## Trạng thái hiện tại

```text
Master TeamCrawl original rows: 12,054
Master TeamCrawl original duplicate post_content_for_labeling: 268
Master TeamCrawl after-dedup rows: 11,786
Master TeamCrawl after-dedup columns: 89
Duplicate post_content_for_labeling after dedup: 0
Annotation TeamCrawl rows: 12,054
Annotation TeamCrawl columns: 15
```

Theo owner trong bản after dedup:

```text
phuc:  3,995
yen:   3,305
han:   2,355
nhung: 2,131
```

Theo schema raw trong bản after dedup:

```text
schema_5_new_timestamp: 8,560
schema_4_basic:         3,226
```

Cờ usable trong bản after dedup:

```text
usable_for_topic_classification:11,786
needs_topic_label:              11,786
usable_for_reaction_analysis:    9,841
usable_for_engagement_analysis:  9,800
```

`usable_for_topic_classification = 1` nếu post có caption. Nhãn sẽ được điền sau trong `topic_label_final`.

## Schema TeamCrawl

Schema nằm trong:

```text
src/build_master_teamcrawl_posts.py
```

Cụ thể:

```text
TEAM_MASTER_COLUMNS      # 89 cột
TEAM_ANNOTATION_COLUMNS  # 15 cột
```

Các cột đã bỏ khỏi Master TeamCrawl:

```text
data_origin
data_source_group
source_type
is_duplicate
duplicate_of
old_label
old_topic_label
old_label_source
post_content_raw
post_content_clean
usable_for_topic_labeling
usable_for_topic_training
usable_for_topic_evaluation
usable_for_time_analysis
```

Lý do:

```text
data_origin/data_source_group/source_type: hằng số trong TeamCrawl Master
is_duplicate/duplicate_of: Master output từ pipeline đã bỏ duplicate theo khóa build; bản After_Dedup xử lý thêm duplicate theo post_content_for_labeling
old_label/old_topic_label/old_label_source: không dùng ViTrend/targeted label
post_content_raw/post_content_clean: đang trùng với post_content_for_labeling
usable_for_topic_labeling/usable_for_topic_training/usable_for_topic_evaluation/usable_for_time_analysis: không còn là 3 cờ chính cần theo dõi
```

## Build lại TeamCrawl

```bash
python3 src/build_master_teamcrawl_posts.py
```

Sau khi điền nhãn:

```bash
python3 src/build_master_teamcrawl_posts.py \
  --annotation-file data/02_Processed_Data/Annotation_Template_TeamCrawl.csv
```

## Annotation

Template hiện có 15 cột:

```text
record_id
usable_for_topic_classification
needs_topic_label
page_name
post_url
post_content_for_labeling
topic_label_final
topic_label_id
label_status
label_source
annotator_1
annotator_2
annotation_round
annotation_note
is_uncertain_label
```

Các cột annotator cần điền chính:

```text
topic_label_final
topic_label_id
label_status
label_source
annotator_1
annotation_note
is_uncertain_label
```

## Dataset báo chí only

Dataset con báo chí only vẫn nằm tại:

```text
data/02_Processed_Data/Báo chí only/
```

Output:

```text
Master_Facebook_News_Posts_Bao_Chi_Only.csv: 6,595 rows, 102 columns
Annotation_Template_Bao_Chi_Only.csv:       6,595 rows, 18 columns
```

Build lại:

```bash
python3 src/build_master_bao_chi_posts.py
```

## Rule dùng cho task

Topic classification:

```text
usable_for_topic_classification = 1
nếu post_content_for_labeling không rỗng
```

Reaction-type analysis:

```text
usable_for_reaction_analysis = 1
nếu total_reactions có giá trị
và like + love + haha + wow + sad + angry + care + sorry == total_reactions
```

Engagement analysis:

```text
usable_for_engagement_analysis = 1
nếu usable_for_reaction_analysis = 1
và có field comment_count/share_count
và comment_count > 0 hoặc share_count > 0
```

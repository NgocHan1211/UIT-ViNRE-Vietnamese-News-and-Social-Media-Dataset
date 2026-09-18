# 02_Processed_Data

Folder này hiện dùng **TeamCrawl Master** làm dữ liệu chính:

```text
Master_Facebook_News_Posts_TeamCrawl.csv
Master_Facebook_News_Posts_TeamCrawl_After_Dedup.csv
Annotation_Template_TeamCrawl.csv
```

Nguồn input:

```text
data/01_Raw_Data/02_Team_Crawled_Raw/
```

Không lấy:

```text
data/01_Raw_Data/01_Existing_ViTrend_Raw/
data/03_Archive_Not_For_Training/
```

Master 14K cũ có cả ViTrend đã được lưu tại:

```text
data/02_Processed_Data/_archive/master_14K_before_teamcrawl_20260603_202533/
```

## File chính

| File | Dòng | Cột | Duplicate `post_content_for_labeling` | Dùng để làm gì |
|---|---:|---:|---:|---|
| `Master_Facebook_News_Posts_TeamCrawl.csv` | 12,054 | 89 | 268 | Master gốc, giữ nguyên để đối chiếu. |
| `Master_Facebook_News_Posts_TeamCrawl_After_Dedup.csv` | 11,786 | 89 | 0 | Master đã dedup theo `post_content_for_labeling`, giữ dòng xuất hiện đầu tiên. |
| `Annotation_Template_TeamCrawl.csv` | 12,054 | 15 | 268 | Template gán nhãn topic gốc, chưa rebuild theo bản after dedup. |
| `Báo chí only/` | folder | - | - | Dataset con chỉ gồm các nguồn báo chí/news đã chọn. |
| `_archive/` | folder | - | - | Lưu Master 14K cũ và output processed cũ. |

## Điều kiện lọc TeamCrawl

Script chỉ giữ record thỏa:

```text
raw_file_path thuộc data/01_Raw_Data/02_Team_Crawled_Raw/
page_name không rỗng
is_duplicate = 0 sau dedup theo pipeline build; bản After_Dedup xử lý thêm duplicate theo post_content_for_labeling
```

Vì đã bỏ ViTrend nên các cột old label đã được loại khỏi schema:

```text
old_label
old_topic_label
old_label_source
```

Một số cột hằng số hoặc trùng lặp cũng đã bỏ:

```text
data_origin
data_source_group
source_type
is_duplicate
duplicate_of
post_content_raw
post_content_clean
usable_for_topic_labeling
usable_for_topic_training
usable_for_topic_evaluation
usable_for_time_analysis
```

`post_content_for_labeling` là cột nội dung chính để gán nhãn/train.

## Số lượng hiện tại của bản after dedup

Theo owner:

```text
phuc:  3,995
yen:   3,305
han:   2,355
nhung: 2,131
```

Theo schema raw:

```text
schema_5_new_timestamp: 8,560
schema_4_basic:         3,226
```

Cờ usable:

```text
usable_for_topic_classification:11,786
needs_topic_label:              11,786
usable_for_reaction_analysis:    9,841
usable_for_engagement_analysis:  9,800
```

`usable_for_topic_classification = 1` nếu post có caption. Nhãn sẽ được điền sau trong `topic_label_final`.

## Cấu trúc CSV xem ở đâu?

Trong code:

```text
src/build_master_teamcrawl_posts.py
```

Cụ thể:

```text
TEAM_MASTER_COLUMNS      # 89 cột của Master_Facebook_News_Posts_TeamCrawl.csv
TEAM_ANNOTATION_COLUMNS  # 15 cột của Annotation_Template_TeamCrawl.csv
```

Xem header trực tiếp:

```bash
python3 - <<'PY'
import csv

for path in [
    "data/02_Processed_Data/Master_Facebook_News_Posts_TeamCrawl.csv",
    "data/02_Processed_Data/Master_Facebook_News_Posts_TeamCrawl_After_Dedup.csv",
    "data/02_Processed_Data/Annotation_Template_TeamCrawl.csv",
]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        print(path)
        print("Số cột:", len(reader.fieldnames or []))
        print(reader.fieldnames)
        print()
PY
```

## Annotation Template

`Annotation_Template_TeamCrawl.csv` có 15 cột:

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

Gợi ý giá trị:

```text
label_status:
human_labeled, human_verified, weak_labeled_checked, excluded

label_source:
manual, source_based, llm_assisted, mixed

is_uncertain_label:
0 hoặc 1
```

## Rule quan trọng

```text
has_page_followers = 1
nếu page_followers > 0
```

```text
usable_for_reaction_analysis = 1
nếu total_reactions có giá trị
và like + love + haha + wow + sad + angry + care + sorry == total_reactions
```

```text
usable_for_engagement_analysis = 1
nếu usable_for_reaction_analysis = 1
và có field comment_count/share_count
và comment_count > 0 hoặc share_count > 0
```

## Build lại

```bash
python3 src/build_master_teamcrawl_posts.py
```

Sau khi điền `Annotation_Template_TeamCrawl.csv`, merge nhãn lại:

```bash
python3 src/build_master_teamcrawl_posts.py \
  --annotation-file data/02_Processed_Data/Annotation_Template_TeamCrawl.csv
```

## Folder `Báo chí only/`

Folder này giữ dataset con báo chí:

| File | Dòng | Cột | Duplicate | Dùng để làm gì |
|---|---:|---:|---:|---|
| `Master_Facebook_News_Posts_Bao_Chi_Only.csv` | 6,595 | 102 | 0 | Master chỉ gồm nguồn báo chí đã chọn. |
| `Annotation_Template_Bao_Chi_Only.csv` | 6,595 | 18 | 0 | Template gán nhãn topic cho Master báo chí. |

Build lại:

```bash
python3 src/build_master_bao_chi_posts.py
```

# Cấu trúc thư mục `data/`

Tài liệu này mô tả cấu trúc `data/` sau khi đã reorganize: mỗi folder chứa gì, file nào dùng làm raw chính, file nào chỉ để archive, và schema JSON/JSONL/CSV đang có.

## Tổng quan nhanh

- `01_Raw_Data/`: dữ liệu raw có thể dùng làm nguồn đầu vào để clean, normalize, merge, dedup.
- `02_Processed_Data/`: nơi để dữ liệu đã xử lý; Master chính hiện tại là TeamCrawl, không lấy ViTrend.
- `03_Archive_Not_For_Training/`: dữ liệu không dùng train trực tiếp: checkpoint, debug/probe, labeled cũ, batch cũ/nhỏ, README trước khi reorganize.
- `README_REORGANIZED.md`: README ngắn được tạo bởi script reorganize.
- `README_DATA_STRUCTURE.md`: file hiện tại, mô tả chi tiết cấu trúc data.

## Cây thư mục chi tiết

```text
data/
├── .gitkeep                                      # giữ thư mục data trong git
├── README_REORGANIZED.md                         # README ngắn sau reorganize
├── README_DATA_STRUCTURE.md                      # tài liệu chi tiết hiện tại
├── 01_Raw_Data/                                  # raw data chính
│   ├── 01_Existing_ViTrend_Raw/                  # raw/legacy crawl có sẵn từ trước
│   │   └── json-crawl-data/                      # crawl cũ, schema riêng, có post/comment
│   │       ├── comments.json                     # 48 comments dạng cây comment
│   │       ├── posts_BLVHoangQuann.json          # 152 posts
│   │       ├── posts_BongDaS2.json               # 187 posts
│   │       ├── posts_Ghien.Am.Nhac.Production.json # 184 posts
│   │       ├── posts_Ghien.Am.Nhac.Production_2025-6-14.jsonl # 184 posts JSONL
│   │       ├── posts_K14vn.json                  # 185 posts
│   │       ├── posts_K14vn_2025-6-14.jsonl       # 185 posts JSONL
│   │       ├── posts_TheOtherReviewer.json       # 153 posts
│   │       ├── posts_TheOtherReviewer_2025-6-14.jsonl # 153 posts JSONL
│   │       ├── posts_Theanh28.json               # 135 posts
│   │       ├── posts_Theanh28_2025-6-14.jsonl    # 135 posts JSONL
│   │       ├── posts_beatvn.network.json         # 177 posts
│   │       ├── posts_beatvn.network_2025-6-14.jsonl # 177 posts JSONL
│   │       ├── posts_blvanhngoc.json             # 179 posts
│   │       ├── posts_bongda6666.json             # 162 posts
│   │       ├── posts_bongda6666_2025-6-14.jsonl  # 162 posts JSONL
│   │       ├── posts_cambongda.json              # 87 posts
│   │       ├── posts_congdongvnexpress.json      # 195 posts
│   │       ├── posts_congdongvnexpress_2025-6-14.jsonl # 195 posts JSONL
│   │       ├── posts_daiphatthanh.sound.json     # 151 posts
│   │       ├── posts_daiphatthanh.sound_2025-6-14.jsonl # 151 posts JSONL
│   │       ├── posts_phephim.json                # 171 posts
│   │       ├── posts_vietnamlovers.json          # 171 posts
│   │       ├── posts_w2wmovie.json               # 192 posts
│   │       ├── posts_warnermusicvn.json          # 193 posts
│   │       ├── posts_yannews.json                # 163 posts
│   │       └── posts_yannews_2025-6-14.jsonl     # 163 posts JSONL
│   └── 02_Team_Crawled_Raw/                      # raw do team mới crawl
│       ├── Han/                                  # dữ liệu của Hân/Han
│       │   └── get_from_Han_legacy/              # batch legacy của Han
│       │       ├── posts_Kenh14_vn.json          # 1161 posts
│       │       ├── posts_Theanh28_Entertainment.json # 557 posts
│       │       └── posts_nguoilaodong.json       # 123 posts
│       ├── Nhung/                                # dữ liệu của Nhung
│       │   ├── get_from_Nhung_legacy/            # batch legacy, giữ để merge/dedup sau
│       │   │   ├── posts_Thong_tin_Chinh_phu.json # 9 posts
│       │   │   └── posts_Tuổi_Trẻ.json         # 1090 posts
│       │   ├── json-nhung-daibieunhandan-v9-3-2/
│       │   │   └── posts_Dai_bieu_Nhan_dan.json  # 400 posts
│       │   ├── json-nhung-thongtinchinhphu-v9-3-2/
│       │   │   └── posts_Thong_tin_Chinh_phu.json # 48 posts
│       │   ├── json-nhung-tintuccand-v9-3-2/
│       │   │   └── posts_Tin_tuc_CAND.json       # 400 posts
│       │   └── json-nhung-tuoitre-v9-3-2/
│       │       └── posts_Tuoi_Tre.json           # 403 posts
│       ├── Phuc/                                 # dữ liệu của Phúc
│       │   ├── json-dantri-multipage-v7/
│       │   │   └── posts_Dantri.json             # 1000 posts
│       │   ├── json-vnexpress-multipage-v7/
│       │   │   └── posts_VnExpress_net.json      # 1000 posts
│       │   ├── json-vtv24-multipage-v7/
│       │   │   └── posts_Tin_tuc_VTV24.json      # 1000 posts
│       │   └── json-yannews-chunk-v1/
│       │       └── posts_YAN_News.json           # 1002 posts
│       └── Yen/                                  # dữ liệu của Yến
│           ├── json-yen-cafebiz-v9-3-2/
│           │   └── posts_CafeBiz.json            # 732 posts
│           ├── json-yen-schannel-v9-3-2/
│           │   ├── posts_Schannel.json           # 1000 posts
│           │   ├── posts_Schannel 2.json         # 673 posts
│           │   └── posts_Schannel 4.json         # 716 posts
│           ├── json-yen-vietnamnet-v9-3-2/
│           │   └── posts_Vietnamnet_vn.json      # 870 posts
│           └── json-yen-weibovietnam-v9-3-2/
│               └── posts_Weibo_Vietnam.json      # 714 posts
├── 02_Processed_Data/                            # output sau clean/normalize/merge/dedup
│   ├── Master_Facebook_News_Posts_TeamCrawl.csv  # Master team crawl gốc, 12054 rows, 89 columns
│   ├── Master_Facebook_News_Posts_TeamCrawl_After_Dedup.csv # dedup post_content_for_labeling, 11786 rows, 89 columns
│   ├── Annotation_Template_TeamCrawl.csv          # template gán nhãn team crawl gốc, 12054 rows, 15 columns
│   ├── README.md                                 # mô tả folder processed
│   ├── Báo chí only/                             # dataset con chỉ gồm nguồn báo chí/news đã chọn
│   │   ├── Master_Facebook_News_Posts_Bao_Chi_Only.csv      # 6595 rows, 102 columns
│   │   ├── Annotation_Template_Bao_Chi_Only.csv              # 6595 rows, 18 columns
│   │   └── README.md                             # nguồn, số lượng, cấu trúc CSV báo chí only
│   └── _archive/                                 # output processed cũ, gồm Master 14K có ViTrend
└── 03_Archive_Not_For_Training/                  # không dùng train trực tiếp
    ├── _before_cleanup_inventory/                # inventory trước/sau reorganize
    │   ├── files_before_cleanup_20260527_000645.txt
    │   ├── folders_before_cleanup_20260527_000645.txt
    │   ├── files_after_cleanup_20260527_000645.txt
    │   └── folders_after_cleanup_20260527_000645.txt
    ├── checkpoints/                              # checkpoint crawl đã tách khỏi raw
    │   └── 02_Team_Crawled_Raw/.../checkpoint_*.json # trạng thái crawl, không phải post
    ├── debug_probe/                              # crawl thử nghiệm/debug
    │   └── json-ttcp-probe-v8-4/
    │       ├── checkpoint_TTCP_probe_v8_4.json   # checkpoint debug
    │       └── posts_Thong_tin_Chinh_phu_probe_v8_4.json # 23 posts probe
    ├── docs_before_reorg/                        # tài liệu cấu trúc cũ
    │   └── README_DATA_STRUCTURE_before_reorg_20260527_000645.md
    ├── failed_posts/                             # nơi lưu post crawl lỗi, hiện không có file
    ├── labeled_unused/                           # dữ liệu có nhãn hoặc labeled cũ, chưa dùng train chính
    │   ├── csv-data(labeled)/                    # CSV/XLSX labeled cũ, không đưa vào Master mặc định
    │   └── json-targeted-crawl/                  # targeted crawl có label/topic_label, có thể tái sử dụng sau kiểm tra
    └── old_or_redundant/                         # batch nhỏ/cũ, tạm không dùng chính
        └── json-final-v2-yannews-vnexpress/
            ├── posts_VnExpress_net.json         # 1 post
            └── posts_YAN_News.json              # 258 posts
```

## Cấu trúc JSON/JSONL

Các file JSON trong repo hiện chia thành 8 schema chính. Với các file cùng schema, chỉ cần dùng cùng một parser/normalizer.

### Schema 1 - Comment tree legacy

Áp dụng cho:

- `data/01_Raw_Data/01_Existing_ViTrend_Raw/json-crawl-data/comments.json`

Dạng file: JSON array, mỗi phần tử là một comment. Comment có thể chứa reply lồng trong `feedback_info.comments`.

```json
{
  "text": "Ở một diễn biến khác, Jason Dilla bất ngờ cập nhật trạng thái:",
  "image": "data\\image\\504373289_1281357230023329_6042820055238308172_n.jpg",
  "reactions": {
    "total": 479,
    "detail": {
      "haha": 395,
      "like": 66,
      "sorry": 15
    }
  },
  "feedback_info": {
    "total_count": 35,
    "id": "ZmVlZGJhY2s6...",
    "expansion_token": "MjoxNzUw...",
    "comments": [
      {
        "text": "Đài Phát Thanh. Trần Sỹ anh Sơn vẫn cay",
        "image": null,
        "reactions": {
          "total": 0,
          "detail": {}
        },
        "feedback_info": {
          "total_count": 1,
          "id": "ZmVlZGJhY2s6...",
          "expansion_token": "MjoxNzUw..."
        }
      }
    ]
  }
}
```

### Schema 2 - Post legacy JSON

Áp dụng cho các file `.json` dạng `posts_*.json` trong:

- `data/01_Raw_Data/01_Existing_ViTrend_Raw/json-crawl-data/`

Không áp dụng cho `comments.json` và các file `.jsonl`.

Dạng file: JSON array, mỗi phần tử là một post crawl cũ. Schema này có `image_paths`, `feedback_id`, `creation_time`, `reactions_detail`, `comments`.

```json
{
  "post_content": "Dù Anh Thư liên tục khẳng định mối quan hệ nhưng hành động của Huy Khánh...",
  "image_paths": [],
  "feedback_id": "ZmVlZGJhY2s6...",
  "creation_time": 1749827432,
  "total_reactions": 12508,
  "reactions_detail": {
    "Like": 12068,
    "Love": 232,
    "Haha": 175,
    "Care": 26,
    "Wow": 3,
    "Sad": 3,
    "Angry": 1
  },
  "share_count": "103",
  "comment_count": 81,
  "post_url": "https://www.facebook.com/...",
  "comments": []
}
```

Ghi chú: `share_count` ở schema này có thể là string, nên cần ép kiểu số khi normalize.

### Schema 3 - Post legacy JSONL

Áp dụng cho các file `.jsonl` trong:

- `data/01_Raw_Data/01_Existing_ViTrend_Raw/json-crawl-data/`

Dạng file: mỗi dòng là một JSON object độc lập, schema giống Schema 2.

```json
{"post_content":"...","image_paths":[],"feedback_id":"...","creation_time":1749827432,"total_reactions":12508,"reactions_detail":{"Like":12068},"share_count":"103","comment_count":81,"post_url":"https://www.facebook.com/...","comments":[]}
```

### Schema 4 - Facebook post cơ bản

Áp dụng cho raw chính:

- `data/01_Raw_Data/02_Team_Crawled_Raw/Han/get_from_Han_legacy/posts_Kenh14_vn.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Han/get_from_Han_legacy/posts_Theanh28_Entertainment.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Han/get_from_Han_legacy/posts_nguoilaodong.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Nhung/get_from_Nhung_legacy/posts_Tuổi_Trẻ.json`

Áp dụng thêm cho một số file archive trong `labeled_unused/json-targeted-crawl/`:

- `Han_posts_Tuổi_Trẻ.json`
- `posts_Schannel.json`
- `posts_VnExpress_net.json`
- `posts_congdongvnexpress.json`

Dạng file: JSON array, mỗi phần tử là một post. Schema này chưa có `post_type` và timestamp gốc của post.

```json
{
  "source_type": "Facebook",
  "page_name": "VnExpress.net",
  "page_url": "https://www.facebook.com/congdongvnexpress",
  "page_handle": "congdongvnexpress",
  "page_followers": 4700000,
  "post_url": "https://www.facebook.com/congdongvnexpress/posts/...",
  "post_id": "pfbid...",
  "post_content": "Tương lai chiến sự Iran sau thượng đỉnh Mỹ - Trung",
  "like_count": 10,
  "love_count": 0,
  "haha_count": 0,
  "wow_count": 0,
  "sad_count": 0,
  "angry_count": 0,
  "care_count": 0,
  "total_reactions": 10,
  "comment_count": 1,
  "share_count": 0,
  "share_per_follower": 0.0,
  "comment_per_follower": 0.0,
  "reaction_per_follower": 0.0,
  "crawl_time": 1740000000,
  "crawl_time_human": "2025-..."
}
```

### Schema 5 - Facebook post mới có timestamp/post_type

Áp dụng cho raw chính:

- `data/01_Raw_Data/02_Team_Crawled_Raw/Nhung/get_from_Nhung_legacy/posts_Thong_tin_Chinh_phu.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Nhung/json-nhung-daibieunhandan-v9-3-2/posts_Dai_bieu_Nhan_dan.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Nhung/json-nhung-thongtinchinhphu-v9-3-2/posts_Thong_tin_Chinh_phu.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Nhung/json-nhung-tintuccand-v9-3-2/posts_Tin_tuc_CAND.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Nhung/json-nhung-tuoitre-v9-3-2/posts_Tuoi_Tre.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Phuc/json-dantri-multipage-v7/posts_Dantri.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Phuc/json-vnexpress-multipage-v7/posts_VnExpress_net.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Phuc/json-vtv24-multipage-v7/posts_Tin_tuc_VTV24.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Phuc/json-yannews-chunk-v1/posts_YAN_News.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Yen/json-yen-cafebiz-v9-3-2/posts_CafeBiz.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Yen/json-yen-schannel-v9-3-2/posts_Schannel.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Yen/json-yen-schannel-v9-3-2/posts_Schannel 2.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Yen/json-yen-schannel-v9-3-2/posts_Schannel 4.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Yen/json-yen-vietnamnet-v9-3-2/posts_Vietnamnet_vn.json`
- `data/01_Raw_Data/02_Team_Crawled_Raw/Yen/json-yen-weibovietnam-v9-3-2/posts_Weibo_Vietnam.json`

Áp dụng thêm cho archive/debug:

- `data/03_Archive_Not_For_Training/debug_probe/json-ttcp-probe-v8-4/posts_Thong_tin_Chinh_phu_probe_v8_4.json`
- `data/03_Archive_Not_For_Training/old_or_redundant/json-final-v2-yannews-vnexpress/posts_VnExpress_net.json`
- `data/03_Archive_Not_For_Training/old_or_redundant/json-final-v2-yannews-vnexpress/posts_YAN_News.json`

Dạng file: JSON array. Đây là schema raw chính nên ưu tiên dùng khi build pipeline normalize.

```json
{
  "source_type": "Facebook",
  "page_name": "Weibo Việt Nam",
  "page_url": "https://www.facebook.com/weibovietnam",
  "page_handle": "weibovietnam",
  "page_followers": 2300000,
  "post_url": "https://www.facebook.com/weibovietnam/posts/...",
  "post_id": "pfbid...",
  "post_type": "post",
  "external_url": null,
  "post_timestamp_raw": "...",
  "post_timestamp_unix": 1779728760,
  "post_timestamp_human": "2026-05-26 00:06:00",
  "timestamp_source": "url_or_dom",
  "timestamp_url": "...",
  "timestamp_status": "ok",
  "post_content": "...",
  "like_count": 100,
  "love_count": 10,
  "haha_count": 5,
  "wow_count": 0,
  "sad_count": 0,
  "angry_count": 0,
  "care_count": 0,
  "total_reactions": 115,
  "comment_count": 20,
  "share_count": 3,
  "share_per_follower": 0.0,
  "comment_per_follower": 0.0,
  "reaction_per_follower": 0.0,
  "crawl_time": 1779750000,
  "crawl_time_human": "2026-05-26 ..."
}
```

### Schema 6 - Checkpoint crawl

Áp dụng cho:

- `data/03_Archive_Not_For_Training/checkpoints/**/checkpoint_*.json`
- `data/03_Archive_Not_For_Training/debug_probe/json-ttcp-probe-v8-4/checkpoint_TTCP_probe_v8_4.json`

Dạng file: JSON object lưu trạng thái crawl. Đây không phải data post và không dùng train.

```json
{
  "reason": "session_end",
  "saved_at": "2026-05-26 05:22:18",
  "total_records": 714,
  "frontier": {
    "total_records": 714,
    "oldest_timestamp_unix": 1775797860,
    "oldest_timestamp_human": "2026-04-10 12:11:00",
    "newest_timestamp_unix": 1779728760,
    "newest_timestamp_human": "2026-05-26 00:06:00"
  },
  "scroll_y": 938178,
  "dom_nodes": 71140,
  "videos": 28,
  "dialogs": 0,
  "js_heap_used_mb": 123.4,
  "js_heap_total_mb": 256.0
}
```

### Schema 7 - Targeted crawl có label/topic_label

Áp dụng cho các file archive trong:

- `data/03_Archive_Not_For_Training/labeled_unused/json-targeted-crawl/`

Nhóm này **không nên xem là bỏ đi**. Các file ở đây là crawl theo page/chủ đề mục tiêu, nhiều post đã có `label` hoặc `topic_label`, nên có thể tái sử dụng cho các việc như:

- bổ sung dữ liệu theo chủ đề `Phim ảnh`, `Thể thao`, `Âm nhạc`;
- tạo tập tham khảo để kiểm tra rule/keyword/topic mapping;
- dùng làm weak labels hoặc seed labels nếu đã kiểm tra lại chất lượng nhãn;
- merge vào dataset chính sau khi normalize schema và dedup theo `post_id`/`post_url`.

Lý do tạm để trong `03_Archive_Not_For_Training/labeled_unused/`: nhãn có sẵn có thể không cùng chuẩn với pipeline train chính, và một số page có thể trùng với raw mới. Chưa nên đưa trực tiếp vào train trước khi audit nhãn và trùng lặp.

### Chi tiết từng file trong `json-targeted-crawl/`

Folder này hiện có 17 file JSON, tổng cộng 2,491 posts. Các file không cùng một schema hoàn toàn:

- **Schema 4 - Facebook post cơ bản**: không có `label/topic_label`, không có `post_type`.
- **Schema 7 - Targeted crawl có label/topic_label**: có `label`, `topic_label`, `feedback_id`.
- **Schema 8 - Targeted Tuổi Trẻ có post_type**: có `post_type`, `external_url`, nhưng không có `label/topic_label`.

| File | Số posts | Page | Nhãn/topic | Schema | Ghi chú tái sử dụng |
|---|---:|---|---|---|---|
| `Han_posts_Tuổi_Trẻ.json` | 39 | Tuổi Trẻ | không có | Schema 4 | Có thể merge với Tuổi Trẻ sau dedup `post_id`/`post_url`. |
| `posts_CGV_Cinemas_Vietnam.json` | 180 | CGV Cinemas Vietnam | Phim ảnh | Schema 7 | Candidate tốt cho chủ đề Phim ảnh. |
| `posts_Cuồng_Phim.json` | 200 | Cuồng Phim | Phim ảnh | Schema 7 | Candidate tốt cho chủ đề Phim ảnh. |
| `posts_Cổ_Động.json` | 71 | Cổ Động | Âm nhạc | Schema 7 | Candidate cho Âm nhạc, cần kiểm tra nội dung page. |
| `posts_FPT_Play_Thể_Thao.json` | 21 | FPT Play Thể Thao | Thể thao | Schema 7 | Ít record, dùng bổ sung hoặc kiểm tra rule. |
| `posts_Ghiền_Bóng_Đá_TV.json` | 200 | Ghiền Bóng Đá TV | Thể thao | Schema 7 | Candidate tốt cho Thể thao. |
| `posts_Music_Hall___Đại_sảnh_Âm_nhạc.json` | 35 | Music Hall - Đại sảnh Âm nhạc | Âm nhạc | Schema 7 | Ít record, dùng bổ sung. |
| `posts_Notifications.json` | 2 | Notifications | Thể thao | Schema 7 | Tên page bất thường, cần kiểm tra trước khi dùng. |
| `posts_On_Sports.json` | 13 | On Sports | Thể thao | Schema 7 | Ít record, dùng bổ sung. |
| `posts_Ra_Rạp_Xem_Gì.json` | 178 | Ra Rạp Xem Gì ? | Phim ảnh | Schema 7 | Candidate tốt cho Phim ảnh. |
| `posts_Schannel.json` | 148 | Schannel | không có | Schema 4 | Không có label sẵn, có thể merge nếu cần nguồn Schannel cũ. |
| `posts_Troll_Bóng_Đá.json` | 203 | Troll Bóng Đá | Thể thao | Schema 7 | Candidate tốt cho Thể thao. |
| `posts_Tuổi_Trẻ.json` | 29 | Tuổi Trẻ | không có | Schema 8 | Có `post_type`; merge với Tuổi Trẻ sau normalize. |
| `posts_VnExpress_net.json` | 769 | VnExpress.net | không có | Schema 4 | Nhiều record, có thể tái dùng nếu dedup với VnExpress raw chính. |
| `posts_congdongvnexpress.json` | 3 | VnExpress.net | không có | Schema 4 | Rất ít record, có thể bỏ hoặc dùng kiểm tra. |
| `posts_Đài_Phát_Thanh.json` | 200 | Đài Phát Thanh. | Âm nhạc | Schema 7 | Candidate tốt cho Âm nhạc. |
| `posts_Ổ_Phim.json` | 200 | Ổ Phim | Phim ảnh | Schema 7 | Candidate tốt cho Phim ảnh. |

### Cấu trúc các schema trong `json-targeted-crawl/`

#### Targeted Schema 4 - Post cơ bản không nhãn

Áp dụng cho:

- `Han_posts_Tuổi_Trẻ.json`
- `posts_Schannel.json`
- `posts_VnExpress_net.json`
- `posts_congdongvnexpress.json`

Các field chính:

```text
source_type, page_name, page_url, page_handle, page_followers,
post_url, post_id, post_content,
like_count, love_count, haha_count, wow_count, sad_count, angry_count, care_count,
total_reactions, comment_count, share_count,
share_per_follower, comment_per_follower, reaction_per_follower,
crawl_time, crawl_time_human
```

Mẫu dữ liệu:

```json
{
  "source_type": "Facebook",
  "page_name": "VnExpress.net",
  "page_url": "https://www.facebook.com/congdongvnexpress",
  "page_handle": "congdongvnexpress",
  "page_followers": 4700000,
  "post_url": "https://www.facebook.com/congdongvnexpress/posts/1429078069254200",
  "post_id": "1429078069254200",
  "post_content": "Thủ tướng yêu cầu khẩn trương dạy bơi trong trường phổ thông",
  "like_count": 2452,
  "love_count": 78,
  "haha_count": 22,
  "wow_count": 2,
  "sad_count": 0,
  "angry_count": 0,
  "care_count": 0,
  "total_reactions": 2554,
  "comment_count": 100,
  "share_count": 12,
  "share_per_follower": 0.0,
  "comment_per_follower": 0.0,
  "reaction_per_follower": 0.0005,
  "crawl_time": 1740000000,
  "crawl_time_human": "2025-..."
}
```

#### Targeted Schema 7 - Post có nhãn/topic

Cụ thể:

- `posts_CGV_Cinemas_Vietnam.json`
- `posts_Cuồng_Phim.json`
- `posts_Cổ_Động.json`
- `posts_FPT_Play_Thể_Thao.json`
- `posts_Ghiền_Bóng_Đá_TV.json`
- `posts_Music_Hall___Đại_sảnh_Âm_nhạc.json`
- `posts_Notifications.json`
- `posts_On_Sports.json`
- `posts_Ra_Rạp_Xem_Gì.json`
- `posts_Troll_Bóng_Đá.json`
- `posts_Đài_Phát_Thanh.json`
- `posts_Ổ_Phim.json`

Dạng file: JSON array. Giống post cơ bản nhưng có thêm `label`, `topic_label`, `feedback_id`. Đây là nhóm **candidate reusable**, không phải dữ liệu hỏng.

Các field chính:

```text
source_type, page_name, page_url, page_followers,
label, topic_label,
post_url, post_id, feedback_id, post_content,
like_count, love_count, haha_count, wow_count, sad_count, angry_count, care_count,
total_reactions, comment_count, share_count,
share_per_follower, comment_per_follower, reaction_per_follower,
crawl_time, crawl_time_human
```

```json
{
  "source_type": "Facebook",
  "page_name": "Ổ Phim",
  "page_url": "https://www.facebook.com/ophimhayx",
  "page_followers": 1100000,
  "label": "Phim ảnh",
  "topic_label": "Phim ảnh",
  "post_url": "https://www.facebook.com/ophimhayx/posts/...",
  "post_id": "pfbid...",
  "feedback_id": "...",
  "post_content": "...",
  "like_count": 100,
  "love_count": 10,
  "haha_count": 0,
  "wow_count": 0,
  "sad_count": 0,
  "angry_count": 0,
  "care_count": 0,
  "total_reactions": 110,
  "comment_count": 12,
  "share_count": 1,
  "share_per_follower": 0.0,
  "comment_per_follower": 0.0,
  "reaction_per_follower": 0.0,
  "crawl_time": 1740000000,
  "crawl_time_human": "2025-..."
}
```

#### Targeted Schema 8 - Post có post_type/external_url

Áp dụng cho:

- `data/03_Archive_Not_For_Training/labeled_unused/json-targeted-crawl/posts_Tuổi_Trẻ.json`

Dạng file: JSON array. Gần với Schema 4 nhưng có thêm `post_type`, `external_url`, không có `post_timestamp_*`. File này cũng thuộc nhóm targeted crawl có thể tái sử dụng sau khi normalize/dedup.

Các field chính:

```text
source_type, page_name, page_url, page_handle, page_followers,
post_url, post_id, post_type, external_url, post_content,
like_count, love_count, haha_count, wow_count, sad_count, angry_count, care_count,
total_reactions, comment_count, share_count,
share_per_follower, comment_per_follower, reaction_per_follower,
crawl_time, crawl_time_human
```

```json
{
  "source_type": "Facebook",
  "page_name": "Tuổi Trẻ",
  "page_url": "https://www.facebook.com/baotuoitre",
  "page_handle": "baotuoitre",
  "page_followers": 2900000,
  "post_url": "https://www.facebook.com/baotuoitre/posts/1330944352503348",
  "post_id": "1330944352503348",
  "post_type": "post",
  "external_url": null,
  "post_content": "...",
  "like_count": 100,
  "love_count": 0,
  "haha_count": 0,
  "wow_count": 0,
  "sad_count": 0,
  "angry_count": 0,
  "care_count": 0,
  "total_reactions": 100,
  "comment_count": 10,
  "share_count": 1,
  "share_per_follower": 0.0,
  "comment_per_follower": 0.0,
  "reaction_per_follower": 0.0,
  "crawl_time": 1740000000,
  "crawl_time_human": "2025-..."
}
```

## Cấu trúc CSV/XLSX archive

Các file CSV/XLSX labeled cũ nằm trong:

```text
data/03_Archive_Not_For_Training/labeled_unused/csv-data(labeled)/
```

Schema CSV:

```text
comments_new.csv:
  post_id, cmt_id, comment

content_posts.csv:
  post_id, content

posts_new.csv:
  post_id, content, comment_ids

posts_new_with_keywords.csv:
  post_id, content, comment_ids, label, keywords

posts_new_with_keywords_classified.csv:
  post_id, content, comment_ids, label, keywords

1.5flash_content_classified.csv:
  post_id, content, comment_ids, label_from_content

2.0flash_content_classified.csv:
  post_id, content, comment_ids, label_from_content

posts_new_content_classified.csv:
  post_id, content, comment_ids, label_from_content

train.csv:
  post_id, content, comment_ids, label_from_content

test.csv:
  post_id, content, comment_ids, label_from_content
```

Ví dụ một dòng CSV dạng post labeled:

```csv
post_id,content,comment_ids,label_from_content
pfbid...,"Nội dung bài viết...", "['cmt_1','cmt_2']", "Tin tức"
```

## So sánh các nhóm dữ liệu đang có

### Giống nhau

Phần lớn dữ liệu trong repo đều xoay quanh **Facebook posts** và có thể quy về một schema phân tích chung sau normalize:

```text
source/page metadata:
  source_type, page_name, page_url, page_handle, page_followers

post identity/content:
  post_url, post_id, post_content

engagement:
  like_count, love_count, haha_count, wow_count, sad_count, angry_count, care_count,
  total_reactions, comment_count, share_count

derived metrics:
  share_per_follower, comment_per_follower, reaction_per_follower

crawl metadata:
  crawl_time, crawl_time_human
```

Các nhóm khác nhau chủ yếu ở mức độ đầy đủ của metadata, cách lưu timestamp, có/không có nhãn, và có/không có comments chi tiết.

### Khác nhau theo nhóm dữ liệu

| Nhóm dữ liệu | Vị trí | Quy mô | Schema chính | Có nhãn? | Có timestamp post? | Có comments chi tiết? | Vai trò hiện tại |
|---|---|---:|---|---|---|---|---|
| Team raw mới | `01_Raw_Data/02_Team_Crawled_Raw/Phuc`, `Nhung`, `Yen` | khoảng 9,967 posts schema mới | Schema 5 | Không | Có `post_timestamp_*` | Không | Nguồn raw chính để train sau normalize/dedup. |
| Team legacy Han/Nhung | `01_Raw_Data/02_Team_Crawled_Raw/Han`, `Nhung/get_from_Nhung_legacy` | khoảng 2,931 posts schema cơ bản | Schema 4 và một phần Schema 5 | Không | Phần lớn không có timestamp post | Không | Raw phụ, dùng bổ sung sau khi normalize. |
| Existing ViTrend raw JSON | `01_Raw_Data/01_Existing_ViTrend_Raw/json-crawl-data/*.json` | 2,837 posts JSON + 48 comments tree | Schema 1, 2 | Không | Có `creation_time`, không cùng chuẩn Schema 5 | Có trường `comments` hoặc `comments.json` | Legacy raw, cần parser riêng. |
| Existing ViTrend raw JSONL | `01_Raw_Data/01_Existing_ViTrend_Raw/json-crawl-data/*.jsonl` | 1,505 posts JSONL | Schema 3 | Không | Có `creation_time` | Có trường `comments` | Bản line-delimited của một phần crawl legacy. |
| Targeted crawl candidate | `03_Archive_Not_For_Training/labeled_unused/json-targeted-crawl` | 2,491 posts | Schema 4, 7, 8 | Một phần có `label/topic_label` | Không có `post_timestamp_*` | Không | Candidate tái sử dụng, cần audit nhãn và dedup. |
| Labeled CSV/XLSX cũ | `03_Archive_Not_For_Training/labeled_unused/csv-data(labeled)` | 1,006-20,105 rows tùy file | CSV tabular | Có `label`, `keywords`, hoặc `label_from_content` ở một số file | Không | Comments tách ở `comments_new.csv` | Dữ liệu ViTrend đã preprocess/gán nhãn, duplicate nhiều; không đưa vào Master mặc định. |
| Checkpoint | `03_Archive_Not_For_Training/checkpoints` | 13 files | Schema 6 | Không | Lưu frontier crawl, không phải post | Không | Chỉ để biết trạng thái crawl/resume. |
| Debug/probe | `03_Archive_Not_For_Training/debug_probe` | 23 posts + 1 checkpoint | Schema 5 + Schema 6 | Không | Có timestamp post ở file posts | Không | Dữ liệu thử nghiệm, không đưa thẳng vào train. |
| Old/redundant final batch | `03_Archive_Not_For_Training/old_or_redundant/json-final-v2-yannews-vnexpress` | 259 posts | Schema 5 | Không | Có timestamp post | Không | Batch nhỏ/cũ, có thể dùng đối chiếu sau dedup. |

### Khác nhau theo schema

| Schema | Dạng file | Điểm nhận diện | Ưu điểm | Lưu ý khi normalize |
|---|---|---|---|---|
| Schema 1 - Comment tree legacy | JSON array | `text`, `image`, `reactions`, `feedback_info.comments` | Có cấu trúc reply/comment chi tiết | Không phải post-level dataset; cần flatten nếu muốn dùng comment. |
| Schema 2 - Post legacy JSON | JSON array | `post_content`, `image_paths`, `feedback_id`, `creation_time`, `reactions_detail`, `comments` | Có ảnh/comments legacy, có `creation_time` | `share_count` có thể là string; reaction keys viết hoa như `Like`, `Love`. |
| Schema 3 - Post legacy JSONL | JSONL | Mỗi dòng là một post, field giống Schema 2 | Dễ stream từng dòng | Không dùng `json.load()` cho cả file. |
| Schema 4 - Facebook post cơ bản | JSON array | Có `page_handle`, không có `post_type`, không có `post_timestamp_*` | Gần với schema raw mới, dễ normalize | Timestamp chỉ là `crawl_time`, không phải thời điểm post. |
| Schema 5 - Facebook post mới | JSON array | Có `post_type`, `external_url`, `post_timestamp_*`, `timestamp_*` | Đầy đủ nhất, nên dùng làm schema đích | Cần kiểm tra `timestamp_status` nếu lọc theo ngày post. |
| Schema 6 - Checkpoint | JSON object | `reason`, `saved_at`, `frontier`, `scroll_y`, `dom_nodes` | Hữu ích để audit crawl | Không phải dữ liệu train. |
| Schema 7 - Targeted có nhãn | JSON array | Có `label`, `topic_label`, `feedback_id` | Có thể tái sử dụng làm weak/seed labels | Cần audit nhãn và chuẩn hóa label taxonomy. |
| Schema 8 - Targeted có post_type | JSON array | Có `post_type`, `external_url`, không có `post_timestamp_*` | Gần Schema 4 nhưng giàu hơn một chút | Cần map về Schema 5 nếu đưa vào pipeline chính. |

### Nhóm nào nên ưu tiên dùng

1. **Ưu tiên 1 - raw chính:** `01_Raw_Data/02_Team_Crawled_Raw/Phuc`, `Nhung`, `Yen`.
   Đây là nhóm mới nhất và đồng nhất nhất, đa số theo Schema 5.

2. **Ưu tiên 2 - raw bổ sung:** `Han/get_from_Han_legacy`, `Nhung/get_from_Nhung_legacy`, và `01_Existing_ViTrend_Raw`.
   Nhóm này tăng coverage nhưng cần normalize kỹ hơn vì schema cũ hoặc thiếu timestamp post.

3. **Ưu tiên 3 - candidate có nhãn:** `labeled_unused/json-targeted-crawl`.
   Nhóm này có giá trị tái sử dụng, nhưng nên audit nhãn, kiểm tra taxonomy, rồi mới đưa vào train.

4. **Không dùng Master mặc định:** `csv-data(labeled)`.
   Nhóm này là dữ liệu ViTrend đã preprocess/gán nhãn, duplicate nhiều với raw, chỉ giữ để audit/benchmark khi cần.

5. **Không dùng train trực tiếp:** `checkpoints`, `debug_probe`, `old_or_redundant`.
   Có thể dùng để audit, đối chiếu, hoặc debug pipeline.

### Các điểm cần chuẩn hóa trước khi merge

- Chuẩn hóa tên trường thời gian: `post_timestamp_unix`/`post_timestamp_human` của Schema 5 khác `creation_time` của Schema 2/3.
- Chuẩn hóa reaction detail: Schema 2/3 dùng `reactions_detail` với key `Like/Love/Haha`, còn Schema 4/5/7/8 tách thành `like_count`, `love_count`, `haha_count`.
- Chuẩn hóa kiểu dữ liệu: `share_count` ở legacy có thể là string, các schema mới thường là number.
- Chuẩn hóa label: `label`, `topic_label`, `label_from_content`, `keywords` không cùng nguồn sinh nhãn.
- Dedup theo nhiều khóa: ưu tiên `post_id`, sau đó `post_url`, sau đó hash nội dung + page + timestamp nếu thiếu id.
- Không trộn checkpoint/debug vào dataset chính.

## Gợi ý sử dụng khi xử lý dữ liệu

- Ưu tiên lấy raw chính từ `data/01_Raw_Data/02_Team_Crawled_Raw/`.
- Legacy raw trong `01_Existing_ViTrend_Raw/` nên normalize riêng vì schema khác đáng kể.
- Không đưa `checkpoint_*.json` vào dataset train; checkpoint chỉ để biết trạng thái crawl.
- Không dùng trực tiếp `03_Archive_Not_For_Training/labeled_unused/` để train nếu chưa kiểm tra lại nhãn và trùng lặp.
- Riêng `labeled_unused/json-targeted-crawl/` có thể tái sử dụng. Nếu quyết định dùng lại, nên chuyển logic bằng pipeline xử lý sang `02_Processed_Data/`, thay vì move raw ngay.
- Nếu muốn đổi cấu trúc sau này, tên hợp lý hơn cho nhóm này là `03_Archive_Not_For_Training/reusable_candidates/json-targeted-crawl/` hoặc `01_Raw_Data/03_Candidate_Labeled_Raw/json-targeted-crawl/`. Hiện tại chưa cần di chuyển khi mới chỉ cân nhắc.
- Khi đọc `.jsonl`, đọc từng dòng bằng `json.loads(line)`, không dùng `json.load()` cho cả file.
- Khi xử lý tên file có dấu cách như `posts_Schannel 2.json`, cần quote path trong shell.

## Master Data pipeline

Checklist và quy trình tạo Master CSV nằm ở:

```text
docs/master_data_pipeline.md
```

Script tạo Master TeamCrawl chính:

```bash
python3 src/build_master_teamcrawl_posts.py
```

Lệnh này chỉ lấy post-level JSON/JSONL trong `data/01_Raw_Data/02_Team_Crawled_Raw/`, chỉ giữ record có `page_name`, không lấy ViTrend, không lấy Archive và không lấy comment-level rows.

Output mặc định:

```text
data/02_Processed_Data/Master_Facebook_News_Posts_TeamCrawl.csv
data/02_Processed_Data/Master_Facebook_News_Posts_TeamCrawl_After_Dedup.csv
data/02_Processed_Data/Annotation_Template_TeamCrawl.csv
```

`Master_Facebook_News_Posts_TeamCrawl.csv` là bản gốc giữ nguyên để đối chiếu. `Master_Facebook_News_Posts_TeamCrawl_After_Dedup.csv` là bản đã dedup theo `post_content_for_labeling`, còn 11,786 dòng và không có duplicate ở cột này. `Annotation_Template_TeamCrawl.csv` là file gán nhãn topic gốc, chưa rebuild theo bản after dedup.

Master 14K cũ có cả ViTrend đã được lưu trong:

```text
data/02_Processed_Data/_archive/master_14K_before_teamcrawl_20260603_202533/
```

Nếu cần build lại Master raw-only cũ để audit, có thể dùng `src/build_master_facebook_posts.py`, nhưng không dùng làm Master chính hiện tại.

Dataset báo chí only nằm trong:

```text
data/02_Processed_Data/Báo chí only/
```

Build lại dataset báo chí only:

```bash
python3 src/build_master_bao_chi_posts.py
```

Output:

```text
data/02_Processed_Data/Báo chí only/Master_Facebook_News_Posts_Bao_Chi_Only.csv
data/02_Processed_Data/Báo chí only/Annotation_Template_Bao_Chi_Only.csv
data/02_Processed_Data/Báo chí only/README.md
```

Mặc định `topic_label_final` để trống để nhóm gán nhãn/audit lại. Sau khi điền template TeamCrawl, merge nhãn bằng:

```bash
python3 src/build_master_teamcrawl_posts.py \
  --annotation-file data/02_Processed_Data/Annotation_Template_TeamCrawl.csv
```

Script `src/build_master_facebook_posts.py` hiện chỉ dùng khi cần audit lại Master raw-only cũ có ViTrend. Không dùng script đó làm Master chính hiện tại.

Nếu cần audit CSV labeled cũ trong Master tạm thời bằng script cũ, có thể bật:

```bash
python3 src/build_master_facebook_posts.py --include-labeled-csv
```

Không khuyến nghị dùng option này cho Master chính vì `csv-data(labeled)` là dữ liệu đã preprocess/gán nhãn, duplicate nhiều và nằm trong Archive.

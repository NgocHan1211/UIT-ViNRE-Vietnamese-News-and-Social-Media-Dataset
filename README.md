# University of Information Technology, Vietnam National University Ho Chi Minh City (UIT)

**Course:** DS107 - Computational Thinking for Data Science  
**Project:** Vietnamese Facebook News Classification and User Reaction Analysis: An Engagement Metadata Approach  
**Field:** Social Media Data Mining and Natural Language Processing (NLP)

---

## Tech Stack

The project uses Python and the following tools:

- **Data processing:** `Pandas`, `NumPy`
- **Language modeling:** `PyTorch`, `PhoBERT`
- **Interactive dashboard:** `Streamlit`

---

## 1. Overview

This document describes the structure, size, and schema of the dataset used in the media trend analysis project.

The project follows a **post-centric approach** and uses a **single source of truth (SSOT)** for its data. Comment records are excluded so that the classification model uses original posts rather than comments. The resulting **Golden Dataset** links post text and topic labels with engagement metadata.

---

## 2. Project Directory Structure

```text
DS107_Repo/
├── data/
│   ├── csv-data(labeled)/     Labeled data, including train.csv and test.csv
│   ├── json-crawl-data/       Raw Facebook metadata in JSON files
│   ├── Processed_Data/        Master_Data_Raw.csv with 2,077 matched records
│   └── .gitkeep
├── notebooks/                 Experimental Jupyter notebooks
├── src/                       Python source code
├── dashboard/                 Streamlit dashboard
├── .gitignore                 Rules for excluding large data and cache files
├── CONTRIBUTING.md            Contribution guidelines and team Git workflow
├── requirements.txt           Project dependencies
└── README.md                  Golden Dataset documentation
```

## 3. Data Volume and Statistics

The data was filtered to remove duplicate, irrelevant, and unmatched records.

| Processing stage | Records | Description |
| :--- | ---: | :--- |
| Initial data | 2,796 | Raw records containing both posts and comments |
| After deduplication | 2,794 | Duplicate content removed |
| After record-type filtering | 2,634 | 160 comment records removed; original posts retained |
| Golden Dataset after mapping | 2,077 | Original posts successfully matched with JSON metadata |

The 2,077 records in this Golden Dataset have five topic labels:

- Social News
- Sports
- Slang & Memes
- Movies
- Music

## 4. Data Schema

The dataset combines fields from two sources.

### 4.1. CSV Data: Topic Labels

- **`content`:** Raw post text used to match records across the two sources.
- **`label_from_content`:** Human-assigned topic label.
- **`comment_ids`:** A field used to distinguish original posts from comment records.

### 4.2. JSON Data: Engagement Metadata

- **`post_content`:** Post text matched against the CSV `content` field.
- **`creation_time`:** Publication time, normalized to a datetime value in UTC+7.
- **`share_count`:** Number of shares, converted to a numeric value.
- **`reactions_detail`:** Reaction counts expanded into separate fields: `like`, `love`, `haha`, `wow`, `sad`, `angry`, and `care`.

## 5. Data Mapping

Because the CSV and JSON sources do not share consistent record IDs, the project matches records by post text:

1. Extract text from `content` in the CSV files and `post_content` in the JSON files.
2. Remove extra spaces, tabs, and line breaks, then convert the text to lowercase to create a normalized matching key.
3. Perform an inner join using that key. Exclude posts whose text cannot be matched reliably because of truncation or encoding differences.

The resulting Golden Dataset contains **2,077 matched post records**.

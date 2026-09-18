# Verify IAA Report

Generated: 2026-06-11 11:27:07

## Scope

Tính IAA trên 100 dòng đầu tiên của 3 file trong `data/05_Labeling/Labeled`. Report này chỉ dùng để verify IAA lần cuối.

## Input Files

| annotator | file | rows_read | missing_topic_labels_in_first_100 |
| --- | --- | --- | --- |
| Nhung | data/05_Labeling/Labeled/[DS107] Gán nhãn - Nhung.csv | 100 | 2 |
| Yen | data/05_Labeling/Labeled/[DS107] Gán nhãn - Yen.csv | 100 | 1 |
| Han | data/05_Labeling/Labeled/[DS107] Gán nhãn - Han.csv | 100 | 4 |

## Record Order Check

| comparison | same_order | same_set |
| --- | --- | --- |
| Nhung vs Yen | True | True |
| Nhung vs Han | True | True |

## Overview

| scope | total_rows | valid_rows_for_fleiss | rows_with_missing_label | labels_seen | fleiss_kappa | mean_cohen_kappa |
| --- | --- | --- | --- | --- | --- | --- |
| first_100_rows | 100 | 96 | 4 | 18 | 0.8239 | 0.8213 |

## Fleiss' Kappa

| n_items | n_raters | observed_agreement | expected_agreement | fleiss_kappa |
| --- | --- | --- | --- | --- |
| 96 | 3 | 0.8438 | 0.1125 | 0.8239 |

## Cohen's Kappa

| pair | n | observed_agreement | expected_agreement | cohen_kappa |
| --- | --- | --- | --- | --- |
| Nhung vs Yen | 98 | 0.8673 | 0.1128 | 0.8505 |
| Nhung vs Han | 96 | 0.8333 | 0.1105 | 0.8126 |
| Yen vs Han | 96 | 0.8229 | 0.1110 | 0.8008 |

## Agreement Counts

| agreement_type | rows | pct_all_100_rows |
| --- | --- | --- |
| full_agreement | 74 | 74.0% |
| partial_disagreement | 21 | 21.0% |
| complete_disagreement | 1 | 1.0% |
| incomplete | 4 | 4.0% |

## Missing Label Rows

| record_id | missing_annotators |
| --- | --- |
| REC_004211 | Nhung, Yen, Han |
| REC_012815 | Han |
| REC_012548 | Han |
| REC_012655 | Nhung, Han |

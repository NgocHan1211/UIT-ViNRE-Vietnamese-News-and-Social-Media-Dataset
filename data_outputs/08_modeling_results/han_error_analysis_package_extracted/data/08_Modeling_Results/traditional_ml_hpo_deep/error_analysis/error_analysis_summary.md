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

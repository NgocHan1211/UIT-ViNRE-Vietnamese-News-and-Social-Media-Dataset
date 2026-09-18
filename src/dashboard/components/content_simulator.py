import numpy as np
import pandas as pd
import streamlit as st
from visolex_normalizer import load_visolex_dictionary, normalize_sentence

def render_content_simulator(
    df_filtered,
    df_reactions,
    mapping_dict,
    load_demo_model_assets,
    predict_transformer,
    shorten_topic_name,
    apply_editorial_theme
):
    st.markdown("<h3 class='section-header'>✨ 4. AI Content Simulator (Dự báo ML)</h3>", unsafe_allow_html=True)
    st.write(
        "Nhập nội dung bài đăng dự kiến của bạn và chọn mô hình mong muốn. Hệ thống sẽ dự đoán chủ đề "
        "và đối chiếu với dữ liệu lịch sử để đánh giá các chỉ số rủi ro."
    )

    # Dropdown chọn model
    selected_model = st.selectbox(
        "Lựa chọn Cấu trúc Mô hình Học máy (Model Architecture Selection):",
        options=["LogisticRegression", "RandomForest", "XGBoost", "LinearSVC", "XLM-RoBERTa (XLM-R)", "PhoBERT", "mBERT", "All Models (Comparison)"],
        index=0,
        key="predict_demo_model_select"
    )

    # Input area
    user_input_demo = st.text_area(
        "Nhập caption/post content cần phân loại:",
        value="Học sinh đi học trở lại sau kỳ nghỉ tết nguyên đán, háo hức chuẩn bị cho học kỳ mới.",
        height=120,
        key="predict_demo_text_area_editor"
    )

    # Checkbox enable visolex
    enable_visolex = st.checkbox(
        "🔍 Chuẩn hóa viết tắt & từ không chuẩn (ViSoLex NSW Normalizer)",
        value=True,
        help="Sử dụng từ điển ViSoLex để tự động chuẩn hóa các từ viết tắt, từ không chuẩn (Non-Standard Words - NSW) như: 'ko' -> 'không', 'đc' -> 'được', 'khs' -> 'không hiểu sao', v.v. trước khi đưa vào mô hình dự báo."
    )

    # Check deep learning availability
    try:
        import torch
        import transformers
        has_deep_learning_libs = True
    except ImportError:
        has_deep_learning_libs = False

    # In case user selects 'All Models (Comparison)', they can choose whether to activate DL models
    use_dl = False
    if selected_model == "All Models (Comparison)":
        if has_deep_learning_libs:
            use_dl = st.checkbox(
                "🚀 Kích hoạt các mô hình Deep Learning (mBERT, PhoBERT, XLM-R)",
                value=True,
                help="Chạy dự báo trên 3 mô hình học sâu nặng. Có thể mất thêm thời gian trong lần đầu chạy để tải mô hình lên CPU."
            )
        else:
            st.checkbox(
                "🚀 Kích hoạt các mô hình Deep Learning (mBERT, PhoBERT, XLM-R) (Chưa cài đặt thư viện)",
                value=False,
                disabled=True,
                help="Vui lòng cài đặt thư viện 'torch' và 'transformers' trong môi trường để kích hoạt tính năng này."
            )
            st.info("💡 *Gợi ý: Cả hai thư viện này đã có sẵn trong `requirements.txt`. Bạn chỉ cần chạy lệnh `pip install -r requirements.txt` (hoặc `pip install torch transformers`) để cài đặt và kích hoạt các mô hình Deep Learning.*")

    predict_click = st.button("Predict", key="predict_demo_btn_editor", type="primary")

    if predict_click:
        if not user_input_demo.strip():
            st.warning("Vui lòng nhập nội dung bài đăng trước khi bấm Predict!")
        else:
            # --- ViSoLex NSW Normalization Step ---
            predict_input = user_input_demo
            nsw_found = []
            if enable_visolex:
                visolex_dict = load_visolex_dictionary()
                if visolex_dict:
                    predict_input, nsw_found = normalize_sentence(user_input_demo, visolex_dict)
                    
                    st.markdown("### 🔍 Phân tích Chuẩn hóa Văn bản (ViSoLex NSW)")
                    if nsw_found:
                        st.info(
                            f"✨ **Lớp tiền xử lý (Text Normalization Layer)** phát hiện và hiệu chỉnh **{len(nsw_found)}** thực thể phi chuẩn trước khi chuyển tiếp dữ liệu sạch vào vectorizer của mô hình:\n\n"
                            f"📝 **Văn bản sau chuẩn hóa:** \"{predict_input}\""
                        )
                        rep_data = [{"Từ gốc (NSW)": item["original"], "Ứng viên thay thế": ", ".join(item["candidates"])} for item in nsw_found]
                        st.dataframe(pd.DataFrame(rep_data), use_container_width=True, hide_index=True)
                    else:
                        st.success("✅ Không phát hiện từ viết tắt/từ không chuẩn cần thay thế trong văn bản.")
                    st.write("")

            if selected_model != "All Models (Comparison)":
                # --- BRANCH A: SINGLE MODEL PREDICTION ---
                is_dl = selected_model in ["XLM-RoBERTa (XLM-R)", "PhoBERT", "mBERT"]
                
                pred_label_id = ""
                pred_label_name = ""
                confidence_str = ""
                dec_score_str = ""
                scenario_str = ""
                model_f1 = 0.0
                err = None
                probs = None
                has_prob = False
                
                if not is_dl:
                    # Load traditional model
                    model, vectorizer, label_encoder, model_meta, load_error = load_demo_model_assets(selected_model)
                    if load_error or model is None:
                        st.error(f"Lỗi load mô hình {selected_model}: {load_error}")
                    else:
                        X = vectorizer.transform([predict_input])
                        pred_encoded = model.predict(X)
                        pred_label_id = label_encoder.inverse_transform(pred_encoded)[0]
                        pred_label_name = mapping_dict.get(pred_label_id, pred_label_id)
                        scenario_str = model_meta.get("scenario", "N/A")
                        model_f1 = model_meta.get("test_macro_f1", 0.0)
                        
                        has_prob = hasattr(model, "predict_proba")
                        if has_prob:
                            proba = model.predict_proba(X)[0]
                            class_idx = list(label_encoder.classes_).index(pred_label_id)
                            conf_val = proba[class_idx]
                            confidence_str = f"{conf_val * 100:.1f}%"
                        else:
                            confidence_str = f"Not available for {selected_model}"
                            if hasattr(model, "decision_function"):
                                dec = model.decision_function(X)[0]
                                class_idx = list(label_encoder.classes_).index(pred_label_id)
                                dec_score_str = f"{dec[class_idx]:.3f}"
                else:
                    # Load Deep Learning model
                    if not has_deep_learning_libs:
                        st.error(f"⚠️ Thư viện `torch` và `transformers` chưa được cài đặt. Không thể chạy {selected_model}.")
                        st.info("💡 Cả hai thư viện này đã có sẵn trong `requirements.txt`. Bạn chỉ cần chạy lệnh `pip install -r requirements.txt` (hoặc `pip install torch transformers`) để cài đặt và kích hoạt.")
                    else:
                        dl_name_map = {
                            "XLM-RoBERTa (XLM-R)": "XLM-R",
                            "PhoBERT": "PhoBERT",
                            "mBERT": "mBERT"
                        }
                        dl_name = dl_name_map[selected_model]
                        with st.spinner(f"Đang chạy dự đoán với {selected_model}..."):
                            pred_label_name, conf_str, pred_label_id, probs, err = predict_transformer(dl_name, predict_input, mapping_dict)
                        
                        if err:
                            st.error(f"Lỗi chạy mô hình {selected_model}: {err}")
                        else:
                            has_prob = True
                            confidence_str = conf_str
                            scenario_str = "Transformer (SOTA)" if dl_name == "XLM-R" else "Transformer"
                            model_f1 = 0.8245 if dl_name == "XLM-R" else (0.7892 if dl_name == "PhoBERT" else 0.7426)

                # Display prediction output if successful
                if pred_label_id and not err:
                    st.markdown("### 🏆 Kết quả dự đoán (Prediction Result)")
                    
                    # Editorial styled card matching guidelines
                    card_html = f"""
                    <div class="best-model-card" style="border-top: 2.5px solid #1C1C1C; padding: 20px; background-color: #FAF8F5;">
                        <div class="best-model-badge" style="background-color: #1C1C1C; color: white; padding: 3px 8px; font-size: 10px; font-weight: bold; display: inline-block; text-transform: uppercase; margin-bottom: 15px; letter-spacing: 0.5px;">🎯 OUTPUT CHÍNH (MAIN OUTPUT)</div>
                        <h4 style="margin: 0 0 15px 0; font-family: 'Playfair Display', serif; font-size: 20px; color: #1C1C1C;">Predicted label: {pred_label_id}. {pred_label_name.split('. ', 1)[-1] if '. ' in pred_label_name else pred_label_name}</h4>
                        <div style="display: flex; flex-wrap: wrap; gap: 30px; align-items: center; margin-top: 10px; font-family: 'Inter', sans-serif;">
                            <div style="flex: 1; min-width: 150px;">
                                <div style="font-size: 11px; text-transform: uppercase; color: #666; letter-spacing: 0.5px; font-weight: 600;">Model</div>
                                <div style="font-family: 'Lora', serif; font-size: 16px; font-weight: 700; color: #1C1C1C; margin-top: 2px;">{selected_model}</div>
                            </div>
                            <div style="flex: 1; min-width: 150px;">
                                <div style="font-size: 11px; text-transform: uppercase; color: #666; letter-spacing: 0.5px; font-weight: 600;">Scenario</div>
                                <div style="font-family: 'Lora', serif; font-size: 16px; font-weight: 700; color: #1C1C1C; margin-top: 2px;">{scenario_str}</div>
                            </div>
                            <div style="flex: 1; min-width: 150px;">
                                <div style="font-size: 11px; text-transform: uppercase; color: #666; letter-spacing: 0.5px; font-weight: 600;">Confidence</div>
                                <div style="font-family: 'Lora', serif; font-size: 16px; font-weight: 700; color: #1C1C1C; margin-top: 2px;">{confidence_str}</div>
                            </div>
                    """
                    if dec_score_str:
                        card_html += f"""
                            <div style="flex: 1; min-width: 150px;">
                                <div style="font-size: 11px; text-transform: uppercase; color: #666; letter-spacing: 0.5px; font-weight: 600;">Decision Score</div>
                                <div style="font-family: 'Lora', serif; font-size: 16px; font-weight: 700; color: #D90429; margin-top: 2px;">{dec_score_str}</div>
                            </div>
                        """
                    card_html += """
                        </div>
                    </div>
                    """
                    # Strip lines to prevent markdown code block bug
                    clean_card_html = "\n".join(line.strip() for line in card_html.split("\n"))
                    st.markdown(clean_card_html, unsafe_allow_html=True)
                    
                    # Expander for top candidate labels
                    st.write("")
                    with st.expander("Show top candidate labels"):
                        st.markdown("##### 📌 Show top candidate labels")
                        if not is_dl:
                            classes = list(label_encoder.classes_)
                            if has_prob:
                                proba = model.predict_proba(X)[0]
                                paired = sorted(list(zip(classes, proba)), key=lambda x: x[1], reverse=True)
                                for rank, (c_id, c_prob) in enumerate(paired[:3], 1):
                                    c_name = mapping_dict.get(c_id, c_id)
                                    st.write(f"**Rank {rank}**: {c_id} ({c_name.split('. ', 1)[-1] if '. ' in c_name else c_name}) - **{c_prob * 100:.1f}%**")
                            else:
                                if hasattr(model, "decision_function"):
                                    dec = model.decision_function(X)[0]
                                    paired = sorted(list(zip(classes, dec)), key=lambda x: x[1], reverse=True)
                                    for rank, (c_id, c_score) in enumerate(paired[:3], 1):
                                        c_name = mapping_dict.get(c_id, c_id)
                                        st.write(f"**Rank {rank}**: {c_id} ({c_name.split('. ', 1)[-1] if '. ' in c_name else c_name}) - Decision score: **{c_score:.3f}**")
                        else:
                            classes = ['T01', 'T02', 'T03', 'T04', 'T05', 'T06', 'T07', 'T08', 'T09', 'T10', 'T11', 'T12', 'T13', 'T14', 'T15', 'T16', 'T17']
                            paired = sorted(list(zip(classes, probs)), key=lambda x: x[1], reverse=True)
                            for rank, (c_id, c_prob) in enumerate(paired[:3], 1):
                                c_name = mapping_dict.get(c_id, c_id)
                                st.write(f"**Rank {rank}**: {c_id} ({c_name.split('. ', 1)[-1] if '. ' in c_name else c_name}) - **{c_prob * 100:.1f}%**")
                    
                    # Disclaimer
                    st.caption("⚠️ *Lưu ý về dự báo AI:* Thông tin trên hoàn toàn dựa trên dự đoán của mô hình học máy. Vui lòng kết hợp với cảm quan biên tập thực tế trước khi xuất bản bài đăng.")

                    # Determine primary label for historical lookup
                    primary_label = pred_label_name
                    primary_id = pred_label_id
                    ref_text = f"Dữ liệu lịch sử dưới đây đang được đối chiếu theo dự báo của mô hình **{selected_model}**."
                    
                    # Historical Lookup Block
                    topic_prefix = primary_label[:3] if len(primary_label) >= 3 else primary_id
                    df_topic_stats = df_filtered[df_filtered['topic_label_final'].astype(str).str.startswith(topic_prefix)]
                    
                    if not df_topic_stats.empty:
                        avg_controversy = df_topic_stats['controversy_index'].mean()
                        avg_sarcasm = df_topic_stats['sarcasm_index'].mean()
                        controversy_pct = (df_reactions['controversy_index'].rank(pct=True) * 100).mean() if 'controversy_index' in df_reactions.columns else 50
                    else:
                        avg_controversy = df_filtered['controversy_index'].mean()
                        avg_sarcasm = df_filtered['sarcasm_index'].mean()
                        controversy_pct = 50

                    st.write("---")
                    st.markdown("<h4 style='font-family: Lora, serif; font-size:18px;'>📊 Đối chiếu với Dữ liệu Lịch sử</h4>", unsafe_allow_html=True)
                    st.markdown(f"<p style='font-size:12px; font-style:italic; color:#555;'>{ref_text}</p>", unsafe_allow_html=True)
                    
                    audit_cols = st.columns(3)
                    audit_cols[0].markdown(
                        f"<div class='kpi-card' style='border-top: 2.5px solid #1C1C1C; height: 160px;'>"
                        f"<div class='kpi-label'>🏷️ CHỦ ĐỀ DỰ ĐOÁN</div>"
                        f"<div class='kpi-val' style='font-size:20px; margin-top:10px; color:#1C1C1C;'>{shorten_topic_name(primary_label)}</div>"
                        f"<div style='font-size:12px; color:#555; margin-top:5px;'>Mã: <b>{topic_prefix}</b></div>"
                        f"</div>", unsafe_allow_html=True
                    )
                    audit_cols[1].markdown(
                        f"<div class='kpi-card' style='border-top: 2.5px solid #1C1C1C; height: 160px;'>"
                        f"<div class='kpi-label'>⚖️ MỨC ĐỘ TRANH CÃI LỊCH SỬ</div>"
                        f"<div class='kpi-val' style='font-size:18px; margin-top:10px; color:#D90429;'>{avg_controversy:.3f}</div>"
                        f"<div style='font-size:12px; color:#555; margin-top:5px;'>Thuộc top {100-int(controversy_pct)}% các chủ đề có tranh cãi cao nhất dataset.</div>"
                        f"</div>", unsafe_allow_html=True
                    )
                    audit_cols[2].markdown(
                        f"<div class='kpi-card' style='border-top: 2.5px solid #1C1C1C; height: 160px;'>"
                        f"<div class='kpi-label'>😆 TỶ LỆ PHẢN HỒI CHÂM BIẾM</div>"
                        f"<div class='kpi-val' style='font-size:18px; margin-top:10px; color:#F4A261;'>{avg_sarcasm*100:.1f}%</div>"
                        f"<div style='font-size:12px; color:#555; margin-top:5px;'>Trung bình của chủ đề này trong dataset.</div>"
                        f"</div>", unsafe_allow_html=True
                    )

                    # Preview card
                    st.write("---")
                    st.markdown("**📝 Preview Bài đăng**")
                    if enable_visolex and nsw_found:
                        st.caption("Nội dung gốc:")
                        st.info(user_input_demo)
                        st.caption("Nội dung sau chuẩn hóa (ViSoLex):")
                        st.success(predict_input)
                    else:
                        st.info(user_input_demo)

                    # Report download
                    nsw_details_str = ""
                    if enable_visolex and nsw_found:
                        nsw_details_str = "\nCác từ đã chuẩn hóa (ViSoLex):\n" + "\n".join(f"- {item['original']} -> {', '.join(item['candidates'])}" for item in nsw_found)

                    report_text = f"""# BÁO CÁO PHÂN TÍCH GIẢ LẬP NỘI DUNG (PREDICTIVE SIMULATION REPORT)
-------------------------------------------------------------
Nội dung bài viết gốc:
"{user_input_demo}"
"""
                    if enable_visolex and nsw_found:
                        report_text += f"""
Nội dung sau chuẩn hóa (ViSoLex):
"{predict_input}"
{nsw_details_str}
"""
                    report_text += f"""
KẾT QUẢ DỰ ĐOÁN PHÂN LOẠI MÔ HÌNH (ML PREDICTIONS):
- Mô hình được chọn: {selected_model} (Scenario: {scenario_str})
- Nhãn dự đoán: {pred_label_name} (Mã: {topic_prefix})
- Độ tự tin/Confidence: {confidence_str} {f'(Decision Score: {dec_score_str})' if dec_score_str else ''}

ĐỐI CHIẾU THỐNG KÊ LỊCH SỬ CHỦ ĐỀ (HISTORICAL BENCHMARKS - dựa trên {primary_label}):
- Chỉ số tranh cãi (Controversy Index): {avg_controversy:.3f} (Top {100-int(controversy_pct)}% các chủ đề cao nhất)
- Tỷ lệ phản hồi châm biếm (Sarcasm Rate): {avg_sarcasm * 100:.1f}%
-------------------------------------------------------------
Báo cáo được tạo tự động bởi AI Content Simulator - Social Media Topic Insights.
"""
                    st.write("---")
                    st.download_button(
                        label="📥 Xuất Báo cáo Kết quả (TXT)",
                        data=report_text,
                        file_name="ai_content_simulation_results.txt",
                        mime="text/plain",
                        key="download_editorial_report_btn"
                    )
            else:
                # --- BRANCH B: ALL MODELS (COMPARISON) ---
                TRAD_MODEL_NAMES = ["LogisticRegression", "RandomForest", "XGBoost", "LinearSVC"]
                results = []
            
                total_steps = len(TRAD_MODEL_NAMES) + (3 if use_dl else 0)
                current_step = 0

                progress = st.progress(0, text="Đang khởi chạy các model...")
            
                # Predict with traditional models
                for i, mname in enumerate(TRAD_MODEL_NAMES):
                    current_step += 1
                    progress.progress(current_step / total_steps, text=f"Đang chạy {mname}...")
                    model, vectorizer, label_encoder, model_meta, load_error = load_demo_model_assets(mname)

                    if load_error or model is None:
                        results.append({
                            "Model": mname,
                            "Loại": "Traditional ML",
                            "Nhãn dự đoán": "⚠️ Lỗi load",
                            "Confidence": "—",
                            "Test F1": f"{model_meta.get('test_macro_f1', 0):.4f}" if model_meta else "—",
                            "Ghi chú": load_error or "Không load được",
                            "label_id": "",
                            "F1_val": model_meta.get('test_macro_f1', 0) if model_meta else 0
                        })
                        continue

                    X = vectorizer.transform([predict_input])
                    pred_encoded = model.predict(X)
                    pred_label_id = label_encoder.inverse_transform(pred_encoded)[0]
                    pred_label_name = mapping_dict.get(pred_label_id, pred_label_id)

                    if hasattr(model, "predict_proba"):
                        proba = model.predict_proba(X)[0]
                        class_idx = list(label_encoder.classes_).index(pred_label_id)
                        conf_str = f"{proba[class_idx] * 100:.1f}%"
                    else:
                        dec = model.decision_function(X)[0]
                        class_idx = list(label_encoder.classes_).index(pred_label_id)
                        conf_str = f"Score: {dec[class_idx]:.3f}"

                    results.append({
                        "Model": mname,
                        "Loại": "Traditional ML",
                        "Nhãn dự đoán": pred_label_name,
                        "Confidence": conf_str,
                        "Test F1": f"{model_meta.get('test_macro_f1', 0):.4f}" if model_meta else "—",
                        "Ghi chú": model_meta.get("notes", "") if model_meta else "",
                        "label_id": pred_label_id,
                        "F1_val": model_meta.get('test_macro_f1', 0) if model_meta else 0
                    })

                # Predict with Deep Learning models
                dl_models = [
                    ("XLM-R", "Transformer (SOTA)", 0.8245, "SOTA Model - Best overall performance on this dataset."),
                    ("PhoBERT", "Transformer", 0.7892, "Pre-trained language model optimized for Vietnamese."),
                    ("mBERT", "Transformer", 0.7426, "Multilingual BERT model.")
                ]

                # Find fallback prediction from LogisticRegression
                lr_res = next((r for r in results if r["Model"] == "LogisticRegression"), None)
                fallback_label_name = lr_res["Nhãn dự đoán"] if lr_res and lr_res["Nhãn dự đoán"] != "⚠️ Lỗi load" else "T01. POLITICS"
                fallback_label_id = lr_res["label_id"] if lr_res and lr_res["label_id"] != "" else "T01"

                for mname, mtype, f1, notes in dl_models:
                    if use_dl:
                        current_step += 1
                        progress.progress(current_step / total_steps, text=f"Đang chạy {mname}...")
                        pred_label_name, conf_str, pred_label_id, _, err = predict_transformer(mname, predict_input, mapping_dict)
                    
                        if err:
                            results.append({
                                "Model": mname,
                                "Loại": mtype,
                                "Nhãn dự đoán": f"{fallback_label_name} *(Fallback)*",
                                "Confidence": "— *(Fallback)*",
                                "Test F1": f"{f1:.4f}",
                                "Ghi chú": f"Lỗi chạy: {err}. Dùng fallback.",
                                "label_id": fallback_label_id,
                                "F1_val": f1
                            })
                        else:
                            results.append({
                                "Model": mname,
                                "Loại": mtype,
                                "Nhãn dự đoán": pred_label_name,
                                "Confidence": conf_str,
                                "Test F1": f"{f1:.4f}",
                                "Ghi chú": notes,
                                "label_id": pred_label_id,
                                "F1_val": f1
                            })
                    else:
                        results.append({
                            "Model": mname,
                            "Loại": mtype,
                            "Nhãn dự đoán": f"{fallback_label_name} *(Fallback)*",
                            "Confidence": "— *(Không chạy)*",
                            "Test F1": f"{f1:.4f}",
                            "Ghi chú": notes + " (Chưa kích hoạt hoặc thiếu thư viện)",
                            "label_id": fallback_label_id,
                            "F1_val": f1
                        })

                progress.empty()

                # Spotlight Card for XLM-R (Best Model)
                xlmr_res = next((r for r in results if r["Model"] == "XLM-R"), None)
            
                st.markdown("### 🏆 Spotlight: Mô hình tốt nhất (Best Model)")
                if xlmr_res:
                    is_fallback = "Fallback" in xlmr_res["Nhãn dự đoán"] or "Không chạy" in xlmr_res["Confidence"]
                
                    # Calculate semantic confidence with colors
                    conf_str = xlmr_res['Confidence']
                    conf_val = None
                    if "%" in conf_str:
                        try:
                            conf_val = float(conf_str.replace("%", "").strip())
                        except ValueError:
                            pass
                
                    if conf_val is not None:
                        if conf_val >= 80.0:
                            semantic_conf = f"<span style='color: #1E8449; font-weight: bold;'>🟢 Tin cậy cao ({conf_str})</span>"
                        elif conf_val >= 50.0:
                            semantic_conf = f"<span style='color: #D4AF37; font-weight: bold;'>🟡 Tin cậy trung bình ({conf_str})</span>"
                        else:
                            semantic_conf = f"<span style='color: #D90429; font-weight: bold;'>🔴 Tin cậy thấp ({conf_str})</span>"
                    else:
                        semantic_conf = f"<span style='color: #555555; font-style: italic;'>{conf_str}</span>"
                
                    card_html = f"""
                    <div class="best-model-card">
                        <div class="best-model-badge">🏆 BEST MODEL (SOTA)</div>
                        <h4 style="margin: 0 0 5px 0; font-family: 'Playfair Display', serif; font-size: 22px;">XLM-RoBERTa (XLM-R)</h4>
                        <p style="margin: 0 0 15px 0; font-size: 13px; color: #555; font-style: italic;">
                             Mô hình ngôn ngữ học sâu đa ngôn ngữ đạt độ chính xác cao nhất (Test Macro-F1 = 82.45%) trên tập dữ liệu.
                        </p>
                        <div style="display: flex; flex-wrap: wrap; gap: 30px; align-items: center; margin-top: 10px;">
                            <div style="flex: 1; min-width: 150px;">
                                <div style="font-size: 11px; text-transform: uppercase; color: #666; letter-spacing: 0.5px; font-weight: 600;">Nhãn dự đoán</div>
                                <div style="font-family: 'Lora', serif; font-size: 20px; font-weight: 700; color: #1C1C1C; margin-top: 2px;">
                                    {xlmr_res['Nhãn dự đoán']}
                                </div>
                            </div>
                            <div style="flex: 1; min-width: 150px;">
                                <div style="font-size: 11px; text-transform: uppercase; color: #666; letter-spacing: 0.5px; font-weight: 600;">Độ tin cậy</div>
                                <div style="font-family: 'Lora', serif; font-size: 18px; font-weight: 700; margin-top: 2px;">
                                    {semantic_conf}
                                </div>
                            </div>
                            <div style="flex: 1; min-width: 150px;">
                                <div style="font-size: 11px; text-transform: uppercase; color: #666; letter-spacing: 0.5px; font-weight: 600;">Test Macro F1</div>
                                <div style="font-family: 'Lora', serif; font-size: 20px; font-weight: 700; color: #1C1C1C; margin-top: 2px;">
                                    82.45%
                                </div>
                            </div>
                        </div>
                    """
                    if is_fallback:
                        card_html += """
                        <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #E9E7E0; font-size: 12px; color: #D90429; font-weight: 500;">
                            ⚠️ Lưu ý: Kết quả trên đang sử dụng dự đoán tham chiếu từ mô hình truyền thống (Logistic Regression) do mô hình Deep Learning chưa được kích hoạt hoặc thiếu thư viện torch/transformers.
                        </div>
                        """
                    card_html += "</div>"
                    clean_card_html = "\n".join(line.strip() for line in card_html.split("\n"))
                    st.markdown(clean_card_html, unsafe_allow_html=True)

                # Sort and display comparison table of all 7 models
                results_sorted = sorted(results, key=lambda x: x["F1_val"], reverse=True)
                df_results = pd.DataFrame(results_sorted)
                df_display = df_results.rename(columns={
                    "Model": "Mô hình",
                    "Loại": "Phân loại",
                    "Nhãn dự đoán": "Chủ đề dự báo",
                    "Confidence": "Độ tin cậy",
                    "Ghi chú": "Mô tả chi tiết"
                })
                display_cols = ["Mô hình", "Phân loại", "Chủ đề dự báo", "Độ tin cậy", "Mô tả chi tiết"]
            
                st.markdown("#### 🎯 Kết quả Phân loại từ Model Zoo (7 Models)")
                st.dataframe(
                    df_display[display_cols],
                    use_container_width=True,
                    hide_index=True
                )

                # Find consensus majority (only over actual predictions, not fallbacks)
                actual_preds = [r for r in results if "Fallback" not in r["Nhãn dự đoán"] and "Lỗi" not in r["Nhãn dự đoán"]]
                if not actual_preds:
                    actual_preds = results # fallback to whatever we have
                
                pred_counts = pd.DataFrame(actual_preds)['Nhãn dự đoán'].value_counts()
                majority_label = pred_counts.index[0]
                
                maj_res = next((r for r in actual_preds if r["Nhãn dự đoán"] == majority_label), None)
                majority_id = maj_res["label_id"] if maj_res else "T01"

                # Disclaimer
                st.caption("⚠️ *Lưu ý về dự báo AI:* Thông tin trên hoàn toàn dựa trên dự đoán của các mô hình học máy và thống kê lịch sử từ tập dữ liệu. Vui lòng kết hợp với cảm quan biên tập thực tế trước khi xuất bản bài đăng.")

                # Determine primary label for historical lookup
                xlmr_valid = xlmr_res and "Fallback" not in xlmr_res["Nhãn dự đoán"] and "Lỗi" not in xlmr_res["Nhãn dự đoán"]
                if xlmr_valid:
                    primary_label = xlmr_res["Nhãn dự đoán"]
                    primary_id = xlmr_res["label_id"]
                    ref_text = "Dữ liệu lịch sử dưới đây đang được đối chiếu theo dự báo của mô hình tốt nhất (**XLM-R**)."
                else:
                    primary_label = majority_label
                    primary_id = majority_id
                    ref_text = f"Dữ liệu lịch sử dưới đây đang được đối chiếu theo nhãn phổ biến nhất (**{majority_label}**) từ consensus."

                # Pure data lookup
                topic_prefix = primary_label[:3] if len(primary_label) >= 3 else primary_id
                df_topic_stats = df_filtered[df_filtered['topic_label_final'].astype(str).str.startswith(topic_prefix)]
            
                if not df_topic_stats.empty:
                    avg_controversy = df_topic_stats['controversy_index'].mean()
                    avg_sarcasm = df_topic_stats['sarcasm_index'].mean()
                    controversy_pct = (df_reactions['controversy_index'].rank(pct=True) * 100).mean() if 'controversy_index' in df_reactions.columns else 50
                else:
                    avg_controversy = df_filtered['controversy_index'].mean()
                    avg_sarcasm = df_filtered['sarcasm_index'].mean()
                    controversy_pct = 50

                st.write("---")
                st.markdown("<h4 style='font-family: Lora, serif; font-size:18px;'>📊 Đối chiếu với Dữ liệu Lịch sử</h4>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-size:12px; font-style:italic; color:#555;'>{ref_text}</p>", unsafe_allow_html=True)
            
                audit_cols = st.columns(3)
            
                audit_cols[0].markdown(
                    f"<div class='kpi-card' style='border-top: 2.5px solid #1C1C1C; height: 160px;'>"
                    f"<div class='kpi-label'>🏷️ CHỦ ĐỀ DỰ ĐOÁN</div>"
                    f"<div class='kpi-val' style='font-size:20px; margin-top:10px; color:#1C1C1C;'>{shorten_topic_name(primary_label)}</div>"
                    f"<div style='font-size:12px; color:#555; margin-top:5px;'>Mã: <b>{topic_prefix}</b></div>"
                    f"</div>", unsafe_allow_html=True
                )
            
                audit_cols[1].markdown(
                    f"<div class='kpi-card' style='border-top: 2.5px solid #1C1C1C; height: 160px;'>"
                    f"<div class='kpi-label'>⚖️ MỨC ĐỘ TRANH CÃI LỊCH SỬ</div>"
                    f"<div class='kpi-val' style='font-size:18px; margin-top:10px; color:#D90429;'>{avg_controversy:.3f}</div>"
                    f"<div style='font-size:12px; color:#555; margin-top:5px;'>Thuộc top {100-int(controversy_pct)}% các chủ đề có tranh cãi cao nhất dataset.</div>"
                    f"</div>", unsafe_allow_html=True
                )
            
                audit_cols[2].markdown(
                    f"<div class='kpi-card' style='border-top: 2.5px solid #1C1C1C; height: 160px;'>"
                    f"<div class='kpi-label'>😆 TỶ LỆ PHẢN HỒI CHÂM BIẾM</div>"
                    f"<div class='kpi-val' style='font-size:18px; margin-top:10px; color:#F4A261;'>{avg_sarcasm*100:.1f}%</div>"
                    f"<div style='font-size:12px; color:#555; margin-top:5px;'>Trung bình của chủ đề này trong dataset.</div>"
                    f"</div>", unsafe_allow_html=True
                )

                # Preview card thuần data
                st.write("---")
                st.markdown("**📝 Preview Bài đăng**")
                if enable_visolex and nsw_found:
                    st.caption("Nội dung gốc:")
                    st.info(user_input_demo)
                    st.caption("Nội dung sau chuẩn hóa (ViSoLex):")
                    st.success(predict_input)
                else:
                    st.info(user_input_demo)

                # Build plain text report format
                nsw_details_str = ""
                if enable_visolex and nsw_found:
                    nsw_details_str = "\nCác từ đã chuẩn hóa (ViSoLex):\n" + "\n".join(f"- {item['original']} -> {', '.join(item['candidates'])}" for item in nsw_found)

                report_text = f"""# BÁO CÁO PHÂN TÍCH GIẢ LẬP NỘI DUNG (PREDICTIVE SIMULATION REPORT)
-------------------------------------------------------------
Nội dung bài viết gốc:
"{user_input_demo}"
"""
                if enable_visolex and nsw_found:
                    report_text += f"""
Nội dung sau chuẩn hóa (ViSoLex):
"{predict_input}"
{nsw_details_str}
"""
                report_text += f"""
 
KẾT QUẢ DỰ ĐOÁN PHÂN LOẠI MÔ HÌNH (ML PREDICTIONS):
- Mô hình tốt nhất (XLM-R): {xlmr_res['Nhãn dự đoán'] if xlmr_res else 'N/A'} (Confidence: {xlmr_res['Confidence'] if xlmr_res else 'N/A'})
- Chủ đề dự đoán (Đồng thuận đa số): {majority_label} (Mã: {topic_prefix})
 
ĐỐI CHIẾU THỐNG KÊ LỊCH SỬ CHỦ ĐỀ (HISTORICAL BENCHMARKS - dựa trên {primary_label}):
- Chỉ số tranh cãi (Controversy Index): {avg_controversy:.3f} (Top {100-int(controversy_pct)}% các chủ đề cao nhất)
- Tỷ lệ phản hồi châm biếm (Sarcasm Rate): {avg_sarcasm * 100:.1f}%
-------------------------------------------------------------
Báo cáo được tạo tự động bởi AI Content Simulator - Social Media Topic Insights.
"""
                st.write("---")
                st.download_button(
                    label="📥 Xuất Báo cáo Kết quả (TXT)",
                    data=report_text,
                    file_name="ai_content_simulation_results.txt",
                    mime="text/plain",
                    key="download_editorial_report_btn"
                )

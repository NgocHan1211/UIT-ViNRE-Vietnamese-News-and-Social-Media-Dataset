import pandas as pd
import streamlit as st
import plotly.express as px

def render_threat_radar(
    df_filtered, 
    df_reactions, 
    shorten_topic_name, 
    apply_editorial_theme, 
    extract_sarcasm_keywords, 
    analyze_topic_spam_bias
):
    st.markdown("<h3 class='section-header'>🚨 Threat Radar (Phân tích Rủi ro & Khủng hoảng)</h3>", unsafe_allow_html=True)
    st.write("Giám sát chỉ số tranh cãi, châm biếm, phân cực dư luận và dấu hiệu spam/seeding trên mạng xã hội.")
    
    if df_reactions.empty:
        st.warning("Không có dữ liệu thỏa mãn bộ lọc có ít nhất 10 reactions và cờ usable_for_reaction_analysis == 1.")
    else:
        sub_tab_sarcasm, sub_tab_controversy, sub_tab_bias = st.tabs([
            "🚨 Điểm nóng Châm biếm (Amusement Outliers)",
            "⚖️ Chỉ số Tranh cãi (Controversy Index)",
            "⚠️ Phân tích Bias & Spam (Bias & Spam Detection)"
        ])
        
        # ----------------------------------------------------
        # SUB-TAB 2A: SARCASM ALERT
        # ----------------------------------------------------
        with sub_tab_sarcasm:
            st.markdown("<h4 class='editorial-heading'>🚨 Phân tích nội dung giải trí / châm biếm & Xác định Điểm nóng Châm biếm (Amusement Outliers)</h4>", unsafe_allow_html=True)
            st.write("Trích xuất các cụm từ nổi bật từ nhóm bài viết có chỉ số Haha đột biến (top 10% Amusement_Index) để nhận diện các phản hồi phi nghiêm túc từ dư luận.")

            threshold = df_reactions['Amusement_Index'].quantile(0.9)
            df_sarcasm = df_reactions[df_reactions['Amusement_Index'] >= threshold]

            if not df_sarcasm.empty and 'caption' in df_sarcasm.columns:
                keywords = extract_sarcasm_keywords(df_sarcasm['caption'], top_n=6)

                col_alert1, col_alert2 = st.columns([2, 3])

                with col_alert1:
                    st.error(
                        f"**Có {len(df_sarcasm)} bài viết** ghi nhận dấu hiệu hoài nghi từ dư luận "
                        f"(Sarcasm/Amusement Index cao) với lượng Haha đột biến."
                    )

                with col_alert2:
                    if keywords:
                        st.markdown("**Từ khóa nổi bật (Key Phrases):**")
                        tags_html = " ".join([
                            f"<span style='background:#F7B125; color:#000; padding:4px 10px; "
                            f"border-radius:15px; font-size:13px; margin-right:5px; display:inline-block; margin-bottom:5px;'>"
                            f"{kw.title()}</span>"
                            for kw in keywords
                        ])
                        st.markdown(tags_html, unsafe_allow_html=True)
                    else:
                        non_empty = df_sarcasm['caption'].dropna().astype(str)
                        non_empty = non_empty[non_empty.str.len() > 3]
                        st.info(
                            f"Chưa trích xuất được từ khóa. "
                            f"({len(non_empty)}/{len(df_sarcasm)} bài có nội dung đủ dài để phân tích)"
                        )
                        
            st.write("---")
            st.markdown("<h5 class='editorial-heading'>🚨 Điểm nóng Châm biếm (Amusement Outliers) trên các Chủ đề Nghiêm túc</h5>", unsafe_allow_html=True)
            st.markdown("<p style='font-size:12px; font-style:italic; color:#555;'>Những bài đăng nghiêm túc (Pháp luật, Chính trị, Y tế, Thiên tai, Môi trường) nhận lượng thả Haha/Wow bất thường (>35%).</p>", unsafe_allow_html=True)
            
            serious_topics_prefixes = ['T01', 'T03', 'T07', 'T08', 'T09']
            df_serious = df_reactions[
                df_reactions['topic_label_final'].astype(str).str[:3].isin(serious_topics_prefixes)
            ].copy()
            
            sarc_alerts = df_serious[(df_serious['sarcasm_index'] > 0.35) & (df_serious['total_reactions'] >= 10)].nlargest(5, 'sarcasm_index')
            
            if sarc_alerts.empty:
                st.success("✅ Hiện tại không phát hiện điểm nóng châm biếm phi nghiêm túc nào trên các chủ đề nghiêm túc.")
            else:
                alerts_table = pd.DataFrame({
                    'Chủ đề': sarc_alerts['topic_label_final'].apply(shorten_topic_name),
                    'Nội dung': sarc_alerts['caption'].astype(str).str[:100] + '...',
                    'Chỉ số mỉa mai (SI)': (sarc_alerts['sarcasm_index'] * 100).round(1).astype(str) + '%',
                    'Haha': sarc_alerts['haha_count'],
                    'Wow': sarc_alerts['wow_count'],
                    'Reactions': sarc_alerts['total_reactions']
                }).reset_index(drop=True)
                alerts_table.index = alerts_table.index + 1
                st.dataframe(alerts_table, use_container_width=True, height=260)

        # ----------------------------------------------------
        # SUB-TAB 2B: CONTROVERSY INDEX
        # ----------------------------------------------------
        with sub_tab_controversy:
            st.markdown("<h4 class='editorial-heading'>⚖️ Phân tích độ phân cực & Chỉ số tranh cãi (Controversy Index)</h4>", unsafe_allow_html=True)
            
            # Leaderboard Section
            st.markdown("##### Bảng Xếp hạng (Leaderboard) Chỉ số Cảm xúc & Tranh cãi nổi bật")
            lead_cols = st.columns(4)
            
            topic_indices = df_reactions.groupby('topic_label_final').agg(
                avg_approval=('Approval_Index', 'mean'),
                avg_outrage=('Outrage_Index', 'mean'),
                avg_amusement=('Amusement_Index', 'mean'),
                avg_empathy=('Empathy_Index', 'mean'),
                avg_controversy=('controversy_index', 'mean'),
                avg_sarcasm=('sarcasm_index', 'mean')
            ).reset_index()
            
            for _col, _alias in [
                ('avg_outrage',     'outrage_pct'),
                ('avg_amusement',   'amusement_pct'),
                ('avg_approval',    'approval_pct'),
                ('avg_empathy',     'empathy_pct'),
            ]:
                topic_indices[_alias] = (topic_indices[_col].rank(pct=True) * 100).round(0).astype(int)

            # 1. Mức độ phẫn nộ cao nhất
            top_outrage = topic_indices.sort_values(by='avg_outrage', ascending=False).iloc[0]
            lead_cols[0].markdown(
                f"<div class='kpi-card' style='border-top: 2px solid #1C1C1C;'>"
                f"<div class='kpi-val'>{top_outrage['avg_outrage'] * 100:.1f}%</div>"
                f"<div class='kpi-label'>💥 Mức độ phẫn nộ cao nhất (Outrage Index)</div>"
                f"<div style='font-size:11px; color:#D90429; margin-top:3px;'>Top {100 - top_outrage['outrage_pct']}% so với các chủ đề khác</div>"
                f"<div style='font-size:12px; font-weight:bold; margin-top:3px; color:#555;'>{shorten_topic_name(top_outrage['topic_label_final'])}</div>"
                f"</div>", unsafe_allow_html=True
            )

            # 2. Mức độ giải trí / châm biếm cao nhất
            top_amusement = topic_indices.sort_values(by='avg_amusement', ascending=False).iloc[0]
            lead_cols[1].markdown(
                f"<div class='kpi-card' style='border-top: 2px solid #1C1C1C;'>"
                f"<div class='kpi-val'>{top_amusement['avg_amusement'] * 100:.1f}%</div>"
                f"<div class='kpi-label'>😆 Mức độ giải trí / châm biếm cao nhất (Amusement Index)</div>"
                f"<div style='font-size:11px; color:#D90429; margin-top:3px;'>Top {100 - top_amusement['amusement_pct']}% so với các chủ đề khác</div>"
                f"<div style='font-size:12px; font-weight:bold; margin-top:3px; color:#555;'>{shorten_topic_name(top_amusement['topic_label_final'])}</div>"
                f"</div>", unsafe_allow_html=True
            )

            # 3. Mức độ tán thành cao nhất
            top_app = topic_indices.sort_values(by='avg_approval', ascending=False).iloc[0]
            lead_cols[2].markdown(
                f"<div class='kpi-card' style='border-top: 2px solid #1C1C1C;'>"
                f"<div class='kpi-val'>{top_app['avg_approval'] * 100:.1f}%</div>"
                f"<div class='kpi-label'>👍 Mức độ tán thành cao nhất (Approval Index)</div>"
                f"<div style='font-size:11px; color:#1E8449; margin-top:3px;'>Top {100 - top_app['approval_pct']}% so với các chủ đề khác</div>"
                f"<div style='font-size:12px; font-weight:bold; margin-top:3px; color:#555;'>{shorten_topic_name(top_app['topic_label_final'])}</div>"
                f"</div>", unsafe_allow_html=True
            )

            # 4. Mức độ đồng cảm cao nhất
            top_emp = topic_indices.sort_values(by='avg_empathy', ascending=False).iloc[0]
            lead_cols[3].markdown(
                f"<div class='kpi-card' style='border-top: 2px solid #1C1C1C;'>"
                f"<div class='kpi-val'>{top_emp['avg_empathy'] * 100:.1f}%</div>"
                f"<div class='kpi-label'>🤗 Mức độ đồng cảm cao nhất (Empathy Index)</div>"
                f"<div style='font-size:11px; color:#1E8449; margin-top:3px;'>Top {100 - top_emp['empathy_pct']}% so với các chủ đề khác</div>"
                f"<div style='font-size:12px; font-weight:bold; margin-top:3px; color:#555;'>{shorten_topic_name(top_emp['topic_label_final'])}</div>"
                f"</div>", unsafe_allow_html=True
            )

            st.write("---")
            
            # Bubble Chart (Public Opinion Map)
            topic_bubble = df_reactions.groupby('topic_label_final').agg(
                avg_polarity=('polarity_score', 'mean'),
                avg_controversy=('controversy_index', 'mean'),
                avg_sarcasm=('sarcasm_index', 'mean'),
                total_engagement=('Total_Engagement', 'sum'),
                post_count=('record_id', 'count')
            ).reset_index()
            
            topic_bubble['Chủ đề'] = topic_bubble['topic_label_final'].apply(shorten_topic_name)
            
            if not topic_bubble.empty:
                max_cont_row = topic_bubble.sort_values(by='avg_controversy', ascending=False).iloc[0]
                max_cont_topic = shorten_topic_name(max_cont_row['topic_label_final'], include_code=False)
                pi_val = max_cont_row['avg_controversy']
                bubble_title = f"🗺️ {max_cont_topic} đang có rủi ro tranh cãi phân cực cao nhất (PI = {pi_val:.3f})"
            else:
                bubble_title = "Bản đồ Dư luận (Public Opinion Map): Tương quan Thái độ và Độ tranh cãi"
                
            st.markdown(f"<h5 class='editorial-heading' style='text-align:center; font-family: Lora, Georgia, serif;'>{bubble_title}</h5>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center; font-style:italic; font-size:13px; color:#555;'>Mỗi bong bóng đại diện cho một chủ đề. Trục hoành (X) biểu thị Thái độ Dư luận (từ cực kỳ tiêu cực đến tích cực). Trục tung (Y) biểu thị Mức độ Tranh cãi. Kích thước đại diện cho Tổng tương tác.</p>", unsafe_allow_html=True)
            
            col_anomaly1, col_anomaly2 = st.columns([2, 3])
            with col_anomaly1:
                highlight_anomalies = st.checkbox(
                    "🚨 Làm nổi bật điểm bất thường (Anomaly Highlight)", 
                    value=False,
                    help="Tô màu nổi bật cho các chủ đề có rủi ro tranh cãi hoặc tỷ lệ Haha/Wow cao (> 75th percentile). Các chủ đề khác có màu xám.",
                    key='bubble_highlight_anomalies_threat_tab'
                )
            with col_anomaly2:
                if highlight_anomalies:
                    st.info("💡 **Khuyến nghị Biên tập**: Các chủ đề cảnh báo đỏ đang bị phân cực ý kiến hoặc mỉa mai cao. Khuyên nghị **giãn tần suất xuất bản** và **cử nhân sự trực bình luận**.")
            
            if highlight_anomalies and len(topic_bubble) > 0:
                q75_cont = topic_bubble['avg_controversy'].quantile(0.75)
                q75_sarc = topic_bubble['avg_sarcasm'].quantile(0.75)
                threshold_cont = max(q75_cont, 0.4)
                threshold_sarc = max(q75_sarc, 0.20)
                
                def classify_bubble(row):
                    c_high = row['avg_controversy'] >= threshold_cont
                    s_high = row['avg_sarcasm'] >= threshold_sarc
                    if c_high and s_high:
                        return "🚨 Nguy cơ Kép (Tranh cãi & Haha/Wow Cao)"
                    elif c_high:
                        return "💥 Tranh cãi Cao (Controversy)"
                    elif s_high:
                        return "🎭 Haha/Wow Cao (High Ratio)"
                    else:
                        return "🟢 Bình thường (Normal)"
                        
                topic_bubble['Trạng thái'] = topic_bubble.apply(classify_bubble, axis=1)
                
                color_discrete_map = {
                    "🚨 Nguy cơ Kép (Tranh cãi & Haha/Wow Cao)": "#D90429",
                    "💥 Tranh cãi Cao (Controversy)": "#F4A261",
                    "🎭 Haha/Wow Cao (High Ratio)": "#E9C46A",
                    "🟢 Bình thường (Normal)": "#D3D7DB"
                }
                status_order = ["🟢 Bình thường (Normal)", "🎭 Haha/Wow Cao (High Ratio)", "💥 Tranh cãi Cao (Controversy)", "🚨 Nguy cơ Kép (Tranh cãi & Haha/Wow Cao)"]
                topic_bubble['Trạng thái'] = pd.Categorical(topic_bubble['Trạng thái'], categories=status_order, ordered=True)
                topic_bubble = topic_bubble.sort_values(by='Trạng thái')
                
                fig_bubble = px.scatter(
                    topic_bubble,
                    x='avg_polarity',
                    y='avg_controversy',
                    size='total_engagement',
                    color='Trạng thái',
                    text='Chủ đề',
                    labels={
                        'avg_polarity': 'Thái độ Dư luận (Valence)',
                        'avg_controversy': 'Mức độ Tranh cãi',
                        'total_engagement': 'Tổng tương tác',
                        'Trạng thái': 'Phân loại Dư luận'
                    },
                    color_discrete_map=color_discrete_map,
                    category_orders={"Trạng thái": status_order},
                    size_max=40,
                    height=550
                )
            else:
                fig_bubble = px.scatter(
                    topic_bubble,
                    x='avg_polarity',
                    y='avg_controversy',
                    size='total_engagement',
                    color='Chủ đề',
                    text='Chủ đề',
                    labels={
                        'avg_polarity': 'Thái độ Dư luận (Valence)',
                        'avg_controversy': 'Mức độ Tranh cãi',
                        'total_engagement': 'Tổng tương tác'
                    },
                    size_max=40,
                    height=550
                )
                
            fig_bubble.update_traces(textposition='top center')
            fig_bubble.add_vline(x=0.0, line_dash='dash', line_color='#1C1C1C', opacity=0.3)
            fig_bubble.add_hline(y=0.15, line_dash='dash', line_color='#1C1C1C', opacity=0.3)
            
            # Add corner annotations for actionable quadrants
            fig_bubble.add_annotation(
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                xanchor="left", yanchor="top",
                text="🚨 <b>Vùng Phẫn nộ / Khủng hoảng</b><br><span style='font-size:9px; font-weight:normal;'>Cảnh báo: Khu vực có sự lệch pha nghiêm trọng giữa nội dung truyền thông và phản ứng cộng đồng.<br>Đề xuất: Đi sâu phân tích đặc trưng ngôn ngữ của các bình luận liên quan.</span>",
                showarrow=False,
                font=dict(size=10, color="#D90429"),
                align="left",
                bgcolor="#FFF0F2",
                bordercolor="#D90429",
                borderwidth=1,
                borderpad=4
            )
            fig_bubble.add_annotation(
                xref="paper", yref="paper",
                x=0.98, y=0.98,
                xanchor="right", yanchor="top",
                text="⚖️ <b>Vùng Tranh biện / Đa chiều</b><br><span style='font-size:9px; font-weight:normal;'>Đặc trưng: Sự clash ý kiến diễn ra cân bằng giữa hai thái cực cảm xúc tích cực và tiêu cực.<br>Đề xuất: Điểm dữ liệu lý tưởng để huấn luyện các mô hình phân tích phân cực phức tạp.</span>",
                showarrow=False,
                font=dict(size=10, color="#D4AF37"),
                align="right",
                bgcolor="#FFFDF0",
                bordercolor="#D4AF37",
                borderwidth=1,
                borderpad=4
            )
            fig_bubble.add_annotation(
                xref="paper", yref="paper",
                x=0.98, y=0.02,
                xanchor="right", yanchor="bottom",
                text="✅ <b>Vùng An toàn / Tích cực</b><br><span style='font-size:9px; font-weight:normal;'>Đặc trưng: Sự đồng thuận cao từ độc giả.<br>Đề xuất: Phù hợp để làm chuẩn đối sánh (Baseline) cho các bài viết thông thường.</span>",
                showarrow=False,
                font=dict(size=10, color="#1E8449"),
                align="right",
                bgcolor="#F4FAF6",
                bordercolor="#1E8449",
                borderwidth=1,
                borderpad=4
            )
            fig_bubble.add_annotation(
                xref="paper", yref="paper",
                x=0.02, y=0.02,
                xanchor="left", yanchor="bottom",
                text="💬 <b>Vùng Ổn định / Ôn hòa</b><br><span style='font-size:9px; font-weight:normal;'>Đặc trưng: Tương tác thấp, ít biến động cảm xúc.<br>Đề xuất: Theo dõi định kỳ, phân tích ở cấp độ vĩ mô.</span>",
                showarrow=False,
                font=dict(size=10, color="#2A6F97"),
                align="left",
                bgcolor="#F4F8FA",
                bordercolor="#2A6F97",
                borderwidth=1,
                borderpad=4
            )
            
            apply_editorial_theme(fig_bubble)
            fig_bubble.update_traces(marker=dict(line=dict(width=1, color='#1C1C1C')))
            st.plotly_chart(fig_bubble, use_container_width=True)

            # --- Trend Line Chart: Controversy Spike Timeline ---
            st.write("---")
            st.markdown("<h5 class='editorial-heading'>📈 Biến động Chỉ số Tranh cãi theo Thời gian (Controversy Spike Timeline)</h5>", unsafe_allow_html=True)
            st.markdown("<p style='font-size:12px; font-style:italic; color:#555;'>Giám sát tốc độ lan truyền (Spike over time) để khoanh vùng các ngòi nổ khủng hoảng (Crisis) khi chỉ số tranh cãi tăng vọt dựng đứng chỉ trong 1-2 ngày.</p>", unsafe_allow_html=True)
            
            df_trend = df_reactions.dropna(subset=['parsed_date']).copy()
            if not df_trend.empty:
                df_trend['Ngày'] = df_trend['parsed_date'].dt.date
                df_trend_grouped = df_trend.groupby(['Ngày', 'topic_label_final'])['controversy_index'].mean().reset_index()
                df_trend_grouped['Chủ đề'] = df_trend_grouped['topic_label_final'].apply(shorten_topic_name)
                df_trend_grouped = df_trend_grouped.sort_values(by='Ngày')
                
                all_trend_topics = sorted(list(df_trend_grouped['Chủ đề'].unique()))
                top_topics_by_cont = (
                    df_trend_grouped.groupby('Chủ đề')['controversy_index']
                    .mean()
                    .nlargest(3)
                    .index.tolist()
                )
                
                selected_trend_topics = st.multiselect(
                    "🔍 Lọc các chủ đề theo dõi xu hướng (mặc định hiển thị Top 3 chủ đề tranh cãi nhất):",
                    options=all_trend_topics,
                    default=top_topics_by_cont if top_topics_by_cont else all_trend_topics,
                    key="threat_trend_topic_select"
                )
                
                df_trend_filtered = df_trend_grouped[df_trend_grouped['Chủ đề'].isin(selected_trend_topics)]
                
                if not df_trend_filtered.empty:
                    fig_line = px.line(
                        df_trend_filtered,
                        x='Ngày',
                        y='controversy_index',
                        color='Chủ đề',
                        markers=True,
                        labels={
                            'Ngày': 'Ngày đăng',
                            'controversy_index': 'Chỉ số Tranh cãi (Trung bình)',
                            'Chủ đề': 'Chủ đề'
                        },
                        height=420
                    )
                    apply_editorial_theme(fig_line)
                    fig_line.update_traces(line=dict(width=2.5), marker=dict(size=6, line=dict(width=1, color='#1C1C1C')))
                    st.plotly_chart(fig_line, use_container_width=True)
                else:
                    st.info("Vui lòng chọn ít nhất một chủ đề để hiển thị biểu đồ xu hướng.")
            else:
                st.info("Không có dữ liệu thời gian (parsed_date) hợp lệ để dựng biểu đồ xu hướng.")

            # Top 5 Controversy Posts
            st.write("---")
            st.markdown("<h5 class='editorial-heading'>💥 Top 5 Bài viết Gây tranh cãi Nhất</h5>", unsafe_allow_html=True)
            st.markdown("<p style='font-size:12px; font-style:italic; color:#555;'>Những bài đăng nhận ý kiến trái chiều sâu sắc (clash) cùng lượng tương tác/bình luận vượt trội.</p>", unsafe_allow_html=True)
            
            top5_cont = df_reactions.nlargest(5, 'controversy_index')
            if top5_cont.empty:
                st.info("Không tìm thấy bài viết gây tranh cãi nào.")
            else:
                top5_table = pd.DataFrame({
                    'Chủ đề': top5_cont['topic_label_final'].apply(shorten_topic_name),
                    'Nội dung': top5_cont['caption'].astype(str).str[:100] + '...',
                    'Tranh cãi (PI)': top5_cont['controversy_index'].round(3),
                    'Bình luận': top5_cont['comment_count'],
                    'Love': top5_cont['love_count'],
                    'Angry': top5_cont['angry_count']
                }).reset_index(drop=True)
                top5_table.index = top5_table.index + 1
                st.dataframe(top5_table, use_container_width=True, height=260)
                st.caption(
                    "🔬 *Chú thích chỉ số Controversy Index (PI):* PI = (Hòa hợp cảm xúc) * (Độ phân cực thảo luận) * (Khối lượng tương tác). "
                    "Chỉ số phản ánh mức độ bất đồng ý kiến sâu sắc (clash) kết hợp với mật độ bình luận vượt trội."
                )

        # ----------------------------------------------------
        # SUB-TAB 2C: BIAS & SPAM DETECTION
        # ----------------------------------------------------
        with sub_tab_bias:
            st.markdown("<h4 class='editorial-heading'>⚠️ Phân tích tỷ trọng tham gia & Bias của Chủ đề</h4>", unsafe_allow_html=True)
            st.markdown(
                "Phân tích xem các chủ đề nổi bật là do được lan truyền rộng rãi qua nhiều Page, "
                "hay chỉ do một vài Page đăng liên tục nhằm mục đích tăng lượng bài (spam/seeding)."
            )
            
            if (
                not df_filtered.empty
                and 'topic_label_final' in df_filtered.columns
                and 'page_name' in df_filtered.columns
            ):
                bias_df = analyze_topic_spam_bias(df_filtered)

                # Style bias data frame to highlight spam warnings
                st.dataframe(
                    bias_df.style.apply(
                        lambda x: [
                            'background-color: #ffcccc; color: black' if v else ''
                            for v in x
                        ],
                        subset=['is_spam_warning']
                    ),
                    use_container_width=True
                )

                # Scatter Plot: Total Posts vs. Unique Pages
                fig_bias = px.scatter(
                    bias_df,
                    x='unique_pages',
                    y='total_posts',
                    color='is_spam_warning',
                    color_discrete_map={True: '#D90429', False: '#2A6F97'},
                    hover_data=['topic_label_final', 'top_page_name', 'top_page_dominance_%'],
                    labels={
                        'unique_pages': 'Số lượng Page tham gia thảo luận',
                        'total_posts': 'Tổng số bài viết',
                        'is_spam_warning': 'Cảnh báo Spam'
                    },
                    title="Độ phủ Chủ đề: Total Posts vs. Unique Pages"
                )
                # Add median pages line
                if not bias_df['unique_pages'].empty:
                    fig_bias.add_vline(
                        x=bias_df['unique_pages'].median(),
                        line_dash="dash",
                        line_color="gray",
                        annotation_text="Median Pages"
                    )
                apply_editorial_theme(fig_bias)
                st.plotly_chart(fig_bias, use_container_width=True)

                st.caption(
                    "📌 Góc trên-trái (nhiều bài, ít page) = dấu hiệu Spam/Seeding. "
                    "Góc trên-phải (nhiều bài, nhiều page) = Viral thực sự."
                )

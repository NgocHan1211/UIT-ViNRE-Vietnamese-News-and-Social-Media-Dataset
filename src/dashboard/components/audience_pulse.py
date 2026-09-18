import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

def render_audience_pulse(
    df_filtered, 
    df_reactions, 
    shorten_topic_name, 
    apply_editorial_theme
):
    st.markdown("<h3 class='section-header'>📊 Audience Pulse (Hành vi & Tương tác)</h3>", unsafe_allow_html=True)
    st.write("Khảo sát hành vi độc giả, cơ cấu reaction chi tiết, mức độ lan truyền và phân tích thời gian đăng bài để theo dõi hiệu quả tương tác.")
    
    if df_reactions.empty:
        st.warning("Không có dữ liệu thỏa mãn bộ lọc có ít nhất 10 reactions và cờ usable_for_reaction_analysis == 1.")
    else:
        # Sub-tabs
        sub_tab_reaction, sub_tab_virality, sub_tab_golden = st.tabs([
            "🎭 Phân tích Phản ứng (Reaction Breakdown)",
            "📈 Hiệu suất Lan truyền (Virality & Top Posts)",
            "⏰ Phân tích Thời gian & Tra cứu (Temporal Trends & Archives)"
        ])
        
        # ----------------------------------------------------
        # SUB-TAB 3A: REACTION BREAKDOWN
        # ----------------------------------------------------
        with sub_tab_reaction:
            st.markdown("<h4 class='editorial-heading'>🎭 Cơ cấu Phản ứng & Dư luận xã hội</h4>", unsafe_allow_html=True)
            
            # Stacked bar chart for sentiment tones (Approval, Outrage, Amusement, Empathy)
            df_sentiment = df_reactions.groupby('topic_label_final').agg(
                Approval=('Approval_Index', 'mean'),
                Outrage=('Outrage_Index', 'mean'),
                Amusement=('Amusement_Index', 'mean'),
                Empathy=('Empathy_Index', 'mean')
            ).reset_index()
            
            if not df_sentiment.empty:
                df_sentiment['Sum'] = df_sentiment['Approval'] + df_sentiment['Outrage'] + df_sentiment['Amusement'] + df_sentiment['Empathy']
                df_sentiment['Sum'] = np.where(df_sentiment['Sum'] == 0, 1e-9, df_sentiment['Sum'])
                df_sentiment['Tích cực / Đồng thuận 👍❤️'] = df_sentiment['Approval'] / df_sentiment['Sum']
                df_sentiment['Phẫn nộ 😡'] = df_sentiment['Outrage'] / df_sentiment['Sum']
                df_sentiment['Châm biếm / Giải trí 😆'] = df_sentiment['Amusement'] / df_sentiment['Sum']
                df_sentiment['Đồng cảm 😢'] = df_sentiment['Empathy'] / df_sentiment['Sum']
                
                df_sentiment_melted = df_sentiment.melt(
                    id_vars='topic_label_final',
                    value_vars=['Tích cực / Đồng thuận 👍❤️', 'Phẫn nộ 😡', 'Châm biếm / Giải trí 😆', 'Đồng cảm 😢'],
                    var_name='Cảm xúc chính (Tone)',
                    value_name='Tỷ lệ'
                )
                df_sentiment_melted['Chủ đề'] = df_sentiment_melted['topic_label_final'].apply(shorten_topic_name)
                
                fig_sentiment = px.bar(
                    df_sentiment_melted,
                    y='Chủ đề',
                    x='Tỷ lệ',
                    color='Cảm xúc chính (Tone)',
                    orientation='h',
                    color_discrete_sequence=['#2A6F97', '#D90429', '#FFB703', '#457B9D'],
                    title='Tỷ lệ Phân bổ Cảm xúc (Sentiment Tone composition per Topic)'
                )
                fig_sentiment.update_layout(barmode='stack', height=450)
                fig_sentiment.update_xaxes(tickformat='.0%')
                apply_editorial_theme(fig_sentiment)
                st.plotly_chart(fig_sentiment, use_container_width=True)
            
            st.caption(
                "🔬 *Giải thích chỉ số cảm xúc:* Chỉ số được chuẩn hóa trên thang đo tỷ lệ phản ứng thực tế của người dùng. "
                "Cơ cấu Valence (Thái độ) sử dụng công thức Laplace Smoothing: `Valence = (Positive - Negative) / (Positive + Negative + α)` "
                "đại diện cho sự hài hòa thái độ trung vị của độc giả, giúp ổn định hóa các bài viết ít tương tác tránh nhiễu dữ liệu."
            )
            
            st.write("---")
            st.markdown("##### Cơ cấu Reaction chi tiết của Chủ đề")
            donut_col1, donut_col2 = st.columns([1, 2])
            with donut_col1:
                donut_topic_pulse = st.selectbox(
                    "🔍 Chọn chủ đề để xem Donut chart:",
                    options=sorted(df_reactions['topic_label_final'].unique()),
                    key='donut_select_pulse_audience_tab',
                    format_func=lambda x: shorten_topic_name(x, include_code=True)
                )
            df_donut = df_reactions[df_reactions['topic_label_final'] == donut_topic_pulse]
            donut_sums = {
                'Like 👍':  df_donut['like_count'].sum(),
                'Love ❤️':  df_donut['love_count'].sum(),
                'Haha 😆':  df_donut['haha_count'].sum(),
                'Wow 😮':   df_donut['wow_count'].sum(),
                'Sad 😢':   df_donut['sad_count'].sum(),
                'Angry 😡': df_donut['angry_count'].sum(),
                'Care 🤗':  df_donut['care_count'].sum(),
            }
            donut_df = pd.DataFrame({'Reaction': list(donut_sums.keys()), 'Count': list(donut_sums.values())})
            donut_df = donut_df[donut_df['Count'] > 0]
            donut_colors = ['#2A6F97','#C9184A','#FFB703','#2A9D8F','#457B9D','#D90429','#FFB703']
            with donut_col2:
                fig_donut = px.pie(
                    donut_df, values='Count', names='Reaction',
                    hole=0.5, color_discrete_sequence=donut_colors,
                    title=f"Thành phần Reaction: {shorten_topic_name(donut_topic_pulse)}"
                )
                fig_donut.update_layout(height=350, legend=dict(orientation='h', y=-0.15))
                apply_editorial_theme(fig_donut)
                st.plotly_chart(fig_donut, use_container_width=True)

        # ----------------------------------------------------
        # SUB-TAB 3B: VIRALITY & TOP POSTS
        # ----------------------------------------------------
        with sub_tab_virality:
            st.markdown("<h4 class='editorial-heading'>📊 Phân tích Biến động & Hiệu suất Lan truyền</h4>", unsafe_allow_html=True)
            
            # Log-scale box plots of virality/engagement by topic
            st.markdown("##### 📈 Phân phối Tương tác theo Chủ đề (Log-scale Box Plot)")
            df_reactions_copy = df_reactions.copy()
            df_reactions_copy['Chủ đề'] = df_reactions_copy['topic_label_final'].apply(shorten_topic_name)
            fig_box = px.box(
                df_reactions_copy,
                y='Chủ đề',
                x='Total_Engagement',
                color='Chủ đề',
                log_x=True,
                labels={'Total_Engagement': 'Tổng tương tác (Log-scale)', 'Chủ đề': 'Chủ đề'},
                title='Phân bố Khối lượng Tương tác (Hộp & Râu - log scale)'
            )
            fig_box.update_layout(showlegend=False, height=450)
            apply_editorial_theme(fig_box)
            st.plotly_chart(fig_box, use_container_width=True)
            st.caption("📌 Trục hoành sử dụng Log-scale để thu gọn phạm vi hiển thị từ các bài viết có tương tác đột biến lớn.")
            
            st.write("---")
            st.markdown("##### 🚀 Bảng xếp hạng Hiệu suất Lan truyền (Virality Ledger) & Bậc Phân vị")
            st.markdown("<p style='font-size:12px; font-style:italic; color:#555;'>Danh sách 10 bài viết có hiệu suất tương tác/lan truyền cao nhất, hiển thị kèm bậc phân vị tương đối và tương tác chuẩn hóa.</p>", unsafe_allow_html=True)
            
            sort_metric = st.radio(
                "Sắp xếp danh sách theo:",
                options=["Tổng Tương tác", "Lượt Chia sẻ", "Lượt Bình luận"],
                horizontal=True, key='virality_sort_metric_pulse_audience'
            )
            
            sort_col = 'Total_Engagement'
            if sort_metric == "Lượt Chia sẻ":
                sort_col = 'share_count'
            elif sort_metric == "Lượt Bình luận":
                sort_col = 'comment_count'
                
            top10 = df_reactions.nlargest(10, sort_col)
            if top10.empty:
                st.info("Không có dữ liệu bài viết.")
            else:
                top10_display = pd.DataFrame({
                    'Chủ đề': top10['topic_label_final'].apply(shorten_topic_name),
                    'Fanpage': top10['page_name'],
                    'Tổng tương tác': top10['Total_Engagement'],
                    'Phân vị Tương tác (%)': top10['Total_Engagement_percentile'].astype(str) + '%',
                    'Tương tác / 100k Followers': top10.apply(
                        lambda r: f"{r['engagement_per_100k']:,}" if r['has_page_followers'] == 1 and r['page_followers'] > 0 else "N/A", axis=1
                    ),
                    'Chỉ số Outrage / Amusement (Phân vị)': top10.apply(
                        lambda r: f"Phẫn nộ: {r.get('Outrage_Index_percentile', 0.0)}% | Haha: {r.get('Amusement_Index_percentile', 0.0)}%", axis=1
                    ),
                    'Bình luận': top10['comment_count'],
                    'Chia sẻ': top10['share_count'],
                    'Nội dung tóm tắt': top10['caption'].astype(str).str[:120] + '...'
                }).reset_index(drop=True)
                top10_display.index = top10_display.index + 1
                st.dataframe(top10_display, use_container_width=True, height=380)

            # Detail charts
            st.write("---")
            with st.expander("📊 Xem thêm biểu đồ so sánh khối lượng và hiệu suất tương tác trung bình"):
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    topic_engagement = df_filtered.groupby('topic_label_final').agg(
                        avg_comments=('comment_count', 'mean'),
                        avg_shares=('share_count', 'mean'),
                        avg_reactions=('total_reactions', 'mean')
                    ).reset_index()
                    
                    if not topic_engagement.empty:
                        topic_engagement['total_avg_eng'] = topic_engagement['avg_comments'] + topic_engagement['avg_shares']
                        max_eng_row = topic_engagement.sort_values(by='total_avg_eng', ascending=False).iloc[0]
                        max_eng_topic = shorten_topic_name(max_eng_row['topic_label_final'], include_code=False)
                        val = max_eng_row['total_avg_eng']
                        engagement_title = f"💬 {max_eng_topic} dẫn đầu hiệu suất tương tác với trung bình {val:.1f} bình luận/chia sẻ mỗi bài"
                    else:
                        engagement_title = "Tổng quan Khối lượng Tương tác (Comments & Shares)"
                        
                    st.markdown(f"<h4 style='text-align:center; font-family: Lora, Georgia, serif; font-size:14px;'>{engagement_title}</h4>", unsafe_allow_html=True)
                    
                    topic_engagement['topic_label_final'] = topic_engagement['topic_label_final'].apply(lambda x: shorten_topic_name(x, include_code=True))
                    topic_engagement = topic_engagement.sort_values(by='total_avg_eng', ascending=True)
                    
                    fig_engagement = px.bar(
                        topic_engagement,
                        x='total_avg_eng',
                        y='topic_label_final',
                        orientation='h',
                        text='total_avg_eng',
                        labels={'total_avg_eng': 'Tương tác trung bình (Bình luận + Chia sẻ) / bài', 'topic_label_final': 'Chủ đề'},
                        color='total_avg_eng',
                        color_continuous_scale='Purples'
                    )
                    fig_engagement.update_traces(texttemplate='%{text:.1f}', textposition='outside')
                    fig_engagement.update_layout(height=450, margin=dict(l=10, r=10, t=10, b=10))
                    apply_editorial_theme(fig_engagement)
                    st.plotly_chart(fig_engagement, use_container_width=True)
                    
                with col_m2:
                    st.markdown("<h4 style='text-align:center; font-family: Lora, Georgia, serif; font-size:14px;'>Hiệu suất Tương tác trung bình theo Chủ đề</h4>", unsafe_allow_html=True)
                    
                    topic_eng = df_filtered.copy()
                    topic_eng['total_eng'] = topic_eng['total_reactions'] + topic_eng['comment_count'] + topic_eng['share_count']
                    topic_rel = topic_eng.groupby('topic_label_final').agg(
                        avg_like=('like_count', 'mean'),
                        avg_share=('share_count', 'mean'),
                        avg_comment=('comment_count', 'mean'),
                        total_rate=('total_eng', 'mean')
                    ).reset_index()
                    topic_rel['Topic_Short'] = topic_rel['topic_label_final'].apply(lambda x: shorten_topic_name(x, include_code=True))
                    topic_rel = topic_rel.sort_values(by='total_rate', ascending=True)
                    
                    fig_rel = px.bar(
                        topic_rel,
                        x='total_rate',
                        y='Topic_Short',
                        orientation='h',
                        text='total_rate',
                        labels={'total_rate': 'Tương tác trung bình / bài', 'Topic_Short': 'Chủ đề'},
                        color='total_rate',
                        color_continuous_scale='Greens'
                    )
                    fig_rel.update_traces(texttemplate='%{text:,.1f}', textposition='outside')
                    fig_rel.update_layout(height=450, margin=dict(l=10, r=10, t=10, b=10))
                    apply_editorial_theme(fig_rel)
                    st.plotly_chart(fig_rel, use_container_width=True)
                    
                st.write("---")
                table_data = topic_rel[['topic_label_final', 'total_rate']].copy()
                table_data.columns = ['Chủ đề', 'Tương tác trung bình / bài']
                table_data['Tương tác trung bình / bài'] = table_data['Tương tác trung bình / bài'].round(1)
                table_data['Chủ đề'] = table_data['Chủ đề'].apply(shorten_topic_name)
                table_data = table_data.sort_values(by='Tương tác trung bình / bài', ascending=False).reset_index(drop=True)
                table_data.index = table_data.index + 1
                
                st.dataframe(table_data, use_container_width=True, height=380)

        # ----------------------------------------------------
        # SUB-TAB 3C: TIMELINE TRENDS & ARCHIVES (MERGED)
        # ----------------------------------------------------
        with sub_tab_golden:
            st.markdown("<h4 class='editorial-heading'>⏰ Phân tích Thời gian đăng & Tra cứu Dữ liệu</h4>", unsafe_allow_html=True)
            
            st.warning(
                "**⚠️ Cảnh báo chất lượng dữ liệu thời gian:**\n\n"
                "Tập dữ liệu crawl có **27.37%** số dòng bị thiếu thông tin mốc thời gian đăng bài (timestamp_missing_rows = 3,226). "
                "Do đó, các biểu đồ phân tích thời gian đăng bài dưới đây **chỉ dựa trên 72.63% dữ liệu có sẵn mốc thời gian (8,560 dòng)**, "
                "chứ không đại diện hoàn toàn cho toàn bộ bài đăng trong dataset."
            )
            
            # Filter for valid post times
            df_time = df_filtered[df_filtered['has_post_created_time'] == 1].copy()
            
            if df_time.empty:
                st.warning("Không có dữ liệu thỏa mãn bộ lọc có chứa trường mốc thời gian đăng bài.")
            else:
                # Parse hour column
                df_time['post_created_hour'] = pd.to_numeric(df_time['post_created_hour'], errors='coerce').fillna(0).astype(int)
                
                # Ensure correct order of weekdays
                weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                weekday_vi = {'Monday':'Thứ 2','Tuesday':'Thứ 3','Wednesday':'Thứ 4',
                              'Thursday':'Thứ 5','Friday':'Thứ 6','Saturday':'Thứ 7','Sunday':'Chủ Nhật'}
                df_time['weekday_vi'] = df_time['post_created_weekday'].map(weekday_vi)
                weekday_vi_order = ['Thứ 2','Thứ 3','Thứ 4','Thứ 5','Thứ 6','Thứ 7','Chủ Nhật']
                df_time['weekday_vi'] = pd.Categorical(df_time['weekday_vi'], categories=weekday_vi_order, ordered=True)
                
                t_col1, t_col2 = st.columns([1, 2])
                
                # Minimum sample size threshold
                MIN_SAMPLE_CELL = 15
                
                # Trends Hour calculations
                hour_trends = df_time.groupby('post_created_hour').agg(
                    posts_count  =('record_id', 'count'),
                    median_reactions=('total_reactions', 'median'),
                    median_comments =('comment_count', 'median'),
                    median_shares   =('share_count', 'median')
                ).reset_index()
                
                with t_col1:
                    pivot_raw = df_time.groupby(['weekday_vi', 'post_created_hour'], observed=False).agg(
                        median_reactions=('total_reactions', 'median'),
                        n_posts      =('total_reactions', 'count')
                    ).reset_index()
                    
                    pivot_raw.loc[pivot_raw['n_posts'] < MIN_SAMPLE_CELL, 'median_reactions'] = float('nan')
                    
                    overall_median_reactions = df_time['total_reactions'].median()
                    reliable_cells = pivot_raw[pivot_raw['n_posts'] >= MIN_SAMPLE_CELL]
                    
                    if not reliable_cells.empty and overall_median_reactions > 0:
                        max_cell = reliable_cells.sort_values(by='median_reactions', ascending=False).iloc[0]
                        best_day = max_cell['weekday_vi']
                        best_hour = int(max_cell['post_created_hour'])
                        best_median = max_cell['median_reactions']
                        ratio = best_median / overall_median_reactions
                        heatmap_title = f"⏰ {best_day} lúc {best_hour}h ghi nhận tương tác cao gấp {ratio:.1f} lần trung vị"
                    else:
                        heatmap_title = "Thời điểm có tương tác trung vị cao nhất trong tuần"
                        
                    st.markdown(f"<h5 style='text-align:center; font-family: Lora, Georgia, serif; font-size: 14px; margin-bottom: 2px;'>{heatmap_title}</h5>", unsafe_allow_html=True)
                    st.markdown("<p style='text-align:center; font-style:italic; font-size:12px; color:#777; margin-top:0px; margin-bottom:10px;'>Lưu ý: Biểu đồ được xây dựng dựa trên 72.6% bài viết có ghi nhận thời gian thực tế. Đã lọc bỏ các khung giờ có dưới 15 bài để tránh nhiễu.</p>", unsafe_allow_html=True)
                    
                    pivot_matrix = pivot_raw.pivot(index='weekday_vi', columns='post_created_hour', values='median_reactions')
                    pivot_matrix = pivot_matrix.reindex(columns=list(range(24)))
                    existing_days = [d for d in weekday_vi_order if d in pivot_matrix.index]
                    pivot_matrix = pivot_matrix.reindex(existing_days)
                    
                    fig_heatmap = px.imshow(
                        pivot_matrix,
                        labels=dict(x="Khung giờ (0–23h)", y="Thứ trong tuần", color="Reactions Trung vị"),
                        x=pivot_matrix.columns,
                        y=pivot_matrix.index,
                        color_continuous_scale='YlOrRd'
                    )
                    fig_heatmap.update_layout(height=450, margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(tickmode='linear', tick0=0, dtick=2))
                    apply_editorial_theme(fig_heatmap)
                    st.plotly_chart(fig_heatmap, use_container_width=True)
                    
                with t_col2:
                    st.markdown("<h5 style='text-align:center; font-size:14px;'>Xu hướng Tương tác theo Khung giờ đăng</h5>", unsafe_allow_html=True)
                    zoom_topic = st.selectbox(
                        "🔍 Lọc theo chủ đề bài đăng:",
                        options=["Tất cả chủ đề"] + list(sorted(df_time['topic_label_final'].unique())),
                        key='zoom_topic_select_temporal_tab_audience_tab',
                        format_func=lambda x: x if x == "Tất cả chủ đề" else shorten_topic_name(x, include_code=True)
                    )
                    
                    if zoom_topic == "Tất cả chủ đề":
                        df_time_zoom = df_time
                    else:
                        df_time_zoom = df_time[df_time['topic_label_final'] == zoom_topic]
                        
                    hour_trends = df_time_zoom.groupby('post_created_hour').agg(
                        posts_count  =('record_id', 'count'),
                        median_reactions=('total_reactions', 'median'),
                        median_comments =('comment_count', 'median'),
                        median_shares   =('share_count', 'median')
                    ).reset_index()
                    
                    hour_reliable = hour_trends[hour_trends['posts_count'] >= MIN_SAMPLE_CELL].copy()
                    hour_sparse   = hour_trends[hour_trends['posts_count'] <  MIN_SAMPLE_CELL].copy()
                    
                    fig_line = go.Figure()
                    fig_line.add_trace(go.Bar(
                        x=hour_trends['post_created_hour'],
                        y=hour_trends['posts_count'],
                        name='Số bài đăng',
                        marker_color='rgba(200,200,200,0.35)',
                        yaxis='y2',
                        hovertemplate='Giờ %{x}h: %{y} bài<extra></extra>'
                    ))
                    
                    for col, color, name in [
                        ('median_reactions', '#2A6F97', 'Reactions Trung vị'),
                        ('median_comments',  '#FFB703', 'Bình luận Trung vị'),
                        ('median_shares',    '#2A9D8F', 'Chia sẻ Trung vị'),
                    ]:
                        fig_line.add_trace(go.Scatter(
                            x=hour_reliable['post_created_hour'],
                            y=hour_reliable[col],
                            mode='lines+markers',
                            name=name,
                            line=dict(color=color, width=2.5)
                        ))
                    
                    if not hour_sparse.empty:
                        fig_line.add_trace(go.Scatter(
                            x=hour_sparse['post_created_hour'],
                            y=hour_sparse['median_reactions'],
                            mode='markers',
                            name=f'Ít dữ liệu (< {MIN_SAMPLE_CELL} bài)',
                            marker=dict(color='lightgray', size=8, symbol='x'),
                            hovertemplate='Giờ %{x}h: chỉ có ' + hour_sparse['posts_count'].astype(str) + ' bài<extra></extra>'
                        ))
                    
                    fig_line.update_layout(
                        xaxis=dict(title='Khung giờ (0–23h)', tickmode='linear', tick0=0, dtick=2),
                        yaxis=dict(title='Tương tác trung vị'),
                        yaxis2=dict(title='Số bài đăng', overlaying='y', side='right', showgrid=False, rangemode='tozero'),
                        height=320,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    apply_editorial_theme(fig_line)
                    st.plotly_chart(fig_line, use_container_width=True)
                    
                # Weekday vs Weekend Comparison
                st.write("---")
                st.markdown("#### So sánh: Ngày Thường (T2–T6) vs Cuối tuần (T7, CN)")
                WEEKEND_DAYS = ['Saturday', 'Sunday']
                df_time_wday = df_time.copy()
                df_time_wday['period'] = df_time_wday['post_created_weekday'].apply(
                    lambda x: 'Cuối tuần (T7/CN)' if x in WEEKEND_DAYS else 'Ngày thường (T2–T6)'
                )
                wday_agg = df_time_wday.groupby('period').agg(
                    median_reactions=('total_reactions', 'median'),
                    median_comments =('comment_count',   'median'),
                    median_shares   =('share_count',      'median'),
                    n_posts      =('total_reactions',  'count')
                ).reset_index()
                
                wday_melted = wday_agg.melt(
                    id_vars='period',
                    value_vars=['median_reactions', 'median_comments', 'median_shares'],
                    var_name='Chỉ số', value_name='Giá trị trung vị'
                )
                wday_melted['Chỉ số'] = wday_melted['Chỉ số'].replace({
                    'median_reactions': 'Reactions Trung vị',
                    'median_comments':  'Bình luận Trung vị',
                    'median_shares':    'Chia sẻ Trung vị'
                })
                
                wday_col1, wday_col2 = st.columns([2, 1])
                with wday_col1:
                    fig_wday = px.bar(
                        wday_melted, x='Chỉ số', y='Giá trị trung vị',
                        color='period', barmode='group',
                        color_discrete_sequence=['#2A6F97', '#FFB703'],
                        text='Giá trị trung vị',
                        labels={'Giá trị trung vị': 'Tương tác Trung vị', 'Chỉ số': ''},
                        title='Hiệu suất tương tác: Ngày thường vs Cuối tuần (Trung vị)'
                    )
                    fig_wday.update_traces(texttemplate='%{text:.0f}', textposition='outside')
                    fig_wday.update_layout(height=350, legend=dict(orientation='h', y=1.05))
                    apply_editorial_theme(fig_wday)
                    st.plotly_chart(fig_wday, use_container_width=True)
                    
                with wday_col2:
                    st.markdown("**🏆 Top 3 Khung giờ có tương tác trung vị cao nhất** (đủ mẫu)")
                    reliable_hours = hour_trends[hour_trends['posts_count'] >= MIN_SAMPLE_CELL].copy()
                    if not reliable_hours.empty:
                        top3 = reliable_hours.nlargest(3, 'median_reactions')[['post_created_hour','median_reactions','posts_count']]
                        for rank, (_, row) in enumerate(top3.iterrows(), 1):
                            medal = ['🥇','🥈','🥉'][rank - 1]
                            st.markdown(f"{medal} **Giờ {int(row['post_created_hour'])}h** — `{row['median_reactions']:.0f}` reactions Trung vị ({int(row['posts_count'])} bài)")
                    else:
                        st.info("Không đủ dữ liệu tin cậy.")

            # ARCHIVES EMBEDDED
            st.write("---")
            st.markdown("##### 📚 Tra cứu Tư liệu Bài viết")
            
            col_arch1, col_arch2 = st.columns([2, 1])
            with col_arch1:
                search_query = st.text_input("🔍 Tìm kiếm từ khóa trong bài viết:", value="", placeholder="Nhập từ khóa cần tìm...", key='archives_search_input_audience_tab')
            with col_arch2:
                max_rows = min(1000, len(df_filtered))
                num_rows = st.slider("Số lượng bài đăng hiển thị:", min_value=10, max_value=max_rows if max_rows > 10 else 50, value=100, step=10, key='archives_num_rows_audience_tab')
                
            df_explorer = df_filtered.copy()
            if search_query.strip():
                df_explorer = df_explorer[df_explorer['caption'].astype(str).str.contains(search_query, case=False, na=False)]
                
            all_cols = df_explorer.columns.tolist()
            preferred_cols = ['topic_label_final', 'page_name', 'caption', 'total_reactions', 'share_count', 'comment_count', 'polarity_score']
            preferred_cols = [c for c in preferred_cols if c in all_cols]
            
            selected_cols = st.multiselect("Lựa chọn các cột thông tin cần hiển thị:", options=all_cols, default=preferred_cols, key='archives_selected_cols_audience_tab')
            
            if not selected_cols:
                st.warning("Vui lòng chọn ít nhất một trường thông tin để hiển thị!")
            else:
                st.write(f"Đang hiển thị `{min(num_rows, len(df_explorer))}` trên tổng số `{len(df_explorer):,}` bài đăng.")
                st.dataframe(df_explorer[selected_cols].head(num_rows), use_container_width=True, height=400)
                
                st.write("---")
                @st.cache_data(show_spinner=False)
                def convert_df(df_to_export):
                    return df_to_export.to_csv(index=False).encode('utf-8')
                    
                csv_data = convert_df(df_explorer[selected_cols])
                
                st.download_button(
                    label="📥 Tải xuống Dữ liệu Đã chọn cột (CSV)",
                    data=csv_data,
                    file_name="social_media_archives_filtered.csv",
                    mime="text/csv",
                    key="download_csv_archives_audience_tab"
                )

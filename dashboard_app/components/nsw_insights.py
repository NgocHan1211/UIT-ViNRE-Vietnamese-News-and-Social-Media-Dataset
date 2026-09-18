from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st


def render_nsw_insights(df_filtered: pd.DataFrame, shorten_topic_name, apply_editorial_theme) -> None:
    st.markdown(
        "<h3 class='section-header'>🔤 NSW Insights (Teencode & Từ viết tắt)</h3>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Mức độ sử dụng teencode / từ viết tắt mạng xã hội (Non-Standard Words) trên dữ liệu "
        "đã lọc — nguồn từ điển: [ViSoLex](https://github.com/HaDung2002/visolex) (UIT-NLP, MIT License). "
        "Chuẩn hoá dựa trên tra từ điển, không xét ngữ cảnh câu, nên dùng cho mục đích thống khen tổng quan."
    )

    if 'nsw_count' not in df_filtered.columns or 'nsw_words' not in df_filtered.columns:
        st.warning(
            "Dataset chưa có cột `nsw_count` / `nsw_words`. "
            "Hãy đảm bảo bước chuẩn hoá ViSoLex đã chạy trong `load_data()` trước khi vào tab này."
        )
        return

    total_posts = len(df_filtered)
    if total_posts == 0:
        st.info("Không có bài viết nào trong dữ liệu đã lọc.")
        return

    posts_with_nsw = int((df_filtered['nsw_count'] > 0).sum())
    pct_with_nsw = posts_with_nsw / total_posts * 100
    avg_nsw_per_post = df_filtered['nsw_count'].mean()

    # ---- KPI row ----
    col1, col2, col3 = st.columns(3)
    col1.markdown(
        f"<div class='kpi-card'><div class='kpi-val'>{pct_with_nsw:.1f}%</div>"
        f"<div class='kpi-label'>Bài đăng chứa Teencode/NSW</div></div>",
        unsafe_allow_html=True,
    )
    col2.markdown(
        f"<div class='kpi-card'><div class='kpi-val'>{avg_nsw_per_post:.2f}</div>"
        f"<div class='kpi-label'>Trung bình NSW / bài</div></div>",
        unsafe_allow_html=True,
    )
    col3.markdown(
        f"<div class='kpi-card'><div class='kpi-val'>{posts_with_nsw:,}</div>"
        f"<div class='kpi-label'>Số bài có chứa NSW</div></div>",
        unsafe_allow_html=True,
    )

    st.write("---")
    col_left, col_right = st.columns(2)

    # ---- Top NSW words toàn dataset ----
    with col_left:
        st.markdown("**Top từ NSW phổ biến nhất**")
        all_nsw = [w for words in df_filtered['nsw_words'] if isinstance(words, list) for w in words]
        if all_nsw:
            counter = Counter(all_nsw)
            top_df = pd.DataFrame(counter.most_common(15), columns=['Từ NSW', 'Số lần xuất hiện'])
            fig = px.bar(top_df, x='Số lần xuất hiện', y='Từ NSW', orientation='h')
            fig = apply_editorial_theme(fig)
            fig.update_layout(yaxis=dict(autorange="reversed"), height=420, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Không phát hiện từ NSW nào trong dữ liệu đã lọc.")

    # ---- % NSW theo chủ đề ----
    with col_right:
        st.markdown("**Tỷ lệ bài đăng chứa NSW theo Chủ đề (Top 10)**")
        if 'topic_label_final' in df_filtered.columns:
            topic_stats = df_filtered.groupby('topic_label_final').agg(
                total=('nsw_count', 'size'),
                with_nsw=('nsw_count', lambda s: int((s > 0).sum())),
            ).reset_index()
            topic_stats['pct_nsw'] = (topic_stats['with_nsw'] / topic_stats['total'] * 100).round(1)
            topic_stats['topic_name'] = topic_stats['topic_label_final'].apply(
                lambda x: shorten_topic_name(x, include_code=False)
            )
            topic_stats = topic_stats[topic_stats['total'] >= 5].sort_values('pct_nsw', ascending=False).head(10)

            if not topic_stats.empty:
                fig2 = px.bar(topic_stats, x='pct_nsw', y='topic_name', orientation='h')
                fig2 = apply_editorial_theme(fig2)
                fig2.update_layout(
                    yaxis=dict(autorange="reversed"), height=420,
                    xaxis_title="% bài có NSW", margin=dict(l=10, r=10, t=30, b=10),
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Không đủ dữ liệu (mỗi chủ đề cần ≥5 bài) để so sánh theo chủ đề.")
        else:
            st.info("Dataset không có cột `topic_label_final`.")

    # ---- Top Fanpage dùng nhiều NSW nhất ----
    st.write("---")
    st.markdown("**Top Fanpage dùng nhiều Teencode/NSW nhất** (chỉ tính Page có ≥5 bài trong dữ liệu đã lọc)")
    if 'page_name' in df_filtered.columns:
        page_stats = df_filtered.groupby('page_name').agg(
            total_posts=('nsw_count', 'size'),
            avg_nsw_per_post=('nsw_count', 'mean'),
            pct_posts_with_nsw=('nsw_count', lambda s: round((s > 0).mean() * 100, 1)),
        ).reset_index()
        page_stats = page_stats[page_stats['total_posts'] >= 5].sort_values(
            'avg_nsw_per_post', ascending=False
        ).head(10)
        page_stats['avg_nsw_per_post'] = page_stats['avg_nsw_per_post'].round(2)

        if not page_stats.empty:
            st.dataframe(
                page_stats.rename(columns={
                    'page_name': 'Fanpage',
                    'total_posts': 'Số bài',
                    'avg_nsw_per_post': 'TB NSW / bài',
                    'pct_posts_with_nsw': '% bài có NSW',
                }),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("Không có Fanpage nào đủ ≥5 bài trong dữ liệu đã lọc hiện tại.")
    else:
        st.info("Dataset không có cột `page_name`.")

    # ---- Ví dụ minh hoạ ----
    st.write("---")
    st.markdown("**Ví dụ minh hoạ chuẩn hoá** (5 bài có nhiều NSW nhất trong dữ liệu đã lọc)")
    sample = df_filtered[df_filtered['nsw_count'] > 0].nlargest(5, 'nsw_count')
    if not sample.empty and 'caption' in sample.columns and 'caption_normalized' in sample.columns:
        for _, row in sample.iterrows():
            with st.container(border=True):
                st.caption(f"Gốc ({row['nsw_count']} từ NSW)")
                st.write(str(row['caption'])[:200])
                st.caption("Sau chuẩn hoá")
                st.write(str(row['caption_normalized'])[:200])
    else:
        st.info("Không có bài viết nào chứa NSW trong dữ liệu đã lọc hiện tại.")

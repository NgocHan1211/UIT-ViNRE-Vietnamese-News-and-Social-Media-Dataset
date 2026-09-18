import os
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from collections import defaultdict


# ---------------------------------------------------------------------------
# LABEL SHORT-NAMES for Heatmap axes
# ---------------------------------------------------------------------------
_LABEL_SHORT = {
    'T01': 'T01 Politics',
    'T02': 'T02 Economy',
    'T03': 'T03 Crime & Law',
    'T04': 'T04 Health',
    'T05': 'T05 Education',
    'T06': 'T06 Sci & Tech',
    'T07': 'T07 Environment',
    'T08': 'T08 Weather',
    'T09': 'T09 Disasters',
    'T10': 'T10 Arts & Media',
    'T11': 'T11 Sport',
    'T12': 'T12 Society',
    'T13': 'T13 Human Interest',
    'T14': 'T14 Labor',
    'T15': 'T15 Lifestyle',
    'T16': 'T16 World',
    'T17': 'T17 Transport',
    'T18': 'T18 Other',
}

# ---------------------------------------------------------------------------
# HELPER: Load & parse annotation conflicts from CSV (cached)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _load_conflict_data(csv_path):
    """Parse label_join_conflicts.csv → returns (pair_counts dict, pair_records dict)."""
    if not csv_path or not os.path.exists(csv_path):
        return {}, {}

    df = pd.read_csv(csv_path)
    conflict_types = [
        'duplicate_label_topic_conflict',
        'unresolved_duplicate_label_topic_conflict',
    ]
    conflicts = df[df['issue_type'].isin(conflict_types)].copy()
    conflicts = conflicts[conflicts['topic_label_id_candidates'].notna()]

    pair_records = defaultdict(list)
    for _, row in conflicts.iterrows():
        cands = str(row['topic_label_id_candidates']).split(';')
        if len(cands) == 2:
            t1, t2 = cands[0].strip(), cands[1].strip()
            key = tuple(sorted([t1, t2]))
            pair_records[key].append({
                'record_id': str(row.get('record_id', '')),
                'issue_type': str(row.get('issue_type', '')),
                'details': str(row.get('details', '')),
            })
    pair_counts = {k: len(v) for k, v in pair_records.items()}
    # Convert defaultdict to regular dict for caching
    return dict(pair_counts), dict(pair_records)


# ---------------------------------------------------------------------------
# HELPER: Build Plotly heatmap from conflict pairs
# ---------------------------------------------------------------------------
def _build_conflict_heatmap(pair_counts, pair_records, apply_editorial_theme):
    if not pair_counts:
        return None, {}

    labels_involved = sorted(
        set(l for pair in pair_counts for l in pair),
        key=lambda x: int(x[1:]) if x[1:].isdigit() else 99
    )
    short_labels = [_LABEL_SHORT.get(l, l) for l in labels_involved]
    n = len(labels_involved)
    idx = {l: i for i, l in enumerate(labels_involved)}

    # Build matrix
    matrix = np.zeros((n, n), dtype=int)
    hover_text = [["" for _ in range(n)] for _ in range(n)]
    cell_records = {}

    for (t1, t2), count in pair_counts.items():
        if t1 in idx and t2 in idx:
            i, j = idx[t1], idx[t2]
            matrix[i][j] = count
            matrix[j][i] = count
            recs = pair_records.get((t1, t2), pair_records.get((t2, t1), []))
            ex_ids = [r['record_id'] for r in recs[:2]]
            tip = f"<b>Conflicts:</b> {count}<br><b>Nhãn:</b> {_LABEL_SHORT.get(t1,t1)} ↔ {_LABEL_SHORT.get(t2,t2)}<br><b>Ví dụ:</b> {', '.join(ex_ids)}"
            hover_text[i][j] = tip
            hover_text[j][i] = tip
            cell_records[(i, j)] = recs
            cell_records[(j, i)] = recs

    # Diagonal = NaN so it's grey (no self-conflict)
    for i in range(n):
        matrix[i][i] = -1

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=short_labels,
        y=short_labels,
        text=[[str(v) if v > 0 else "" for v in row] for row in matrix],
        texttemplate="%{text}",
        hovertext=hover_text,
        hovertemplate="%{hovertext}<extra></extra>",
        colorscale=[
            [0.0, '#FAF8F5'],
            [0.001, '#D6E4F0'],
            [0.5, '#3498DB'],
            [1.0, '#1A5276'],
        ],
        zmin=0,
        zmax=max(max(pair_counts.values()), 1),
        showscale=True,
        colorbar=dict(
            title=dict(text="Số lần<br>Conflict", font=dict(size=10, family="Inter, sans-serif")),
            thickness=12,
            len=0.7,
        ),
    ))

    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(
            tickangle=-35,
            tickfont=dict(size=10, family="Inter, sans-serif"),
            side='bottom',
        ),
        yaxis=dict(
            tickfont=dict(size=10, family="Inter, sans-serif"),
            autorange='reversed',
        ),
    )
    apply_editorial_theme(fig)
    return fig, cell_records


# ---------------------------------------------------------------------------
# HELPER: Build Strategic Topic Quadrant
# ---------------------------------------------------------------------------
def _build_strategic_quadrant(df_filtered, shorten_topic_name, apply_editorial_theme):
    """Volume vs Avg Engagement bubble chart with 4 strategic quadrants."""
    df_copy = df_filtered.copy()
    df_copy['total_eng'] = (
        df_copy['total_reactions'] + df_copy['comment_count'] + df_copy['share_count']
    )

    agg = df_copy.groupby('topic_label_final').agg(
        volume=('total_eng', 'count'),
        avg_eng=('total_eng', 'mean'),
        avg_controversy=('controversy_index', 'mean') if 'controversy_index' in df_copy.columns else ('total_eng', 'count'),
    ).reset_index()
    agg['short_name'] = agg['topic_label_final'].apply(
        lambda x: shorten_topic_name(x, include_code=True)
    )
    agg['topic_code'] = agg['topic_label_final'].apply(
        lambda x: x.split('. ')[0] if '. ' in x else x
    )

    if agg.empty or len(agg) < 2:
        return None

    med_x = agg['volume'].median()
    med_y = agg['avg_eng'].median()

    # Bubble size: scale controversy → 10–40 range
    if 'controversy_index' in df_copy.columns:
        size_col = agg['avg_controversy']
        size_min, size_max = size_col.min(), size_col.max()
        if size_max > size_min:
            agg['bubble_size'] = 10 + 30 * (size_col - size_min) / (size_max - size_min)
        else:
            agg['bubble_size'] = 20
    else:
        agg['bubble_size'] = 20

    def quadrant_label(row):
        hi_v = row['volume'] >= med_x
        hi_e = row['avg_eng'] >= med_y
        if hi_v and hi_e:
            return "🔴 Chiến lược Cốt lõi (High Vol / High Eng)"
        elif hi_v and not hi_e:
            return "🟡 Nền tảng Thảo luận (High Vol / Low Eng)"
        elif not hi_v and hi_e:
            return "🟢 Chủ đề Nổi bật (Low Vol / High Eng)"
        else:
            return "⚪ Chủ đề Ngoại vi (Low Vol / Low Eng)"

    agg['quadrant'] = agg.apply(quadrant_label, axis=1)

    color_map = {
        "🔴 Chiến lược Cốt lõi (High Vol / High Eng)": "#C0392B",
        "🟡 Nền tảng Thảo luận (High Vol / Low Eng)":  "#D4AC0D",
        "🟢 Chủ đề Nổi bật (Low Vol / High Eng)":       "#1E8449",
        "⚪ Chủ đề Ngoại vi (Low Vol / Low Eng)":        "#808B96",
    }

    fig = px.scatter(
        agg,
        x='volume',
        y='avg_eng',
        size='bubble_size',
        color='quadrant',
        color_discrete_map=color_map,
        text='topic_code',
        hover_name='short_name',
        hover_data={
            'volume': True,
            'avg_eng': ':.0f',
            'quadrant': True,
            'bubble_size': False,
            'topic_code': False,
        },
        labels={
            'volume': 'Số lượng Bài đăng (Volume)',
            'avg_eng': 'Tương tác Trung bình / Bài (Avg Engagement)',
            'quadrant': 'Phân loại Chiến lược',
        },
        size_max=40,
    )

    # Quadrant dividers
    for shape_cfg in [
        dict(type='line', x0=med_x, x1=med_x,
             y0=agg['avg_eng'].min() * 0.9, y1=agg['avg_eng'].max() * 1.1,
             line=dict(color='#1C1C1C', width=1, dash='dot')),
        dict(type='line', y0=med_y, y1=med_y,
             x0=agg['volume'].min() * 0.9, x1=agg['volume'].max() * 1.1,
             line=dict(color='#1C1C1C', width=1, dash='dot')),
    ]:
        fig.add_shape(**shape_cfg)

    # Quadrant annotations
    x_min, x_max = agg['volume'].min(), agg['volume'].max()
    y_min, y_max = agg['avg_eng'].min(), agg['avg_eng'].max()
    quad_annotations = [
        dict(x=(med_x + x_max) / 2, y=(med_y + y_max) / 2,
             text="Core Strategic Topic", showarrow=False,
             font=dict(size=9, color="#C0392B", family="Inter, sans-serif"),
             opacity=0.4),
        dict(x=(x_min + med_x) / 2, y=(med_y + y_max) / 2,
             text="Niche Star", showarrow=False,
             font=dict(size=9, color="#1E8449", family="Inter, sans-serif"),
             opacity=0.4),
        dict(x=(med_x + x_max) / 2, y=(y_min + med_y) / 2,
             text="Discussion Base", showarrow=False,
             font=dict(size=9, color="#D4AC0D", family="Inter, sans-serif"),
             opacity=0.4),
        dict(x=(x_min + med_x) / 2, y=(y_min + med_y) / 2,
             text="Peripheral", showarrow=False,
             font=dict(size=9, color="#808B96", family="Inter, sans-serif"),
             opacity=0.4),
    ]
    fig.update_layout(
        annotations=quad_annotations,
        height=430,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(
            orientation='h',
            yanchor='bottom', y=-0.28,
            xanchor='center', x=0.5,
            font=dict(size=10, family='Inter, sans-serif'),
        ),
    )
    fig.update_traces(textposition='top center', textfont=dict(size=9, family='Inter, sans-serif'))
    apply_editorial_theme(fig)
    return fig


# ---------------------------------------------------------------------------
# MAIN RENDER FUNCTION
# ---------------------------------------------------------------------------
def render_front_page(df_filtered, df_raw, shorten_topic_name, apply_editorial_theme, metrics, conflicts_csv_path=None):
    st.markdown("<h3 class='section-header'>🗞️ The Front Page (Tổng quan Trong Ngày)</h3>", unsafe_allow_html=True)

    # ── 1. Topic Distribution Chart ──────────────────────────────────────────
    topic_counts = df_filtered['topic_label_final'].value_counts().reset_index()
    topic_counts.columns = ['Topic', 'Count']

    if not topic_counts.empty:
        max_row = topic_counts.sort_values(by='Count', ascending=True).iloc[-1]
        max_topic = shorten_topic_name(max_row['Topic'], include_code=False)
        total_count = topic_counts['Count'].sum()
        pct = (max_row['Count'] / total_count * 100) if total_count > 0 else 0
        topic_dist_title = f"📰 {max_topic} chiếm tỷ trọng cao nhất trong cấu trúc thảo luận với {pct:.1f}% tổng số bài đăng"
    else:
        topic_dist_title = "Phân bổ Chủ đề Thảo luận (Topic Distribution)"

    st.markdown(
        f"<h4 style='text-align:center; font-family: Lora, Georgia, serif; font-size:15px; margin-top:10px;'>"
        f"{topic_dist_title}</h4>",
        unsafe_allow_html=True
    )

    topic_counts['Topic'] = topic_counts['Topic'].apply(lambda x: shorten_topic_name(x, include_code=True))
    topic_counts = topic_counts.sort_values(by='Count', ascending=True)

    fig_topic_dist = px.bar(
        topic_counts,
        x='Count', y='Topic',
        orientation='h', text='Count',
        color='Count', color_continuous_scale='Blues',
        labels={'Count': 'Số lượng bài đăng', 'Topic': 'Chủ đề'}
    )
    fig_topic_dist.update_traces(textposition='outside')
    fig_topic_dist.update_layout(height=450, margin=dict(l=10, r=10, t=10, b=10))
    apply_editorial_theme(fig_topic_dist)
    st.plotly_chart(fig_topic_dist, use_container_width=True)

    st.write("---")

    # ── 2. Highlights & Risks (Dynamic) ─────────────────────────────────────
    avg_polarity = df_filtered['polarity_score'].mean()
    if avg_polarity > 0.05:
        polarity_status = f"<span style='color:#1E8449;'>nghiêng về sắc thái tích cực / đồng thuận</span> (Polarity = {avg_polarity:.3f})"
    elif avg_polarity < -0.05:
        polarity_status = f"<span style='color:#D90429;'>nghiêng về sắc thái tiêu cực / phẫn nộ</span> (Polarity = {avg_polarity:.3f})"
    else:
        polarity_status = f"<span style='color:#F4A261;'>ở mức trung lập hoặc đa chiều tự triệt tiêu</span> (Polarity = {avg_polarity:.3f})"

    missing_time_pct = (
        (df_filtered['has_post_created_time'] == 0).sum() / len(df_filtered) * 100
        if len(df_filtered) > 0 else 0
    )

    col_light, col_dark = st.columns(2)
    with col_light:
        card_hl = f"""
        <div class='editorial-brief-card'>
            <h5 style='color: #1E8449; font-family: Lora, Georgia, serif; font-size: 15px; margin-top: 0; margin-bottom: 10px;'>🟢 Điểm sáng Dữ liệu (Highlights)</h5>
            <ul style='margin-bottom: 0; padding-left: 20px; font-family: "Inter", sans-serif; font-size: 13px; line-height: 1.6; color: #1C1C1C;'>
                <li style='margin-bottom: 8px;'><b>Chủ đề có Mật độ Bài đăng Cao nhất</b> <i>(Volume)</i>: <b>{metrics['most_active_name']}</b> chiếm <b>{metrics['most_active_pct']:.1f}%</b> tổng số bài — phản ánh độ phủ của dữ liệu hiện tại.</li>
                <li style='margin-bottom: 8px;'><b>Chủ đề đạt Mức độ Lan tỏa Cao nhất</b> <i>(Engagement)</i>: <b>{metrics['best_eng_topic']}</b> đạt trung bình <b>{int(round(metrics['best_eng_val'])):,}</b> tương tác/bài (bao gồm Proxy Signals: Reactions, Comments, Shares).</li>
                <li style='margin-bottom: 0;'><b>Thái độ Dư luận Tổng quát</b>: Mức độ Phân cực (Polarity Score) trung bình hiện tại đang {polarity_status}.</li>
            </ul>
        </div>
        """
        st.markdown("\n".join(line.strip() for line in card_hl.split("\n")), unsafe_allow_html=True)

    with col_dark:
        card_rk = f"""
        <div class='editorial-brief-card'>
            <h5 style='color: #D90429; font-family: Lora, Georgia, serif; font-size: 15px; margin-top: 0; margin-bottom: 10px;'>🔴 Chỉ báo Phân cực &amp; Điểm nóng Dư luận</h5>
            <ul style='margin-bottom: 0; padding-left: 20px; font-family: "Inter", sans-serif; font-size: 13px; line-height: 1.6; color: #1C1C1C;'>
                <li style='margin-bottom: 8px;'><b>Điểm nóng Xung đột cảm xúc</b>: Chủ đề <b>{metrics['worst_cont_topic']}</b> ghi nhận Controversy Index trung bình cao nhất (<b>{metrics['worst_cont_val']:.3f}</b>), thể hiện sự bất đồng ý kiến sâu sắc kết hợp thảo luận dày đặc.</li>
                <li style='margin-bottom: 8px;'><b>Mức độ Giải trí / Châm biếm cao nhất</b>: Chủ đề <b>{metrics['worst_sarc_topic']}</b> có tỷ lệ Amusement Index đạt <b>{metrics['worst_sarc_val']:.1f}%</b>, báo hiệu xu hướng tiếp nhận phi nghiêm túc từ dư luận.</li>
                <li style='margin-bottom: 0;'><b>Khuyết thiếu Metadata Thời gian (Limitation)</b>: Ghi nhận <b>{missing_time_pct:.1f}%</b> bài đăng bị khuyết hoặc lỗi định dạng Timestamp, đòi hỏi sự thận trọng khi ngoại suy các kết luận về xu hướng thời gian (Temporal Trends).</li>
            </ul>
        </div>
        """
        st.markdown("\n".join(line.strip() for line in card_rk.split("\n")), unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # DATA TRANSPARENCY LAYER — 4 Research Evidence Panels
    # ════════════════════════════════════════════════════════════════════════
    st.write("---")
    st.markdown(
        "<h4 style='font-family: Playfair Display, Georgia, serif; font-size: 18px; "
        "color:#1C1C1C; margin-bottom:4px;'>🔬 Lớp Minh bạch Hóa Dữ liệu "
        "<span style=\"font-family:Inter,sans-serif; font-size:12px; "
        "font-weight:400; color:#666;\">(Data Transparency Layer)</span></h4>"
        "<p style='font-family:Inter,sans-serif; font-size:12px; color:#666; margin-top:0;'>"
        "Hệ thống minh chứng thực nghiệm — đối chiếu với Mục 5–6 trong báo cáo nghiên cứu</p>",
        unsafe_allow_html=True
    )

    # ── Panel 1 & 2 (side by side) ───────────────────────────────────────────
    col_p1, col_p2 = st.columns(2)

    # ── PANEL 1: Data Quality Audit ──────────────────────────────────────────
    with col_p1:
        st.markdown(
            "<h5 style='font-family: Lora, Georgia, serif; font-size:14px; "
            "color:#1C1C1C; border-top: 2px solid #1C1C1C; padding-top:10px; margin-bottom:8px;'>"
            "📋 Panel 1 — Kiểm toán Chất lượng Dữ liệu</h5>",
            unsafe_allow_html=True
        )

        # Compute from df_filtered (dynamic) vs df_raw (global baseline)
        total_master = len(df_raw)
        usable_master = int((df_raw['usable_for_reaction_analysis'] == 1).sum())
        excluded_master = total_master - usable_master
        usable_pct_master = usable_master / total_master * 100 if total_master > 0 else 0

        total_filtered = len(df_filtered)
        usable_filtered = int((df_filtered['usable_for_reaction_analysis'] == 1).sum())
        usable_pct_filtered = usable_filtered / total_filtered * 100 if total_filtered > 0 else 0

        # Donut-style metrics
        p1_html = f"""
        <div style='border: 1.5px solid #D9D7D0; padding: 14px 16px; background:#FAF8F5;'>
            <div style='display:flex; gap:20px; align-items:center; margin-bottom:12px;'>
                <div style='text-align:center; flex:1;'>
                    <div style='font-family: Playfair Display, serif; font-size:26px; font-weight:700; color:#1E8449;'>{usable_pct_master:.1f}%</div>
                    <div style='font-family:Inter,sans-serif; font-size:10px; text-transform:uppercase; letter-spacing:0.5px; color:#555;'>Usable (Master)</div>
                </div>
                <div style='text-align:center; flex:1;'>
                    <div style='font-family: Playfair Display, serif; font-size:26px; font-weight:700; color:#D90429;'>{100-usable_pct_master:.1f}%</div>
                    <div style='font-family:Inter,sans-serif; font-size:10px; text-transform:uppercase; letter-spacing:0.5px; color:#555;'>Excluded</div>
                </div>
                <div style='text-align:center; flex:1;'>
                    <div style='font-family: Playfair Display, serif; font-size:26px; font-weight:700; color:#2471A3;'>{usable_pct_filtered:.1f}%</div>
                    <div style='font-family:Inter,sans-serif; font-size:10px; text-transform:uppercase; letter-spacing:0.5px; color:#555;'>Usable (Filter)</div>
                </div>
            </div>
            <table style='width:100%; font-family:Inter,sans-serif; font-size:12px; border-collapse:collapse;'>
                <tr style='border-bottom:1px solid #EBE9E4;'>
                    <td style='padding:4px 0; color:#555;'>Master Dataset</td>
                    <td style='text-align:right; font-weight:600;'>{total_master:,} bản ghi</td>
                </tr>
                <tr style='border-bottom:1px solid #EBE9E4;'>
                    <td style='padding:4px 0; color:#1E8449;'>✅ Đủ điều kiện Reaction</td>
                    <td style='text-align:right; font-weight:600; color:#1E8449;'>{usable_master:,}</td>
                </tr>
                <tr style='border-bottom:1px solid #EBE9E4;'>
                    <td style='padding:4px 0; color:#D90429;'>❌ Loại trừ (Nhiễu / Thiếu metadata)</td>
                    <td style='text-align:right; font-weight:600; color:#D90429;'>{excluded_master:,}</td>
                </tr>
                <tr>
                    <td style='padding:4px 0; color:#2471A3;'>🔍 Filter hiện tại (Usable)</td>
                    <td style='text-align:right; font-weight:600; color:#2471A3;'>{usable_filtered:,}</td>
                </tr>
            </table>
            <p style='font-family:Inter,sans-serif; font-size:11px; color:#888; margin-top:10px; margin-bottom:0; font-style:italic;'>
                Hệ thống tự động loại trừ <b>{100-usable_pct_master:.1f}%</b> mẫu thiếu metadata để đảm bảo độ tin cậy cho các chỉ số Proxy Signals — theo cờ <code>usable_for_reaction_analysis</code>.
            </p>
        </div>
        """
        st.markdown(p1_html, unsafe_allow_html=True)

    # ── PANEL 2: Annotation Integrity Badge ──────────────────────────────────
    with col_p2:
        st.markdown(
            "<h5 style='font-family: Lora, Georgia, serif; font-size:14px; "
            "color:#1C1C1C; border-top: 2px solid #1C1C1C; padding-top:10px; margin-bottom:8px;'>"
            "🏅 Panel 2 — Annotation Integrity &amp; IAA</h5>",
            unsafe_allow_html=True
        )
        p2_html = """
        <div style='border: 2.5px double #D4AF37; background:#FFFDF0; padding: 16px;'>
            <div style='background:#D4AF37; color:#FAF8F5; font-family:Inter,sans-serif;
                        font-size:10px; font-weight:700; text-transform:uppercase;
                        letter-spacing:0.8px; display:inline-block; padding:2px 8px; margin-bottom:10px;'>
                ✔ HUMAN-LABELED CORPUS — Quality Verified
            </div>
            <div style='display:flex; gap:16px; margin-bottom:12px;'>
                <div style='text-align:center; flex:1; border-right:1px solid #D9D7D0; padding-right:16px;'>
                    <div style='font-family: Playfair Display, serif; font-size:30px; font-weight:700; color:#D4AF37;'>0.8239</div>
                    <div style='font-family:Inter,sans-serif; font-size:10px; text-transform:uppercase; letter-spacing:0.5px; color:#555;'>Fleiss' Kappa (IAA)</div>
                    <div style='font-family:Inter,sans-serif; font-size:10px; color:#1E8449; margin-top:3px;'>● Mức nhất quán Cao</div>
                </div>
                <div style='text-align:center; flex:1;'>
                    <div style='font-family: Playfair Display, serif; font-size:30px; font-weight:700; color:#1C1C1C;'>17</div>
                    <div style='font-family:Inter,sans-serif; font-size:10px; text-transform:uppercase; letter-spacing:0.5px; color:#555;'>Topic Classes</div>
                    <div style='font-family:Inter,sans-serif; font-size:10px; color:#555; margin-top:3px;'>T01 → T17 (excl. T18)</div>
                </div>
            </div>
            <table style='width:100%; font-family:Inter,sans-serif; font-size:12px; border-collapse:collapse;'>
                <tr style='border-bottom:1px solid #EBE9E4;'>
                    <td style='padding:4px 0; color:#555;'>Phương pháp Gán nhãn</td>
                    <td style='text-align:right; font-weight:600;'>Human Annotation</td>
                </tr>
                <tr style='border-bottom:1px solid #EBE9E4;'>
                    <td style='padding:4px 0; color:#555;'>Số lượng Người gán nhãn</td>
                    <td style='text-align:right; font-weight:600;'>3 Annotators</td>
                </tr>
                <tr style='border-bottom:1px solid #EBE9E4;'>
                    <td style='padding:4px 0; color:#555;'>Quy mô Dữ liệu được xác minh</td>
                    <td style='text-align:right; font-weight:600;'>8,922 bản ghi</td>
                </tr>
                <tr>
                    <td style='padding:4px 0; color:#555;'>Phân xử Xung đột</td>
                    <td style='text-align:right; font-weight:600;'>Majority Vote + Review</td>
                </tr>
            </table>
            <p style='font-family:Inter,sans-serif; font-size:11px; color:#888; margin-top:10px; margin-bottom:0; font-style:italic;'>
                Fleiss' Kappa = 0.8239 vượt ngưỡng chấp nhận <b>κ ≥ 0.80</b> (Landis &amp; Koch, 1977) — phân loại mức <b>"Almost Perfect Agreement"</b>.
            </p>
        </div>
        """
        st.markdown(p2_html, unsafe_allow_html=True)

    # ── PANEL 3: Error Analysis Heatmap ──────────────────────────────────────
    st.markdown(
        "<h5 style='font-family: Lora, Georgia, serif; font-size:14px; "
        "color:#1C1C1C; border-top: 2px solid #1C1C1C; padding-top:10px; margin-top:20px; margin-bottom:4px;'>"
        "🗺️ Panel 3 — Ma trận Xung đột Gán nhãn (Annotation Conflict Matrix)</h5>"
        "<p style='font-family:Inter,sans-serif; font-size:12px; color:#666; margin-top:0; margin-bottom:8px;'>"
        "Các ô có màu đậm = cặp nhãn gây tranh chấp nhiều nhất giữa các annotators. "
        "Hover vào ô để xem chi tiết record_id và ngữ cảnh xung đột.</p>",
        unsafe_allow_html=True
    )

    pair_counts, pair_records = _load_conflict_data(conflicts_csv_path)
    if pair_counts:
        fig_heatmap, cell_records = _build_conflict_heatmap(pair_counts, pair_records, apply_editorial_theme)
        if fig_heatmap:
            st.plotly_chart(fig_heatmap, use_container_width=True)

            # Top-conflict expandable detail
            top_pairs = sorted(pair_counts.items(), key=lambda x: -x[1])[:5]
            with st.expander("🔍 Truy vết Chi tiết — Top Cặp Nhãn Xung đột Nhiều nhất", expanded=False):
                for (t1, t2), count in top_pairs:
                    recs = pair_records.get((t1, t2), pair_records.get((t2, t1), []))
                    n1 = _LABEL_SHORT.get(t1, t1)
                    n2 = _LABEL_SHORT.get(t2, t2)
                    st.markdown(
                        f"**{n1} ↔ {n2}** — `{count}` lần xung đột  "
                        f"| Record IDs: `{'`, `'.join([r['record_id'] for r in recs])}`"
                    )
                    st.caption(
                        f"*Phân tích ngữ nghĩa:* {n1.split(' ', 1)[-1]} và {n2.split(' ', 1)[-1]} "
                        f"có ranh giới khái niệm mờ khi bài đăng đề cập đồng thời cả hai bối cảnh — "
                        f"phản ánh thách thức điển hình trong phân loại chủ đề đa nhãn."
                    )
                    st.write("")

            st.caption(
                f"📌 *Dữ liệu từ `label_join_conflicts.csv` — {sum(pair_counts.values())} annotation conflicts "
                f"trên {len(pair_counts)} cặp nhãn, được giải quyết bằng quy trình Majority Vote + Expert Review.*"
            )
    else:
        st.info("ℹ️ Không tìm thấy file `label_join_conflicts.csv`. Heatmap xung đột gán nhãn không khả dụng.")

    # ── PANEL 4: Strategic Topic Quadrant ────────────────────────────────────
    st.markdown(
        "<h5 style='font-family: Lora, Georgia, serif; font-size:14px; "
        "color:#1C1C1C; border-top: 2px solid #1C1C1C; padding-top:10px; margin-top:20px; margin-bottom:4px;'>"
        "📡 Panel 4 — Ma trận Phân loại Chủ đề Chiến lược "
        "<span style=\"font-size:12px; font-weight:400;\">(Volume × Engagement Quadrant)</span></h5>"
        "<p style='font-family:Inter,sans-serif; font-size:12px; color:#666; margin-top:0; margin-bottom:8px;'>"
        "Mỗi bong bóng = một chủ đề. Trục X = lượng bài đăng (Volume), Trục Y = tương tác trung bình/bài. "
        "Đường gạch chấm = ngưỡng trung vị (Median). Kích thước bong bóng ∝ Controversy Index trung bình.</p>",
        unsafe_allow_html=True
    )

    fig_quadrant = _build_strategic_quadrant(df_filtered, shorten_topic_name, apply_editorial_theme)
    if fig_quadrant:
        st.plotly_chart(fig_quadrant, use_container_width=True)
        st.caption(
            "📌 *Phân loại chiến lược dựa trên ngưỡng trung vị (Median) của toàn bộ tập dữ liệu đang được lọc. "
            "Kết quả thay đổi theo bộ lọc Sidebar — đảm bảo tính phân tích động (Dynamic Analysis).*"
        )
    else:
        st.info("ℹ️ Không đủ dữ liệu để hiển thị Strategic Quadrant với bộ lọc hiện tại.")

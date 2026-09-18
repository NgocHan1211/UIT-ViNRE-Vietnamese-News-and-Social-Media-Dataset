import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import time
import os

# ----------------------------------------------------
# HELPER FUNCTIONS FOR BIAS & SARCASM ANALYSIS
# ----------------------------------------------------
def analyze_topic_spam_bias(df):
    """
    Phân tích xem một chủ đề có bị spam/thống trị bởi một số lượng nhỏ Page hay không.
    Trả về DataFrame gồm: total_posts, unique_pages, top_page_name,
    top_page_dominance_%, is_spam_warning cho mỗi topic.
    """
    # Tổng số bài và số page độc nhất cho mỗi chủ đề
    topic_stats = df.groupby('topic_label_final').agg(
        total_posts=('page_name', 'count'),
        unique_pages=('page_name', 'nunique')
    ).reset_index()

    # Page đăng nhiều bài nhất trong từng chủ đề
    page_topic_counts = df.groupby(['topic_label_final', 'page_name']).size().reset_index(name='posts_by_page')
    top_page_idx = page_topic_counts.groupby('topic_label_final')['posts_by_page'].idxmax()
    top_pages = page_topic_counts.loc[top_page_idx].rename(
        columns={'page_name': 'top_page_name', 'posts_by_page': 'top_page_posts'}
    )

    # Gộp và tính Concentration Ratio
    bias_df = pd.merge(topic_stats, top_pages, on='topic_label_final')
    bias_df['top_page_dominance_%'] = (
        bias_df['top_page_posts'] / bias_df['total_posts'] * 100
    ).round(2)

    # Cắm cờ cảnh báo: >50% bài từ 1 page, HOẶC chỉ có <=2 page tham gia
    bias_df['is_spam_warning'] = (
        (bias_df['top_page_dominance_%'] > 50.0) | (bias_df['unique_pages'] <= 2)
    )

    return bias_df.sort_values('total_posts', ascending=False)


from sklearn.feature_extraction.text import CountVectorizer

VN_STOPWORDS = [
    "và", "là", "của", "các", "có", "trong", "để", "với", "một",
    "không", "những", "cho", "người", "khi", "này", "đã", "từ",
    "rằng", "đến", "thì", "mà", "bị", "được", "như", "trên", "tại", "vào"
]

@st.cache_data
def extract_sarcasm_keywords(text_series, top_n=6):
    texts = text_series.dropna().astype(str)
    # Lọc bỏ chuỗi quá ngắn (dưới 3 ký tự)
    texts = texts[texts.str.len() > 3].tolist()
    if len(texts) < 2:
        return []
    
    # Thử bigram/trigram trước
    for ngram_range, min_df in [((2, 3), 2), ((1, 2), 1)]:
        try:
            vectorizer = CountVectorizer(
                ngram_range=ngram_range,
                stop_words=VN_STOPWORDS,
                max_df=0.9,
                min_df=min_df
            )
            X = vectorizer.fit_transform(texts)
            if X.shape[1] == 0:
                continue
            sum_words = X.sum(axis=0)
            words_freq = [
                (word, sum_words[0, idx])
                for word, idx in vectorizer.vocabulary_.items()
            ]
            words_freq.sort(key=lambda x: x[1], reverse=True)
            result = [word for word, _ in words_freq[:top_n]]
            if result:
                return result
        except ValueError:
            continue
    return []


# --------------------------------------------------------------------
# MODEL INFRASTRUCTURE HELPERS (TOP-LEVEL)
# --------------------------------------------------------------------
@st.cache_resource
def load_demo_model_assets(model_name):
    import json
    import joblib
    import os
    
    base_dir = os.path.dirname(__file__)
    registry_path = os.path.join(base_dir, "08_Modeling_Results/traditional_ml_hpo_deep/model_zoo/model_registry.json")
    
    if not os.path.exists(registry_path):
        return None, None, None, None, f"Registry file not found at {registry_path}"
        
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
    except Exception as e:
        return None, None, None, None, f"Failed to read model registry: {str(e)}"
        
    model_meta = next((r for r in registry if r.get("model_name") == model_name and r.get("recommended_for_demo") == True), None)
    if not model_meta:
        return None, None, None, None, f"Model metadata for {model_name} not found in registry"
        
    m_path = model_meta["model_path"]
    v_path = model_meta["vectorizer_path"]
    le_path = model_meta["label_encoder_path"]
    
    if m_path.startswith("data/"): m_path = m_path[5:]
    if v_path.startswith("data/"): v_path = v_path[5:]
    if le_path.startswith("data/"): le_path = le_path[5:]
    
    full_m_path = os.path.join(base_dir, m_path)
    full_v_path = os.path.join(base_dir, v_path)
    full_le_path = os.path.join(base_dir, le_path)
    
    if not os.path.exists(full_m_path):
        return None, None, None, None, (
            f"Tệp trọng số mô hình không tìm thấy tại: `{m_path}`.\n\n"
            f"Do dung lượng file mô hình {model_name} quá lớn (>100MB), file này đã bị cấu hình bỏ qua trong `.gitignore` và không được đẩy lên GitHub.\n\n"
            "**Cách khắc phục:**\n"
            "Hãy tải tệp tin `model.joblib` tương ứng về và sao chép vào đúng thư mục trên máy của bạn."
        )

    try:
        model = joblib.load(full_m_path)
        vectorizer = joblib.load(full_v_path)
        label_encoder = joblib.load(full_le_path)
        return model, vectorizer, label_encoder, model_meta, None
    except Exception as e:
        err_msg = str(e)
        if "libxgboost" in err_msg or "libomp" in err_msg:
            err_msg += "\n\n💡 *Gợi ý: Dòng máy macOS cần cài OpenMP runtime bằng cách chạy lệnh: `brew install libomp`*"
        return None, None, None, None, err_msg


@st.cache_resource
def load_transformer_cached(model_dir):
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        if torch.cuda.is_available():
            device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
            
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        model.to(device)
        return model, tokenizer, device, None
    except Exception as e:
        return None, None, None, str(e)


def predict_transformer(model_name, text, mapping_dict):
    model_dirs = {
        "mBERT": "08_Modeling_Results/mbert_best_model_kb4",
        "PhoBERT": "08_Modeling_Results/phobert_kb4_best_model",
        "XLM-R": "08_Modeling_Results/xlmr_best_model_kb5"
    }
    
    base_dir = os.path.dirname(__file__)
    model_dir = os.path.join(base_dir, model_dirs[model_name])
    
    if not os.path.exists(model_dir):
        return None, None, None, None, (
            f"⚠️ Thư mục checkpoint của mô hình {model_name} không tìm thấy tại: `{model_dirs[model_name]}`.\n\n"
            "Do dung lượng mô hình Deep Learning rất lớn (>500MB), thư mục này đã bị cấu hình bỏ qua trong `.gitignore` và không được đẩy lên GitHub.\n\n"
            "**Cách khắc phục:**\n"
            "1. Vui lòng tải xuống thư mục checkpoint mô hình và sao chép vào đúng đường dẫn trên trong thư mục dự án của bạn.\n"
            "2. Đảm bảo thư mục chứa đầy đủ các file cấu hình và trọng số (ví dụ: `pytorch_model.bin`, `config.json`, các file tokenizer)."
        )

    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError:
        return None, None, None, None, "Yêu cầu cài đặt `torch` và `transformers` để chạy mô hình Deep Learning."

    try:
        model, tokenizer, device, err = load_transformer_cached(model_dir)
        if err:
            return None, None, None, None, err
            
        classes = ['T01', 'T02', 'T03', 'T04', 'T05', 'T06', 'T07', 'T08', 'T09', 'T10', 'T11', 'T12', 'T13', 'T14', 'T15', 'T16', 'T17']
        
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=256)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model(**inputs)
            
        probs = torch.softmax(outputs.logits, dim=-1).cpu().numpy()[0]
        pred_class_idx = probs.argmax()
        confidence = probs[pred_class_idx]
        pred_label_id = classes[pred_class_idx]
        pred_label_name = mapping_dict.get(pred_label_id, pred_label_id)
        
        return pred_label_name, f"{confidence * 100:.1f}%", pred_label_id, probs, None
    except Exception as e:
        return None, None, None, None, f"Lỗi chạy mô hình: {str(e)}"


@st.cache_data
def load_taxonomy_mapping():
    import os
    import pandas as pd
    
    base_dir = os.path.dirname(__file__)
    csv_path = os.path.join(base_dir, "taxonomy_mapping_used.csv")
    mapping = {}
    if os.path.exists(csv_path):
        try:
            df_map = pd.read_csv(csv_path)
            for _, row in df_map.iterrows():
                tid = str(row['topic_label_id']).strip()
                tval = str(row['topic_label_final']).strip()
                mapping[tid] = tval
        except Exception:
            pass
    fallback = {
        'T01': 'T01. POLITICS',
        'T02': 'T02. ECONOMY_BUSINESS_AND_FINANCE',
        'T03': 'T03. CRIME_LAW_AND_JUSTICE',
        'T04': 'T04. HEALTH',
        'T05': 'T05. EDUCATION',
        'T06': 'T06. SCIENCE_AND_TECHNOLOGY',
        'T07': 'T07. ENVIRONMENT',
        'T08': 'T08. WEATHER',
        'T09': 'T09. DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT',
        'T10': 'T10. ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA',
        'T11': 'T11. SPORT',
        'T12': 'T12. SOCIETY',
        'T13': 'T13. HUMAN_INTEREST',
        'T14': 'T14. LABOR',
        'T15': 'T15. LIFESTYLE_AND_LEISURE',
        'T16': 'T16. WORLD_INTERNATIONAL',
        'T17': 'T17. TRANSPORT_INFRASTRUCTURE',
        'T18': 'T18. OTHER_UNCLEAR'
    }
    for k, v in fallback.items():
        if k not in mapping:
            mapping[k] = v
    return mapping


# --------------------------------------------------------------------
# CONFIGURATION & STYLE DESIGN
# ----------------------------------------------------
st.set_page_config(
    page_title="Social Media Topic Insights Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Editorial UI styling (Newspaper-inspired: Serif fonts, flat borders, off-white background)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #FAF8F5 !important;
        color: #1C1C1C !important;
        line-height: 1.6 !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    
    /* Editorial headlines */
    h1, h2, .editorial-title {
        font-family: 'Playfair Display', Georgia, serif !important;
        color: #1C1C1C !important;
        font-weight: 700 !important;
        letter-spacing: -0.2px !important;
    }
    
    h3, h4, h5, h6, .editorial-heading {
        font-family: 'Source Serif 4', Georgia, serif !important;
        color: #2D2D2D !important;
        font-weight: 600 !important;
        letter-spacing: -0.1px !important;
    }
    
    /* Premium KPI Card Styling (Newspaper Columns style) */
    .kpi-container {
        display: flex;
        gap: 15px;
        margin-bottom: 25px;
        border-top: 2px solid #1C1C1C;
        border-bottom: 2px solid #1C1C1C;
        padding: 15px 0;
    }
    .kpi-card {
        flex: 1;
        border-right: 1px solid #D9D7D0;
        padding: 5px 15px;
        text-align: left;
        min-width: 0;
    }
    .kpi-card:last-child {
        border-right: none;
    }
    .kpi-val {
        font-family: 'Playfair Display', Georgia, serif !important;
        font-size: 28px;
        font-weight: 700;
        color: #1C1C1C;
        margin-bottom: 3px;
        line-height: 1.2 !important;
        white-space: normal !important;
        word-wrap: break-word !important;
        font-variant-numeric: lining-nums !important;
        font-feature-settings: "lnum" 1 !important;
    }
    .kpi-label {
        font-family: 'Inter', sans-serif !important;
        font-size: 11px;
        color: #555555;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
        white-space: normal;
        word-wrap: break-word;
    }
    
    /* Section headers */
    .section-header {
        border-bottom: 1.5px solid #1C1C1C;
        padding-bottom: 5px;
        margin-top: 35px;
        margin-bottom: 20px;
        font-family: 'Playfair Display', Georgia, serif !important;
        font-size: 24px;
        font-weight: 700;
        color: #1C1C1C;
    }
    
    /* Remove rounding and borders from tabs and inputs to match newspaper theme */
    div[data-baseweb="select"] > div {
        background-color: #FAF8F5 !important;
        color: #1C1C1C !important;
        border: 1px solid #D9D7D0 !important;
        border-radius: 0px !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* Giới hạn độ rộng tối đa của nội dung app và căn giữa để không tràn màn hình */
    .block-container {
        max-width: 1200px !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        margin: 0 auto !important;
    }
    
    /* Premium Best Model Card Styling */
    .best-model-card {
        border: 2.5px double #D4AF37 !important;
        background-color: #FFFDF0 !important;
        padding: 20px !important;
        margin-bottom: 20px !important;
        border-radius: 0px !important;
        border-left: 5px solid #D4AF37 !important;
    }
    .best-model-badge {
        background-color: #D4AF37 !important;
        color: #FAF8F5 !important;
        padding: 3px 8px !important;
        font-size: 11px !important;
        font-family: 'Inter', sans-serif !important;
        text-transform: uppercase !important;
        font-weight: 700 !important;
        display: inline-block !important;
        margin-bottom: 8px !important;
        letter-spacing: 0.5px !important;
    }
    
    /* Editorial Insight Storytelling Box Styling */
    .insight-box {
        border-top: 1.5px solid #1C1C1C !important;
        border-bottom: 1.5px solid #1C1C1C !important;
        padding: 12px 10px !important;
        margin-bottom: 25px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 13px !important;
        line-height: 1.6 !important;
        text-align: justify !important;
        background-color: #FAF8F5 !important;
    }
    
    /* Editorial Brief Card Styling (Highlights/Risks) */
    .editorial-brief-card {
        border-top: 2px solid #1C1C1C !important;
        padding: 15px 5px !important;
        margin-top: 10px !important;
        margin-bottom: 15px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 13px !important;
        line-height: 1.6 !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to translate and shorten topic names for UI
def shorten_topic_name(topic_label, include_code=False):
    if not isinstance(topic_label, str):
        return "Other"
    code = ""
    clean_name = topic_label
    if '. ' in topic_label:
        parts = topic_label.split('. ', 1)
        code = parts[0] + ". "
        clean_name = parts[1]
    
    mapping = {
        'POLITICS': 'Politics',
        'ECONOMY_BUSINESS_AND_FINANCE': 'Economy, Business & Finance',
        'CRIME_LAW_AND_JUSTICE': 'Crime, Law & Justice',
        'ENVIRONMENT': 'Environment',
        'HEALTH': 'Health',
        'DISASTER_ACCIDENT_AND_EMERGENCY_INCIDENT': 'Disasters, Accidents & Emergencies',
        'ARTS_CULTURE_ENTERTAINMENT_AND_MEDIA': 'Arts, Culture, Entertainment & Media',
        'HUMAN_INTEREST': 'Human Interest',
        'LABOR': 'Labor',
        'LIFESTYLE_AND_LEISURE': 'Lifestyle & Leisure',
        'TRANSPORT_INFRASTRUCTURE': 'Transport & Infrastructure',
        'OTHER': 'Other',
        'OTHER_UNCLASSIFIED': 'Other'
    }
    translated = mapping.get(clean_name, clean_name.replace('_', ' ').title())
    if include_code and code:
        return f"{code}{translated}"
    return translated

# Helper function to style Plotly charts for the Editorial theme
def apply_editorial_theme(fig):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(
            family="Plus Jakarta Sans, sans-serif",
            size=12,
            color="#1C1C1C"
        ),
        xaxis=dict(
            gridcolor="#EBE9E4",
            linecolor="#1C1C1C",
            tickfont=dict(color="#1C1C1C")
        ),
        yaxis=dict(
            gridcolor="#EBE9E4",
            linecolor="#1C1C1C",
            tickfont=dict(color="#1C1C1C")
        )
    )
    
    # Only update title font if title text is present to avoid rendering "undefined"
    if fig.layout.title and getattr(fig.layout.title, 'text', None):
        fig.update_layout(
            title_font=dict(
                family="Lora, Georgia, serif",
                size=16,
                color="#1C1C1C"
            )
        )
    else:
        fig.layout.title = None
        
    # Configure soft colors & contrast fonts for bar charts dynamically to avoid overlaps/unreadable text
    try:
        fig.update_traces(
            selector=dict(type='bar'),
            insidetextfont=dict(
                color='#FAF8F5',
                family='Plus Jakarta Sans, sans-serif',
                size=11
            ),
            outsidetextfont=dict(
                color='#1C1C1C',
                family='Plus Jakarta Sans, sans-serif',
                size=11
            )
        )
    except Exception:
        pass
        
    return fig


# ----------------------------------------------------
# 1. LOAD DATA
# ----------------------------------------------------
@st.cache_data
def load_data(epsilon=1e-5):
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Public_Response_Streamlit_Enriched.csv")
    df = pd.read_csv(csv_path, low_memory=False)
    
    # 1.1 Data Type Conversion & Parsing
    # Count columns conversion to integer
    count_cols = [
        'like_count', 'love_count', 'haha_count', 'wow_count', 
        'sad_count', 'angry_count', 'care_count', 'sorry_count', 
        'total_reactions', 'share_count', 'comment_count'
    ]
    for col in count_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
    # Followers conversion
    if 'page_followers' in df.columns:
        df['page_followers'] = pd.to_numeric(df['page_followers'], errors='coerce').fillna(0).astype(int)
        
    if 'post_created_date' in df.columns:
        # Convert only where date is not missing
        df['parsed_date'] = pd.to_datetime(df['post_created_date'], errors='coerce')
        # Shift 2026 to 2024 to map to current timeline
        if 'parsed_date' in df.columns:
            mask_2026 = (df['parsed_date'].dt.year == 2026) & df['parsed_date'].notna()
            df.loc[mask_2026, 'parsed_date'] = df.loc[mask_2026, 'parsed_date'] - pd.DateOffset(years=2)
            df['post_created_date'] = df['parsed_date'].dt.strftime('%Y-%m-%d')
        
    # 1.2 Mathematical Indices Fallback & Recalculation
    # Ratios are only calculated for posts with >= 10 reactions to prevent division/proportion noise
    df['outrage_reaction_index'] = np.where(df['total_reactions'] >= 10, df['angry_count'] / df['total_reactions'], 0.0)
    df['amusement_reaction_index'] = np.where(df['total_reactions'] >= 10, df['haha_count'] / df['total_reactions'], 0.0)
    df['empathy_reaction_index'] = np.where(
        df['total_reactions'] >= 10, 
        (df['sad_count'] + df['care_count']) / df['total_reactions'], 
        0.0
    )
    df['approval_reaction_index'] = np.where(
        df['total_reactions'] >= 10, 
        (df['like_count'] + df['love_count']) / df['total_reactions'], 0.0
    )
        
    # Recalculate Polarity & Intensity with Laplace Smoothing
    sr_pos = df['love_count'] + df['care_count']
    sr_neg = df['angry_count'] + df['sad_count']
    sr_ambiguous = df['haha_count'] + df['wow_count']
    sr_all = sr_pos + sr_neg + sr_ambiguous
    all_tot = sr_all + df['like_count']

    df['reaction_intensity'] = np.where(all_tot > 0, sr_all / all_tot, 0.0)
    valence = (sr_pos - sr_neg + epsilon) / (sr_pos + sr_neg + epsilon)
    df['polarity_score'] = df['reaction_intensity'] * valence

    # 1.3 Controversy & Sarcasm Indices Fallback (Advanced Journalistic Metrics)
    if 'controversy_index' not in df.columns:
        pos = df['love_count'] + df['care_count']
        neg = df['angry_count']
        ec = np.minimum(pos, neg) / (np.maximum(pos, neg) + 1.0)
        dr_bounded = df['comment_count'] / (df['comment_count'] + df['total_reactions'] + 1.0)
        v = np.log10(df['comment_count'] + df['share_count'] + df['total_reactions'] + 1.0)
        df['controversy_index'] = ec * dr_bounded * v
        
    if 'sarcasm_index' not in df.columns:
        df['sarcasm_index'] = (df['haha_count'] + df['wow_count']) / (df['total_reactions'] + 1.0)

    # 1.4 Normalized Engagement Calculations (Rates per Follower)
    df['rel_spread'] = np.where((df['has_page_followers'] == 1) & (df['page_followers'] > 0), df['share_count'] / df['page_followers'], 0.0)
    df['rel_discussion'] = np.where((df['has_page_followers'] == 1) & (df['page_followers'] > 0), df['comment_count'] / df['page_followers'], 0.0)
    df['rel_like'] = np.where((df['has_page_followers'] == 1) & (df['page_followers'] > 0), df['like_count'] / df['page_followers'], 0.0)
    
    # Combined index columns name alias
    df['Outrage_Index'] = df['outrage_reaction_index']
    df['Amusement_Index'] = df['amusement_reaction_index']
    df['Empathy_Index'] = df['empathy_reaction_index']
    df['Approval_Index'] = df['approval_reaction_index']
    
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Lỗi khi đọc file enriched dataset: {e}")
    st.stop()


# ----------------------------------------------------
# 2. SIDEBAR FILTERS
# ----------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/facebook-new.png", width=60)
st.sidebar.title("Điều khiển Dashboard")
st.sidebar.write("---")

# 2.1 Outlier & Filter Strict Mode Toggle
outlier_mode = st.sidebar.selectbox(
    "🛡️ Chế độ lọc Outlier tương tác",
    options=["Tiêu chuẩn (Standard)", "Nghiêm ngặt (Strict - Loại bỏ Outliers)"],
    help="Chế độ Nghiêm ngặt kích hoạt bộ lọc loại bỏ các bài viết có tương tác đột biến/spam (usable_for_engagement_analysis_strict)",
    key="filter_outlier_mode"
)

# Apply outlier mode selection to df
if outlier_mode == "Nghiêm ngặt (Strict - Loại bỏ Outliers)":
    df_filtered_outliers = df_raw[df_raw['usable_for_engagement_analysis_strict'] == 1]
    outlier_status_text = "Đã lọc Outliers (Strict)"
else:
    df_filtered_outliers = df_raw
    outlier_status_text = "Tiêu chuẩn (Có Outliers)"

# 2.2 Topic Multi-select (Dynamic list)
all_topics = sorted(df_raw['topic_label_final'].dropna().unique())
selected_topics = st.sidebar.multiselect(
    "🏷️ Chọn Chủ đề hiển thị",
    options=all_topics,
    default=all_topics,
    help="Lọc các biểu đồ theo các chủ đề được chọn",
    format_func=lambda x: shorten_topic_name(x, include_code=True),
    key="filter_selected_topics"
)

# 2.3 Date range filter (For records with valid date metadata)
valid_dates = df_raw[df_raw['has_post_created_time'] == 1]['parsed_date'].dropna()
if not valid_dates.empty:
    min_date = valid_dates.min().date()
    max_value_date = valid_dates.max().date()
    
    date_range = st.sidebar.date_input(
        "📅 Khoảng thời gian đăng bài",
        value=(min_date, max_value_date),
        min_value=min_date,
        max_value=max_value_date,
        help="Lọc bài viết theo ngày tạo (chỉ áp dụng cho dòng có thông tin thời gian)",
        key="filter_date_range"
    )
    
    if len(date_range) != 2:
        st.sidebar.warning("Vui lòng chọn đầy đủ ngày bắt đầu và ngày kết thúc trên lịch.")
        st.stop()
        
    start_date, end_date = date_range
    
    # Filter dates
    df_filtered_dates = df_filtered_outliers[
        (df_filtered_outliers['parsed_date'].isna()) | 
        ((df_filtered_outliers['parsed_date'].dt.date >= start_date) & (df_filtered_outliers['parsed_date'].dt.date <= end_date))
    ]
else:
    df_filtered_dates = df_filtered_outliers

# 2.4 Min Reactions slider
st.sidebar.write("---")
min_reactions = st.sidebar.slider(
    "⚡ Tối thiểu tổng Reactions / bài",
    min_value=0, max_value=500, value=0, step=10,
    help="Lọc bỏ các bài viết có ít reaction hơn ngưỡng này (0 = không lọc)",
    key="filter_min_reactions"
)

laplace_alpha = st.sidebar.slider(
    "🔬 Độ nhạy Phân tích Thái độ (Làm mịn α)",
    min_value=0, max_value=20, value=5, step=1,
    help="α càng cao → các bài ít tương tác bị kéo về điểm trung tính 0 mạnh hơn. α=0 tương đương không làm mịn.",
    key="filter_laplace_alpha"
)
st.sidebar.caption(
    "🔬 **Hệ số làm mịn (Laplace α)** giúp điều chỉnh trọng số của các bài viết ít tương tác. "
    "Khi hệ số α tăng, các bài viết có ít phản hồi sẽ tự động được đưa về trạng thái trung tính (0) "
    "để tránh làm lệch các chỉ số chung của fanpage, giảm nhiễu dữ liệu hiệu quả."
)

# 2.5 Active filtering logic
if not selected_topics:
    st.warning("Vui lòng chọn ít nhất một chủ đề ở Sidebar!")
    st.stop()

df_filtered = df_filtered_dates[df_filtered_dates['topic_label_final'].isin(selected_topics)].copy()

# Apply new filters
if min_reactions > 0:
    df_filtered = df_filtered[df_filtered['total_reactions'] >= min_reactions]

# Tính lại polarity_score trên df_filtered với laplace_alpha từ sidebar
_sr_pos  = df_filtered['love_count'] + df_filtered['care_count']
_sr_neg  = df_filtered['angry_count'] + df_filtered['sad_count']
_sr_amb  = df_filtered['haha_count'] + df_filtered['wow_count']
_sr_all  = _sr_pos + _sr_neg + _sr_amb
_all_tot = _sr_all + df_filtered['like_count']
df_filtered['reaction_intensity'] = np.where(_all_tot > 0, _sr_all / _all_tot, 0.0)
_valence = (_sr_pos - _sr_neg) / (_sr_pos + _sr_neg + laplace_alpha + 1e-9)
df_filtered['polarity_score'] = df_filtered['reaction_intensity'] * _valence

# Check if empty
if df_filtered.empty:
    st.sidebar.warning("⚠️ Không có bài viết nào thỏa mãn bộ lọc hiện tại!")
    st.warning("⚠️ Không có bài viết nào thỏa mãn bộ lọc hiện tại! Vui lòng thay đổi cấu hình lọc bên Sidebar.")
    st.stop()

# Show current record count in sidebar
st.sidebar.markdown(f"**Trạng thái dữ liệu hiện tại:**")
st.sidebar.info(
    f"• Số bài viết: `{len(df_filtered):,}`\n"
    f"• Lọc tương tác: `{outlier_status_text}`\n"
    f"• Min Reactions: `≥ {min_reactions}`\n"
    f"• Nguồn: `TeamCrawl Labeled`"
)

st.sidebar.write("---")
if st.sidebar.button("🔄 Reset Bộ lọc (Clear Filters)", type="secondary"):
    for k in ["filter_outlier_mode", "filter_selected_topics", "filter_date_range", "filter_min_reactions", "filter_laplace_alpha"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()


# ----------------------------------------------------
# MAIN DASHBOARD APP LAYOUT
# ----------------------------------------------------
st.title("📰 Báo cáo Toàn cảnh: Social Media Topic Insights")
st.markdown("Ấn phẩm phân tích chuyên sâu các chủ đề mạng xã hội dựa trên nhãn chủ đề và phản ứng tương tác.")

st.warning(
    "**⚠️ Tuyên bố miễn trừ trách nhiệm (Disclaimer):**\n\n"
    "Dữ liệu được trình bày trong dashboard này được trích xuất từ một tập dữ liệu "
    "thu thập (crawl) tự động trong một khoảng thời gian và phạm vi giới hạn. "
    "Các thống kê, biểu đồ và nhận định dưới đây **chỉ phản ánh đặc tính của chính tập dữ liệu mẫu này**, "
    "và **không mang tính đại diện cho toàn bộ nền tảng mạng xã hội** hay xu hướng chung. "
    "Vui lòng cân nhắc giới hạn của phương pháp thu thập trước khi đưa ra kết luận."
)

# ====================================================
# EXECUTIVE SUMMARY SECTION (TOP LEVEL)
# ====================================================
# Calculate Insight Report dynamically
most_active_raw = df_filtered['topic_label_final'].value_counts().idxmax()
most_active_name = shorten_topic_name(most_active_raw, include_code=False)
most_active_pct = (df_filtered['topic_label_final'].value_counts().max() / len(df_filtered) * 100)

df_filtered_copy = df_filtered.copy()
df_filtered_copy['total_eng'] = df_filtered_copy['total_reactions'] + df_filtered_copy['comment_count'] + df_filtered_copy['share_count']
topic_eng_mean = df_filtered_copy.groupby('topic_label_final')['total_eng'].mean().reset_index()
if not topic_eng_mean.empty:
    best_eng_row = topic_eng_mean.sort_values(by='total_eng', ascending=False).iloc[0]
    best_eng_topic = shorten_topic_name(best_eng_row['topic_label_final'], include_code=False)
    best_eng_val = best_eng_row['total_eng']
else:
    best_eng_topic = "N/A"
    best_eng_val = 0
    
overall_avg_eng = df_filtered_copy['total_eng'].mean()

# Risks & Bottlenecks calculations
df_reactions_copy = df_filtered[df_filtered['usable_for_reaction_analysis'] == 1].copy()
if not df_reactions_copy.empty:
    topic_indices_rep = df_reactions_copy.groupby('topic_label_final').agg(
        avg_controversy=('controversy_index', 'mean'),
        avg_sarcasm=('sarcasm_index', 'mean')
    ).reset_index()
    
    if not topic_indices_rep.empty:
        worst_cont_row = topic_indices_rep.sort_values(by='avg_controversy', ascending=False).iloc[0]
        worst_cont_topic = shorten_topic_name(worst_cont_row['topic_label_final'], include_code=False)
        worst_cont_val = worst_cont_row['avg_controversy']
        
        worst_sarc_row = topic_indices_rep.sort_values(by='avg_sarcasm', ascending=False).iloc[0]
        worst_sarc_topic = shorten_topic_name(worst_sarc_row['topic_label_final'], include_code=False)
        worst_sarc_val = worst_sarc_row['avg_sarcasm'] * 100
    else:
        worst_cont_topic = "N/A"
        worst_cont_val = 0
        worst_sarc_topic = "N/A"
        worst_sarc_val = 0
else:
    worst_cont_topic = "N/A"
    worst_cont_val = 0
    worst_sarc_topic = "N/A"
    worst_sarc_val = 0

# 1. Dynamic Headline (Storytelling Box)
st.markdown(
    f'<div class="insight-box">'
    f'<b>Tâm điểm trong ngày:</b> Chủ đề <b>{most_active_name}</b> dẫn đầu về lượng bài viết '
    f'({most_active_pct:.1f}% tổng số bài). Trong khi đó, chủ đề <b>{best_eng_topic}</b> đang có hiệu suất tương tác cao nhất '
    f'với trung bình <b>{int(round(best_eng_val)):,}</b> tương tác/bài. '
    f'Về mặt rủi ro, <b>{worst_cont_topic}</b> ghi nhận chỉ số tranh cãi cao nhất ({worst_cont_val:.3f}) '
    f'và <b>{worst_sarc_topic}</b> tiềm ẩn nguy cơ mỉa mai lớn nhất ({worst_sarc_val:.1f}%). '
    f'</div>',
    unsafe_allow_html=True
)

# 2. Key Metrics Cards
kpis = st.columns(4)
total_posts = len(df_filtered)
total_engagement = (df_filtered['total_reactions'] + df_filtered['comment_count'] + df_filtered['share_count']).sum()
pages_count = df_filtered['page_name'].nunique()

# Calculate overall average engagement per post
avg_eng_post = total_engagement / total_posts if total_posts > 0 else 0
badge_html = f"<div style='font-size:11px; margin-top:5px; color:#1E8449;'>🟢 TB: <b>{int(round(avg_eng_post)):,}</b> tt / bài</div>"

# Calculate page productivity
avg_posts_per_page = total_posts / pages_count if pages_count > 0 else 0
badge_page_html = f"<div style='font-size:11px; margin-top:5px; color:#555;'>📊 TB <b>{avg_posts_per_page:,.1f}</b> bài / page</div>"

kpis[0].markdown(f"<div class='kpi-card'><div class='kpi-val'>{total_posts:,}</div><div class='kpi-label'>Tổng bài đăng</div></div>", unsafe_allow_html=True)
kpis[1].markdown(f"<div class='kpi-card'><div class='kpi-val'>{total_engagement:,}</div><div class='kpi-label'>Tổng tương tác</div>{badge_html}</div>", unsafe_allow_html=True)
kpis[2].markdown(f"<div class='kpi-card'><div class='kpi-val'>{pages_count:,}</div><div class='kpi-label'>Nguồn Fanpage</div>{badge_page_html}</div>", unsafe_allow_html=True)
kpis[3].markdown(f"<div class='kpi-card'><div class='kpi-val'>{most_active_name}</div><div class='kpi-label'>Chủ đề nóng nhất</div></div>", unsafe_allow_html=True)

# Jump to Threat Radar button / alert warning
if worst_cont_val >= 0.40 or worst_sarc_val >= 30.0:
    st.error(
        f"🔴 **PHÁT HIỆN RỦI RO CAO:** Chủ đề **{worst_cont_topic}** có Controversy Index trung bình ({worst_cont_val:.3f}) "
        f"hoặc chủ đề **{worst_sarc_topic}** có rủi ro mỉa mai ({worst_sarc_val:.1f}%) đang vượt ngưỡng cảnh báo. "
        f"Vui lòng chọn tab **🚨 2. Threat Radar (Rủi ro & Khủng hoảng)** phía dưới để điều tra nguồn phát tán và chi tiết bài viết."
    )

# Create the 4 main tabs representing the Editorial Workflow
tab_front, tab_threat, tab_audience, tab_editor = st.tabs([
    "🗞️ 1. The Front Page (Tổng quan)",
    "🚨 2. Threat Radar (Rủi ro & Khủng hoảng)",
    "📊 3. Audience Pulse (Hành vi & Tương tác)",
    "✨ 4. AI Content Simulator (Dự báo ML)"
])

# ----------------------------------------------------
# TAB 1: THE FRONT PAGE (TỔNG QUAN)
# ----------------------------------------------------
with tab_front:
    st.markdown("<h3 class='section-header'>🗞️ The Front Page (Tổng quan Trong Ngày)</h3>", unsafe_allow_html=True)
    
    # 1. Topic Distribution Chart (Full Width)
    topic_counts = df_filtered['topic_label_final'].value_counts().reset_index()
    topic_counts.columns = ['Topic', 'Count']
    
    if not topic_counts.empty:
        max_row = topic_counts.sort_values(by='Count', ascending=True).iloc[-1]
        max_topic = shorten_topic_name(max_row['Topic'], include_code=False)
        total_count = topic_counts['Count'].sum()
        pct = (max_row['Count'] / total_count * 100) if total_count > 0 else 0
        topic_dist_title = f"📰 {max_topic} thống trị thảo luận với {pct:.1f}% tổng số bài đăng"
    else:
        topic_dist_title = "Phân bổ Chủ đề Thảo luận (Topic Distribution)"
        
    st.markdown(f"<h4 style='text-align:center; font-family: Lora, Georgia, serif; font-size:15px; margin-top:10px;'>{topic_dist_title}</h4>", unsafe_allow_html=True)
    
    topic_counts['Topic'] = topic_counts['Topic'].apply(lambda x: shorten_topic_name(x, include_code=True))
    topic_counts = topic_counts.sort_values(by='Count', ascending=True)
    
    fig_topic_dist = px.bar(
        topic_counts,
        x='Count',
        y='Topic',
        orientation='h',
        text='Count',
        color='Count',
        color_continuous_scale='Blues',
        labels={'Count': 'Số lượng bài đăng', 'Topic': 'Chủ đề'}
    )
    fig_topic_dist.update_traces(textposition='outside')
    fig_topic_dist.update_layout(height=450, margin=dict(l=10, r=10, t=10, b=10))
    apply_editorial_theme(fig_topic_dist)
    st.plotly_chart(fig_topic_dist, use_container_width=True)
    
    st.write("---")
    
    # 2. Highlights & Risks in two equal columns (Perfect balance!)
    col_light, col_dark = st.columns(2)
    
    with col_light:
        card_hl = f"""
        <div class='editorial-brief-card'>
            <h5 style='color: #1E8449; font-family: Lora, Georgia, serif; font-size: 15px; margin-top: 0; margin-bottom: 10px;'>🟢 Điểm sáng Dữ liệu (Highlights)</h5>
            <ul style='margin-bottom: 0; padding-left: 20px; font-family: "Inter", sans-serif; font-size: 13px; line-height: 1.6; color: #1C1C1C;'>
                <li style='margin-bottom: 8px;'><b>Chủ đề dẫn đầu về lượng bài đăng</b> <i>(trong tập crawl)</i>: <b>{most_active_name}</b> chiếm <b>{most_active_pct:.1f}%</b> tổng số bài — phản ánh phạm vi thu thập dữ liệu hiện tại.</li>
                <li style='margin-bottom: 8px;'><b>Chủ đề có tương tác cao nhất</b> <i>(đã lọc)</i>: <b>{best_eng_topic}</b> đạt trung bình <b>{int(round(best_eng_val)):,}</b> tương tác/bài (reactions + comments + shares), vượt trội so với trung bình toàn dataset là <b>{int(round(overall_avg_eng)):,}</b>.</li>
                <li style='margin-bottom: 0;'><b>Mức độ đồng thuận dư luận</b>: Tỷ lệ cảm xúc tích cực ở mức ổn định, các nội dung nhận được sự đồng thuận và phản hồi tương đối ôn hòa từ cộng đồng mạng.</li>
            </ul>
        </div>
        """
        st.markdown("\n".join(line.strip() for line in card_hl.split("\n")), unsafe_allow_html=True)
        
    with col_dark:
        card_rk = f"""
        <div class='editorial-brief-card'>
            <h5 style='color: #D90429; font-family: Lora, Georgia, serif; font-size: 15px; margin-top: 0; margin-bottom: 10px;'>🔴 Điểm tối & Rủi ro (Risks & Bottlenecks)</h5>
            <ul style='margin-bottom: 0; padding-left: 20px; font-family: "Inter", sans-serif; font-size: 13px; line-height: 1.6; color: #1C1C1C;'>
                <li style='margin-bottom: 8px;'><b>Điểm nóng tranh cãi</b> <i>(đã lọc)</i>: Chủ đề <b>{worst_cont_topic}</b> ghi nhận Controversy Index trung bình cao nhất ở mức <b>{worst_cont_val:.3f}</b>, thể hiện độ phân cực ý kiến sâu sắc kết hợp thảo luận dày đặc.</li>
                <li style='margin-bottom: 8px;'><b>Phản hồi châm biếm nổi bật</b>: Chủ đề <b>{worst_sarc_topic}</b> có tỷ lệ Haha/Wow cao nhất ở mức <b>{worst_sarc_val:.1f}%</b> trên tổng số reactions, báo hiệu xu hướng chế giễu hoặc hoài nghi từ dư luận.</li>
                <li style='margin-bottom: 0;'><b>Hiệu suất lệch múi giờ</b>: Ghi nhận sự chênh lệch lớn về lượng tương tác trung vị theo khung giờ đăng bài, phản ánh hành vi tiếp nhận thông tin không đồng đều của độc giả.</li>
            </ul>
        </div>
        """
        st.markdown("\n".join(line.strip() for line in card_rk.split("\n")), unsafe_allow_html=True)

# ----------------------------------------------------
# GLOBAL REACTION AND PERCENTILE DATA PREPARATION
# ----------------------------------------------------
MIN_REACTIONS_THRESHOLD = 10
df_reactions = df_filtered[
    (df_filtered['usable_for_reaction_analysis'] == 1) & 
    (df_filtered['total_reactions'] >= MIN_REACTIONS_THRESHOLD)
].copy()

if not df_reactions.empty:
    # Calculate percentile ranks for metrics display
    for col in ['total_reactions', 'Outrage_Index', 'Amusement_Index']:
        if col in df_reactions.columns:
            df_reactions[f'{col}_percentile'] = (
                df_reactions[col].rank(pct=True) * 100
            ).round(1)
            
    # Calculate Total_Engagement and its percentile rank for Virality Ledger
    df_reactions['Total_Engagement'] = df_reactions['total_reactions'] + df_reactions['comment_count'] + df_reactions['share_count']
    df_reactions['Total_Engagement_percentile'] = (
        df_reactions['Total_Engagement'].rank(pct=True) * 100
    ).round(1)
    
    # Calculate normalized engagement per 100k followers for Virality Ledger
    df_reactions['engagement_per_100k'] = np.where(
        (df_reactions['has_page_followers'] == 1) & (df_reactions['page_followers'] > 0),
        (df_reactions['Total_Engagement'] / df_reactions['page_followers'] * 100000).round(1),
        0.0
    )


# ----------------------------------------------------
# TAB 2: THREAT RADAR (RỦI RO & KHỦNG HOẢNG)
# ----------------------------------------------------
with tab_threat:
    st.markdown("<h3 class='section-header'>🚨 Threat Radar (Phân tích Rủi ro & Khủng hoảng)</h3>", unsafe_allow_html=True)
    st.write("Giám sát chỉ số tranh cãi, châm biếm, phân cực dư luận và dấu hiệu spam/seeding trên mạng xã hội.")
    
    if df_reactions.empty:
        st.warning("Không có dữ liệu thỏa mãn bộ lọc có ít nhất 10 reactions và cờ usable_for_reaction_analysis == 1.")
    else:
        sub_tab_sarcasm, sub_tab_controversy, sub_tab_bias = st.tabs([
            "🚨 Cảnh báo Châm biếm (Sarcasm Alert)",
            "⚖️ Chỉ số Tranh cãi (Controversy Index)",
            "⚠️ Phân tích Bias & Spam (Bias & Spam Detection)"
        ])
        
        # ----------------------------------------------------
        # SUB-TAB 2A: SARCASM ALERT
        # ----------------------------------------------------
        with sub_tab_sarcasm:
            st.markdown("<h4 class='editorial-heading'>🚨 Phân tích nội dung châm biếm / giải trí & Cảnh báo Khủng hoảng ngầm</h4>", unsafe_allow_html=True)
            st.write("Trích xuất các cụm từ nổi bật từ nhóm bài viết có chỉ số Haha đột biến (top 10% Amusement_Index) để hiểu chủ đề dư luận cợt nhả.")

            threshold = df_reactions['Amusement_Index'].quantile(0.9)
            df_sarcasm = df_reactions[df_reactions['Amusement_Index'] >= threshold]

            if not df_sarcasm.empty and 'caption' in df_sarcasm.columns:
                keywords = extract_sarcasm_keywords(df_sarcasm['caption'], top_n=6)

                col_alert1, col_alert2 = st.columns([2, 3])

                with col_alert1:
                    st.error(
                        f"**Có {len(df_sarcasm)} bài viết** bị cảnh báo châm biếm / cợt nhả "
                        f"(Sarcasm) với lượng Haha đột biến."
                    )

                with col_alert2:
                    if keywords:
                        st.markdown("**Từ khóa chính đang bị thảo luận:**")
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
            st.markdown("<h5 class='editorial-heading'>🚨 Cảnh báo Khủng hoảng ngầm (Sarcasm Alerts) trên các Chủ đề Nghiêm túc</h5>", unsafe_allow_html=True)
            st.markdown("<p style='font-size:12px; font-style:italic; color:#555;'>Những bài đăng nghiêm túc (Pháp luật, Chính trị, Y tế, Thiên tai, Môi trường) nhận lượng thả Haha/Wow bất thường (>35%).</p>", unsafe_allow_html=True)
            
            serious_topics_prefixes = ['T01', 'T03', 'T07', 'T08', 'T09']
            df_serious = df_reactions[
                df_reactions['topic_label_final'].astype(str).str[:3].isin(serious_topics_prefixes)
            ].copy()
            
            sarc_alerts = df_serious[(df_serious['sarcasm_index'] > 0.35) & (df_serious['total_reactions'] >= 10)].nlargest(5, 'sarcasm_index')
            
            if sarc_alerts.empty:
                st.success("✅ Hiện tại không phát hiện khủng hoảng mỉa mai/châm biếm nào trên các chủ đề nghiêm túc.")
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
                ('avg_controversy', 'controversy_pct'),
                ('avg_sarcasm',     'sarcasm_pct'),
                ('avg_approval',    'approval_pct'),
                ('avg_empathy',     'empathy_pct'),
            ]:
                topic_indices[_alias] = (topic_indices[_col].rank(pct=True) * 100).round(0).astype(int)

            # 1. Tranh cãi nhất
            top_cont = topic_indices.sort_values(by='avg_controversy', ascending=False).iloc[0]
            lead_cols[0].markdown(
                f"<div class='kpi-card' style='border-top: 2px solid #1C1C1C;'>"
                f"<div class='kpi-val'>{top_cont['avg_controversy']:.3f}</div>"
                f"<div class='kpi-label'>💥 Tranh cãi nhất</div>"
                f"<div style='font-size:11px; color:#D90429; margin-top:3px;'>Top {100 - top_cont['controversy_pct']}% so với các chủ đề khác</div>"
                f"<div style='font-size:12px; font-weight:bold; margin-top:3px; color:#555;'>{shorten_topic_name(top_cont['topic_label_final'])}</div>"
                f"</div>", unsafe_allow_html=True
            )

            # 2. Tỷ lệ Haha/Wow cao nhất
            top_sarc = topic_indices.sort_values(by='avg_sarcasm', ascending=False).iloc[0]
            lead_cols[1].markdown(
                f"<div class='kpi-card' style='border-top: 2px solid #1C1C1C;'>"
                f"<div class='kpi-val'>{top_sarc['avg_sarcasm'] * 100:.1f}%</div>"
                f"<div class='kpi-label'>😆 Tỷ lệ Haha/Wow cao nhất</div>"
                f"<div style='font-size:11px; color:#D90429; margin-top:3px;'>Top {100 - top_sarc['sarcasm_pct']}% so với các chủ đề khác</div>"
                f"<div style='font-size:12px; font-weight:bold; margin-top:3px; color:#555;'>{shorten_topic_name(top_sarc['topic_label_final'])}</div>"
                f"</div>", unsafe_allow_html=True
            )

            # 3. Đồng thuận nhất
            top_app = topic_indices.sort_values(by='avg_approval', ascending=False).iloc[0]
            lead_cols[2].markdown(
                f"<div class='kpi-card' style='border-top: 2px solid #1C1C1C;'>"
                f"<div class='kpi-val'>{top_app['avg_approval'] * 100:.1f}%</div>"
                f"<div class='kpi-label'>👍 Đồng thuận nhất</div>"
                f"<div style='font-size:11px; color:#1E8449; margin-top:3px;'>Top {100 - top_app['approval_pct']}% so với các chủ đề khác</div>"
                f"<div style='font-size:12px; font-weight:bold; margin-top:3px; color:#555;'>{shorten_topic_name(top_app['topic_label_final'])}</div>"
                f"</div>", unsafe_allow_html=True
            )

            # 4. Đồng cảm nhất
            top_emp = topic_indices.sort_values(by='avg_empathy', ascending=False).iloc[0]
            lead_cols[3].markdown(
                f"<div class='kpi-card' style='border-top: 2px solid #1C1C1C;'>"
                f"<div class='kpi-val'>{top_emp['avg_empathy'] * 100:.1f}%</div>"
                f"<div class='kpi-label'>🤗 Đồng cảm nhất</div>"
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
                text="🚨 <b>Vùng Phẫn nộ / Khủng hoảng</b><br><span style='font-size:9px; font-weight:normal;'>Đề xuất: Giãn đăng bài, trực bình luận</span>",
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
                text="⚖️ <b>Vùng Tranh biện / Đa chiều</b><br><span style='font-size:9px; font-weight:normal;'>Đề xuất: Đưa tin khách quan, đa chiều</span>",
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
                text="✅ <b>Vùng An toàn / Tích cực</b><br><span style='font-size:9px; font-weight:normal;'>Đề xuất: Duy trì tần suất xuất bản</span>",
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
                text="💬 <b>Vùng Ổn định / Ôn hòa</b><br><span style='font-size:9px; font-weight:normal;'>Đề xuất: Theo dõi định kỳ, tương tác nhẹ</span>",
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


# ----------------------------------------------------
# TAB 3: AUDIENCE PULSE (HÀNH VI & TƯƠNG TÁC)
# ----------------------------------------------------
with tab_audience:
    st.markdown("<h3 class='section-header'>📊 Audience Pulse (Hành vi & Tương tác)</h3>", unsafe_allow_html=True)
    st.write("Khảo sát hành vi độc giả, cơ cấu reaction chi tiết, mức độ lan truyền và phân tích thời gian đăng bài để theo dõi hiệu quả tương tác.")
    
    if df_reactions.empty:
        st.warning("Không có dữ liệu thỏa mãn bộ lọc có ít nhất 10 reactions và cờ usable_for_reaction_analysis == 1.")
    else:
        # Reduced sub-tabs to 3!
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

            # MOVED DETAIL CHARTS FROM TAB 1
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
                
                with t_col1:
                    # Calculations
                    MIN_SAMPLE_CELL = 15
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
                    # Scale heatmap height to 450 to avoid compressed texts
                    fig_heatmap.update_layout(height=450, margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(tickmode='linear', tick0=0, dtick=2))
                    apply_editorial_theme(fig_heatmap)
                    st.plotly_chart(fig_heatmap, use_container_width=True)
                    st.caption(
                        "⚠️ Lưu ý phương pháp: Biểu đồ này chỉ tính trên các bài viết có thông tin "
                        "thời gian đăng hợp lệ. Trong tập dữ liệu hiện tại, 27.37% bài viết "
                        "(khoảng 3.226 bài) không có timestamp do giới hạn của pipeline thu thập. "
                        "Các xu hướng trên đây phản ánh hành vi của 72.63% còn lại và nên được "
                        "xem như tín hiệu định hướng, không phải kết luận tuyệt đối."
                    )
                    
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
                    st.caption(
                        "⚠️ Lưu ý phương pháp: Biểu đồ này chỉ tính trên các bài viết có thông tin "
                        "thời gian đăng hợp lệ. Trong tập dữ liệu hiện tại, 27.37% bài viết "
                        "(khoảng 3.226 bài) không có timestamp do giới hạn của pipeline thu thập. "
                        "Các xu hướng trên đây phản ánh hành vi của 72.63% còn lại và nên được "
                        "xem như tín hiệu định hướng, không phải kết luận tuyệt đối."
                    )
                    
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
                    top3 = reliable_hours.nlargest(3, 'median_reactions')[['post_created_hour','median_reactions','posts_count']]
                    for rank, (_, row) in enumerate(top3.iterrows(), 1):
                        medal = ['🥇','🥈','🥉'][rank - 1]
                        st.markdown(f"{medal} **Giờ {int(row['post_created_hour'])}h** — `{row['median_reactions']:.0f}` reactions Trung vị ({int(row['posts_count'])} bài)")

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

# ----------------------------------------------------
# TAB 4: AI CONTENT SIMULATOR (DỰ BÁO ML)
# ----------------------------------------------------
with tab_editor:
    st.markdown("<h3 class='section-header'>✨ 4. AI Content Simulator (Dự báo ML)</h3>", unsafe_allow_html=True)
    st.write(
        "Nhập nội dung bài đăng dự kiến của bạn và chọn mô hình mong muốn. Hệ thống sẽ dự đoán chủ đề "
        "và đối chiếu với dữ liệu lịch sử để đánh giá các chỉ số rủi ro."
    )

    mapping_dict = load_taxonomy_mapping()
    
    # Dropdown chọn model
    selected_model = st.selectbox(
        "Dropdown chọn model (Select Model):",
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
                        X = vectorizer.transform([user_input_demo])
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
                            pred_label_name, conf_str, pred_label_id, probs, err = predict_transformer(dl_name, user_input_demo, mapping_dict)
                        
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
                    st.info(user_input_demo)

                    # Report download
                    report_text = f"""# BÁO CÁO PHÂN TÍCH GIẢ LẬP NỘI DUNG (PREDICTIVE SIMULATION REPORT)
-------------------------------------------------------------
Nội dung bài viết dự thảo:
"{user_input_demo}"

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

                    X = vectorizer.transform([user_input_demo])
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
                        pred_label_name, conf_str, pred_label_id, _, err = predict_transformer(mname, user_input_demo, mapping_dict)
                    
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

                # Sort and display comparison table of all 7 models using ProgressColumn
                results_sorted = sorted(results, key=lambda x: x["F1_val"], reverse=True)
                df_results = pd.DataFrame(results_sorted)
                df_results['Độ chính xác (F1)'] = df_results['F1_val']
                df_display = df_results.rename(columns={
                    "Model": "Mô hình",
                    "Loại": "Phân loại",
                    "Nhãn dự đoán": "Chủ đề dự báo",
                    "Confidence": "Độ tin cậy",
                    "Ghi chú": "Mô tả chi tiết"
                })
                display_cols = ["Mô hình", "Phân loại", "Chủ đề dự báo", "Độ tin cậy", "Độ chính xác (F1)", "Mô tả chi tiết"]
            
                st.markdown("#### 🎯 Kết quả Phân loại từ Model Zoo (7 Models)")
                st.dataframe(
                    df_display[display_cols],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Độ chính xác (F1)": st.column_config.ProgressColumn(
                            "Độ chính xác (F1)",
                            help="Test Macro F1-Score của mô hình",
                            format="%.4f",
                            min_value=0.0,
                            max_value=1.0
                        )
                    }
                )

                # Find consensus majority (only over actual predictions, not fallbacks)
                valid_predictions = [
                    r for r in results 
                    if "Fallback" not in r["Nhãn dự đoán"] 
                    and "Lỗi" not in r["Nhãn dự đoán"] 
                    and "Không chạy" not in r["Confidence"]
                ]
            
                labels_predicted = [r["Nhãn dự đoán"] for r in valid_predictions]
                label_ids_predicted = [r["label_id"] for r in valid_predictions]
            
                if labels_predicted:
                    majority_label = max(set(labels_predicted), key=labels_predicted.count)
                    majority_id = max(set(label_ids_predicted), key=label_ids_predicted.count) if label_ids_predicted else majority_label[:3]
                    consensus_count = labels_predicted.count(majority_label)
                    total_valid_models = len(labels_predicted)
                
                    if consensus_count == total_valid_models:
                        st.success(f"✅ Tất cả {total_valid_models} mô hình đồng thuận dự đoán: **{majority_label}**")
                    else:
                        st.warning(f"⚠️ Các mô hình chưa đồng thuận hoàn toàn. Nhãn phổ biến nhất: **{majority_label}** ({consensus_count}/{total_valid_models} mô hình)")

                # Disclaimer right under consensus results
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
                st.info(user_input_demo)

                # Build plain text report format
                report_text = f"""# BÁO CÁO PHÂN TÍCH GIẢ LẬP NỘI DUNG (PREDICTIVE SIMULATION REPORT)
-------------------------------------------------------------
Nội dung bài viết dự thảo:
"{user_input_demo}"
 
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


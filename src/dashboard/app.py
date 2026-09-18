import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import time
import os

import importlib
import components.front_page
importlib.reload(components.front_page)
from components.front_page import render_front_page

from components.nsw_insights import render_nsw_insights
from components.threat_radar import render_threat_radar
from components.audience_pulse import render_audience_pulse
from components.content_simulator import render_content_simulator
import json

# ----------------------------------------------------
# CONFIG-AS-CODE LOAD (Separating config from logic)
# ----------------------------------------------------
_base_dir = os.path.dirname(os.path.abspath(__file__))
_config_path = os.path.join(_base_dir, "config.json")
_config = {}
if os.path.exists(_config_path):
    try:
        with open(_config_path, "r", encoding="utf-8") as _f:
            _config = json.load(_f)
    except Exception:
        pass

MODEL_PATHS_CONFIG = _config.get("MODEL_PATHS_CONFIG", {
    "traditional_registry": "08_Modeling_Results/traditional_ml_hpo_deep/model_zoo/model_registry.json",
    "mBERT": "08_Modeling_Results/mbert_best_model_kb4",
    "PhoBERT": "08_Modeling_Results/phobert_kb4_best_model",
    "XLM-R": "08_Modeling_Results/xlmr_best_model_kb5"
})

DASHBOARD_PARAMS = _config.get("DASHBOARD_PARAMS", {
    "min_reactions_threshold": 10,
    "default_laplace_alpha": 5,
    "controversy_warning_threshold": 0.40,
    "sarcasm_warning_threshold": 30.0,
    "raw_data_path": "../report/Master_Facebook_News_Posts_TeamCrawl_Labeled.csv",
    "enriched_data_path": "Public_Response_Streamlit_Enriched.csv"
})


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
    registry_rel = MODEL_PATHS_CONFIG.get("traditional_registry")
    registry_path = os.path.join(base_dir, registry_rel)
    
    if not os.path.exists(registry_path):
        return None, None, None, None, f"Registry file not found at {registry_rel}"
        
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
        
        # Xác định thiết bị chạy mô hình
        # MPS (Apple Silicon GPU) bị tắt chủ động vì một số toán tử Transformer
        # chưa được PyTorch hỗ trợ đầy đủ trên MPS, dẫn đến Segmentation Fault.
        # PYTORCH_ENABLE_MPS_FALLBACK=1 là biện pháp dự phòng nhưng không đủ
        # cho toàn bộ kiến trúc Transformer — an toàn nhất là chạy trên CPU.
        import os as _os
        _os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
        if torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"  # MPS bị bỏ qua có chủ đích để tránh crash Segfault
            
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        model = AutoModelForSequenceClassification.from_pretrained(
            model_dir,
            torch_dtype=torch.float32  # float32 tránh lỗi dtype không tương thích
        )
        model.to(device)
        model.eval()
        return model, tokenizer, device, None
    except Exception as e:
        return None, None, None, str(e)



def predict_transformer(model_name, text, mapping_dict):
    model_dir_rel = MODEL_PATHS_CONFIG.get(model_name)
    if not model_dir_rel:
        return None, None, None, None, f"Mô hình {model_name} chưa được cấu hình."
        
    base_dir = os.path.dirname(__file__)
    model_dir = os.path.join(base_dir, model_dir_rel)
    
    if not os.path.exists(model_dir):
        return None, None, None, None, (
            f"⚠️ Thư mục checkpoint của mô hình {model_name} không tìm thấy tại: `{model_dir_rel}`.\n\n"
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
# 1. LOAD DATA & REPRODUCIBLE PREPROCESSING PIPELINE
# ----------------------------------------------------
@st.cache_data
def load_data(include_t18=False, epsilon=1e-5):
    from data_loader import clean_and_enrich_data
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    raw_rel = DASHBOARD_PARAMS.get("raw_data_path", "../report/Master_Facebook_News_Posts_TeamCrawl_Labeled.csv")
    enriched_rel = DASHBOARD_PARAMS.get("enriched_data_path", "Public_Response_Streamlit_Enriched.csv")
    
    raw_path = os.path.join(base_dir, raw_rel)
    enriched_path = os.path.join(base_dir, enriched_rel)
    
    # Nếu bật T18 hoặc không tìm thấy file Enriched, chạy pipeline trực tiếp từ Raw
    if include_t18 or not os.path.exists(enriched_path):
        if os.path.exists(raw_path):
            df_raw_csv = pd.read_csv(raw_path, low_memory=False)
            df = clean_and_enrich_data(df_raw_csv, include_t18=include_t18)
        else:
            if os.path.exists(enriched_path):
                df = pd.read_csv(enriched_path, low_memory=False)
            else:
                raise FileNotFoundError(f"Không tìm thấy tệp raw ({raw_rel}) hoặc enriched ({enriched_rel})")
    else:
        # Load nhanh tệp enriched đã lưu
        df = pd.read_csv(enriched_path, low_memory=False)
        
    # 1.1 Data Type Conversion & Parsing
    count_cols = [
        'like_count', 'love_count', 'haha_count', 'wow_count', 
        'sad_count', 'angry_count', 'care_count', 'sorry_count', 
        'total_reactions', 'share_count', 'comment_count'
    ]
    for col in count_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
    if 'page_followers' in df.columns:
        df['page_followers'] = pd.to_numeric(df['page_followers'], errors='coerce').fillna(0).astype(int)
        
    if 'post_created_date' in df.columns:
        df['parsed_date'] = pd.to_datetime(df['post_created_date'], errors='coerce')
        if 'parsed_date' in df.columns:
            mask_2026 = (df['parsed_date'].dt.year == 2026) & df['parsed_date'].notna()
            df.loc[mask_2026, 'parsed_date'] = df.loc[mask_2026, 'parsed_date'] - pd.DateOffset(years=2)
            df['post_created_date'] = df['parsed_date'].dt.strftime('%Y-%m-%d')
        
    # 1.2 Controversy & Sarcasm Indices Fallback (Advanced Journalistic Metrics)
    if 'controversy_index' not in df.columns:
        pos = df['love_count'] + df['care_count']
        neg = df['angry_count']
        ec = np.minimum(pos, neg) / (np.maximum(pos, neg) + 1.0)
        dr_bounded = df['comment_count'] / (df['comment_count'] + df['total_reactions'] + 1.0)
        v = np.log10(df['comment_count'] + df['share_count'] + df['total_reactions'] + 1.0)
        df['controversy_index'] = ec * dr_bounded * v
        
    if 'sarcasm_index' not in df.columns:
        df['sarcasm_index'] = (df['haha_count'] + df['wow_count']) / (df['total_reactions'] + 1.0)

    # 1.3 Normalized Engagement Calculations (Rates per Follower)
    df['rel_spread'] = np.where((df['has_page_followers'] == 1) & (df['page_followers'] > 0), df['share_count'] / df['page_followers'], 0.0)
    df['rel_discussion'] = np.where((df['has_page_followers'] == 1) & (df['page_followers'] > 0), df['comment_count'] / df['page_followers'], 0.0)
    df['rel_like'] = np.where((df['has_page_followers'] == 1) & (df['page_followers'] > 0), df['like_count'] / df['page_followers'], 0.0)
    
    # Combined index columns name alias
    df['Outrage_Index'] = df['outrage_reaction_index']
    df['Amusement_Index'] = df['amusement_reaction_index']
    df['Empathy_Index'] = df['empathy_reaction_index']
    df['Approval_Index'] = df['approval_reaction_index']
    
    df['caption_normalized'] = df['caption'].fillna('').astype(str) if 'caption' in df.columns else ''
    df['nsw_count'] = 0
    df['nsw_words'] = [[] for _ in range(len(df))]
        
    return df


# ----------------------------------------------------
# 2. SIDEBAR FILTERS
# ----------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/facebook-new.png", width=60)
st.sidebar.title("Cấu hình Tham số Hệ thống")

# 2.0 T18 Checkbox to control preprocessing pipeline dynamically on startup
include_t18 = st.sidebar.checkbox(
    "Hiển thị dữ liệu bao gồm cả T18",
    value=False,
    help="Bao gồm cả các bài viết thuộc nhãn kỹ thuật T18 (Other Unclear) trong phân tích và tái lập dữ liệu.",
    key="include_t18_checkbox"
)

try:
    df_raw = load_data(include_t18=include_t18)
except Exception as e:
    st.error(f"Lỗi khi đọc file enriched dataset: {e}")
    st.stop()

# Dynamic Data Audit description depending on T18 status
if include_t18:
    data_caption = f"📊 **Minh bạch Dữ liệu:** Tập dữ liệu phân tích gồm {len(df_raw):,} mẫu (đã bao gồm nhãn kỹ thuật T18 - Other Unclear)."
else:
    data_caption = f"📊 **Minh bạch Dữ liệu:** Tập dữ liệu phân tích gồm {len(df_raw):,} mẫu (đã loại trừ các mẫu thuộc nhãn kỹ thuật T18 - Other Unclear)."

st.sidebar.caption(
    f"{data_caption} Các phân tích tương tác sâu được lọc nghiêm ngặt qua hệ thống cờ `usable_for_reaction_analysis`."
)
st.sidebar.write("---")

# 2.0.1 Developer / Audit Mode Toggle
st.sidebar.markdown("**⚙️ Chế độ hiển thị**")
audit_mode = st.sidebar.toggle(
    "🔬 Developer / Audit Mode",
    value=False,
    help="Bật để hiển thị Tab 5 (Data Preprocessing & Noise Analysis) và chạy ViSoLex NSW Normalization trên toàn bộ dataset. Tắt để giao diện gọn hơn.",
    key="audit_mode_toggle"
)
st.sidebar.write("---")

# 2.1 Outlier & Filter Strict Mode Toggle
outlier_mode = st.sidebar.selectbox(
    "🛡️ Chế độ lọc Outlier tương tác",
    options=["Tiêu chuẩn (Standard)", "Nghiêm ngặt (Strict - Loại bỏ Outliers)"],
    help="Chế độ Nghiêm ngặt kích hoạt bộ lọc loại bỏ các bài viết có tương tác đột biến/spam (usable_for_engagement_analysis_strict)",
    key="filter_outlier_mode"
)
st.sidebar.caption("💡 *Chế độ Nghiêm ngặt: Loại bỏ các bài viết có tương tác cao đột biến (Outliers) bằng phương pháp IQR kết hợp kiểm định bài đăng.*")

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
    "🏷️ Phạm vi Phân loại Chủ đề (Topic Taxonomy)",
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

default_alpha = DASHBOARD_PARAMS.get("default_laplace_alpha", 5)
laplace_alpha = st.sidebar.slider(
    "🔬 Độ nhạy Phân tích Thái độ (Làm mịn α)",
    min_value=0, max_value=20, value=default_alpha, step=1,
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
# 2.4 METHODOLOGY & RATIONALE
# ----------------------------------------------------
METHODOLOGY_MD = r"""
**Cơ sở Phương pháp luận:** Hệ thống đo lường được kế thừa từ nghiên cứu của Pratama (2022) về việc sử dụng siêu dữ liệu (Special Reactions) làm "biến đại diện" (Proxy signals) cho cảm xúc văn bản. Nhóm đã thực hiện **Hiệu chỉnh Văn hóa (Cultural Context Adaptation)** cho Facebook Việt Nam: chuyển biểu tượng *Care* (Thương thương) sang nhóm Tích cực, trong khi *Haha* vẫn giữ ở nhóm Tiêu cực (đại diện cho sự mỉa mai).

**Quy ước Biến cơ sở:**
* Tương tác tích cực ($SR^{+}$): Love, Care.
* Tương tác tiêu cực ($SR^{-}$): Haha, Angry, Sad, Wow.
* Tổng tương tác đặc biệt ($\sum SR$): $SR^{+} + SR^{-}$
* Tổng toàn bộ tương tác ($\sum All$): $\sum SR + Like$

---

### 1. Thước đo chính: Độ phân cực dư luận (Polarity)
Đánh giá xu hướng và mức độ gay gắt của dư luận thông qua hệ thống đo lường kép:

* **Cường độ (Intensity):** $I = \frac{\sum SR}{\sum All}$ 
(Đo lường mức độ quan tâm/bức xúc sâu sắc của dư luận đối với bài đăng thay vì thói quen "thả Like dạo").
* **Hóa trị (Valence):** $V = \frac{SR^{+} - SR^{-}}{SR^{+} + SR^{-} + \alpha}$ 
(Xác định chiều hướng cảm xúc. *Lưu ý: Dashboard áp dụng thêm hệ số làm mịn Laplace $\alpha$ để chống nhiễu cho các bài viết có quá ít tương tác*).
* **Độ phân cực (Polarity):** $P = I \times V$ (Giá trị từ -1 đến 1).

---

### 2. Thước đo thành phần: Phân tách Sắc thái (Sub-metrics)
Bóc tách siêu dữ liệu thành các chỉ số chuyên sâu nhằm phân tích bối cảnh truyền thông:

* **Chỉ số Phẫn nộ (Outrage Index):** $\frac{Angry}{\sum All}$
*(Đánh giá mức độ nghiêm trọng của khủng hoảng, bức xúc).*
* **Chỉ số Giải trí / Cợt nhả (Amusement Index):** $\frac{Haha}{\sum All}$
*(Phản ánh thái độ mỉa mai, cười trừ của cộng đồng. Tỷ lệ Haha cao đi kèm tin tức nghiêm túc thường biểu thị sự châm biếm).*
* **Chỉ số Đồng cảm (Empathy Index):** $\frac{Sad + Care}{\sum All}$
*(Đo lường lòng trắc ẩn. Sự kết hợp giữa sắc thái xoa dịu (Care) và buồn bã (Sad) đại diện cho mức độ đồng cảm chung của xã hội).*
* **Chỉ số Tích cực (Approval Index):** $\frac{Like + Love}{\sum All}$
*(Đo lường sự tự hào, đồng tình và đón nhận thông tin).*
"""

st.sidebar.write("---")
with st.sidebar.expander("📚 Cơ sở Phương pháp luận (Methodology)"):
    st.markdown(METHODOLOGY_MD)


# ----------------------------------------------------
# MAIN DASHBOARD APP LAYOUT
# ----------------------------------------------------
st.title("📰 Báo cáo Toàn cảnh: Social Media Topic Insights")
st.markdown("Ấn phẩm phân tích chuyên sâu các chủ đề mạng xã hội dựa trên nhãn chủ đề và phản ứng tương tác.")

st.warning(
    "**⚠️ Lưu ý Học thuật (Disclaimer):**\n\n"
    "Trong hệ thống này, các tương tác (Reactions, Comments, Shares) được sử dụng làm **tín hiệu đại diện (Proxy Signals)** ở mức tổng hợp nhằm phân tích sự khác biệt giữa các chủ đề, không mang ý nghĩa là nhãn cảm xúc tuyệt đối (Ground-truth Sentiment) của từng cá nhân."
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
    f'<b>Tóm tắt Đặc trưng Tập Dữ liệu Mẫu:</b> Chủ đề <b>{most_active_name}</b> chiếm tỷ trọng cao nhất trong cấu trúc thảo luận '
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
kpis[3].markdown(f"<div class='kpi-card'><div class='kpi-val'>{most_active_name}</div><div class='kpi-label'>Mật độ bài đăng cao nhất</div></div>", unsafe_allow_html=True)

# Jump to Threat Radar button / alert warning using warning thresholds from config parameters
warn_cont = DASHBOARD_PARAMS.get("controversy_warning_threshold", 0.40)
warn_sarc = DASHBOARD_PARAMS.get("sarcasm_warning_threshold", 30.0)
if worst_cont_val >= warn_cont or worst_sarc_val >= warn_sarc:
    st.error(
        f"🔴 **PHÁT HIỆN RỦI RO CAO:** Chủ đề **{worst_cont_topic}** có Controversy Index trung bình ({worst_cont_val:.3f}) "
        f"hoặc chủ đề **{worst_sarc_topic}** có rủi ro mỉa mai ({worst_sarc_val:.1f}%) đang vượt ngưỡng cảnh báo. "
        f"Vui lòng chọn tab **🚨 2. Threat Radar (Rủi ro & Khủng hoảng)** phía dưới để điều tra nguồn phát tán và chi tiết bài viết."
    )

# Create tabs: 5 tabs when Audit Mode is on, 4 tabs otherwise
if audit_mode:
    tab_front, tab_threat, tab_audience, tab_editor, tab_normalize = st.tabs([
        "🗞️ 1. The Front Page (Tổng quan)",
        "🚨 2. Phân tích Phân cực & Xung đột Dư luận (Controversy & Polarity)",
        "📊 3. Audience Pulse (Hành vi & Tương tác)",
        "✨ 4. AI Content Simulator (Dự báo ML)",
        "🔤 5. Data Preprocessing & Noise Analysis"
    ])
else:
    tab_front, tab_threat, tab_audience, tab_editor = st.tabs([
        "🗞️ 1. The Front Page (Tổng quan)",
        "🚨 2. Phân tích Phân cực & Xung đột Dư luận (Controversy & Polarity)",
        "📊 3. Audience Pulse (Hành vi & Tương tác)",
        "✨ 4. AI Content Simulator (Dự báo ML)"
    ])
    tab_normalize = None

# Prepare metrics dict for front page component
front_page_metrics = {
    "most_active_name": most_active_name,
    "most_active_pct": most_active_pct,
    "best_eng_topic": best_eng_topic,
    "best_eng_val": best_eng_val,
    "overall_avg_eng": overall_avg_eng,
    "worst_cont_topic": worst_cont_topic,
    "worst_cont_val": worst_cont_val,
    "worst_sarc_topic": worst_sarc_topic,
    "worst_sarc_val": worst_sarc_val,
}

# ----------------------------------------------------
# TAB 1: THE FRONT PAGE (TỔNG QUAN)
# ----------------------------------------------------
with tab_front:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Trigger module reload to sync updated render_front_page signature
    conflicts_csv_path = os.path.join(base_dir, "../report/label_join_conflicts.csv")
    render_front_page(
        df_filtered, 
        df_raw, 
        shorten_topic_name, 
        apply_editorial_theme, 
        front_page_metrics,
        conflicts_csv_path=conflicts_csv_path
    )

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
    render_threat_radar(
        df_filtered, 
        df_reactions, 
        shorten_topic_name, 
        apply_editorial_theme, 
        extract_sarcasm_keywords, 
        analyze_topic_spam_bias
    )



# ----------------------------------------------------
# TAB 3: AUDIENCE PULSE (HÀNH VI & TƯƠNG TÁC)
# ----------------------------------------------------
with tab_audience:
    render_audience_pulse(df_filtered, df_reactions, shorten_topic_name, apply_editorial_theme)

# ----------------------------------------------------
# TAB 4: AI CONTENT SIMULATOR (DỰ BÁO ML)
# ----------------------------------------------------
with tab_editor:
    render_content_simulator(
        df_filtered,
        df_reactions,
        load_taxonomy_mapping(),
        load_demo_model_assets,
        predict_transformer,
        shorten_topic_name,
        apply_editorial_theme
    )


# ----------------------------------------------------
# TAB 5: NSW INSIGHTS (chỉ hiển thị khi Audit Mode bật)
# ----------------------------------------------------
if audit_mode and tab_normalize is not None:
    # Chạy ViSoLex normalization theo yêu cầu (lazy) cho df_filtered
    from visolex_normalizer import load_visolex_dictionary, normalize_sentence
    
    @st.cache_data(show_spinner="🔍 Đang chạy ViSoLex NSW Normalizer trên dataset...")
    def run_visolex_on_df(captions_tuple):
        """Chạy ViSoLex normalization on-demand, cache theo nội dung captions."""
        vdict = load_visolex_dictionary()
        norm_texts, counts, words = [], [], []
        for cap in captions_tuple:
            norm, found = normalize_sentence(str(cap), vdict) if vdict else (str(cap), [])
            norm_texts.append(norm)
            counts.append(len(found))
            words.append([item['original'] for item in found])
        return norm_texts, counts, words

    captions_tuple = tuple(df_filtered['caption'].fillna('').astype(str).tolist())
    norm_texts, counts, words = run_visolex_on_df(captions_tuple)
    df_filtered = df_filtered.copy()
    df_filtered['caption_normalized'] = norm_texts
    df_filtered['nsw_count'] = counts
    df_filtered['nsw_words'] = words

    with tab_normalize:
        render_nsw_insights(df_filtered, shorten_topic_name, apply_editorial_theme)



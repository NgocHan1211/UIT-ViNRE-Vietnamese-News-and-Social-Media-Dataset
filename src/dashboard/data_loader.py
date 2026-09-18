import os
import sys
import pandas as pd
import numpy as np

def clean_and_enrich_data(df, include_t18=False):
    """
    Quy trình Tiền xử lý & Làm giàu dữ liệu tự động (Preprocessing Pipeline):
    - Đổi tên trường dữ liệu thô sang caption.
    - Loại bỏ nhãn rỗng (NaN) và tùy chọn loại bỏ nhãn kỹ thuật T18 (Other Unclear).
    - Tính toán các chỉ số thống kê đặc trưng mạng xã hội dựa trên Proxy Reactions (Intensity, Valence, Polarity).
    - Tính toán các chỉ số phân cực phụ (Approval, Outrage, Amusement, Empathy).
    """
    df = df.copy()
    
    # 1. Đồng bộ tên cột nội dung bài đăng
    if 'post_content_for_labeling' in df.columns:
        df = df.rename(columns={'post_content_for_labeling': 'caption'})
    
    # 2. Loại bỏ bản ghi khuyết nhãn chủ đề
    df = df[df['topic_label_id'].notna()]
    
    # 3. Lọc nhãn T18 theo cấu hình (mặc định loại bỏ để phục vụ mô hình hóa)
    if not include_t18:
        df = df[df['topic_label_id'] != 'T18']
        
    # 4. Ép kiểu số cho các trường tương tác
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

    # 5. Phân nhóm cảm xúc (Cultural Adaptation)
    # Tích cực: Love, Care. Tiêu cực: Angry, Sad, Haha, Wow.
    df['positive_reaction_total'] = df['love_count'] + df['care_count']
    df['negative_reaction_total'] = df['angry_count'] + df['sad_count'] + df['haha_count'] + df['wow_count']
    df['special_reaction_total'] = df['positive_reaction_total'] + df['negative_reaction_total']
    df['all_reaction_total_for_formula'] = df['special_reaction_total'] + df['like_count']
    
    # 6. Tính toán các chỉ số Polarity & Intensity
    # Cường độ tương tác đặc biệt
    df['reaction_intensity'] = np.where(
        df['all_reaction_total_for_formula'] > 0,
        df['special_reaction_total'] / df['all_reaction_total_for_formula'],
        np.nan
    )
    
    # Hóa trị cảm xúc (Valence: -1.0, 0.0, 1.0)
    df['reaction_valence'] = np.where(
        df['special_reaction_total'] > 0,
        np.sign(df['positive_reaction_total'] - df['negative_reaction_total']),
        np.nan
    )
    
    # Chỉ số phân cực (Polarity Score = Intensity * Valence)
    df['polarity_score'] = df['reaction_intensity'] * df['reaction_valence']
    
    # 7. Tính toán tỷ lệ Reactions trên tổng Reactions
    total_reactions_for_ratios = np.where(df['total_reactions'] > 0, df['total_reactions'], 1)
    df['love_ratio'] = df['love_count'] / total_reactions_for_ratios
    df['care_ratio'] = df['care_count'] / total_reactions_for_ratios
    df['haha_ratio'] = df['haha_count'] / total_reactions_for_ratios
    df['wow_ratio'] = df['wow_count'] / total_reactions_for_ratios
    df['sad_ratio'] = df['sad_count'] / total_reactions_for_ratios
    df['angry_ratio'] = df['angry_count'] / total_reactions_for_ratios
    
    # 8. Tính toán các chỉ số con (Sub-metrics) - chỉ áp dụng cho bài đăng >= 10 reactions
    df['approval_reaction_index'] = np.where(df['total_reactions'] >= 10, (df['like_count'] + df['love_count']) / df['total_reactions'], 0.0)
    df['outrage_reaction_index'] = np.where(df['total_reactions'] >= 10, df['angry_count'] / df['total_reactions'], 0.0)
    df['amusement_reaction_index'] = np.where(df['total_reactions'] >= 10, df['haha_count'] / df['total_reactions'], 0.0)
    df['empathy_reaction_index'] = np.where(df['total_reactions'] >= 10, (df['sad_count'] + df['care_count']) / df['total_reactions'], 0.0)
    
    # 9. Tính toán chỉ số lan tỏa trên lượng follower
    has_followers = (df['has_page_followers'] == 1) & (df['page_followers'] > 0)
    df['reaction_per_follower'] = np.where(has_followers, df['total_reactions'] / df['page_followers'], 0.0)
    df['share_per_follower'] = np.where(has_followers, df['share_count'] / df['page_followers'], 0.0)
    df['comment_per_follower'] = np.where(has_followers, df['comment_count'] / df['page_followers'], 0.0)
    df['engagement_total'] = df['total_reactions'] + df['comment_count'] + df['share_count']
    df['engagement_per_follower'] = np.where(has_followers, df['engagement_total'] / df['page_followers'], 0.0)
    
    return df

def run_full_pipeline(input_path, output_path, include_t18=False):
    """Đọc tệp dữ liệu thô, thực hiện tiền xử lý và lưu kết quả đầu ra."""
    print(f"🔄 Đang tải dữ liệu thô từ: {input_path}")
    if not os.path.exists(input_path):
        print(f"❌ Lỗi: Không tìm thấy tệp {input_path}")
        return False
        
    df_raw = pd.read_csv(input_path, low_memory=False)
    print(f"📊 Kích thước dữ liệu thô: {df_raw.shape}")
    
    df_clean = clean_and_enrich_data(df_raw, include_t18=include_t18)
    print(f"✅ Đã tiền xử lý thành công. Kích thước dữ liệu sạch: {df_clean.shape}")
    
    df_clean.to_csv(output_path, index=False)
    print(f"💾 Đã lưu dữ liệu làm giàu tại: {output_path}")
    return True

if __name__ == "__main__":
    # Hỗ trợ chạy trực tiếp như CLI
    default_input = "../report/Master_Facebook_News_Posts_TeamCrawl_Labeled.csv"
    default_output = "Public_Response_Streamlit_Enriched.csv"
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else default_input
    output_file = sys.argv[2] if len(sys.argv) > 2 else default_output
    
    # Cho phép giữ lại T18 qua tham số dòng lệnh
    include_t18 = "--include-t18" in sys.argv
    
    success = run_full_pipeline(input_file, output_file, include_t18=include_t18)
    sys.exit(0 if success else 1)

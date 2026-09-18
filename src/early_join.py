import pandas as pd
import json
import glob
import os
import re

# ==========================================
# BƯỚC 1: Tiền xử lý tập CSV (Trích xuất Bài đăng gốc)
# ==========================================
def preprocess_csv(csv_dir):
    # Đọc và gộp (concat) train.csv và test.csv
    df_train = pd.read_csv(os.path.join(csv_dir, 'train.csv'), encoding='utf-8')
    df_test = pd.read_csv(os.path.join(csv_dir, 'test.csv'), encoding='utf-8')
    df_csv = pd.concat([df_train, df_test], ignore_index=True)

    # Xóa các dòng bị trùng lặp nội dung
    df_csv = df_csv.drop_duplicates(subset=['content'])

    # Lọc bỏ toàn bộ bình luận (Comments): Giữ lại các dòng có comment_ids CÓ CHỨA DỮ LIỆU
    df_csv = df_csv[df_csv['comment_ids'].notna()]

    # Xóa cột comment_ids vì không còn cần thiết
    df_csv = df_csv.drop(columns=['comment_ids'])

    print(f"[BƯỚC 1] Số lượng Bài đăng gốc trong CSV sau khi lọc: {len(df_csv)}")
    return df_csv

# ==========================================
# BƯỚC 2: Tiền xử lý tập JSON (Trích xuất Metadata)
# ==========================================
def preprocess_json(json_dir):
    all_data = []
    
    # Duyệt qua tất cả các file JSON bài đăng, bỏ qua tệp comments.json
    json_files = glob.glob(os.path.join(json_dir, '*.json'))
    for file_path in json_files:
        if 'comments.json' in os.path.basename(file_path):
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                posts = json.load(f) # Đọc danh sách bài đăng
                for post in posts:
                    # Trích xuất các keys cần thiết, sử dụng .get() để tránh lỗi KeyError
                    extracted = {
                        'post_content': post.get('post_content'),
                        'creation_time': post.get('creation_time'),
                        'reactions_detail': post.get('reactions_detail', {}), # Khởi tạo dict rỗng nếu không có
                        'share_count': post.get('share_count', 0),
                        'total_reactions': post.get('total_reactions', 0)
                    }
                    all_data.append(extracted)
            except Exception as e:
                print(f"Lỗi khi đọc file {file_path}: {e}")
                
    df_json = pd.DataFrame(all_data)
    print(f"[BƯỚC 2] Số lượng Metadata trích xuất từ các file JSON: {len(df_json)}")
    return df_json

# ==========================================
# BƯỚC 3: The Golden Match (Tạo khóa nối & Nối bảng)
# ==========================================
def clean_text_for_match(text):
    """
    Hàm chuẩn hóa Text:
    - Ép về kiểu chuỗi (str) và chuyển thành chữ thường (lowercase)
    - Xóa toàn bộ khoảng trắng, tab, và ký tự xuống dòng bằng Regex
    """
    if pd.isna(text):
        return ""
    text = str(text).lower()
    # Thay thế 1 hoặc nhiều ký tự trắng (\s bao gồm khoảng trắng, tab \t, newline \n, \r) thành rỗng
    text = re.sub(r'\s+', '', text)
    return text

def golden_match(df_csv, df_json):
    # Tạo cột match_key ở cả hai DataFrame
    df_csv['match_key'] = df_csv['content'].apply(clean_text_for_match)
    df_json['match_key'] = df_json['post_content'].apply(clean_text_for_match)
    
    # Thực hiện pd.merge() dạng Inner Join
    df_merged = pd.merge(df_csv, df_json, on='match_key', how='inner')
    
    print(f"[BƯỚC 3] Số lượng Golden Dataset khớp thành công: {len(df_merged)}")
    return df_merged

# ==========================================
# BƯỚC 4: Chuẩn hóa Schema và Xuất file (Formatting)
# ==========================================
def format_and_export(df_merged, output_path):
    # 1. Xóa các cột tạm (match_key, post_content)
    df_merged = df_merged.drop(columns=['match_key', 'post_content'])
    
    # 2. Xử lý Reactions
    # Giải nén dictionary bằng cách chuyển series dicts thành DataFrame mới (phương pháp tối ưu và nhanh nhất)
    reactions_df = pd.DataFrame(df_merged['reactions_detail'].tolist(), index=df_merged.index)
    
    # Khai báo các cột reactions yêu cầu
    required_reactions = ['like', 'love', 'haha', 'wow', 'sad', 'angry', 'care']
    for col in required_reactions:
        if col not in reactions_df.columns:
            reactions_df[col] = 0 # Thêm cột nếu JSON bị thiếu hoàn toàn loại reaction đó
            
    # Lọc lại đúng 7 cột, điền NaN bằng 0 và ép kiểu Số nguyên
    reactions_df = reactions_df[required_reactions].fillna(0).astype(int)
    
    # Nối lại các cột này vào df gốc và xóa đi cột reactions_detail
    df_merged = pd.concat([df_merged, reactions_df], axis=1)
    df_merged = df_merged.drop(columns=['reactions_detail'])
    
    # 3. Xử lý Thời gian (Timezone: Asia/Ho_Chi_Minh UTC+7)
    # Unit='s' vì creation_time là Unix Timestamp (giây)
    df_merged['creation_time'] = pd.to_datetime(df_merged['creation_time'], unit='s', errors='coerce')
    # Gán UTC trước, sau đó convert sang múi giờ VN
    df_merged['creation_time'] = df_merged['creation_time'].dt.tz_localize('UTC').dt.tz_convert('Asia/Ho_Chi_Minh')
    
    # 4. Xử lý Share & Total Reactions (Ép kiểu)
    df_merged['share_count'] = pd.to_numeric(df_merged['share_count'], errors='coerce').fillna(0).astype(int)
    df_merged['total_reactions'] = pd.to_numeric(df_merged['total_reactions'], errors='coerce').fillna(0).astype(int)
    
    # Tạo thư mục nếu chưa tồn tại
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Xuất file Master_Data_Raw.csv
    df_merged.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"[BƯỚC 4] Quá trình hoàn tất. Đã lưu file tại: {output_path}")

def main():
    # Khai báo đường dẫn thư mục bằng os.path.join để chạy đa nền tảng
    csv_dir = os.path.join('data', 'csv-data(labeled)')
    json_dir = os.path.join('data', 'json-crawl-data')
    output_path = os.path.join('data', 'Processed_Data', 'Master_Data_Raw.csv')
    
    print("-" * 50)
    print(" BẮT ĐẦU QUÁ TRÌNH EARLY JOIN DATASET")
    print("-" * 50)
    
    df_csv = preprocess_csv(csv_dir)
    df_json = preprocess_json(json_dir)
    df_merged = golden_match(df_csv, df_json)
    format_and_export(df_merged, output_path)

if __name__ == "__main__":
    main()

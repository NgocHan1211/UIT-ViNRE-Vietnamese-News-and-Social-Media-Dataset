import pandas as pd
import json
import glob
import os
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def normalize_text(text):
    if pd.isna(text):
        return ""
    return re.sub(r'\s+', '', str(text).lower())

def run_pipeline():
    print("🚀 BẮT ĐẦU PIPELINE TÍCH HỢP DỮ LIỆU MỚI")
    
    # 1. Đọc dữ liệu CSV
    df_train = pd.read_csv("data/csv-data(labeled)/train.csv")
    df_test = pd.read_csv("data/csv-data(labeled)/test.csv")
    df_post = pd.concat([df_train, df_test], ignore_index=True)
    df_post = df_post[df_post['comment_ids'].notna() & (df_post['comment_ids'] != '')].copy()
    
    # 2. Đọc dữ liệu JSON
    json_files = glob.glob("data/json-crawl-data/*.json") + glob.glob("data/json-crawl-data/*.jsonl")
    json_data = []
    for f in json_files:
        try:
            if f.endswith('.json'):
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    if isinstance(data, list):
                        for post in data:
                            if isinstance(post, dict) and post.get('post_content'):
                                json_data.append({
                                    'json_text': post.get('post_content', ''),
                                    'reactions': post.get('total_reactions', 0),
                                    'shares': post.get('share_count', 0),
                                    'json_source': os.path.basename(f)
                                })
            elif f.endswith('.jsonl'):
                with open(f, 'r', encoding='utf-8') as file:
                    for line in file:
                        post = json.loads(line)
                        if post.get('post_content'):
                            json_data.append({
                                'json_text': post.get('post_content', ''),
                                'reactions': post.get('total_reactions', 0),
                                'shares': post.get('share_count', 0),
                                'json_source': os.path.basename(f)
                            })
        except Exception:
            pass

    df_json = pd.DataFrame(json_data)
    
    # 3. Chuẩn hóa Text
    df_post['norm_text'] = df_post['content'].apply(normalize_text)
    df_json['norm_json_text'] = df_json['json_text'].apply(normalize_text)
    df_json = df_json.drop_duplicates(subset=['norm_json_text']).dropna(subset=['norm_json_text'])
    df_json = df_json[df_json['norm_json_text'] != '']
    
    # 4. Giai đoạn 1: EXACT MATCH (Inner Join)
    df_exact = df_post.merge(df_json, how='inner', left_on='norm_text', right_on='norm_json_text')
    print(f"✅ Exact Match thành công: {len(df_exact)} posts")
    
    # 5. Giai đoạn 2: VỚT BÀI RỚT BẰNG FUZZY MATCH (TF-IDF Cosine Similarity)
    # Lọc ra các bài rớt
    matched_ids = df_exact['post_id'].tolist()
    df_failed = df_post[~df_post['post_id'].isin(matched_ids)].copy()
    
    print(f"⚠️ Đang vớt {len(df_failed)} bài rớt bằng TF-IDF Cosine Similarity > 0.85...")
    
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
    
    # Tạo vectors
    if len(df_failed) > 0 and len(df_json) > 0:
        tfidf_json = vectorizer.fit_transform(df_json['norm_json_text'])
        tfidf_failed = vectorizer.transform(df_failed['norm_text'])
        
        # Tính similarity
        sim_matrix = cosine_similarity(tfidf_failed, tfidf_json)
        
        fuzzy_matches = []
        for i in range(len(df_failed)):
            max_sim = sim_matrix[i].max()
            if max_sim > 0.85:
                best_idx = sim_matrix[i].argmax()
                row_post = df_failed.iloc[i].to_dict()
                row_json = df_json.iloc[best_idx].to_dict()
                row_post.update(row_json)
                fuzzy_matches.append(row_post)
        
        df_fuzzy = pd.DataFrame(fuzzy_matches)
        print(f"🛟 Fuzzy Match vớt thành công: {len(df_fuzzy)} posts")
        
        if len(df_fuzzy) > 0:
            df_final = pd.concat([df_exact, df_fuzzy], ignore_index=True)
        else:
            df_final = df_exact
    else:
        df_final = df_exact
        
    print(f"🎯 TỔNG SỐ POST SAU KHI JOIN: {len(df_final)}")
    
    # 6. Tách luồng dữ liệu theo Decision
    print("\n📦 XUẤT PIPELINE:")
    print("- Luồng 1 (Train AI Model): Sử dụng toàn bộ CSV gốc (2.636 bài) để train Classification, đảm bảo không mất label gốc.")
    print(f"- Luồng 2 (Toán học Cảm xúc): Sử dụng {len(df_final)} bài đã Join thành công để phân tích Reactions/Shares.")
    
    # Có thể lưu ra file
    df_final.to_csv("data/Processed_Data/Master_Data_Fuzzy_Joined.csv", index=False)

if __name__ == "__main__":
    run_pipeline()

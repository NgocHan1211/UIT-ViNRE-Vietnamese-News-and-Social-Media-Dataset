# Traditional ML Model Zoo

Folder này gom artifacts để Streamlit có thể load nhiều model sau deep HPO finalization.

## Groups

- `best_by_model/`: 4 model, mỗi model là scenario tốt nhất theo validation Macro-F1 trong model family.
- `by_scenario/`: đủ 5 scenarios x 4 models.

Các file `model.joblib`, `vectorizer.joblib`, `label_encoder.joblib` được tạo bằng symlink tương đối tới artifact gốc để tránh nhân đôi dung lượng. Nếu hệ thống không hỗ trợ symlink, script fallback sang copy.

Registry chính:

- `model_registry.csv`
- `model_registry.json`

Streamlit nên đọc registry, chọn row `recommended_for_demo=true` cho demo nhanh hoặc cho phép user chọn mọi row trong `by_scenario`.

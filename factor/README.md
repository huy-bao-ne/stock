# Cách chạy
```bash
# venv
python -m venv venv
venv\Scripts\activate

# Đặt API key trong env vào
set GROQ_API_KEY=gsk_...
streamlit run ui/app.py


Nếu data không có ở các folder, Groq sẽ gọi tool → tool trả error → retry → model trả text thay thế (graceful fallback).

# Cách chạy lấy dữ liệu 
python main.py                              # full pipeline
python main.py --skip-fetch                 # đã có raw data
python main.py --skip-fetch --skip-process  # chỉ chạy correlation

# Lấy dữ liệu theo ngành
python main.py --sector SECURITIES                              # Chạy theo ngành
python main.py --sector SECURITIES --skip-collect               # raw files đã có, chỉ cần re-process 
python main.py --sector FOOD --debug                            # Debug


# file test_agent.py để test riêng 
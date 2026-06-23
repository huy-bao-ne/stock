# Cách chạy
/Bật venv trước khi chạy

uvicorn api:app --host 0.0.0.0 --port 8000

set GROQ_API_KEY=gsk_...
set NEWS_AGENT_URL=http://localhost:8000
streamlit run ui/app.py
# Cách chạy
/Bật venv trước khi chạy
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
uvicorn api:app --host 0.0.0.0 --port 8000

set GROQ_API_KEY=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
set NEWS_AGENT_URL=http://localhost:8000
streamlit run ui/app.py
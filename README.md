# Cách chạy
/Bật venv trước khi chạy
$env:

set GROQ_API_KEY=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
set TAVILY_API_KEY=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
set SERPER_API_KEY=802d08dbed7f6aec0358572461b727719836aec7
uvicorn api:app --host 0.0.0.0 --port 8000
python agent1_collector.py




------------------------------------------------------------------------------
set GROQ_API_KEY=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
set NEWS_AGENT_URL=http://localhost:8000
streamlit run ui/app.py
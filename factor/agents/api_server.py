"""
agents/api_server.py
=====================
FastAPI server expose FinancialAgent qua HTTP.

Cách chạy:
    cd project/
    python agents/api_server.py

    Hoặc dùng uvicorn trực tiếp:
    uvicorn agents.api_server:app --host 0.0.0.0 --port 8000 --reload

Endpoints:
    POST /ask          — gửi câu hỏi, nhận câu trả lời
    GET  /health       — kiểm tra server còn sống
    GET  /data-summary — xem tóm tắt dữ liệu hiện có

Cách test nhanh bằng curl:
    curl -X POST http://localhost:8000/ask \
         -H "Content-Type: application/json" \
         -d '{"question": "Ngành nào có factor mạnh nhất?"}'
"""

import os
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Import agent (path relative khi chạy từ project root)
import sys
sys.path.insert(0, str(__file__).replace("agents/api_server.py", ""))

from agents.financial_agent import FinancialAgent, ToolExecutor


# ======================================================================
# KHỞI TẠO APP
# ======================================================================

app = FastAPI(
    title       = "Financial Factor Analysis Agent",
    description = "AI Agent phân tích nhân tố tài chính chứng khoán Việt Nam",
    version     = "1.0.0",
)

# Cho phép UI ở domain khác gọi vào (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],   # production: thay bằng domain cụ thể
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# Khởi tạo agent 1 lần khi server start
# API key đọc từ biến môi trường ANTHROPIC_API_KEY
_agent: Optional[FinancialAgent] = None

def get_agent() -> FinancialAgent:
    global _agent
    if _agent is None:
        _agent = FinancialAgent(
            data_root    = "data",
            output_root  = "outputs",
            verbose      = False,
        )
    return _agent


# ======================================================================
# SCHEMAS
# ======================================================================

class AskRequest(BaseModel):
    question: str
    verbose: bool = False   # True = in log tool calls ra console

class AskResponse(BaseModel):
    answer: str
    question: str
    elapsed_seconds: float


# ======================================================================
# ENDPOINTS
# ======================================================================

@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """
    Gửi câu hỏi bằng ngôn ngữ tự nhiên, nhận câu trả lời từ AI Agent.

    Ví dụ request body:
        {"question": "VCB có ROA bao nhiêu năm 2023?"}

    Ví dụ response:
        {
            "answer": "ROA của VCB năm 2023 là 1.8%...",
            "question": "VCB có ROA bao nhiêu năm 2023?",
            "elapsed_seconds": 3.2
        }
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống.")

    try:
        agent     = get_agent()
        t0        = time.time()
        answer    = agent.ask(request.question)
        elapsed   = round(time.time() - t0, 2)

        return AskResponse(
            answer          = answer,
            question        = request.question,
            elapsed_seconds = elapsed,
        )
    except ValueError as e:
        # Thiếu API key
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi agent: {str(e)}")


@app.get("/health")
async def health():
    """Kiểm tra server đang chạy."""
    return {"status": "ok", "message": "Financial Agent API đang hoạt động"}


@app.get("/data-summary")
async def data_summary():
    """Xem tóm tắt dữ liệu đang có trong hệ thống."""
    executor = ToolExecutor(data_root="data", output_root="outputs")
    summary  = executor.execute("get_available_data", {})
    return {"summary": summary}


# ======================================================================
# CHẠY TRỰC TIẾP
# ======================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 50)
    print("  Financial Factor Analysis Agent API")
    print("=" * 50)
    print(f"  API Key: {'✔ Đã set' if os.environ.get('ANTHROPIC_API_KEY') else '✗ Chưa set — cần set ANTHROPIC_API_KEY'}")
    print(f"  Docs   : http://localhost:8000/docs")
    print(f"  Health : http://localhost:8000/health")
    print("=" * 50)

    uvicorn.run(
        "agents.api_server:app",
        host    = "0.0.0.0",
        port    = 8000,
        reload  = True,
    )
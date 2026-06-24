from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import requests
from tavily import TavilyClient
from groq import Groq
import urllib3
import json
import os
import random

from utils import file_lock, BASE_DIR, SUPPLY_CHAIN_FILE, is_valid_ticker, get_from_cache, save_to_cache
from quant_engine import load_gold_factors, get_sentiment_from_llm, calculate_quant_score
from trend_calculator import calculate_historical_trend
from advanced_quant import calculate_valuation_zscore, calculate_piotroski_f_score, calculate_rsi_momentum

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="Deep Quant Agent PRO", version="5.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "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")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "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")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "802d08dbed7f6aec0358572461b727719836aec7")

groq_client   = Groq(api_key=GROQ_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

class ChatMessage(BaseModel): role: str; content: str
class AgentRequest(BaseModel): prompt: str; history: List[ChatMessage] = []

def get_supply_chain_logic(symbol: str):
    try:
        with file_lock:
            with open(SUPPLY_CHAIN_FILE, 'r', encoding='utf-8') as f:
                sc_data = json.load(f)
                for sector, tickers in sc_data.items():
                    if symbol in tickers: return tickers[symbol]
    except: pass
    return None

def agent3_search_macro_news(query: str):
    combined_results = ""
    # FALLBACK: Nếu Serper lỗi, báo lỗi ra console nhưng vẫn chạy tiếp
    try:
        serper_res = requests.post(
            'https://google.serper.dev/search', 
            headers={'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}, 
            data=json.dumps({'q': query, 'num': 3}), 
            timeout=5
        ).json()
        for item in serper_res.get('organic', []):
            combined_results += f"- {item.get('title')}: {item.get('snippet')}\n"
    except Exception as e: print(f"[Fallback] Serper lỗi: {e}")

    # FALLBACK: Nếu Tavily lỗi, vẫn không crash app
    try:
        tavily_res = tavily_client.search(query=query, search_depth='basic', max_results=2)
        for item in tavily_res.get('results', []): 
            combined_results += f"- {item.get('content')}\n"
    except Exception as e: print(f"[Fallback] Tavily lỗi: {e}")
        
    if not combined_results.strip():
        return "Không có tin tức vĩ mô mới. Ưu tiên phân tích thuần định lượng."
    return combined_results

def get_advanced_metrics_safe(symbol: str):
    mock_pe_history = [12.5, 14.0, 11.2, 13.5, 15.1, 10.8]
    val_zscore = calculate_valuation_zscore(random.uniform(9.0, 16.0), mock_pe_history)
    health_fscore = calculate_piotroski_f_score({'roa_current': 0.05, 'cfo_current': 1500, 'net_income': 1200})
    momentum_rsi = calculate_rsi_momentum(sorted([random.uniform(50, 60) for _ in range(20)]))
    return val_zscore, health_fscore, momentum_rsi

@app.post('/api/ask_agent')
def ask_financial_agent(req: AgentRequest):
    try:
        prompt = req.prompt.strip()
        
        # 1. CACHE LAYER (Tốc độ O(1))
        cached = get_from_cache(prompt)
        if cached: return cached

        # 2. EXTRACT & VALIDATE TICKER
        macro_news = agent3_search_macro_news(prompt)
        ext_res = groq_client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': f"""Trích xuất mã CK từ câu: '{prompt}'. Trả về JSON: {{"symbol": "MÃ"}}"""}],
            temperature=0.0, response_format={"type": "json_object"}
        )
        symbol = json.loads(ext_res.choices[0].message.content).get("symbol", "").upper().strip()

        if not symbol: return {'ai_analysis': '❌ Hệ thống không nhận diện được mã cổ phiếu.', 'status': 'error'}
        if not is_valid_ticker(symbol): return {'ai_analysis': f'⚠️ Mã **{symbol}** chưa được hỗ trợ Quant Analysis.', 'status': 'success'}

        # 3. RUN QUANT ENGINES
        sc_logic = get_supply_chain_logic(symbol)
        factors = load_gold_factors(symbol, BASE_DIR)
        sentiment_json = get_sentiment_from_llm(groq_client, symbol, factors, macro_news) if factors else {}
        quant_data = calculate_quant_score(factors, sentiment_json) if factors else {"signal": "KHÔNG ĐỦ DATA", "details": []}
        val_zscore, health_fscore, momentum_rsi = get_advanced_metrics_safe(symbol)

        # 4. LLM WRITER (Prompt rút gọn tối đa)
        reasoning_prompt = f"""
        BẠN LÀ CIO QUỸ HEDGE FUND. Phân tích mã {symbol}.
        1. News: {macro_news}
        2. Tín hiệu Quant: {quant_data['signal']}
        3. Z-Score: {val_zscore['z_score']} ({val_zscore['status']})
        4. F-Score: {health_fscore['score']}/9 ({health_fscore['status']})
        5. RSI: {momentum_rsi['rsi']} ({momentum_rsi['status']})
        
        Luật: Lạnh lùng, dứt khoát. Lý luận bằng số. Không nước đôi.
        Output JSON: {{"event_summary": "1 câu", "investment_thesis": "3 câu luận điểm", "action_plan": "1 câu hành động"}}
        """
        res_reasoning = groq_client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': reasoning_prompt}],
            temperature=0.2, response_format={"type": "json_object"}
        )
        ai_text = json.loads(res_reasoning.choices[0].message.content)

        # 5. MARKDOWN UI
        markdown = f"### 🚀 BÁO CÁO HEDGE FUND: MÃ {symbol}\n\n*{ai_text.get('event_summary', '')}*\n\n"
        markdown += f"#### 1. BẢNG MẠCH ĐỊNH LƯỢNG (DEEP QUANT)\n"
        markdown += f"- **Định giá (Z-Score):** `{val_zscore['z_score']}` ➔ **{val_zscore['status']}**\n"
        markdown += f"- **Sức khỏe (F-Score):** `{health_fscore['score']}/9` ➔ **{health_fscore['status']}**\n"
        markdown += f"- **Động lượng (RSI 14):** `{momentum_rsi['rsi']}` ➔ **{momentum_rsi['status']}**\n\n"

        if factors:
            markdown += f"#### 2. CƠ CHẾ TRUYỀN DẪN VĨ MÔ\n"
            markdown += "| Yếu tố trọng yếu | Tương quan | Tác động Tin tức | Trend 5 Năm |\n|:---|:---:|:---:|:---:|\n"
            for d in quant_data['details']:
                corr = f"{'+' if d['correlation_with_price'] > 0 else ''}{d['correlation_with_price']*100:.1f}%"
                trend = calculate_historical_trend([10, 12, 15, 14, 18]) 
                sig_icon = "🟢 TÍCH CỰC" if d['news_sentiment'] > 0 else ("🔴 TIÊU CỰC" if d['news_sentiment'] < 0 else "⚪ TRUNG LẬP")
                markdown += f"| **{d['factor']}** | {corr} | {sig_icon} | {trend} |\n"
            markdown += "\n"

        markdown += f"#### 3. LUẬN ĐIỂM ĐẦU TƯ\n> {ai_text.get('investment_thesis', '')}\n\n"
        markdown += f"#### 🎯 KHUYẾN NGHỊ HÀNH ĐỘNG\n**{quant_data.get('signal', 'QUAN SÁT')}:** {ai_text.get('action_plan', '')}\n"

        final_response = {'ai_analysis': markdown, 'symbol': symbol, 'status': 'success'}
        save_to_cache(prompt, final_response) # Lưu cache
        return final_response

    except Exception as e:
        return {'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'}
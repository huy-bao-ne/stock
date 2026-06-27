"""
news/api.py
============
News & Analysis Agent — FastAPI backend 
Tập trung 100% vào Bước 3: Phân tích Tác động Vĩ mô lên Chỉ báo tài chính (Factors).
"""
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
import re

from utils import file_lock, BASE_DIR, SUPPLY_CHAIN_FILE, is_valid_ticker, get_from_cache, save_to_cache
from quant_engine import load_gold_factors

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="Macro Analysis Agent", version="11.0.0")
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
    try:
        serper_res = requests.post(
            'https://google.serper.dev/search', 
            headers={'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}, 
            data=json.dumps({'q': query, 'num': 3}), timeout=5
        ).json()
        for item in serper_res.get('organic', []):
            combined_results += f"- {item.get('title')}: {item.get('snippet')}\n"
    except: pass

    try:
        tavily_res = tavily_client.search(query=query, search_depth='basic', max_results=2)
        for item in tavily_res.get('results', []): 
            combined_results += f"- {item.get('content')}\n"
    except: pass
        
    return combined_results if combined_results.strip() else "Không có dữ liệu tin tức vĩ mô."

def parse_llm_json(raw_text: str) -> dict:
    try:
        cleaned_text = raw_text.replace('```json', '').replace('```', '').strip()
        match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
        if match: return json.loads(match.group(0))
        return {}
    except: return {}

@app.post('/api/ask_agent')
def ask_financial_agent(req: AgentRequest):
    try:
        prompt = req.prompt.strip()
        
        cached = get_from_cache(prompt)
        if cached: return cached

        macro_news = agent3_search_macro_news(prompt)
        
        extractor_prompt = f"""Trích xuất mã CK từ câu: '{prompt}'. Trả về JSON: {{"symbol": "MÃ"}}"""
        ext_res = groq_client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': extractor_prompt}],
            temperature=0.0
        )
        symbol = parse_llm_json(ext_res.choices[0].message.content).get("symbol", "").upper().strip()

        if not symbol: return {'ai_analysis': '❌ Hệ thống không nhận diện được mã cổ phiếu.', 'status': 'error'}
        if not is_valid_ticker(symbol): return {'ai_analysis': f'⚠️ Mã **{symbol}** chưa được hỗ trợ.', 'status': 'success'}

        # Lấy Chuẩn hóa Chuỗi cung ứng và Danh sách Chỉ báo
        sc_logic = get_supply_chain_logic(symbol)
        sc_context = f"Cơ chế chuỗi cung ứng: {sc_logic['logic']}" if sc_logic else "Phân tích theo bản chất ngành."
        factors_to_analyze = load_gold_factors(symbol, BASE_DIR)

        # Chuẩn bị bối cảnh chuỗi cung ứng cực nét
        if sc_logic:
            sc_context = f"- Động lực Đầu vào: {sc_logic.get('input_driver', 'Chưa rõ')}\n- Động lực Đầu ra: {sc_logic.get('output_driver', 'Chưa rõ')}\n- Bản chất cốt lõi: {sc_logic.get('logic', 'Chưa rõ')}"
        else:
            sc_context = "Tự xác định bản chất ngành. (Ví dụ: Ngành Công nghệ giá vốn là lương kỹ sư, Ngân hàng giá vốn là lãi suất huy động, Sản xuất giá vốn là nguyên vật liệu...)"

        # GỌI LLM: PHÂN TÍCH TÁC ĐỘNG VĨ MÔ
        reasoning_prompt = f"""
        BẠN LÀ CHUYÊN GIA PHÂN TÍCH VĨ MÔ LÕI CỦA QUỸ HEDGE FUND ĐẦU NGÀNH.
        Phân tích tác động của sự kiện vĩ mô đối với mã cổ phiếu {symbol}.
        
        [DỮ LIỆU BẮT BUỘC SỬ DỤNG]
        1. Sự kiện vĩ mô (News): {macro_news}
        2. Các chỉ báo cần đánh giá: {factors_to_analyze}
        
        [ĐẶC THÙ DOANH NGHIỆP {symbol} - KỶ LUẬT THÉP BẮT BUỘC TUÂN THỦ]
        {sc_context}
        ⚠️ LỆNH CẤM: 
        - NẾU {symbol} LÀ CÔNG TY CÔNG NGHỆ, DỊCH VỤ, NGÂN HÀNG: TUYỆT ĐỐI KHÔNG dùng văn mẫu "tăng chi phí nguyên vật liệu đầu vào, giá dầu, đứt gãy chuỗi cung ứng hàng hóa". (Ví dụ: FPT sản xuất phần mềm, không mua dầu mỏ để làm ra phần mềm).
        - CHỈ ĐƯỢC phân tích cơ chế dựa trên đúng Yếu tố Đầu vào/Đầu ra đã cung cấp (Tỷ giá, Lãi suất, Nhu cầu chi tiêu IT, v.v.).

        [YÊU CẦU JSON ĐẦU RA - CHỈ DÙNG STRING]
        {{
            "event_nature": "Phân tích bản chất sự kiện, dòng tiền vĩ mô đang chạy đi đâu? (1-2 câu).",
            "impact_direction": "TÍCH CỰC / TIÊU CỰC / TRUNG LẬP",
            "factor_1_name": "Tên chỉ báo 1",
            "factor_1_trend": "TĂNG / GIẢM / KHÔNG ĐỔI",
            "factor_1_reason": "Giải thích ĐÚNG THEO MÔ HÌNH KINH DOANH. Tại sao sự kiện làm TĂNG/GIẢM chỉ báo này?",
            "factor_2_name": "Tên chỉ báo 2",
            "factor_2_trend": "TĂNG / GIẢM / KHÔNG ĐỔI",
            "factor_2_reason": "Giải thích cơ chế truyền dẫn cực kỳ logic tài chính.",
            "factor_3_name": "Tên chỉ báo 3",
            "factor_3_trend": "TĂNG / GIẢM / KHÔNG ĐỔI",
            "factor_3_reason": "Đào sâu vào động lực cốt lõi.",
            "final_verdict": "Triển vọng đầu tư cơ bản."
        }}
        """
        res_reasoning = groq_client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': reasoning_prompt}],
            temperature=0.2
        )
        ai = parse_llm_json(res_reasoning.choices[0].message.content)

        # TRÌNH BÀY GIAO DIỆN MARKDOWN CHUẨN MỰC
        markdown = f"### 📰 PHÂN TÍCH TÁC ĐỘNG VĨ MÔ: MÃ {symbol}\n\n"
        markdown += f"**BẢN CHẤT SỰ KIỆN:**\n> {ai.get('event_nature', 'Đang cập nhật sự kiện...')}\n\n"
        
        markdown += f"#### 🎯 MỔ XẺ CƠ CHẾ TRUYỀN DẪN VÀO BÁO CÁO TÀI CHÍNH\n"
        markdown += "| Chỉ báo trọng yếu (Factor) | Xu hướng bị tác động | Giải thích cơ chế (Tại sao?) |\n"
        markdown += "|:---|:---:|:---|\n"
        
        for i in range(1, 4):
            fname = ai.get(f'factor_{i}_name')
            if not fname: continue
            ftrend = ai.get(f'factor_{i}_trend', 'KHÔNG ĐỔI')
            freason = ai.get(f'factor_{i}_reason', '')
            
            # Gắn icon cho đẹp
            icon = "🟢" if "TĂNG" in ftrend.upper() else ("🔴" if "GIẢM" in ftrend.upper() else "⚪")
            markdown += f"| **{fname}** | {icon} **{ftrend.upper()}** | {freason} |\n"

        markdown += f"\n#### ⚖️ KẾT LUẬN TRIỂN VỌNG DOANH NGHIỆP\n"
        
        impact = ai.get('impact_direction', 'TRUNG LẬP')
        impact_color = "text-emerald-600" if "TÍCH CỰC" in impact else ("text-rose-600" if "TIÊU CỰC" in impact else "text-slate-600")
        markdown += f"- **Đánh giá tổng quan:** Tác động mang tính **{impact}**.\n"
        markdown += f"- **Góc nhìn cơ bản:** {ai.get('final_verdict', '')}\n"

        final_response = {'ai_analysis': markdown, 'symbol': symbol, 'status': 'success'}
        save_to_cache(prompt, final_response) 
        return final_response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'}
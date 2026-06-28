"""
news/api.py
============
BẢN NÂNG CẤP HOÀN CHỈNH - GIAO DIỆN CHUYÊN NGHIỆP & BÁO CÁO CHUẨN MỰC
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles       
from fastapi.responses import FileResponse 
from pydantic import BaseModel
from typing import List
import requests
from tavily import TavilyClient
from groq import Groq
import urllib3
import json
import os
import re
import time
from datetime import datetime
import pandas as pd

pd.set_option('future.no_silent_downcasting', True)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from utils import (
    data_lock, watchlist_lock, sc_lock, BASE_DIR, 
    SUPPLY_CHAIN_FILE, DATA_FILE, WATCHLIST_FILE, 
    is_valid_ticker, get_from_cache, save_to_cache
)
from quant_engine import load_gold_factors

app = FastAPI(title="Multi-Agent Router", version="15.4.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def serve_ui():
    return FileResponse("frontend/index.html")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")      
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "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")   
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "802d08dbed7f6aec0358572461b727719836aec7") 

groq_client = Groq(api_key=GROQ_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

class ChatMessage(BaseModel):
    role: str
    content: str

class AgentRequest(BaseModel):
    prompt: str
    history: List[ChatMessage] = []

def build_matrix_markdown_table(financial_records: list) -> str:
    if not financial_records or len(financial_records) == 0 or "error" in str(financial_records):
        return '> *⚠️ Đang đồng bộ BCTC. Phân tích sẽ dựa trên bối cảnh dòng tiền và tin tức vĩ mô...*\n\n'
    
    try: financial_records = sorted(financial_records, key=lambda x: str(x.get('quy', '')))
    except: pass

    quarters_headers = [str(item.get('quy', 'N/A')) for item in financial_records]
    indicators = {
        'Doanh Thu Thuần (VND)': 'doanh_thu',
        'Lợi Nhuận Gộp (VND)': 'ln_gop',
        'Lợi Nhuận Sau Thuế (VND)': 'lnst',
        'Tổng Tài Sản (VND)': 'tong_tai_san',
        'Vốn Chủ Sở Hữu (VND)': 'von_csh',
        'Nợ Phải Trả (VND)': 'no_phai_tra',
        'Thu nhập trên CP (EPS)': 'eps',
        'Biên LN Gộp (%)': 'bien_ln_gop',
        'ROE (%)': 'roe',
        'Hệ số P/E': 'pe'
    }
    
    table_str = '| Chỉ tiêu Tài chính | ' + ' | '.join(quarters_headers) + ' |\n'
    table_str += '| :--- | ' + ' | '.join([' :---: ' for _ in quarters_headers]) + ' |\n'
    
    has_any_data = False
    for label, key in indicators.items():
        row_cells = []
        has_meaningful = False
        for item in financial_records:
            value = item.get(key, 0)
            if isinstance(value, (int, float)) and value != 0:
                has_meaningful = True; has_any_data = True
                if '%' in label or label == 'Hệ số P/E': row_cells.append(f'{value:.2f}')
                else: row_cells.append(f'{value:,.0f}')
            else:
                row_cells.append('-')
        if has_meaningful:
            table_str += f'| **{label}** | ' + ' | '.join(row_cells) + ' |\n'
            
    if not has_any_data: return ""
    return f"**📊 MA TRẬN TÀI CHÍNH TỔNG HỢP (Nguồn: Vnstock)**\n\n{table_str}\n\n"

def get_financial_data_with_wait(symbol: str, max_wait_seconds=15):
    try:
        with watchlist_lock:
            try:
                if os.path.exists(WATCHLIST_FILE):
                    with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f: wl = json.load(f)
                else: wl = {}
            except: wl = {}
            wl[symbol] = datetime.now().strftime("%Y-%m-%d")
            with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f: json.dump(wl, f, ensure_ascii=False, indent=4)
    except: pass

    for _ in range(max_wait_seconds):
        try:
            with data_lock:
                if os.path.exists(DATA_FILE):
                    with open(DATA_FILE, 'r', encoding='utf-8') as f:
                        warehouse = json.load(f)
                        data = warehouse.get(symbol)
                        if data and "error" not in str(data):
                            if isinstance(data, dict): return [data]
                            return data
        except: pass
        time.sleep(1)

    return None

def get_supply_chain_logic(symbol: str):
    try:
        with sc_lock:
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
            data=json.dumps({'q': query, 'num': 4}), timeout=5
        ).json()
        for item in serper_res.get('organic', []):
            combined_results += f"- {item.get('title')}: {item.get('snippet')}\n"
    except: pass

    try:
        tavily_res = tavily_client.search(query=query, search_depth='basic', max_results=3)
        for item in tavily_res.get('results', []): combined_results += f"- {item.get('content')}\n"
    except: pass
        
    return combined_results if combined_results.strip() else "Không tìm thấy dữ liệu tin tức thị trường."

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

        # ==================================
        # AI ROUTER
        # ==================================
        router_prompt = f"""
        Phân loại ý định người dùng. Câu hỏi: '{prompt}'
        - "GENERAL_ADVICE": Báo cáo tài chính, kết quả kinh doanh, có nên mua bán, phân tích chung.
        - "SPECIFIC_EVENT": CHỈ KHI CÓ SỰ KIỆN VĨ MÔ TỪ BÊN NGOÀI (Chiến tranh, Bầu cử, Tăng lãi suất).
        Trả về JSON: {{"symbol": "MÃ", "intent": "SPECIFIC_EVENT" hoặc "GENERAL_ADVICE"}}
        """
        router_res = groq_client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role': 'user', 'content': router_prompt}], temperature=0.0)
        parsed_router = parse_llm_json(router_res.choices[0].message.content)
        symbol = parsed_router.get("symbol", "").upper().strip()
        
        # ==================================
        # KHÓA CHẶT ROUTER BẰNG PYTHON
        # ==================================
        prompt_lower = prompt.lower()
        if any(kw in prompt_lower for kw in ["kết quả kinh doanh", "báo cáo tài chính", "có nên mua", "tiềm năng", "đánh giá mã", "phân tích"]):
            intent = "GENERAL_ADVICE"
        else:
            intent = parsed_router.get("intent", "GENERAL_ADVICE").upper()

        if not symbol or not is_valid_ticker(symbol): 
            return {'ai_analysis': f'⚠️ Không tìm thấy hoặc không hỗ trợ phân tích mã {symbol}.', 'status': 'success'}

        fin_records = get_financial_data_with_wait(symbol, max_wait_seconds=15)
        
        if fin_records:
            fin_table_md = build_matrix_markdown_table(fin_records)
            fin_context = json.dumps(fin_records, ensure_ascii=False)
            strict_finance_rule = "BẮT BUỘC nhìn vào chuỗi thời gian của các quý để đánh giá xu hướng Doanh thu/LNST. TRÍCH DẪN con số trực tiếp từ BCTC để làm luận cứ."
        else:
            fin_table_md = "> *⚠️ Không trích xuất được số liệu tài chính. Phân tích sẽ dựa trên động lực ngành và tin tức.*\n\n"
            fin_context = "KHÔNG CÓ DỮ LIỆU TÀI CHÍNH."
            strict_finance_rule = "BỎ QUA PHÂN TÍCH SỐ LIỆU TÀI CHÍNH. TẬP TRUNG 100% VÀO TIN TỨC VÀ ĐỘNG LỰC NGÀNH."

        # ---------------------------------------------------------------------
        # LUỒNG 1: BÁO CÁO TƯ VẤN CHUYÊN NGHIỆP
        # ---------------------------------------------------------------------
        if intent == "GENERAL_ADVICE":
            news = agent3_search_macro_news(f"Sự kiện vĩ mô, tin tức trọng yếu, hợp đồng mới, dự án của doanh nghiệp cổ phiếu {symbol} mới nhất hiện tại")
            gen_prompt = f"""
            Bạn là Chuyên gia Phân tích Đầu tư Cao cấp (Senior Equity Analyst) tại một công ty chứng khoán hàng đầu.
            Nhiệm vụ: Viết báo cáo tư vấn đầu tư chuyên sâu, logic và thuyết phục cho mã {symbol}.

            [LỊCH SỬ BCTC CÁC QUÝ GẦN NHẤT]: {fin_context}
            [TIN TỨC THỊ TRƯỜNG HIỆN TẠI TỪ WEB]: {news}
            
            🚨 KỶ LUẬT VĂN PHONG TỐI THƯỢNG:
            1. {strict_finance_rule}
            2. Viết thành các ĐOẠN VĂN CHI TIẾT. Kết hợp chặt chẽ giữa TIN TỨC thực tế và LUẬN ĐIỂM ĐẦU TƯ. Tránh viết những câu chung chung, sáo rỗng.
            3. Ngôn từ chuẩn mực, học thuật, mang tính khách quan của dân phân tích tài chính chuyên nghiệp. CẤM dùng các từ như "Cá mập", "Tử huyệt", "Thực chiến".
            4. QUAN TRỌNG: TUYỆT ĐỐI KHÔNG in ra các dãy số dài (Ví dụ: 12479997206775). BẮT BUỘC quy đổi và định dạng lại thành "tỷ đồng" hoặc "nghìn tỷ đồng" (Ví dụ: 12.480 tỷ đồng) để dễ đọc.
            
            [YÊU CẦU ĐẦU RA - CHỈ TRẢ VỀ JSON THUẦN]:
            {{
                "market_context": "Đánh giá bối cảnh vĩ mô và ngành. Nêu rõ các sự kiện, hợp đồng, hoặc tin tức nổi bật đang diễn ra với doanh nghiệp (Ít nhất 4-5 câu).",
                "financial_health": "Đánh giá sức khỏe tài chính. Trích dẫn số liệu BCTC và dùng tin tức để giải thích động lực đằng sau sự tăng/giảm của Doanh thu và Lợi nhuận (Ít nhất 4-5 câu).",
                "catalysts_and_risks": "Phân tích khách quan về các Yếu tố hỗ trợ tăng trưởng (Catalysts) và Rủi ro đầu tư tiềm ẩn (Ít nhất 4-5 câu).",
                "actionable_strategy": "Khuyến nghị chiến lược hành động. Giải thích rõ ràng luận điểm đầu tư và vùng giá kỳ vọng.",
                "final_rating": "KHUYẾN NGHỊ: (MUA / NẮM GIỮ / QUAN SÁT / BÁN)"
            }}
            """
            res = groq_client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role': 'user', 'content': gen_prompt}], temperature=0.35, max_tokens=3000)
            ai = parse_llm_json(res.choices[0].message.content)
            
            markdown = f"### 📑 BÁO CÁO PHÂN TÍCH ĐẦU TƯ: MÃ {symbol}\n\n{fin_table_md}"
            markdown += f"#### 🌐 1. BỐI CẢNH VĨ MÔ & ĐỘNG LỰC NGÀNH\n> {ai.get('market_context', '')}\n\n"
            markdown += f"#### 📊 2. ĐÁNH GIÁ SỨC KHỎE TÀI CHÍNH\n> {ai.get('financial_health', '')}\n\n"
            markdown += f"#### ⚡ 3. CHẤT XÚC TÁC (CATALYSTS) & RỦI RO\n> {ai.get('catalysts_and_risks', '')}\n\n"
            markdown += f"#### 🎯 4. CHIẾN LƯỢC GIAO DỊCH KHUYẾN NGHỊ\n> {ai.get('actionable_strategy', '')}\n\n"
            markdown += f"---\n### 💡 KẾT LUẬN HÀNH ĐỘNG: **{ai.get('final_rating', 'QUAN SÁT')}**"

        # ---------------------------------------------------------------------
        # LUỒNG 2: PHÂN TÍCH TÁC ĐỘNG SỰ KIỆN VĨ MÔ
        # ---------------------------------------------------------------------
        else:
            macro_news = agent3_search_macro_news(prompt)
            sc_logic = get_supply_chain_logic(symbol)
            factors_to_analyze = load_gold_factors(symbol, BASE_DIR)
            sc_context = f"- Đầu vào: {sc_logic.get('input_driver', 'Chưa rõ')}\n- Đầu ra: {sc_logic.get('output_driver', 'Chưa rõ')}" if sc_logic else "Phân tích theo đặc thù ngành."

            mac_prompt = f"""
            Bạn là Chuyên gia Phân tích Vĩ mô (Macro Analyst). 
            Đánh giá khách quan tác động của sự kiện đối với mã {symbol}.
            [SỰ KIỆN]: {prompt} | [TIN TỨC]: {macro_news} | [BCTC]: {fin_context} | [ĐẶC THÙ]: {sc_context}
            
            🚨 KỶ LUẬT THÉP: {strict_finance_rule}
            TUYỆT ĐỐI KHÔNG in ra dãy số quá dài, hãy quy đổi ra "tỷ đồng" hoặc "nghìn tỷ đồng".
            
            [YÊU CẦU JSON]:
            {{
                "event_nature": "Bản chất sự kiện tác động đến chuỗi cung ứng hoặc tâm lý nhà đầu tư (2 câu).",
                "impact_direction": "TÍCH CỰC / TIÊU CỰC / TRUNG LẬP",
                "factor_1_name": "Tên chỉ báo 1", "factor_1_trend": "TĂNG / GIẢM / KHÔNG ĐỔI", "factor_1_reason": "Giải thích cơ chế kinh tế cốt lõi.",
                "factor_2_name": "Tên chỉ báo 2", "factor_2_trend": "TĂNG / GIẢM / KHÔNG ĐỔI", "factor_2_reason": "Giải thích cơ chế kinh tế cốt lõi.",
                "final_verdict": "Kết luận tác động tổng quan."
            }}
            """
            res = groq_client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role': 'user', 'content': mac_prompt}], temperature=0.1, max_tokens=2000)
            ai = parse_llm_json(res.choices[0].message.content)

            markdown = f"### 📰 ĐÁNH GIÁ TÁC ĐỘNG SỰ KIỆN: MÃ {symbol}\n\n{fin_table_md}"
            markdown += f"**BẢN CHẤT SỰ KIỆN:**\n> {ai.get('event_nature', '')}\n\n"
            markdown += f"#### 🎯 MỔ XẺ CƠ CHẾ TRUYỀN DẪN KINH TẾ\n| Chỉ báo | Chiều tác động | Cơ chế truyền dẫn cốt lõi |\n|:---|:---:|:---|\n"
            for i in range(1, 3):
                if fname := ai.get(f'factor_{i}_name'):
                    ftrend = ai.get(f'factor_{i}_trend', 'KHÔNG ĐỔI')
                    icon = "🟢" if "TĂNG" in ftrend.upper() else ("🔴" if "GIẢM" in ftrend.upper() else "⚪")
                    markdown += f"| **{fname}** | {icon} **{ftrend.upper()}** | {ai.get(f'factor_{i}_reason', '')} |\n"

            markdown += f"\n#### ⚖️ KẾT LUẬN: Tác động {ai.get('impact_direction', 'TRUNG LẬP')}\n> {ai.get('final_verdict', '')}\n"

        final_response = {'ai_analysis': markdown, 'symbol': symbol, 'status': 'success'}
        
        if fin_records and "error" not in str(fin_records):
            save_to_cache(prompt, final_response) 
            
        return final_response

    except Exception as e:
        return {'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'}
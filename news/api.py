"""
news/api.py
============
BẢN NÂNG CẤP HOÀN CHỈNH - GIAO DIỆN CHUYÊN NGHIỆP & BÁO CÁO CHUẨN MỰC
Bổ sung: Luồng EVENT_SCREENING (Top-Down) để tìm kiếm các mã bị ảnh hưởng bởi sự kiện.
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
    is_valid_ticker, get_from_cache, save_to_cache,
    AVAILABLE_SECTORS, extract_tickers_from_query # <--- ĐÃ IMPORT THÊM CÔNG CỤ MỚI
)
from quant_engine import load_gold_factors, get_factor_trend_data

app = FastAPI(title="Multi-Agent Router", version="15.5.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def serve_ui():
    return FileResponse("frontend/index.html")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")      
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")   
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")

groq_client   = Groq(api_key=GROQ_API_KEY)
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

    try:
        financial_records = sorted(financial_records, key=lambda x: str(x.get('quy', '')))
    except:
        pass

    quarters_headers = [str(item.get('quy', 'N/A')) for item in financial_records]
    indicators = {
        'Doanh Thu Thuần (VND)':   'doanh_thu',
        'Lợi Nhuận Gộp (VND)':     'ln_gop',
        'Lợi Nhuận Sau Thuế (VND)':'lnst',
        'Tổng Tài Sản (VND)':      'tong_tai_san',
        'Vốn Chủ Sở Hữu (VND)':   'von_csh',
        'Nợ Phải Trả (VND)':       'no_phai_tra',
        'Thu nhập trên CP (EPS)':   'eps',
        'Biên LN Gộp (%)':          'bien_ln_gop',
        'ROE (%)':                   'roe',
        'Hệ số P/E':                 'pe',
    }

    table_str  = '| Chỉ tiêu Tài chính | ' + ' | '.join(quarters_headers) + ' |\n'
    table_str += '| :--- | ' + ' | '.join([' :---: ' for _ in quarters_headers]) + ' |\n'

    has_any_data = False
    for label, key in indicators.items():
        row_cells = []
        has_meaningful = False
        for item in financial_records:
            value = item.get(key, 0)
            if isinstance(value, (int, float)) and value != 0:
                has_meaningful = True
                has_any_data   = True
                if '%' in label or label == 'Hệ số P/E':
                    row_cells.append(f'{value:.2f}')
                else:
                    row_cells.append(f'{value:,.0f}')
            else:
                row_cells.append('-')
        if has_meaningful:
            table_str += f'| **{label}** | ' + ' | '.join(row_cells) + ' |\n'

    if not has_any_data:
        return ""
    return f"**📊 MA TRẬN TÀI CHÍNH TỔNG HỢP (Nguồn: Vnstock)**\n\n{table_str}\n\n"


def get_financial_data_with_wait(symbol: str, max_wait_seconds: int = 15):
    # Ghi vào watchlist để agent1 biết cần cào ticker này
    try:
        with watchlist_lock:
            wl = {}
            if os.path.exists(WATCHLIST_FILE):
                try:
                    with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
                        wl = json.load(f)
                except:
                    pass
            wl[symbol] = datetime.now().strftime("%Y-%m-%d")
            with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(wl, f, ensure_ascii=False, indent=4)
    except:
        pass

    for _ in range(max_wait_seconds):
        try:
            with data_lock:
                if os.path.exists(DATA_FILE):
                    with open(DATA_FILE, 'r', encoding='utf-8') as f:
                        warehouse = json.load(f)
                    data = warehouse.get(symbol)
                    if data and "error" not in str(data):
                        if isinstance(data, dict):
                            return [data]
                        return data
        except:
            pass
        time.sleep(1)

    return None


def get_supply_chain_logic(symbol: str):
    try:
        with sc_lock:
            with open(SUPPLY_CHAIN_FILE, 'r', encoding='utf-8') as f:
                sc_data = json.load(f)
            for sector, tickers in sc_data.items():
                if symbol in tickers:
                    return tickers[symbol]
    except:
        pass
    return None


def agent3_search_macro_news(query: str) -> str:
    combined_results = ""
    try:
        serper_res = requests.post(
            'https://google.serper.dev/search',
            headers={'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'},
            data=json.dumps({'q': query, 'num': 4}),
            timeout=5,
        ).json()
        for item in serper_res.get('organic', []):
            combined_results += f"- {item.get('title')}: {item.get('snippet')}\n"
    except:
        pass

    try:
        tavily_res = tavily_client.search(query=query, search_depth='basic', max_results=3)
        for item in tavily_res.get('results', []):
            combined_results += f"- {item.get('content')}\n"
    except:
        pass

    return combined_results.strip() or "Không tìm thấy dữ liệu tin tức thị trường."


def parse_llm_json(raw_text: str) -> dict:
    try:
        cleaned = raw_text.replace('```json', '').replace('```', '').strip()
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        print(f"[parse_llm_json] Không tìm thấy JSON trong: {raw_text[:300]}")
        return {}
    except Exception as e:
        print(f"[parse_llm_json] Lỗi parse: {e} | Raw: {raw_text[:300]}")
        return {}


# ======================================================================
# MAIN ENDPOINT
# ======================================================================

@app.post('/api/ask_agent')
def ask_financial_agent(req: AgentRequest):
    try:
        prompt = req.prompt.strip()

        # 1. CACHE CHECK
        cached = get_from_cache(prompt)
        if cached:
            return cached

        # 2. AI ROUTER (CẬP NHẬT THÊM INTENT SCREENING)
        router_prompt = f"""
        Phân loại ý định người dùng. Câu hỏi: '{prompt}'
        - "GENERAL_ADVICE": Báo cáo tài chính, kết quả kinh doanh, có nên mua bán, phân tích 1 mã chung chung.
        - "SPECIFIC_EVENT": CÓ SỰ KIỆN VĨ MÔ TỪ BÊN NGOÀI ảnh hưởng đến 1 mã cổ phiếu CỤ THỂ.
        - "EVENT_SCREENING": Hỏi về SỰ KIỆN VĨ MÔ/NGÀNH nhưng KHÔNG CHỈ ĐỊNH rõ mã cổ phiếu nào (VD: Giá thép giảm ảnh hưởng nhóm nào?).
        Trả về JSON: {{"symbol": "MÃ CỔ PHIẾU (nếu có, không có thì để rỗng)", "intent": "TÊN_INTENT_Ở_TRÊN"}}
        """
        router_res = groq_client.chat.completions.create(
            model='qwen/qwen3.6-27b',
            messages=[{'role': 'user', 'content': router_prompt}],
            temperature=0.0,
        )
        parsed_router = parse_llm_json(router_res.choices[0].message.content)
        
        symbol = parsed_router.get("symbol", "").upper().strip()
        intent = parsed_router.get("intent", "EVENT_SCREENING").upper()

        # Áp dụng Hardcode rule để dự phòng an toàn
        prompt_lower = prompt.lower()
        if any(kw in prompt_lower for kw in ["kết quả kinh doanh", "báo cáo tài chính", "có nên mua", "tiềm năng", "đánh giá mã", "phân tích"]):
            if symbol: intent = "GENERAL_ADVICE"

        # Nếu router không tìm thấy mã, hoặc người dùng chỉ hỏi sự kiện chung chung
        if intent == "EVENT_SCREENING" or (not symbol and "GENERAL_ADVICE" not in intent):
            intent = "EVENT_SCREENING"

        # Nếu không phải screening mà thiếu mã, thử dùng Regex cứu vãn
        if intent != "EVENT_SCREENING" and (not symbol or not is_valid_ticker(symbol)):
            found = extract_tickers_from_query(prompt)
            if found:
                symbol = found[0]
            else:
                intent = "EVENT_SCREENING" # Bắt buộc qua screening nếu hoàn toàn không có mã

        # ──────────────────────────────────────────────────────────────
        # LUỒNG 3 (MỚI): QUÉT SỰ KIỆN & TÌM MÃ CỔ PHIẾU BỊ ẢNH HƯỞNG
        # ──────────────────────────────────────────────────────────────
        if intent == "EVENT_SCREENING":
            news = agent3_search_macro_news(prompt)
            sectors_json = json.dumps(AVAILABLE_SECTORS, ensure_ascii=False, indent=2)
            
            screen_prompt = f"""
            Bạn là một Chuyên gia Chiến lược Đầu tư Vĩ mô.
            Sự kiện người dùng hỏi: "{prompt}"
            Tin tức thời gian thực: {news}

            Hệ thống của chúng tôi CHỈ theo dõi 10 nhóm ngành và các mã cổ phiếu sau:
            {sectors_json}

            Nhiệm vụ của bạn:
            1. Đánh giá sự kiện này tác động TÍCH CỰC hay TIÊU CỰC đến những ngành nào trong danh sách trên.
            2. Từ các ngành bị ảnh hưởng, hãy TÌM VÀ NÊU TÊN CHÍNH XÁC các mã cổ phiếu có mặt trong danh mục.
            3. Giải thích logic kinh tế học hoặc mô hình kinh doanh cốt lõi giải thích vì sao nhóm cổ phiếu đó lại bị ảnh hưởng.
            4. KHÔNG BỊA ĐẶT thêm mã ngoài danh sách. Nếu không có ngành/mã nào liên quan, hãy trả lời rõ.
            
            [YÊU CẦU JSON THUẦN]:
            {{
                "analysis_markdown": "Trình bày báo cáo của bạn bằng Markdown chuyên nghiệp (có in đậm, bullet points giải thích lý do).",
                "affected_tickers": ["MÃ 1", "MÃ 2"],
                "impact_direction": "TÍCH CỰC / TIÊU CỰC / TRUNG LẬP"
            }}
            """
            res = groq_client.chat.completions.create(
                model='qwen/qwen3.6-27b',
                messages=[{'role': 'user', 'content': screen_prompt}],
                temperature=0.2,
                max_tokens=2000,
            )
            ai = parse_llm_json(res.choices[0].message.content)
            
            markdown = ai.get("analysis_markdown", "Đang xử lý dữ liệu...")
            affected_tickers = ai.get("affected_tickers", [])
            impact = ai.get("impact_direction", "TRUNG LẬP").upper()
            direction = "positive" if "TÍCH CỰC" in impact else ("negative" if "TIÊU CỰC" in impact else "mixed")
            
            # Kích hoạt Agent 1: Đẩy các mã tìm thấy vào watchlist để tải BCTC chuẩn bị cho câu hỏi tiếp theo
            if affected_tickers:
                try:
                    with watchlist_lock:
                        wl = {}
                        if os.path.exists(WATCHLIST_FILE):
                            try:
                                with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
                                    wl = json.load(f)
                            except: pass
                        for tk in affected_tickers:
                            if is_valid_ticker(tk):
                                wl[tk] = datetime.now().strftime("%Y-%m-%d")
                        with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
                            json.dump(wl, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    print(f"Lỗi ghi watchlist tự động: {e}")

            final_response = {
                'ai_analysis': f"### 🌍 LỌC CỔ PHIẾU THEO TÁC ĐỘNG SỰ KIỆN\n\n{markdown}",
                'affected_factors': affected_tickers, # Mượn trường này trả về mảng ticker cho UI
                'direction': direction,
                'symbol': ", ".join(affected_tickers) if affected_tickers else "VĨ MÔ",
                'status': 'success'
            }
            save_to_cache(prompt, final_response)
            return final_response

        # ──────────────────────────────────────────────────────────────
        # NẾU CÓ MÃ CỤ THỂ, LẤY BCTC ĐỂ CHẠY LUỒNG 1 HOẶC 2
        # ──────────────────────────────────────────────────────────────
        fin_records = get_financial_data_with_wait(symbol, max_wait_seconds=15)
        factors_to_analyze = load_gold_factors(symbol, BASE_DIR)  

        if fin_records:
            fin_table_md   = build_matrix_markdown_table(fin_records)
            fin_context    = json.dumps(fin_records, ensure_ascii=False)
            strict_finance = "BẮT BUỘC nhìn vào chuỗi thời gian các quý để đánh giá xu hướng Doanh thu/LNST. TRÍCH DẪN con số trực tiếp từ BCTC làm luận cứ."
        else:
            fin_table_md   = "> *⚠️ Không trích xuất được số liệu tài chính. Phân tích dựa trên động lực ngành và tin tức.*\n\n"
            fin_context    = "KHÔNG CÓ DỮ LIỆU TÀI CHÍNH."
            strict_finance = "BỎ QUA PHÂN TÍCH SỐ LIỆU TÀI CHÍNH. TẬP TRUNG 100% VÀO TIN TỨC VÀ ĐỘNG LỰC NGÀNH."

        # ──────────────────────────────────────────────────────────────
        # LUỒNG 1: BÁO CÁO TƯ VẤN CHUYÊN NGHIỆP (MÃ CỤ THỂ)
        # ──────────────────────────────────────────────────────────────
        if intent == "GENERAL_ADVICE":
            news = agent3_search_macro_news(
                f"Sự kiện vĩ mô, tin tức trọng yếu, hợp đồng mới, dự án của doanh nghiệp cổ phiếu {symbol} mới nhất hiện tại"
            )
            gen_prompt = f"""
            Bạn là Chuyên gia Phân tích Đầu tư Cao cấp (Senior Equity Analyst).
            Nhiệm vụ: Viết báo cáo tư vấn đầu tư chuyên sâu cho mã {symbol}.

            [LỊCH SỬ BCTC CÁC QUÝ GẦN NHẤT]: {fin_context}
            [TIN TỨC THỊ TRƯỜNG HIỆN TẠI]: {news}

            🚨 KỶ LUẬT VĂN PHONG:
            1. {strict_finance}
            2. Viết thành đoạn văn chi tiết. Kết hợp chặt chẽ TIN TỨC và LUẬN ĐIỂM ĐẦU TƯ.
            3. Ngôn từ chuẩn mực, học thuật. CẤM dùng "Cá mập", "Tử huyệt", "Thực chiến".
            4. TUYỆT ĐỐI KHÔNG in dãy số dài. BẮT BUỘC quy đổi ra "tỷ đồng" hoặc "nghìn tỷ đồng".

            [YÊU CẦU JSON THUẦN]:
            {{
                "market_context": "Bối cảnh vĩ mô và ngành, sự kiện/hợp đồng/tin tức nổi bật (4-5 câu).",
                "financial_health": "Sức khỏe tài chính, trích dẫn số liệu BCTC và giải thích động lực (4-5 câu).",
                "catalysts_and_risks": "Yếu tố hỗ trợ tăng trưởng (Catalysts) và Rủi ro tiềm ẩn (4-5 câu).",
                "actionable_strategy": "Chiến lược hành động và vùng giá kỳ vọng.",
                "final_rating": "KHUYẾN NGHỊ: (MUA / NẮM GIỮ / QUAN SÁT / BÁN)"
            }}
            """
            res = groq_client.chat.completions.create(
                model='qwen/qwen3.6-27b',
                messages=[{'role': 'user', 'content': gen_prompt}],
                temperature=0.35,
                max_tokens=2000,
            )
            ai = parse_llm_json(res.choices[0].message.content)

            if not ai or not ai.get('market_context'):
                print(f"[LUỒNG 1] JSON rỗng lần 1, retry...")
                time.sleep(3)
                res2 = groq_client.chat.completions.create(
                    model='qwen/qwen3.6-27b',
                    messages=[{'role': 'user', 'content': gen_prompt}],
                    temperature=0.35,
                    max_tokens=1500,
                )
                ai = parse_llm_json(res2.choices[0].message.content)

            if not ai or not ai.get('market_context'):
                print(f"[LUỒNG 1] JSON vẫn rỗng sau retry, trả fallback")
                affected_factors = [f["name"] for f in factors_to_analyze] if factors_to_analyze else []
                return {
                    'ai_analysis': (
                        f"### 📑 BÁO CÁO PHÂN TÍCH: MÃ {symbol}\n\n"
                        f"{fin_table_md}"
                        f"> ⚠️ Không thể phân tích chi tiết do giới hạn API (rate limit). "
                        f"Vui lòng thử lại sau 30-60 giây.\n\n"
                        f"**Dữ liệu tài chính đã có sẵn trong bảng trên.**"
                    ),
                    'affected_factors': affected_factors,
                    'direction':        'mixed',
                    'symbol':           symbol,
                    'status':           'success',
                }

            markdown  = f"### 📑 BÁO CÁO PHÂN TÍCH ĐẦU TƯ: MÃ {symbol}\n\n{fin_table_md}"
            markdown += f"#### 🌐 1. BỐI CẢNH VĨ MÔ & ĐỘNG LỰC NGÀNH\n> {ai.get('market_context', '')}\n\n"
            markdown += f"#### 📊 2. ĐÁNH GIÁ SỨC KHỎE TÀI CHÍNH\n> {ai.get('financial_health', '')}\n\n"
            markdown += f"#### ⚡ 3. CHẤT XÚC TÁC (CATALYSTS) & RỦI RO\n> {ai.get('catalysts_and_risks', '')}\n\n"
            markdown += f"#### 🎯 4. CHIẾN LƯỢC GIAO DỊCH KHUYẾN NGHỊ\n> {ai.get('actionable_strategy', '')}\n\n"
            markdown += f"---\n### 💡 KẾT LUẬN: **{ai.get('final_rating', 'QUAN SÁT')}**"

            affected_factors = [f["name"] for f in factors_to_analyze] if factors_to_analyze else []
            rating = ai.get("final_rating", "").upper()
            direction = "positive" if "MUA" in rating else ("negative" if "BÁN" in rating else "mixed")

        # ──────────────────────────────────────────────────────────────
        # LUỒNG 2: PHÂN TÍCH TÁC ĐỘNG SỰ KIỆN VĨ MÔ LÊN MÃ CỤ THỂ
        # ──────────────────────────────────────────────────────────────
        else:
            macro_news = agent3_search_macro_news(prompt)
            sc_logic   = get_supply_chain_logic(symbol)
            sc_context = (
                f"- Đầu vào: {sc_logic.get('input_driver', 'Chưa rõ')}\n"
                f"- Đầu ra: {sc_logic.get('output_driver', 'Chưa rõ')}"
                if sc_logic else "Phân tích theo đặc thù ngành."
            )

            factors_context = ""
            if factors_to_analyze:
                factor_names = [f["name"] for f in factors_to_analyze]
                factors_context = (
                    f"Các factors có tương quan mạnh nhất với giá CP {symbol}: {factor_names}. "
                    f"Ưu tiên phân tích tác động lên các factors này."
                )

            mac_prompt = f"""
            Bạn là Chuyên gia Phân tích Vĩ mô (Macro Analyst).
            Đánh giá khách quan tác động của sự kiện đối với mã {symbol}.
            [SỰ KIỆN]: {prompt}
            [TIN TỨC]: {macro_news}
            [BCTC]: {fin_context}
            [ĐẶC THÙ CHUỖI CUNG ỨNG]: {sc_context}
            [FACTORS QUAN TRỌNG NHẤT]: {factors_context}

            🚨 KỶ LUẬT THÉP: {strict_finance}
            TUYỆT ĐỐI KHÔNG in dãy số dài, quy đổi ra "tỷ đồng" hoặc "nghìn tỷ đồng".

            [YÊU CẦU JSON]:
            {{
                "event_nature": "Bản chất sự kiện tác động (2 câu).",
                "impact_direction": "TÍCH CỰC / TIÊU CỰC / TRUNG LẬP",
                "factor_1_name": "Tên chỉ báo 1 (ưu tiên từ factors quan trọng nhất)",
                "factor_1_trend": "TĂNG / GIẢM / KHÔNG ĐỔI",
                "factor_1_reason": "Cơ chế kinh tế cốt lõi.",
                "factor_2_name": "Tên chỉ báo 2 (ưu tiên từ factors quan trọng nhất)",
                "factor_2_trend": "TĂNG / GIẢM / KHÔNG ĐỔI",
                "factor_2_reason": "Cơ chế kinh tế cốt lõi.",
                "final_verdict": "Kết luận tác động tổng quan."
            }}
            """
            res = groq_client.chat.completions.create(
                model='qwen/qwen3.6-27b',
                messages=[{'role': 'user', 'content': mac_prompt}],
                temperature=0.1,
                max_tokens=2000,
            )
            ai = parse_llm_json(res.choices[0].message.content)

            if not ai or not ai.get('event_nature'):
                print(f"[LUỒNG 2] JSON rỗng lần 1, retry...")
                time.sleep(3)
                res2 = groq_client.chat.completions.create(
                    model='qwen/qwen3.6-27b',
                    messages=[{'role': 'user', 'content': mac_prompt}],
                    temperature=0.1,
                    max_tokens=1000,
                )
                ai = parse_llm_json(res2.choices[0].message.content)

            if not ai or not ai.get('event_nature'):
                affected_factors = [ai.get(f"factor_{i}_name","") for i in range(1,3) if ai.get(f"factor_{i}_name","")]
                fallback_factors = [f["name"] for f in factors_to_analyze] if factors_to_analyze else []
                return {
                    'ai_analysis': f"⚠️ Không phân tích được sự kiện cho {symbol} (rate limit). Thử lại sau.",
                    'affected_factors': affected_factors or fallback_factors,
                    'direction': 'mixed', 'symbol': symbol, 'status': 'success',
                }

            markdown  = f"### 📰 ĐÁNH GIÁ TÁC ĐỘNG SỰ KIỆN: MÃ {symbol}\n\n{fin_table_md}"
            markdown += f"**BẢN CHẤT SỰ KIỆN:**\n> {ai.get('event_nature', '')}\n\n"
            markdown += "#### 🎯 MỔ XẺ CƠ CHẾ TRUYỀN DẪN KINH TẾ\n"
            markdown += "| Chỉ báo | Chiều tác động | Cơ chế truyền dẫn cốt lõi |\n|:---|:---:|:---|\n"
            for i in range(1, 3):
                fname = ai.get(f'factor_{i}_name', '')
                if fname:
                    ftrend = ai.get(f'factor_{i}_trend', 'KHÔNG ĐỔI')
                    icon   = "🟢" if "TĂNG" in ftrend.upper() else ("🔴" if "GIẢM" in ftrend.upper() else "⚪")
                    markdown += f"| **{fname}** | {icon} **{ftrend.upper()}** | {ai.get(f'factor_{i}_reason', '')} |\n"
            markdown += f"\n#### ⚖️ KẾT LUẬN: Tác động {ai.get('impact_direction', 'TRUNG LẬP')}\n> {ai.get('final_verdict', '')}\n"

            affected_factors = [ai.get(f"factor_{i}_name", "") for i in range(1, 3) if ai.get(f"factor_{i}_name")]
            impact = ai.get("impact_direction", "").upper()
            direction = "positive" if "TÍCH CỰC" in impact else ("negative" if "TIÊU CỰC" in impact else "mixed")

        # ── BUILD FINAL RESPONSE ────────────────────────────────────
        final_response = {
            'ai_analysis':      markdown,
            'affected_factors': affected_factors,   
            'direction':        direction,           
            'symbol':           symbol,
            'status':           'success',
        }

        if fin_records and "error" not in str(fin_records):
            save_to_cache(prompt, final_response)

        return final_response

    except Exception as e:
        return {'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'}
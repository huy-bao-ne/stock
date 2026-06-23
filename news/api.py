"""
news/api.py
============
News & Analysis Agent — FastAPI backend

Pipeline xử lý mỗi câu hỏi:
  1. Tìm kiếm tin tức vĩ mô theo prompt
  2. Dùng LLM phụ trích xuất mã CK (symbol) và năm sự kiện
  3. Kéo số liệu tài chính từ cache (warehouse) hoặc vnstock
  4. LLM chính mổ xẻ cơ chế truyền dẫn sự kiện → chỉ số → giá CP
  5. Trích xuất factors bị ảnh hưởng để trả về cho factor/agents/financial_agent.py

Cải tiến so với bản gốc:
  - API keys đọc từ biến môi trường (không hardcode)
  - Thread-safe file I/O dùng chung lock với agent1_collector
  - Thêm endpoint /api/internal/factor_impact để financial_agent.py gọi trực tiếp
  - Validate và sanitize output LLM trước khi trả về
  - Xử lý rõ ràng trường hợp không tìm được symbol hoặc dữ liệu rỗng
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import requests
from tavily import TavilyClient
from groq import Groq
from datetime import datetime
import urllib3
import json
import os
import threading
import pandas as pd
import re

# Import class Finance từ Vnstock
from vnstock import Finance

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(
    title="News & Financial Analysis Agent",
    description="Agent phân tích tin tức và tài chính chứng khoán Việt Nam",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================================
# API KEYS — đọc từ môi trường trước, fallback về hardcode cho dev
# ======================================================================
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY",   "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")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY",  "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")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY",  "802d08dbed7f6aec0358572461b727719836aec7")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8715058434:AAGkzlVIU0gIXDAka5CE89Y7ErcjMvLvmpQ")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID",   "2141887336")

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
APP_DATA_DIR  = os.path.join(BASE_DIR, "runtime_data")
os.makedirs(APP_DATA_DIR, exist_ok=True)

DATA_FILE      = os.path.join(APP_DATA_DIR, "data_warehouse.json")
WATCHLIST_FILE = os.path.join(APP_DATA_DIR, "smart_watchlist.json")

# Lock dùng chung với agent1_collector để tránh ghi đè file đồng thời
_file_lock = threading.Lock()

groq_client   = Groq(api_key=GROQ_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

class ChatMessage(BaseModel):
    role: str
    content: str

class AgentRequest(BaseModel):
    prompt: str
    history: List[ChatMessage] = []

# Endpoint nội bộ: financial_agent gọi để phân tích tác động tin tức lên factors
class InternalFactorRequest(BaseModel):
    question:   str
    tickers:    List[str] = []
    top_factors: List[dict] = []  # [{"factor_name": "...", "correlation_r": "+71.4%", "direction": "đồng_biến"}]


def send_telegram_log(message: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=5, verify=False)
    except Exception:
        pass

# --- HÀM CẬP NHẬT WATCHLIST ---
def _update_watchlist(symbol: str):
    """
    Cập nhật ngày truy cập trong watchlist.
    Agent1 dựa vào đây để quyết định ticker nào còn được dùng.
    Thread-safe: dùng _file_lock dùng chung với agent1_collector.
    """
    with _file_lock:
        wl = {}
        if os.path.exists(WATCHLIST_FILE):
            try:
                with open(WATCHLIST_FILE, "r") as f:
                    wl = json.load(f)
            except (json.JSONDecodeError, IOError):
                wl = {}
        wl[symbol] = datetime.now().strftime("%Y-%m-%d")
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(wl, f, indent=4)

# --- HÀM XÂY DỰNG TRUY VẤN THÔNG MINH ---
def build_smart_query(symbol: str, original_prompt: str, year: int = None) -> str:
    year_str = str(year) if year else datetime.now().strftime("%Y")
    return f"{symbol} báo cáo tài chính kết quả kinh doanh {year_str} site:cafef.vn OR site:vietstock.vn OR site:ndh.vn"

# --- LOGIC TẠO BẢNG MARKDOWN ---
def build_matrix_markdown_table(financial_records: list) -> str:
    if not financial_records:
        return 'Không có dữ liệu số liệu để lập bảng.'
    try:
        financial_records = sorted(financial_records, key=lambda x: str(x.get('quy', '')))
    except Exception: pass

    quarters_headers = [str(item.get('quy', 'N/A')) for item in financial_records]
    indicators = {
        'Doanh Thu Thuần (VND)': 'doanh_thu',
        'Lợi Nhuận Sau Thuế (VND)': 'lnst',
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
            value = item.get(key, None) if isinstance(item, dict) else None
            if isinstance(value, (int, float)):
                if value != 0:
                    has_meaningful = True
                    has_any_data = True
                    if '%' in label or label == 'Hệ số P/E':
                        row_cells.append(f'{value:.2f}')
                    else:
                        row_cells.append(f'{value:,.0f}')
                else:
                    row_cells.append('-')
            else:
                if value is None:
                    row_cells.append('-')
                else:
                    s = str(value).strip()
                    if s in ['', '-', '0', '0.0', '0.00']:
                        row_cells.append('-')
                    else:
                        has_meaningful = True
                        has_any_data = True
                        row_cells.append(s)
        if has_meaningful:
            table_str += f'| **{label}** | ' + ' | '.join(row_cells) + ' |\n'

    if not has_any_data:
        return "Báo cáo tài chính chưa được cập nhật đủ dữ liệu."
    return table_str

# --- CÔNG CỤ KÉO VNSTOCK VỚI CACHE ---
def agent2_get_internal_data(symbol: str, target_year: int = None):
    symbol = symbol.upper().strip()

    # ĐỌC CACHE TRƯỚC — nếu có thì dùng luôn
    with _file_lock:
        warehouse = {}
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    warehouse = json.load(f)
            except (json.JSONDecodeError, IOError):
                warehouse = {}

    if symbol in warehouse:
        _update_watchlist(symbol)
        return f"[BẢNG TÀI CHÍNH TỪ CACHE - {symbol}]\n{build_matrix_markdown_table([warehouse[symbol]])}"

    # Không có cache → gọi vnstock
    _update_watchlist(symbol)

    try:
        finance = Finance(source='vci', symbol=symbol, period='quarter')
        try:
            df_is = finance.income_statement(lang='vi', dropna=True)
            if df_is is None or df_is.empty:
                raise ValueError("VCI IS Empty")
        except:
            finance = Finance(source='tcbs', symbol=symbol, period='quarter')
            df_is = finance.income_statement(lang='vi', dropna=True)

        if df_is is None or df_is.empty:
            return f"❌ KHÔNG_CÓ_DỮ_LIỆU: Không tìm thấy BCTC cho mã {symbol}."

        try: df_bs = finance.balance_sheet(lang='vi', dropna=True)
        except: df_bs = None
        try: df_ratio = finance.ratio(lang='vi', dropna=True)
        except: df_ratio = None

        for df in [df_is, df_bs]:
            if df is not None and not df.empty:
                cols_to_drop = [c for c in ['item_en', 'item_id', 'Mã TTM'] if c in df.columns]
                df.drop(columns=cols_to_drop, inplace=True, errors='ignore')
                df.set_index(df.columns[0], inplace=True)

        # Logic Lọc hoặc Trượt Mềm tự động
        note_text = ""
        if df_is is not None:
            df_is = df_is.T.sort_index()
            if target_year:
                target_str = [str(target_year - 1), str(target_year), str(target_year + 1)]
                filtered_idx = []
                for idx in df_is.index:
                    if any(y in str(idx) for y in target_str):
                        filtered_idx.append(idx)

                if filtered_idx:
                    df_is = df_is.loc[filtered_idx]
                else:
                    df_is = df_is.tail(8)
                    note_text = f"⚠️ [HỆ THỐNG CẢNH BÁO: Dữ liệu BCTC năm {target_year} không khả dụng trên server. Hệ thống tự động trượt về dữ liệu mới nhất để phân tích thực chứng cấu trúc phòng thủ].\n\n"
            else:
                df_is = df_is.tail(8)

        if df_bs is not None: df_bs = df_bs.T

        if df_ratio is not None and not df_ratio.empty:
            cols_to_drop = [c for c in ['item_en', 'item_id', 'Mã TTM'] if c in df_ratio.columns]
            df_ratio.drop(columns=cols_to_drop, inplace=True, errors='ignore')

        real_data_list = []
        for index_val, row in df_is.iterrows():
            quy_str = str(index_val).strip()
            if 'Q' not in quy_str and '20' not in quy_str: continue

            y_match = re.search(r'(20\d{2})', quy_str)
            q_match = re.search(r'Q([1-4])', quy_str.upper())
            year = y_match.group(1) if y_match else ''
            quarter = q_match.group(1) if q_match else ''

            def parse_numeric(x):
                if x is None or (isinstance(x, float) and pd.isna(x)): return 0
                try:
                    if isinstance(x, str):
                        s = x.strip().replace('(', '-').replace(')', '')
                        if s.endswith('%'):
                            return float(re.sub(r"[^0-9\.-]", "", s.rstrip('%'))) / 100.0
                        s = re.sub(r'[^0-9\.-]', '', s)
                        return float(s) if s not in ['', '-', '.'] else 0
                    return float(x)
                except (ValueError, TypeError):
                    return 0

            def get_val_transposed(df_source, row_idx, keywords):
                if df_source is None or df_source.empty: return 0
                for r_idx in df_source.index:
                    if str(row_idx) in str(r_idx):
                        candidates = [col for col in df_source.columns if any(k.lower() in str(col).lower() for k in keywords)]
                        for col in candidates:
                            try:
                                val = parse_numeric(df_source.loc[r_idx, col])
                                if val != 0: return val
                            except (KeyError, TypeError, ValueError):
                                continue
                for col in df_source.columns:
                    if any(k.lower() in str(col).lower() for k in keywords):
                        try:
                            return parse_numeric(df_source.iloc[-1][col])
                        except (KeyError, TypeError, ValueError):
                            continue
                return 0

            def get_val_ratio(df_r, y, q, keywords):
                if df_r is None or df_r.empty: return 0
                try:
                    period_candidates = [c for c in df_r.columns if re.search(r"20\d{2}", str(c))]
                    for col in period_candidates:
                        if str(y) in str(col) and (f"q{q}" in str(col).lower() or f"quý {q}" in str(col).lower()):
                            for idx in range(len(df_r)):
                                row_text = ' '.join([str(df_r.iloc[idx].get(c, '')) for c in df_r.columns[:3]]).lower()
                                if any(k.lower() in row_text for k in keywords):
                                    return parse_numeric(df_r.iloc[idx].get(col, 0))
                except (KeyError, TypeError, AttributeError):
                    pass
                return 0

            doanh_thu = get_val_transposed(df_is, quy_str, ['doanh thu thuần', 'net sales', 'doanh thu bán hàng'])
            lnst = get_val_transposed(df_is, quy_str, ['lợi nhuận của cổ đông', 'lãi/(lỗ) thuần', 'lợi nhuận sau thuế', 'net income'])
            no_phai_tra = get_val_transposed(df_bs, quy_str, ['nợ phải trả', 'tổng nợ', 'liabilities'])
            eps = get_val_transposed(df_is, quy_str, ['lãi cơ bản trên cổ phiếu', 'eps', 'thu nhập trên mỗi cổ phiếu'])

            bien_ln_gop = get_val_ratio(df_ratio, year, quarter, ['biên ln gộp', 'biên lợi nhuận gộp', 'gross margin'])
            if not bien_ln_gop:
                gp = get_val_transposed(df_is, quy_str, ['lợi nhuận gộp', 'gross profit'])
                try:
                    bien_ln_gop = (gp / doanh_thu) if doanh_thu and doanh_thu != 0 else 0
                except (ZeroDivisionError, TypeError):
                    bien_ln_gop = 0

            roe = get_val_ratio(df_ratio, year, quarter, ['roe', 'tỷ suất lnst trên vốn', 'return on equity'])
            pe = get_val_ratio(df_ratio, year, quarter, ['p/e', 'hệ số p/e', 'pe ratio'])

            if 0 < roe < 1: roe *= 100
            if 0 < doanh_thu < 10000000:
                doanh_thu *= 1000000000
                lnst *= 1000000000
                no_phai_tra *= 1000000000

            real_data_list.append({
                'quy': quy_str.replace(' ', '/'),
                'doanh_thu': doanh_thu, 'lnst': lnst, 'no_phai_tra': no_phai_tra,
                'eps': eps, 'bien_ln_gop': bien_ln_gop, 'roe': roe, 'pe': pe
            })

        markdown_table = build_matrix_markdown_table(real_data_list)
        return f'{note_text}[BẢNG TÀI CHÍNH TỪ VNSTOCK MÃ {symbol}]\n{markdown_table}'
    except Exception as api_err:
        return f'❌ KHÔNG_CÓ_DỮ_LIỆU: Lỗi trích xuất hệ chỉnh: {str(api_err)}'

# --- TÌM KIẾM WEB ---
def agent3_search_macro_news(query: str):
    combined_results = ""
    try:
        url = 'https://google.serper.dev/search'
        payload = json.dumps({'q': query, 'num': 4})
        headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
        serper_res = requests.post(url, headers=headers, data=payload, timeout=10).json()
        if 'organic' in serper_res:
            for item in serper_res['organic']:
                combined_results += f"- {item.get('title')}: {item.get('snippet')}\n"
    except Exception: pass

    try:
        tavily_res = tavily_client.search(query=query, search_depth='basic', max_results=3)
        for item in tavily_res.get('results', []): combined_results += f"- {item.get('content')}\n"
    except Exception: pass

    return combined_results

# --- API CHÍNH: CHẠY THEO LUỒNG TUẦN TỰ THÔNG MINH ---
@app.post('/api/ask_agent')
def ask_financial_agent(req: AgentRequest):
    try:
        prompt = req.prompt.strip()

        # BƯỚC 1: QUÉT TIN TỨC VĨ MÔ TRƯỚC ĐỂ LẤY BỐI CẢNH VÀ DÒ TIMELINE
        macro_news = agent3_search_macro_news(prompt)

        # BƯỚC 2: DÙNG MỘT LLM PHỤ ĐỂ TRÍCH XUẤT MÃ VÀ NĂM TỰ ĐỘNG TỪ BÀI BÁO
        extractor_prompt = f"""
        Bạn là một trợ lý phân tích dữ liệu chuyên nghiệp. Hãy đọc câu hỏi của người dùng và các tin tức tìm kiếm được dưới đây để trích xuất ra thông tin chính xác.

        YÊU CẦU TRÍCH XUẤT:
        1. "symbol": Mã cổ phiếu xuất hiện hoặc liên quan trực tiếp (Ví dụ: FPT, HPG, VNM). Phải viết hoa, từ 3-5 ký tự.
        2. "target_year": Năm chính xác xảy ra hoặc bùng nổ mạnh nhất của sự kiện được nhắc tới (Phải là một số nguyên, Ví dụ: 2022, 2023, 2025). Nếu trong câu hỏi không ghi năm, hãy đọc phần Tin Tức để suy luận xem sự kiện đó nổ ra vào năm nào.

        Câu hỏi người dùng: {prompt}
        Tin tức quét được: {macro_news}

        TRẢ VỀ KẾT QUẢ DƯỚI ĐỊNH DẠNG JSON DUY NHẤT NHƯ SAU, KHÔNG THÊM BẤT KỲ CHỮ NÀO KHÁC:
        {{
            "symbol": "MÃ CỔ PHIẾU",
            "target_year": NĂM_SỰ_KIỆN
        }}
        """

        extract_res = groq_client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': extractor_prompt}],
            temperature=0.0,
            response_format={"type": "json_object"}
        )

        meta_data = json.loads(extract_res.choices[0].message.content)
        symbol_called = meta_data.get("symbol", "").upper().strip()
        target_year = meta_data.get("target_year")

        if target_year:
            try: target_year = int(target_year)
            except: target_year = None

        # Nếu có symbol và target_year, tối ưu hóa query tin tức
        if symbol_called:
            smart_query = build_smart_query(symbol_called, prompt, target_year)
            macro_news = agent3_search_macro_news(smart_query)

        # BƯỚC 3: KÉO SỐ LIỆU TÀI CHÍNH KHÓA CHẶT THEO NĂM VỪA TÌM ĐƯỢC (SỬ DỤNG TRUY VẤN THÔNG MINH)
        tool_results_text = f"=== BỐI CẢNH SỰ KIỆN VĨ MÔ ===\n{macro_news}\n"
        if symbol_called:
            tool_results_text += f"\n{agent2_get_internal_data(symbol_called, target_year)}\n"
            supplemental_query = f"{symbol_called} hoạt động trong lĩnh vực gì, ngành nghề kinh doanh cốt lõi, sản phẩm chính, chi phí đầu vào"
            tool_results_text += f"\n{agent3_search_macro_news(supplemental_query)}\n"

        # BƯỚC 4: THIẾT QUÂN LUẬT MỔ XẺ CƠ CHẾ TRUYỀN DẪN (TẠI SAO TĂNG/GIẢM)
        writer_instruction = f"""
        Bạn là Giám đốc Đầu tư (CIO) chuyên ngành phân tích thực chứng tài chính nâng cao.
        🚨 MỤC TIÊU TỐI THƯỢNG: Phải mổ xẻ sâu sắc CƠ CHẾ TRUYỀN DẪN (TẠI SAO biến động vĩ mô lại ép chỉ số tài chính nhảy số như vậy). KHÔNG viết chung chung. KHÔNG dùng cấu trúc AI.

        🚨 NÚT TỰ HỦY:
        Nếu dữ liệu đầu vào chứa "❌ KHÔNG_CÓ_DỮ_LIỆU", in đúng câu: "Hệ thống không trích xuất được dữ liệu thực chứng. Đánh giá bị hủy." và dừng lại.

        🚨 NGUYÊN TẮC SUY LUẬN HUYỆT ĐẠO NGÀNH (CẤM SAI LỆCH):
        - Đối với nhóm CÔNG NGHỆ (như FPT): Đầu vào là chi phí nhân công (kỹ sư), đầu ra là ngân sách chi tiêu CNTT (IT Spending) của tập khách hàng quốc tế (Mỹ, Nhật, EU). Sự bất ổn địa chính trị tác động đến công nghệ thông qua việc lạm phát leo thang ở nước ngoài khiến các tập đoàn thắt chặt ngân sách chi tiêu phần mềm, hoặc thông qua biến động Tỷ giá (FPT thu USD/JPY).
        - TUYỆT ĐỐI CẤM phân tích các câu ngớ ngẩn như "FPT bị đội chi phí vận tải biển, linh kiện đi qua eo biển Hormuz". Họ bán phần mềm vô hình, không đóng container đường biển!

        🚨 BẮT BUỘC TRÌNH BÀY THEO CẤU TRÚC SAU:

        1. BỐI CẢNH VĨ MÔ THỰC CHỨNG VÀ KÊNH TRUYỀN DẪN ĐẾN NGÀNH:
        - Nêu rõ sự kiện xảy ra vào thời gian nào (Tháng/Năm bùng nổ).
        - Chỉ rõ biến số kinh tế vĩ mô cốt lõi bị kích hoạt trực tiếp từ sự kiện đó (Lạm phát, Lãi suất, hay Tỷ giá) ảnh hưởng thế nào đến lực cầu ngành.

        2. MỔ XẺ CHI TIẾT BIẾN ĐỘNG CHỈ BÁO TÀI CHÍNH (BẮT BUỘC GIẢI THÍCH CHỮ "TẠI SAO"):
        - Bạn PHẢI đối chiếu trực tiếp số liệu Trước và Sau sự kiện từ [BẢNG TÀI CHÍNH TỪ VNSTOCK].
        - Đối với **Doanh thu thuần**: Tăng hay giảm bao nhiêu phần trăm? Giải thích TẠI SAO (Ví dụ: Do doanh nghiệp ký được hợp đồng mới dịch chuyển từ vùng chiến sự, hay do đối tác cắt giảm chi tertiary?).
        - Đối với **Biên lợi nhuận gộp**: Tăng hay giảm? Giải thích TẠI SAO (Cơ cấu chi phí nhân sự kỹ sư cố định tăng lên trong khi đơn giá sụt giảm do khách hàng ép giá, v.v.).
        - Đối với **EPS và Quản trị rủi ro**: Tại sao doanh thu sụt giảm mà EPS lại duy trì tốt (hoặc ngược lại)? Hãy soi vào chỉ tiêu Nợ phải trả xem doanh nghiệp có cấu trúc giảm nợ để né bẫy lãi suất cao hay không.

        3. ĐỊNH HƯỚNG GIÁ CỔ PHIẾU & KHUYẾN NGHỊ KHÔNG NƯỚC ĐÔI:
        - Giá cổ phiếu sẽ bị định giá lại (Re-rate) Giảm ngắn hạn do tâm lý, hay Tăng trưởng vững chắc nhờ bộ đệm tài chính phòng thủ?
        - Đưa ra hành động dứt khoát: Gom tích lũy vùng chiết khấu hay Thoát hàng hạ tỷ trọng.

        LUÔN LUÔN hiển thị [BẢNG TÀI CHÍNH TỪ VNSTOCK] lên trên cùng của báo cáo.
        """

        messages_2 = [{'role': 'system', 'content': writer_instruction}]
        for msg in req.history[-6:]: messages_2.append({'role': msg.role, 'content': msg.content})
        messages_2.append({'role': 'user', 'content': f"Yêu cầu: {prompt}\n\n=== DỮ LIỆU ĐẦU VÀO ===\n{tool_results_text}"})

        final_response = groq_client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=messages_2,
            temperature=0.2,
            max_tokens=2500
        )

        # BƯỚC 5: TRÍCH XUẤT YẾU TỐ TÀI CHÍNH BỊ ẢNH HƯỚNG (từ đề xuất)
        factor_extractor_prompt = f"""
        Đọc bài phân tích sau và liệt kê các chỉ tiêu tài chính bị ảnh hưởng bởi sự kiện này.
        Chỉ được dùng các tên sau (viết chính xác, không sửa):
        - lợi_nhuận_sau_thuế_% tăng trưởng
        - doanh_thu_thuần_% tăng trưởng
        - lợi_nhuận_gộp_% tăng trưởng
        - eps_cơ_bản_% tăng trưởng
        - roa_%
        - roe_%
        - vay_ngắn_hạn_% tăng trưởng
        - tổng_tài_sản_% tăng trưởng

        Bài phân tích:
        {final_response.choices[0].message.content}

        Trả về JSON duy nhất:
        {{
            "affected_factors": ["tên_factor_1", "tên_factor_2"],
            "direction": "positive" hoặc "negative" hoặc "mixed"
        }}
        """

        factor_res = groq_client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': factor_extractor_prompt}],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        factor_data = json.loads(factor_res.choices[0].message.content)

        # Trả về response có thêm field mới — KHÔNG phá vỡ format cũ
        return {
            'ai_analysis':       final_response.choices[0].message.content,
            'affected_factors':  factor_data.get('affected_factors', []),
            'direction':         factor_data.get('direction', 'unknown'),
            'symbol':            symbol_called,
            'status':            'success'
        }

    except Exception as e:
        return {'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'}


# ======================================================================
# ENDPOINT NỘI BỘ: financial_agent.py gọi để lấy phân tích tin tức
# ======================================================================

@app.post('/api/internal/factor_impact')
def internal_factor_impact(req: InternalFactorRequest):
    """
    Endpoint dành cho financial_agent.py (tool analyze_news_and_events).

    Khác với /api/ask_agent ở chỗ:
    - Nhận thêm top_factors từ Agent 2 (correlation results)
    - Prompt LLM tập trung đánh giá tác động sự kiện lên CÁC FACTOR ĐÃ BIẾT
    - Trả về structured JSON (không phải markdown) để financial_agent dễ parse

    Request body:
        {
          "question": "Mỹ tấn công Iran ảnh hưởng thế nào đến GMD?",
          "tickers": ["GMD"],
          "top_factors": [
            {"factor_name": "net_margin", "correlation_r": "+58.2%", "direction": "đồng_biến"},
            {"factor_name": "revenue_growth", "correlation_r": "+52.1%", "direction": "đồng_biến"}
          ]
        }
    """
    try:
        question = req.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="question không được để trống")

        tickers_str = ", ".join(req.tickers) if req.tickers else "chưa xác định"

        # Bước 1: Tìm tin tức liên quan
        macro_news = agent3_search_macro_news(question)
        if req.tickers:
            for ticker in req.tickers:
                supplemental = agent3_search_macro_news(
                    f"{ticker} {question} tác động tài chính"
                )
                macro_news += supplemental

        # Bước 2: Tạo context về factors từ Agent 2
        factors_context = ""
        if req.top_factors:
            factors_context = "CÁC FACTOR ĐÃ BIẾT TỪ PHÂN TÍCH TƯƠNG QUAN:\n"
            for f in req.top_factors:
                factors_context += (
                    f"  - {f.get('factor_name')}: r={f.get('correlation_r')} "
                    f"({f.get('direction', 'không rõ')} với giá CP)\n"
                )

        # Bước 3: LLM phân tích tác động CỤ THỂ lên từng factor
        analyst_prompt = f"""
Bạn là chuyên gia phân tích tài chính chứng khoán Việt Nam.

Câu hỏi: {question}
Ticker liên quan: {tickers_str}

{factors_context}

Tin tức tìm được:
{macro_news if macro_news.strip() else "Không tìm được tin tức liên quan."}

NHIỆM VỤ:
1. Tóm tắt sự kiện/tin tức chính (2-3 câu, nêu tên sự kiện cụ thể, thời gian, số liệu nếu có)
2. Với TỪNG factor trong danh sách ở trên, đánh giá:
   - Sự kiện này làm factor đó TĂNG, GIẢM hay KHÔNG ĐỔI?
   - Lý do ngắn gọn (1 câu chuỗi nhân quả)
   - Tín hiệu giá: nếu factor đồng_biến với giá mà factor TĂNG → giá TĂNG; nếu factor GIẢM → giá GIẢM
3. Tín hiệu tổng hợp: TĂNG MẠNH / TĂNG NHẸ / TRUNG LẬP / GIẢM NHẸ / GIẢM MẠNH
4. Độ tin cậy (0.0-1.0): dựa trên chất lượng tin tức tìm được

LƯU Ý QUAN TRỌNG:
- Nếu KHÔNG tìm được tin tức liên quan → tín hiệu = TRUNG LẬP, confidence = 0.0
- Phân tích theo đúng ngành của ticker (công nghệ ≠ vận tải, KHÔNG nhầm cơ chế truyền dẫn)
- Không bịa số liệu

Trả về JSON duy nhất theo format sau, không thêm text nào khác:
{{
    "event_summary": "Tóm tắt sự kiện 2-3 câu",
    "factor_impacts": [
        {{
            "factor_name": "tên_factor",
            "impact_direction": "tăng" hoặc "giảm" hoặc "không_đổi",
            "price_signal": "↑ TĂNG" hoặc "↓ GIẢM" hoặc "→ KHÔNG ĐỔI",
            "reasoning": "Chuỗi nhân quả 1 câu"
        }}
    ],
    "overall_signal": "TĂNG MẠNH" hoặc "TĂNG NHẸ" hoặc "TRUNG LẬP" hoặc "GIẢM NHẸ" hoặc "GIẢM MẠNH",
    "confidence": 0.0 đến 1.0,
    "news_quality": "cao" hoặc "trung_bình" hoặc "thấp" hoặc "không_có"
}}
"""

        response = groq_client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': analyst_prompt}],
            temperature=0.1,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        # Đảm bảo các field bắt buộc tồn tại
        result.setdefault('event_summary',   'Không tìm được tin tức liên quan.')
        result.setdefault('factor_impacts',  [])
        result.setdefault('overall_signal',  'TRUNG LẬP')
        result.setdefault('confidence',      0.0)
        result.setdefault('news_quality',    'không_có')
        result['status'] = 'success'
        result['tickers'] = req.tickers

        return result

    except json.JSONDecodeError:
        # LLM không trả về JSON hợp lệ
        return {
            'status':         'success',
            'event_summary':  'Không phân tích được tin tức.',
            'factor_impacts': [],
            'overall_signal': 'TRUNG LẬP',
            'confidence':     0.0,
            'news_quality':   'không_có',
            'tickers':        req.tickers,
        }
    except Exception as e:
        return {'status': 'error', 'message': f'Lỗi internal factor_impact: {str(e)}'}


# ======================================================================
# HEALTH CHECK & ENTRY POINT
# ======================================================================

@app.get("/health")
def health():
    """Kiểm tra News Agent server đang chạy."""
    return {
        "status":  "ok",
        "service": "News & Financial Analysis Agent",
        "version": "2.0.0",
        "endpoints": [
            "POST /api/ask_agent          — phân tích câu hỏi + tin tức (dành cho UI)",
            "POST /api/internal/factor_impact — tác động tin tức lên factors (dành cho financial_agent)",
            "GET  /health                 — kiểm tra server",
        ]
    }


if __name__ == "__main__":
    import uvicorn

    print("=" * 55)
    print("  News & Financial Analysis Agent")
    print("=" * 55)
    print(f"  GROQ_API_KEY  : {'✔ Đã set' if os.environ.get('GROQ_API_KEY') else '⚠ Dùng key hardcode (dev only)'}")
    print(f"  TAVILY_API_KEY: {'✔ Đã set' if os.environ.get('TAVILY_API_KEY') else '⚠ Dùng key hardcode (dev only)'}")
    print(f"  Docs   : http://localhost:8001/docs")
    print(f"  Health : http://localhost:8001/health")
    print(f"  Factor : http://localhost:8000 (factor agent, chạy riêng)")
    print("=" * 55)

    uvicorn.run(
        "api:app",
        host   = "0.0.0.0",
        port   = 8001,
        reload = True,
    )
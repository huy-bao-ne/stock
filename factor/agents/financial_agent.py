"""
agents/financial_agent.py
==========================
AI Agent phân tích tài chính chứng khoán Việt Nam.

Kiến trúc:
  FinancialAgent          ← Orchestrator chính: nhận câu hỏi, quản lý conversation
    └── LLMProvider       ← Abstract: tách phần AI ra riêng để dễ swap provider
          ├── AnthropicProvider   ← Claude (Anthropic)
          ├── GroqProvider        ← Llama/Kimi/Qwen... qua Groq (OpenAI-compatible)
          ├── OpenAIProvider      ← GPT (OpenAI) — placeholder
          └── GoogleProvider      ← Gemini (Google) — placeholder
    └── ToolExecutor      ← Thực thi tools: đọc CSV, gọi vnstock

Cách dùng:
    from agents.financial_agent import FinancialAgent

    # Anthropic (mặc định)
    agent = FinancialAgent(api_key="sk-ant-...")

    # Groq (Llama 3.3 70B)
    agent = FinancialAgent(
        provider="groq",
        api_key="gsk_...",
        model="llama-3.3-70b-specdec",
    )

    answer = agent.ask("Ngành nào có factor mạnh nhất?")

    # Multi-turn
    agent.ask("VCB có ROA bao nhiêu năm 2023?")
    agent.ask("So với TCB thì thế nào?")
    agent.reset()
"""

import os
import json
import time
import hashlib
import pandas as pd
from pathlib import Path
from typing import Optional
from abc import ABC, abstractmethod


# ======================================================================
# CUSTOM EXCEPTIONS
# ======================================================================

class RateLimitError(Exception):
    """Raise khi Groq API bị rate limit sau tất cả retry attempts."""
    pass


class SimpleCache:
    """
    Cache Q&A đơn giản — lưu vào file JSON, TTL 24 giờ.
    Chỉ cache câu hỏi nặng (predict_ticker) để tránh gọi API lặp lại.
    Cache key = hash(question.lower().strip()) để match câu hỏi tương tự.
    """
    TTL_SECONDS = 86400  # 24 giờ

    def __init__(self, cache_file: str = "data/agent_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict = {}
        self._load()

    def _load(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}

    def _save(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _key(self, question: str) -> str:
        return hashlib.md5(question.lower().strip().encode()).hexdigest()

    def get(self, question: str) -> Optional[str]:
        k = self._key(question)
        entry = self._data.get(k)
        if not entry:
            return None
        if time.time() - entry["ts"] > self.TTL_SECONDS:
            del self._data[k]
            self._save()
            return None
        return entry["answer"]

    def set(self, question: str, answer: str):
        k = self._key(question)
        self._data[k] = {"question": question, "answer": answer, "ts": time.time()}
        self._save()

    def clear(self):
        self._data = {}
        if self.cache_file.exists():
            self.cache_file.unlink()


# ======================================================================
# CẤU HÌNH
# ======================================================================

SECTORS = [
    "BANKING", "REALESTATE", "TECHNOLOGY", "FOOD",
    "CONSTRUCTION", "TRANSPORT", "CHEMICALS",
    "UTILITIES", "SECURITIES", "HEALTHCARE",
]

SECTOR_LABELS = {
    "BANKING":      "Ngân hàng",
    "REALESTATE":   "Bất động sản",
    "TECHNOLOGY":   "Công nghệ",
    "FOOD":         "Thực phẩm & Đồ uống",
    "CONSTRUCTION": "Xây dựng",
    "TRANSPORT":    "Vận tải - Kho bãi",
    "CHEMICALS":    "SX Nhựa - Hóa chất",
    "UTILITIES":    "Tiện ích",
    "SECURITIES":   "Chứng khoán",
    "HEALTHCARE":   "Chăm sóc sức khỏe",
}

SYSTEM_PROMPT = """Bạn là chuyên gia phân tích tài chính chứng khoán Việt Nam.
Hệ thống có dữ liệu 10 ngành, 50 tickers, 2018-2024 (Spearman correlation + Bonferroni).

TOOLS & KHI NÀO DÙNG:
- predict_ticker(ticker,sector,question): Dự báo/xu hướng/nên mua-bán 1 ticker → LUÔN dùng tool này, KHÔNG tự gọi riêng lẻ get_ticker_factor_trend hay analyze_news_and_events.
- load_sector_results(sectors,level,significant_only): Ranking factors theo ngành.
- load_gold_dataset(sector,tickers,years,columns): Số liệu cụ thể (roa_%, roe_%, eps_cơ_bản...).
- get_available_data(): Xem danh sách tickers/ngành có trong hệ thống.
- fetch_latest_price(ticker,days): Giá realtime.
- analyze_news_and_events(question,tickers): Tin tức — chỉ dùng khi KHÔNG cần dự báo.
- get_ticker_factor_trend(ticker,sector,top_n): Trend lịch sử — chỉ dùng khi KHÔNG cần dự báo.

50 TICKERS: BANKING(VCB,BID,CTG,TCB,VPB) REALESTATE(VIC,VHM,KSF,VRE,BCM) TECHNOLOGY(FPT,CTR,CMG,SGT,ELC) FOOD(MCH,VNM,MSN,SAB,SBT) CONSTRUCTION(THD,REE,HUT,LGC,VCG) TRANSPORT(VJC,HVN,GMD,VTP,PVT) CHEMICALS(GVR,DCM,DGC,DPM,BMP) UTILITIES(GAS,POW,PGV,IDC,SIP) SECURITIES(SSI,VND,HCM,MBS,VCI) HEALTHCARE(DHG,IMP,DHT,DBD,TRA)

TÊN CỘT ĐÚNG (load_gold_dataset): roa_%, roe_%, eps_cơ_bản, gross_margin_%, net_margin_%, debt_ratio_%, asset_turnover, lợi_nhuận_sau_thuế_% tăng trưởng, doanh_thu_thuần_% tăng trưởng. Banking thêm: nim_%, cir_%, ldr_%.

TICKER NGOÀI HỆ THỐNG: Thông báo rõ → xác định ngành gần nhất → gọi load_sector_results ngành đó → nói đây là suy luận từ ngành, không phải số liệu thực của công ty.

CÂU HỎI VĨ MÔ KHÔNG CÓ TICKER CỤ THỂ (vd: "chiến tranh ảnh hưởng thế nào đến ngành chứng khoán"):
- KHÔNG gọi predict_ticker (không có ticker để phân tích)
- Gọi load_sector_results cho ngành liên quan (sectors=["SECURITIES"] nếu hỏi chứng khoán)
- Gọi analyze_news_and_events với câu hỏi gốc
- Tổng hợp: factors quan trọng nhất của ngành đó + tác động từ sự kiện vĩ mô
- Trả lời bằng văn xuôi, KHÔNG dùng format predict_ticker
- Chỉ gọi MỖI TOOL 1 LẦN DUY NHẤT, không lặp lại

CHỐNG BỊA SỐ: Chỉ dùng số có trong kết quả tool. Nếu tool trả rỗng/lỗi → nói "không tìm thấy dữ liệu". KHÔNG tự suy ra số liệu.

LOAD_SECTOR_RESULTS: Nếu cần tất cả ngành → sectors=[] (rỗng). KHÔNG liệt kê cả 10 ngành.

FORMAT KHI TRÌNH BÀY KẾT QUẢ predict_ticker:
---
## 📊 PHÂN TÍCH DỰ BÁO: [TICKER] — [Ngành]
### 🔍 Bối cảnh sự kiện
[Sự kiện cụ thể từ tin tức] **Hướng tác động:** [TÍCH CỰC ↑ / TIÊU CỰC ↓ / HỖN HỢP ↕]
### 📈 BẢNG TƯƠNG QUAN & TREND LỊCH SỬ (2018-2024)
| Factor | r với giá CP | Trend 2018-2024 | Giá trị 2023 | Giá trị 2024 | YoY |
|--------|-------------|-----------------|--------------|--------------|-----|
### 🎯 ĐÁNH GIÁ TÁC ĐỘNG TIN TỨC LÊN TỪNG FACTOR
| Factor bị ảnh hưởng | Tương quan (r) | Độ mạnh | Tác động tin tức | Tín hiệu |
|---------------------|----------------|---------|-----------------|---------|
### 🔮 DỰ BÁO XU HƯỚNG
**Tín hiệu tổng hợp:** [TĂNG MẠNH/TĂNG NHẸ/TRUNG LẬP/GIẢM NHẸ/GIẢM MẠNH]
**Lý luận:** [dựa trên số liệu thực] **Khung thời gian:** [Ngắn/Trung hạn]
> ⚠️ Phân tích định tính. Không phải tư vấn đầu tư chắc chắn.
---
QUAN TRỌNG khi điền bảng TREND LỊCH SỬ: kết quả predict_ticker (PHẦN 1) đã có sẵn
cột "Trend" (↑ TĂNG/↓ GIẢM/→ ỔN ĐỊNH) và dòng "Nhận xét trend" có công thức YoY
("tăng/giảm X% so với năm Y"). PHẢI lấy đúng giá trị Trend và % YoY từ đó, KHÔNG
được để trống "—" nếu dữ liệu gốc đã có. Nếu PHẦN 1 thật sự ghi "—" (do thiếu dữ liệu)
thì mới giữ "—" trong bảng.
Độ mạnh: Mạnh=|r|>50%, Trung bình=30-50%, Yếu=<30% (áp dụng chính xác).
Trả lời bằng ngôn ngữ user dùng (Việt/Anh). KHÔNG chêm tiếng Trung/Hàn.
"""



# ======================================================================
# TOOLS DEFINITION (Anthropic-style schema — convert sang OpenAI khi cần)
# ======================================================================

TOOLS = [
    {
        "name": "get_available_data",
        "description": (
            "Liệt kê toàn bộ dữ liệu đang có trong hệ thống: "
            "ngành nào, tickers nào, năm nào, files nào tồn tại. "
            "Dùng khi cần biết hệ thống có gì trước khi truy vấn chi tiết."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "load_sector_results",
        "description": (
            "Đọc kết quả correlation analysis của 1 hoặc nhiều ngành. "
            "Trả về bảng ranking các factor: tên chỉ báo, độ tương quan (%), "
            "p-value, có significant sau Bonferroni không. "
            "Dùng khi hỏi về: factor nào quan trọng, ngành nào có tín hiệu mạnh, "
            "so sánh factors giữa các ngành."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sectors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Danh sách mã ngành cần đọc, viết HOA. "
                        "Các giá trị hợp lệ: BANKING, REALESTATE, TECHNOLOGY, FOOD, "
                        "CONSTRUCTION, TRANSPORT, CHEMICALS, UTILITIES, SECURITIES, HEALTHCARE. "
                        "Ví dụ: [\"BANKING\", \"FOOD\"]"
                    ),
                },
                "level": {
                    "type": "string",
                    "enum": ["sector", "ticker", "both"],
                    "description": "'sector' = kết quả tổng hợp toàn ngành, 'ticker' = từng công ty, 'both' = cả hai",
                    "default": "sector",
                },
                "significant_only": {
                    "type": "boolean",
                    "description": "True = chỉ lấy factors có ý nghĩa sau Bonferroni",
                    "default": False,
                },
            },
            "required": ["sectors"],
        },
    },
    {
        "name": "load_gold_dataset",
        "description": (
            "Đọc dữ liệu tài chính chi tiết của 1 ngành (gold dataset). "
            "Chứa tất cả factors theo từng ticker và từng năm: "
            "ROA, ROE, NIM, growth rates, margins... "
            "Dùng khi hỏi về: số liệu cụ thể của 1 công ty, "
            "xu hướng qua các năm, so sánh công ty trong cùng ngành."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sector": {
                    "type": "string",
                    "description": (
                        "Mã ngành cần đọc, viết HOA. Một trong: BANKING, REALESTATE, "
                        "TECHNOLOGY, FOOD, CONSTRUCTION, TRANSPORT, CHEMICALS, "
                        "UTILITIES, SECURITIES, HEALTHCARE."
                    ),
                },
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lọc theo tickers. Bỏ trống = lấy tất cả.",
                },
                "years": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Lọc theo năm. Bỏ trống = lấy tất cả.",
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lọc theo cột. Bỏ trống = lấy tất cả.",
                },
            },
            "required": ["sector"],
        },
    },
    {
        "name": "fetch_latest_price",
        "description": (
            "Lấy giá cổ phiếu mới nhất từ vnstock (realtime). "
            "Dùng khi hỏi về: giá hiện tại, biến động gần đây của 1 cổ phiếu."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Mã cổ phiếu. Ví dụ: 'VCB', 'FPT'",
                },
                "days": {
                    "type": "integer",
                    "description": "Số ngày gần nhất. Mặc định 30.",
                    "default": 30,
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "predict_ticker",
        "description": (
            "TOOL CHÍNH để dự báo xu hướng giá 1 ticker cụ thể. "
            "Tự động thực hiện đầy đủ 3 bước: (1) lấy trend lịch sử các factors quan trọng, "
            "(2) phân tích tin tức/sự kiện hiện tại, (3) lấy độ tương quan với giá cổ phiếu — "
            "rồi trả về 1 bảng tổng hợp đầy đủ, sẵn sàng để bạn trình bày cho user. "
            "LUÔN dùng tool này (KHÔNG dùng riêng lẻ get_ticker_factor_trend/analyze_news_and_events) "
            "khi user hỏi: dự báo, xu hướng, nên mua/bán, triển vọng, tình hình hiện tại của 1 ticker."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Mã cổ phiếu. Ví dụ: 'FPT', 'VCB'",
                },
                "sector": {
                    "type": "string",
                    "description": "Ngành của ticker, viết HOA. Ví dụ: 'TECHNOLOGY', 'BANKING'",
                },
                "question": {
                    "type": "string",
                    "description": "Câu hỏi gốc của user (truyền nguyên văn, dùng để tìm tin tức liên quan)",
                },
            },
            "required": ["ticker", "sector", "question"],
        },
    },
    {
        "name": "get_ticker_factor_trend",
        "description": (
            "Lấy giá trị lịch sử của các factors quan trọng nhất cho 1 ticker cụ thể "
            "qua các năm (2018-2024), kèm tính toán trend (tăng/giảm/ổn định). "
            "Dùng khi cần: phân tích xu hướng dài hạn, so sánh năm hiện tại vs quá khứ, "
            "đánh giá momentum của các chỉ số quan trọng trước khi kết hợp với tin tức."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Mã cổ phiếu. Ví dụ: 'FPT', 'VCB'",
                },
                "sector": {
                    "type": "string",
                    "description": "Ngành của ticker. Ví dụ: 'TECHNOLOGY', 'BANKING'",
                },
                "top_n": {
                    "type": "integer",
                    "description": "Số factors quan trọng nhất cần lấy. Mặc định 5.",
                    "default": 5,
                },
            },
            "required": ["ticker", "sector"],
        },
    },
    {
        "name": "analyze_news_and_events",
        "description": (
            "Phân tích tin tức vĩ mô và sự kiện kinh tế ảnh hưởng đến cổ phiếu/ngành. "
            "Tool này gọi AI Agent chuyên về news analysis (tích hợp Google Search/Tavily realtime). "
            "Dùng khi hỏi về: tin tức mới nhất, sự kiện ảnh hưởng đến giá cổ phiếu, "
            "phân tích vĩ mô (lãi suất, tỷ giá, chính sách), dự đoán xu hướng giá, "
            "hoặc bất kỳ câu hỏi nào cần kết hợp tin tức + dữ liệu tài chính."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": (
                        "Câu hỏi đầy đủ cần phân tích. Nên bao gồm: "
                        "tên công ty/ticker, loại phân tích cần (tác động tin tức, dự báo giá...). "
                        "Ví dụ: 'Tin tức gần đây ảnh hưởng thế nào đến FPT?'"
                    ),
                },
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách ticker liên quan. Ví dụ: ['FPT', 'VCB']",
                },
            },
            "required": ["question"],
        },
    },
]


def _anthropic_tools():
    """TOOLS đã ở format Anthropic — dùng trực tiếp."""
    return TOOLS


def _openai_tools():
    """
    Convert TOOLS sang format OpenAI/Groq function calling:
        {"type": "function", "function": {"name", "description", "parameters"}}
    """
    converted = []
    for t in TOOLS:
        converted.append({
            "type": "function",
            "function": {
                "name":        t["name"],
                "description": t["description"],
                "parameters":  t["input_schema"],
            },
        })
    return converted


# ======================================================================
# TOOL EXECUTOR
# ======================================================================

class ToolExecutor:
    """Thực thi các tools khi AI gọi."""

    def __init__(self, data_root: str = "data", output_root: str = "outputs"):
        self.data_root   = Path(data_root)
        self.output_root = Path(output_root)

    def execute(self, tool_name: str, tool_input: dict) -> str:
        try:
            if tool_name == "get_available_data":
                return self._get_available_data()
            elif tool_name == "load_sector_results":
                return self._load_sector_results(**tool_input)
            elif tool_name == "load_gold_dataset":
                return self._load_gold_dataset(**tool_input)
            elif tool_name == "fetch_latest_price":
                return self._fetch_latest_price(**tool_input)
            elif tool_name == "predict_ticker":
                return self._predict_ticker(**tool_input)
            elif tool_name == "get_ticker_factor_trend":
                return self._get_ticker_factor_trend(**tool_input)
            elif tool_name == "analyze_news_and_events":
                return self._analyze_news_and_events(**tool_input)
            else:
                return f"Tool '{tool_name}' không tồn tại."
        except Exception as e:
            return f"Lỗi khi chạy tool '{tool_name}': {str(e)}"

    def _get_available_data(self) -> str:
        rows = []
        for sector in SECTORS:
            label      = SECTOR_LABELS[sector]
            sector_dir = self.data_root / sector.lower()
            out_dir    = self.output_root / sector.lower()
            gold_exists    = (sector_dir / "gold_factors.csv").exists()
            results_exists = (out_dir / f"{sector.lower()}_factor_results.csv").exists()
            tickers, years = [], []
            if gold_exists:
                try:
                    df = pd.read_csv(sector_dir / "gold_factors.csv", encoding="utf-8-sig")
                    tickers = sorted(df["mã_chứng_khoán"].unique().tolist())
                    years   = sorted(df["năm"].unique().tolist())
                except Exception:
                    pass
            rows.append(
                f"- {label} ({sector}): tickers={tickers}, năm={years}, "
                f"gold={'✔' if gold_exists else '✗'}, "
                f"results={'✔' if results_exists else '✗'}"
            )
        master = self.data_root / "master" / "master_index.csv"
        master_info = ""
        all_tickers = []
        if master.exists():
            df_m = pd.read_csv(master, encoding="utf-8-sig")
            master_info = f"\nMaster index: {len(df_m)} tickers tổng cộng"
            if "mã_chứng_khoán" in df_m.columns:
                all_tickers = sorted(df_m["mã_chứng_khoán"].unique().tolist())

        # Liệt kê tất cả tickers để agent biết ticker nào có/không có trong hệ thống
        ticker_note = ""
        if all_tickers:
            ticker_note = (
                f"\n\nTẤT CẢ {len(all_tickers)} TICKERS TRONG HỆ THỐNG: {all_tickers}"
                f"\nNếu user hỏi ticker KHÔNG có trong danh sách này → áp dụng "
                f"hướng dẫn xử lý ticker ngoài hệ thống (dùng ngành gần nhất)."
            )
        return "Dữ liệu hiện có:\n" + "\n".join(rows) + master_info + ticker_note

    def _load_sector_results(
        self, sectors: list = None,
        level: str = "sector",
        significant_only: bool = False,
    ) -> str:
        # Nếu không chỉ định ngành (None hoặc []) → lấy tất cả 10 ngành
        if not sectors:
            sectors = SECTORS

        parts = []
        for sector in sectors:
            label   = SECTOR_LABELS.get(sector, sector)
            out_dir = self.output_root / sector.lower()
            if level in ("sector", "both"):
                path = out_dir / f"{sector.lower()}_factor_results.csv"
                if path.exists():
                    df = pd.read_csv(path, encoding="utf-8-sig")
                    if significant_only:
                        mask = df["có_ý_nghĩa_sau_bonferroni"].apply(
                            lambda v: str(v).strip().lower() == "true"
                        )
                        df = df[mask]
                    cols = ["xếp_hạng","chỉ_báo","độ_tương_quan_%","kết_luận",
                            "độ_mạnh","p_value","có_ý_nghĩa_thống_kê",
                            "có_ý_nghĩa_sau_bonferroni","bonferroni_threshold","số_quan_sát"]
                    df = df[[c for c in cols if c in df.columns]].copy()

                    # Tính lại độ_mạnh đúng theo ngưỡng (tránh Llama tự phân loại sai)
                    if "độ_tương_quan_%" in df.columns:
                        def _strength(r_str):
                            try:
                                r = abs(float(str(r_str).replace("%","").strip()))
                                if r >= 50: return "Mạnh"
                                if r >= 30: return "Trung bình"
                                return "Yếu"
                            except: return "—"
                        df["độ_mạnh"] = df["độ_tương_quan_%"].apply(_strength)

                    parts.append(f"\n=== {label} — Sector-level ===\n" + df.head(10).to_string(index=False))
                else:
                    parts.append(f"\n=== {label} ===\nChưa có kết quả.")
            if level in ("ticker", "both"):
                path = out_dir / f"{sector.lower()}_ticker_results.csv"
                if path.exists():
                    df = pd.read_csv(path, encoding="utf-8-sig")
                    parts.append(f"\n=== {label} — Ticker-level ===\n" + df.head(20).to_string(index=False))
        return "\n".join(parts) if parts else "Không tìm thấy dữ liệu."

    def _load_gold_dataset(
        self, sector: str,
        tickers: Optional[list] = None,
        years: Optional[list] = None,
        columns: Optional[list] = None,
    ) -> str:
        path = self.data_root / sector.lower() / "gold_factors.csv"
        if not path.exists():
            return f"Không tìm thấy gold dataset cho {sector}."
        df = pd.read_csv(path, encoding="utf-8-sig")
        if tickers:
            df = df[df["mã_chứng_khoán"].isin([t.upper() for t in tickers])]
        if years:
            df = df[df["năm"].isin(years)]
        drop_cols = ["năm_chưa_kết_thúc", "thiếu_dữ_liệu"]
        df = df.drop(columns=[c for c in drop_cols if c in df.columns])

        if columns:
            # So khớp case-insensitive với tên cột thực tế
            available = list(df.columns)
            avail_lower = {c.lower(): c for c in available}
            matched = []
            unmatched = []
            for req in columns:
                if req in available:
                    matched.append(req)
                elif req.lower() in avail_lower:
                    matched.append(avail_lower[req.lower()])
                else:
                    unmatched.append(req)

            if unmatched:
                # Không khớp → trả về danh sách cột có sẵn để model tự sửa tên và gọi lại
                factor_cols = [c for c in available if c not in ("mã_chứng_khoán", "năm")]
                return (
                    f"LỖI: Không tìm thấy cột {unmatched} trong dữ liệu {SECTOR_LABELS.get(sector, sector)}.\n"
                    f"Các cột factor có sẵn (dùng đúng tên này, có dấu %/_ nếu có):\n"
                    + ", ".join(factor_cols) + "\n\n"
                    f"Hãy gọi lại tool với tên cột đúng từ danh sách trên."
                )

            keep = ["mã_chứng_khoán", "năm"] + matched
            df = df[keep]

        if df.empty:
            return "Không tìm thấy dữ liệu với bộ lọc đã chọn."
        label = SECTOR_LABELS.get(sector, sector)
        return (
            f"=== Gold Dataset: {label} ===\n"
            f"Shape: {df.shape[0]} rows × {df.shape[1]} cols\n"
            f"Tickers: {sorted(df['mã_chứng_khoán'].unique().tolist())}\n"
            f"Năm: {sorted(df['năm'].unique().tolist())}\n\n"
            + df.to_string(index=False)
        )

    def _predict_ticker(
        self,
        ticker: str,
        sector: str,
        question: str,
    ) -> str:
        """
        TOOL ĐIỀU PHỐI — code tự gọi 3 bước theo đúng thứ tự,
        không phụ thuộc vào việc Llama có nhớ gọi đủ tool hay không.

        Bước 1: get_ticker_factor_trend  → trend lịch sử 2018-2024
        Bước 2: analyze_news_and_events  → tin tức + affected_factors + direction
        Bước 3: Ghép 2 nguồn thành 1 bảng tổng hợp duy nhất, kèm tính độ mạnh
                bằng code (không để Llama tự phân loại Mạnh/TB/Yếu).
        """
        ticker = ticker.upper().strip()
        sector = sector.upper().strip()
        label  = SECTOR_LABELS.get(sector, sector)

        output = f"=== DỰ BÁO TỔNG HỢP: {ticker} ({label}) ===\n\n"

        # ── BƯỚC 1: Trend lịch sử ─────────────────────────────────
        trend_result = self._get_ticker_factor_trend(ticker, sector, top_n=5)
        output += "## PHẦN 1 — TREND LỊCH SỬ (2018-2024)\n" + trend_result + "\n\n"

        # ── BƯỚC 2: Tin tức & sự kiện ────────────────────────────
        # Delay nhỏ giữa 2 bước để tránh burst requests lên Groq API
        import time as _time
        _time.sleep(2)
        news_result = self._analyze_news_and_events(question=question, tickers=[ticker])
        output += "## PHẦN 2 — TIN TỨC & SỰ KIỆN HIỆN TẠI\n" + news_result + "\n\n"

        # ── BƯỚC 3: Ghép — tính độ mạnh bằng code, không để Llama tự phân loại ──
        sector_lower = sector.lower()
        factor_path  = self.output_root / sector_lower / f"{sector_lower}_factor_results.csv"

        output += "## PHẦN 3 — HƯỚNG DẪN TỔNG HỢP CHO BẠN (Llama)\n"

        # Detect xem PHẦN 2 có thực sự có dữ liệu tin tức hay không
        news_failed = (
            "Không kết nối được News Agent" in news_result
            or "Không tìm thấy dữ liệu tin tức" in news_result
            or "News Agent trả về nội dung rỗng" in news_result
            or "lỗi" in news_result.lower()[:200]
        )

        if news_failed:
            output += (
                "⚠️ PHẦN 2 KHÔNG CÓ DỮ LIỆU TIN TỨC THẬT (lỗi kết nối hoặc không tìm thấy).\n"
                "VẪN PHẢI dùng đúng FORMAT BẮT BUỘC trong system prompt (đầy đủ heading ###, "
                "emoji, bảng Markdown) — chỉ thay đổi NỘI DUNG bên trong các mục sau:\n"
                "1. Mục '🔍 Bối cảnh sự kiện': ghi rõ "
                "'Không có dữ liệu tin tức (News Agent lỗi/không phản hồi).' "
                "Hướng tác động: ghi 'KHÔNG XÁC ĐỊNH' (không được tự suy ra TÍCH CỰC/TIÊU CỰC/HỖN HỢP).\n"
                "2. Bảng '🎯 ĐÁNH GIÁ TÁC ĐỘNG TIN TỨC LÊN TỪNG FACTOR': vẫn giữ bảng Markdown "
                "nhưng cột 'Tác động tin tức' và 'Tín hiệu' ghi '— (không có dữ liệu)' cho mỗi factor.\n"
                "3. Mục '🔮 Dự báo xu hướng': CHỈ dựa trên PHẦN 1 (trend lịch sử từ bảng), "
                "ghi rõ trong phần Lý luận: 'Dự báo dựa thuần túy trên dữ liệu lịch sử do "
                "thiếu dữ liệu tin tức hiện tại.'\n"
                "TUYỆT ĐỐI KHÔNG được bỏ qua cấu trúc bảng Markdown chỉ vì thiếu tin tức — "
                "PHẦN 1 (trend lịch sử) vẫn có đầy đủ dữ liệu thật để điền bảng.\n"
            )
        else:
            output += (
                "Hãy trình bày lại PHẦN 1 và PHẦN 2 ở trên theo đúng FORMAT BẮT BUỘC "
                "trong system prompt (có bảng Markdown, số liệu cụ thể từ 2 phần trên). "
                "KHÔNG bịa thêm số liệu nào ngoài 2 phần đã cung cấp.\n"
            )

        return output

    def _get_ticker_factor_trend(
        self,
        ticker: str,
        sector: str,
        top_n: int = 5,
    ) -> str:
        """
        Lấy giá trị lịch sử của top factors quan trọng nhất cho 1 ticker.
        Kết hợp correlation results (r) + gold dataset (giá trị thực) + trend calculation.
        """
        # Bước 1: Load correlation results để biết factor nào quan trọng nhất
        factor_path = self.output_root / sector.upper().lower() / f"{sector.lower()}_factor_results.csv"

        # Fix: sector.lower() cho path
        sector_lower = sector.lower()
        factor_path  = self.output_root / sector_lower / f"{sector_lower}_factor_results.csv"
        gold_path    = self.data_root   / sector_lower / "gold_factors.csv"
        label        = SECTOR_LABELS.get(sector.upper(), sector)

        if not factor_path.exists():
            return f"Không tìm thấy correlation results cho {label}."
        if not gold_path.exists():
            return f"Không tìm thấy gold dataset cho {label}."

        # Load top factors theo r
        df_factors = pd.read_csv(factor_path, encoding="utf-8-sig")
        df_factors["abs_r"] = df_factors["độ_tương_quan_%"].str.replace("%","").str.strip().astype(float).abs()
        top_factors = df_factors.nlargest(top_n, "abs_r")["chỉ_báo"].tolist()

        # Load gold dataset cho ticker — chỉ lấy 3 năm gần nhất để giảm token
        df_gold = pd.read_csv(gold_path, encoding="utf-8-sig")
        df_ticker = df_gold[df_gold["mã_chứng_khoán"] == ticker.upper()].sort_values("năm")
        if len(df_ticker) > 3:
            df_ticker = df_ticker.tail(3)  # 2022, 2023, 2024

        if df_ticker.empty:
            return f"Không tìm thấy dữ liệu cho {ticker.upper()} trong {label}."

        # Lấy các cột factor có trong gold dataset
        avail_factors = [f for f in top_factors if f in df_ticker.columns]
        if not avail_factors:
            return f"Không tìm thấy cột factor trong gold dataset của {ticker.upper()}."

        # Bỏ factor nếu tất cả giá trị đều 0 hoặc NaN — không có ý nghĩa phân tích
        # (ví dụ: quỹ_phát_triển_khcn_% FPT không công bố → toàn 0.0%)
        def _has_real_data(col):
            vals = df_ticker[col].dropna().tolist()
            return any(v != 0 for v in vals)

        avail_factors = [f for f in avail_factors if _has_real_data(f)]
        if not avail_factors:
            return f"Không có factor nào có dữ liệu thực cho {ticker.upper()}."

        # Lấy thêm r cho từng factor
        r_map = dict(zip(df_factors["chỉ_báo"], df_factors["độ_tương_quan_%"]))

        # Build bảng trend
        years = df_ticker["năm"].tolist()
        result = f"=== TREND FACTORS: {ticker.upper()} ({label}) ===\n"
        result += f"Dữ liệu từ năm {min(years)} đến {max(years)}\n\n"

        # Bảng header
        result += f"| Factor | r với giá CP | " + " | ".join(str(y) for y in years) + " | Trend |\n"
        result += f"|--------|-------------|" + "------|" * len(years) + "-------|\n"

        for factor in avail_factors:
            r_val = r_map.get(factor, "N/A")
            values = df_ticker[factor].tolist()

            # Tính trend: với 3 năm dùng so sánh đầu-cuối, với >=4 năm dùng nửa đầu/nửa cuối
            trend = "—"
            valid_vals = [v for v in values if pd.notna(v) and v != 0]
            if len(valid_vals) >= 4:
                first_half = sum(valid_vals[:len(valid_vals)//2]) / (len(valid_vals)//2)
                second_half = sum(valid_vals[len(valid_vals)//2:]) / (len(valid_vals) - len(valid_vals)//2)
                if second_half > first_half * 1.05:
                    trend = "↑ TĂNG"
                elif second_half < first_half * 0.95:
                    trend = "↓ GIẢM"
                else:
                    trend = "→ ỔN ĐỊNH"
            elif len(valid_vals) >= 2:
                # Chỉ có 2-3 giá trị (do giới hạn 3 năm gần nhất) → so sánh đầu vs cuối
                first_val = valid_vals[0]
                last_val  = valid_vals[-1]
                if last_val > first_val * 1.05:
                    trend = "↑ TĂNG"
                elif last_val < first_val * 0.95:
                    trend = "↓ GIẢM"
                else:
                    trend = "→ ỔN ĐỊNH"

            # Format values
            val_strs = []
            for v in values:
                if pd.isna(v):
                    val_strs.append("—")
                elif abs(v) > 1000:
                    val_strs.append(f"{v:,.0f}")
                else:
                    val_strs.append(f"{v:.1f}%")

            result += f"| {factor} | {r_val} | " + " | ".join(val_strs) + f" | {trend} |\n"

        # Thêm nhận xét trend tổng quan
        result += "\n**Nhận xét trend:**\n"
        for factor in avail_factors[:3]:  # top 3 factors quan trọng nhất
            r_val = r_map.get(factor, "")
            values = df_ticker[factor].tolist()
            valid_vals = [v for v in values if pd.notna(v) and v != 0]
            if len(valid_vals) >= 2:
                latest = valid_vals[-1]
                prev   = valid_vals[-2]
                yr_latest = years[-1]
                yr_prev   = years[-2]
                if prev != 0:
                    chg = (latest - prev) / abs(prev) * 100
                    direction_word = "tăng" if chg > 0 else "giảm"
                    result += (
                        f"- **{factor}** (r={r_val}): "
                        f"Năm {yr_latest} = {latest:.1f}%, "
                        f"{direction_word} {abs(chg):.1f}% so với {yr_prev}\n"
                    )

        return result

    def _analyze_news_and_events(
        self,
        question: str,
        tickers: Optional[list] = None,
    ) -> str:
        """
        Gọi News Agent API (microservice của partner) để phân tích tin tức/sự kiện.
        URL mặc định: http://localhost:8000/api/ask_agent
        Có thể override qua env var NEWS_AGENT_URL.
        """
        import urllib.request
        import urllib.error

        base_url = os.environ.get("NEWS_AGENT_URL", "http://localhost:8000")
        endpoint = f"{base_url}/api/ask_agent"

        # Build prompt gửi sang news agent — kèm context về tickers nếu có
        prompt = question
        if tickers:
            ticker_str = ", ".join(t.upper() for t in tickers)
            prompt = f"[Tickers liên quan: {ticker_str}] {question}"

        payload = json.dumps({
            "prompt":   prompt,
            "history":  [],     # stateless call — context đã có trong prompt
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                endpoint,
                data    = payload,
                headers = {"Content-Type": "application/json"},
                method  = "POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if data.get("status") == "error":
                return f"⚠️ News Agent báo lỗi: {data.get('message', 'Unknown error')}"

            # Lấy phân tích chính
            ai_analysis = (
                data.get("ai_analysis")
                or data.get("content")
                or data.get("answer")
                or str(data)
            )

            # Kiểm tra nội dung có thực sự rỗng không (News Agent có thể trả
            # status="success" nhưng các section bên trong đều trống "> \n").
            # Đếm tỷ lệ dòng blockquote ('>') bị rỗng — nếu phần lớn rỗng,
            # coi như News Agent không thực sự phân tích được gì.
            lines = ai_analysis.split("\n")
            quote_lines = [l for l in lines if l.strip().startswith(">")]
            empty_quotes = [l for l in quote_lines if l.strip() in (">", "> ", ">  ")]
            content_is_empty = (
                len(quote_lines) > 0
                and (len(empty_quotes) / len(quote_lines)) >= 0.5
            )

            if content_is_empty:
                return (
                    "Không tìm thấy dữ liệu tin tức (News Agent trả về nội dung rỗng). "
                    "Không có sự kiện/tin tức nào để phân tích."
                )

            # Lấy affected_factors và direction — cầu nối với correlation results
            affected = data.get("affected_factors", [])
            direction = data.get("direction", "unknown")
            symbol_res = data.get("symbol", "")

            # Build output có cấu trúc để agent ghép với factor analysis
            result = f"=== Phân tích tin tức & sự kiện ===\n{ai_analysis}\n"

            if affected:
                direction_label = {
                    "positive": "TÍCH CỰC ↑",
                    "negative": "TIÊU CỰC ↓",
                    "mixed":    "HỖN HỢP ↕",
                }.get(direction, direction.upper())

                result += (
                    f"\n--- KẾT NỐI VỚI FACTOR ANALYSIS ---\n"
                    f"Ticker: {symbol_res}\n"
                    f"Hướng tác động: {direction_label}\n"
                    f"Các factors bị ảnh hưởng bởi tin tức này:\n"
                )
                for f_name in affected:
                    result += f"  • {f_name}\n"

                result += (
                    f"\nGỢI Ý: Dùng load_sector_results để xem độ tương quan "
                    f"của các factors trên với giá cổ phiếu, "
                    f"sau đó kết hợp với hướng tác động '{direction_label}' "
                    f"để đưa ra nhận định tổng hợp."
                )

            return result

        except urllib.error.URLError as e:
            return (
                f"⚠️ Không kết nối được News Agent tại {endpoint}.\n"
                f"Lỗi: {str(e)}\n\n"
                f"Để dùng tính năng này, cần chạy News Agent server trước:\n"
                f"  python news_agent/app.py  (hoặc tương đương)\n"
                f"Sau đó set env var: NEWS_AGENT_URL=http://localhost:<port>"
            )
        except json.JSONDecodeError:
            return f"⚠️ News Agent trả về dữ liệu không hợp lệ (non-JSON)."
        except Exception as e:
            return f"⚠️ Lỗi khi gọi News Agent: {str(e)}"

    def _fetch_latest_price(self, ticker: str, days: int = 30) -> str:
        try:
            import io, contextlib
            from vnstock import Vnstock
            from datetime import datetime, timedelta
            end   = datetime.today().strftime("%Y-%m-%d")
            start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")

            # vnstock in banner/quảng cáo ra stdout khi import/gọi — chặn lại
            # để không làm nhiễu output của chatbot
            _buf = io.StringIO()
            with contextlib.redirect_stdout(_buf):
                stock = Vnstock().stock(symbol=ticker.upper(), source="VCI")
                df    = stock.quote.history(start=start, end=end, interval="1D")
            if df is None or df.empty:
                return f"Không lấy được giá của {ticker}."
            df.columns = [c.lower() for c in df.columns]
            latest = df.iloc[-1]
            prev   = df.iloc[-2] if len(df) > 1 else None
            change = ""
            if prev is not None and prev["close"] != 0:
                pct = (latest["close"] - prev["close"]) / prev["close"] * 100
                change = f" ({pct:+.2f}% so với phiên trước)"
            # vnstock (nguồn VCI) trả giá theo đơn vị NGHÌN ĐỒNG -> nhân 1000 để ra VNĐ thật
            UNIT = 1000
            return (
                f"Giá {ticker.upper()} ngày {latest.get('time', end)}:\n"
                f"  Đóng cửa : {latest['close']*UNIT:,.0f} VNĐ{change}\n"
                f"  Cao nhất : {latest['high']*UNIT:,.0f} VNĐ\n"
                f"  Thấp nhất: {latest['low']*UNIT:,.0f} VNĐ\n"
                f"  Khối lượng: {latest.get('volume', 'N/A'):,}"
            )
        except ImportError:
            return "vnstock chưa được cài."
        except Exception as e:
            return f"Lỗi khi lấy giá {ticker}: {str(e)}"


# ======================================================================
# LLM PROVIDER — abstract class để dễ swap AI provider
# ======================================================================

class LLMProvider(ABC):
    """
    Abstract class tách phần gọi AI ra khỏi logic agent.

    Mỗi provider implement chat() trả về dict chuẩn hoá:
      {
        "stop_reason": "tool_use" | "end_turn",
        "content": [ {"type":"text","text":...} | {"type":"tool_use","id","name","input"} ],
        "raw_assistant_msg": <object để append vào history đúng format provider>,
      }
    Và 2 helper để build lại messages cho lượt tiếp theo:
      - assistant_message(raw_assistant_msg) -> dict (message để append)
      - tool_result_message(results: list[{"tool_use_id","content"}]) -> dict
    """

    @abstractmethod
    def chat(self, messages: list, tools: list, system: str) -> dict:
        pass

    @abstractmethod
    def assistant_message(self, raw) -> dict:
        pass

    @abstractmethod
    def tool_result_message(self, results: list) -> dict:
        pass


class AnthropicProvider(LLMProvider):
    """
    Provider cho Claude (Anthropic).
    Cài đặt: pip install anthropic
    API key: ANTHROPIC_API_KEY
    """

    def __init__(self, api_key: str, model: str = "claude-opus-4-5", max_tokens: int = 4096):
        import anthropic
        self.client     = anthropic.Anthropic(api_key=api_key)
        self.model      = model
        self.max_tokens = max_tokens

    def chat(self, messages: list, tools: list, system: str) -> dict:
        response = self.client.messages.create(
            model      = self.model,
            max_tokens = self.max_tokens,
            system     = system,
            tools      = _anthropic_tools(),
            messages   = messages,
        )
        content = []
        for block in response.content:
            if block.type == "text":
                content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                content.append({
                    "type": "tool_use", "id": block.id,
                    "name": block.name, "input": block.input,
                })
        return {
            "stop_reason":       response.stop_reason,
            "content":           content,
            "raw_assistant_msg": response.content,
        }

    def assistant_message(self, raw) -> dict:
        return {"role": "assistant", "content": raw}

    def tool_result_message(self, results: list) -> dict:
        return {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": r["tool_use_id"], "content": r["content"]}
            for r in results
        ]}


class GroqProvider(LLMProvider):
    """
    Provider cho các model trên Groq (Llama 3.3, Kimi, Qwen, GPT-OSS...).
    API tương thích OpenAI — dùng SDK `openai` với base_url của Groq.

    Cài đặt: pip install openai
    API key: GROQ_API_KEY (lấy tại console.groq.com/keys)

    Model gợi ý: 'llama-3.3-70b-specdec' (text, không reasoning, 128K context)
    """

    BASE_URL = "https://api.groq.com/openai/v1"

    # Model routing: 70B cho câu hỏi phức tạp, 8B cho câu hỏi đơn giản
    HEAVY_MODEL = "qwen/qwen3.6-27b"  # predict_ticker, analyze_news
    LIGHT_MODEL = "qwen/qwen3.6-27b"     # tra cứu số liệu, ranking, giá

    # Keywords quyết định dùng model nặng
    HEAVY_KEYWORDS = [
        "dự báo", "nên mua", "nên bán", "triển vọng", "xu hướng",
        "có nên", "forecast", "predict", "buy", "sell", "phân tích tổng",
        # Câu hỏi vĩ mô/sự kiện cần 70B để điều phối đúng
        "ảnh hưởng", "tác động", "chiến tranh", "lãi suất",
        "tỷ giá", "lạm phát", "sự kiện", "khủng hoảng",
    ]

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-specdec", max_tokens: int = 4096):
        from openai import OpenAI
        self.client        = OpenAI(api_key=api_key, base_url=self.BASE_URL)
        self.model         = model   # model mặc định (override nếu cần)
        self.max_tokens    = max_tokens
        self._force_model  = (model != self.HEAVY_MODEL)  # True nếu user chỉ định model cụ thể

    def _pick_model(self, messages: list) -> str:
        """
        Chọn model phù hợp dựa trên nội dung câu hỏi cuối cùng.
        - Câu hỏi dự báo/phân tích tổng hợp → 70B (chính xác hơn)
        - Câu hỏi tra cứu/số liệu đơn giản  → 8B  (nhanh hơn, rate limit cao hơn)
        """
        if self._force_model:
            return self.model   # user đã chỉ định model cụ thể → dùng đúng model đó

        # Lấy câu hỏi gần nhất của user
        last_user = ""
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    last_user = content.lower()
                    break

        # Nếu có tool predict_ticker trong messages gần đây → cần 70B
        recent_str = str(messages[-3:]).lower()
        if "predict_ticker" in recent_str:
            return self.HEAVY_MODEL

        # Kiểm tra keyword
        if any(kw in last_user for kw in self.HEAVY_KEYWORDS):
            return self.HEAVY_MODEL

        return self.LIGHT_MODEL

    def chat(self, messages: list, tools: list, system: str) -> dict:
        import time
        import openai as openai_module

        # Chọn model phù hợp cho câu hỏi này
        active_model = self._pick_model(messages)

        # OpenAI/Groq format: system là 1 message riêng trong list, không phải param riêng
        full_messages = [{"role": "system", "content": system}] + messages

        # ── Retry with exponential backoff cho rate limit (429) ──────────
        MAX_RETRIES = 6
        BASE_DELAY  = 10  # giây — Qwen/Groq reset sau 10-60s

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model      = active_model,
                    max_tokens = self.max_tokens,
                    tools      = _openai_tools(),
                    messages   = full_messages,
                )
                break   # thành công → thoát vòng lặp

            except openai_module.RateLimitError as e:
                last_error = e
                if attempt == MAX_RETRIES - 1:
                    print(f"[Rate limit] Đã thử {MAX_RETRIES} lần, vẫn bị limit. Dừng lại.", flush=True)
                raise RateLimitError(
                        f"Đã thử {MAX_RETRIES} lần (tổng ~{sum(BASE_DELAY * (2**i) for i in range(MAX_RETRIES))}s) "
                        f"nhưng vẫn bị rate limit. Vui lòng đợi 1-2 phút rồi thử lại."
                    ) from e
                wait = BASE_DELAY * (2 ** attempt)   # 5 → 10 → 20 → 40s
                # GroqProvider không có verbose — dùng print trực tiếp
                print(f"[Rate limit] Chạm giới hạn API. Đợi {wait}s rồi thử lại (lần {attempt+1}/{MAX_RETRIES})...", flush=True)
                for remaining in range(wait, 0, -5):
                    print(f"  → Còn {remaining}s...", flush=True)
                    time.sleep(min(5, remaining))
                print(f"  → Thử lại ngay bây giờ...", flush=True)
                continue

            except openai_module.BadRequestError as e:
                # Llama trên Groq đôi khi sinh tool call sai format (lỗi 'tool_use_failed')
                # khi schema/câu hỏi quá phức tạp. Retry 1 lần KHÔNG kèm tools để model
                # trả lời bằng text thường (tốt hơn là crash toàn bộ chương trình).
                # Check bằng string match — robust hơn vì cấu trúc e.body có thể
                # khác nhau giữa các phiên bản SDK.
                err_str = str(e)

                # Groq có thể trả về 2 dạng lỗi khi Llama sinh tool call sai format:
                # - "tool_use_failed" (lỗi cũ)
                # - "tool call validation failed" (lỗi mới khi tool name bị ghép sai)
                is_tool_format_error = (
                    "tool_use_failed" in err_str
                    or "tool call validation failed" in err_str
                    or "attempted to call tool" in err_str
                )

                if is_tool_format_error:
                    retry_messages = full_messages + [{
                        "role": "system",
                        "content": (
                            "Lệnh gọi tool trước bị lỗi format — tên tool và tham số "
                            "bị ghép sai cú pháp. Hãy gọi lại ĐÚNG 1 tool duy nhất "
                            "với tham số đơn giản. Với predict_ticker chỉ cần: "
                            "ticker (mã CP), sector (ngành viết HOA), question (câu hỏi ngắn). "
                            "KHÔNG dùng cú pháp function=name,{...} — dùng đúng tool call format."
                        ),
                    }]
                    response = self.client.chat.completions.create(
                        model      = active_model,
                        max_tokens = self.max_tokens,
                        tools      = _openai_tools(),
                        messages   = retry_messages,
                    )
                else:
                    raise

        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason  # 'tool_calls' | 'stop' | ...

        content = []
        if msg.content:
            content.append({"type": "text", "text": msg.content})

        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}
                content.append({
                    "type": "tool_use", "id": tc.id,
                    "name": tc.function.name, "input": args,
                })

        stop_reason = "tool_use" if (msg.tool_calls and finish_reason == "tool_calls") else "end_turn"

        # Nếu retry không trả text và không có tool_calls, đảm bảo vẫn có content
        if not content:
            content = [{"type": "text", "text": "(Không có phản hồi từ model — thử hỏi lại với câu đơn giản hơn.)"}]

        return {
            "stop_reason":       stop_reason,
            "content":           content,
            "raw_assistant_msg": msg,   # giữ object gốc để build lại tool_calls đúng format
        }

    def assistant_message(self, raw) -> dict:
        """
        raw là ChatCompletionMessage gốc từ OpenAI SDK.
        Convert về dict format chuẩn OpenAI để append vào messages list.
        """
        msg = {"role": "assistant", "content": raw.content}
        if raw.tool_calls:
            msg["tool_calls"] = [
                {
                    "id":   tc.id,
                    "type": "function",
                    "function": {
                        "name":      tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in raw.tool_calls
            ]
        return msg

    def tool_result_message(self, results: list) -> dict:
        """
        OpenAI/Groq yêu cầu MỖI tool result là 1 message riêng với role='tool'.
        Vì FinancialAgent append message này như 1 message duy nhất,
        ta trả về list — FinancialAgent sẽ detect và extend thay vì append.
        """
        return {
            "_multi": [
                {"role": "tool", "tool_call_id": r["tool_use_id"], "content": r["content"]}
                for r in results
            ]
        }


class OpenAIProvider(LLMProvider):
    """Placeholder — chưa implement. Dùng GroqProvider (cùng format) hoặc tự thêm."""

    def __init__(self, api_key: str, model: str = "gpt-4o", max_tokens: int = 4096):
        raise NotImplementedError(
            "OpenAIProvider chưa implement. GroqProvider dùng chung format OpenAI, "
            "có thể copy logic và đổi base_url='https://api.openai.com/v1'."
        )

    def chat(self, messages, tools, system):
        raise NotImplementedError

    def assistant_message(self, raw):
        raise NotImplementedError

    def tool_result_message(self, results):
        raise NotImplementedError


class GoogleProvider(LLMProvider):
    """Placeholder — chưa implement."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro", max_tokens: int = 4096):
        raise NotImplementedError("GoogleProvider chưa implement.")

    def chat(self, messages, tools, system):
        raise NotImplementedError

    def assistant_message(self, raw):
        raise NotImplementedError

    def tool_result_message(self, results):
        raise NotImplementedError


# ======================================================================
# PROVIDER FACTORY
# ======================================================================

PROVIDER_DEFAULT_MODELS = {
    "anthropic": "claude-opus-4-5",
    "groq":      "llama-3.3-70b-specdec",
    "openai":    "gpt-4o",
    "google":    "gemini-1.5-pro",
}

PROVIDER_ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "groq":      "GROQ_API_KEY",
    "openai":    "OPENAI_API_KEY",
    "google":    "GOOGLE_API_KEY",
}


def create_provider(provider: str = "anthropic", api_key: str = None, **kwargs) -> LLMProvider:
    """
    Tạo LLM provider theo tên.

    Parameters
    ----------
    provider : 'anthropic' | 'groq' | 'openai' | 'google'
    api_key  : API key (hoặc set env var tương ứng — xem PROVIDER_ENV_KEYS)
    kwargs   : model, max_tokens...
    """
    p = provider.lower()

    if p not in PROVIDER_ENV_KEYS:
        raise ValueError(f"Provider '{provider}' không hỗ trợ. Chọn: {list(PROVIDER_ENV_KEYS)}")

    env_key = PROVIDER_ENV_KEYS[p]
    key = api_key or os.environ.get(env_key)
    if not key:
        raise ValueError(f"Cần {env_key}. Set env var hoặc truyền api_key.")

    # Model mặc định nếu không truyền
    kwargs.setdefault("model", PROVIDER_DEFAULT_MODELS[p])

    if p == "anthropic":
        return AnthropicProvider(api_key=key, **kwargs)
    elif p == "groq":
        return GroqProvider(api_key=key, **kwargs)
    elif p == "openai":
        return OpenAIProvider(api_key=key, **kwargs)
    elif p == "google":
        return GoogleProvider(api_key=key, **kwargs)


# ======================================================================
# FINANCIAL AGENT
# ======================================================================

class FinancialAgent:
    """
    AI Agent phân tích tài chính — hỗ trợ multi-turn conversation.

    Cách dùng:
        # Anthropic
        agent = FinancialAgent(provider="anthropic", api_key="sk-ant-...")

        # Groq (Llama 3.3 70B)
        agent = FinancialAgent(provider="groq", api_key="gsk_...")

        print(agent.ask("Ngành nào có factor mạnh nhất?"))

        # Multi-turn
        agent.ask("VCB có ROA bao nhiêu năm 2023?")
        agent.ask("So với TCB thì sao?")
        agent.reset()
    """

    def __init__(
        self,
        provider: str = "anthropic",
        api_key: Optional[str] = None,
        data_root: str = "data",
        output_root: str = "outputs",
        verbose: bool = False,
        max_tool_turns: int = 8,
        **provider_kwargs,
    ):
        self.llm            = create_provider(provider, api_key, **provider_kwargs)
        self.executor       = ToolExecutor(data_root=data_root, output_root=output_root)
        self.verbose        = verbose
        self.max_tool_turns = max_tool_turns
        self._history: list = []
        self._cache         = SimpleCache(cache_file=f"{data_root}/agent_cache.json")

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def ask(self, question: str) -> str:
        """
        Gửi câu hỏi — agent nhớ context từ các câu trước.
        Raises: RateLimitError nếu Groq rate limit sau tất cả retry.
        """
        # Cache check — cache câu hỏi nặng (dự báo, phân tích sự kiện vĩ mô)
        _is_heavy = any(kw in question.lower() for kw in
                        ["dự báo", "nên mua", "nên bán", "triển vọng", "xu hướng",
                         "có nên", "forecast", "predict", "buy", "sell",
                         # Thêm: câu hỏi sự kiện vĩ mô cũng nặng token
                         "ảnh hưởng", "tác động", "chiến tranh", "lãi suất",
                         "tỷ giá", "lạm phát", "sự kiện", "khủng hoảng",
                         "phân tích", "đánh giá", "nhận định"])
        if _is_heavy:
            cached = self._cache.get(question)
            if cached:
                if self.verbose:
                    print(f"[Cache HIT] Returning cached answer")
                return f"*(Từ cache — cập nhật mỗi 24h)*\n\n{cached}"

        self._history.append({"role": "user", "content": question})

        if self.verbose:
            print(f"\n[Agent] Q: {question}")

        seen_calls = set()  # detect tool call lặp lại y hệt (cùng tool + cùng input)

        for _ in range(self.max_tool_turns):
            response = self.llm.chat(
                messages = self._history,
                tools    = TOOLS,
                system   = SYSTEM_PROMPT,
            )

            if response["stop_reason"] == "tool_use":
                self._append(self.llm.assistant_message(response["raw_assistant_msg"]))

                tool_results = []
                for block in response["content"]:
                    if block["type"] == "tool_use":
                        if self.verbose:
                            print(f"[Agent] Tool: {block['name']}({block['input']})")

                        call_sig = (block["name"], json.dumps(block["input"], sort_keys=True))
                        if call_sig in seen_calls:
                            # Tool call y hệt lần trước → không chạy lại, báo cho model biết
                            result = (
                                "LƯU Ý: Bạn đã gọi tool này với CÙNG tham số ở lượt trước "
                                "và không nhận được dữ liệu cần thiết. "
                                "Đừng gọi lại với tham số giống nhau — hãy thử tên cột khác "
                                "(xem danh sách cột có sẵn ở kết quả trước), hoặc nếu vẫn không có, "
                                "trả lời người dùng là không tìm thấy dữ liệu."
                            )
                        else:
                            seen_calls.add(call_sig)
                            result = self.executor.execute(block["name"], block["input"])

                        if self.verbose:
                            print(f"[Agent] Result: {result[:150]}...")
                        tool_results.append({"tool_use_id": block["id"], "content": result})

                self._append(self.llm.tool_result_message(tool_results))

            elif response["stop_reason"] == "end_turn":
                answer = ""
                for block in response["content"]:
                    if block["type"] == "text":
                        answer += block["text"]
                answer = answer.strip()
                self._history.append({"role": "assistant", "content": answer})

                # Lưu vào cache nếu là câu hỏi nặng (dự báo/phân tích tổng hợp)
                if _is_heavy and answer:
                    self._cache.set(question, answer)
                    if self.verbose:
                        print(f"[Cache SAVE] Đã lưu câu trả lời vào cache")

                return answer

            else:
                return f"Agent dừng với lý do: {response['stop_reason']}"

        return "Agent đã thử quá nhiều lần gọi tool mà chưa có câu trả lời cuối. Vui lòng hỏi lại rõ hơn."

    def _append(self, msg: dict):
        """
        Append message vào history.
        Một số provider (Groq/OpenAI) cần nhiều message 'tool' riêng biệt
        cho 1 lượt tool_result — msg dạng {"_multi": [...]} sẽ được extend.
        """
        if "_multi" in msg:
            self._history.extend(msg["_multi"])
        else:
            self._history.append(msg)

    def reset(self):
        """Xóa conversation history — bắt đầu cuộc hội thoại mới."""
        self._history = []
        if self.verbose:
            print("[Agent] Conversation reset.")

    @property
    def history(self) -> list:
        """Xem lịch sử hội thoại (rút gọn, chỉ user/assistant text)."""
        readable = []
        for msg in self._history:
            content = msg.get("content")
            if isinstance(content, str):
                readable.append({
                    "role":    msg["role"],
                    "content": content[:200] + "..." if len(content) > 200 else content,
                })
        return readable

    @property
    def turn_count(self) -> int:
        """Số lượt hỏi đáp trong cuộc hội thoại hiện tại."""
        return sum(1 for m in self._history if m.get("role") == "user" and isinstance(m.get("content"), str))
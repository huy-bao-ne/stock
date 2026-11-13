"""
ui/app.py
==========
Streamlit UI cho Financial Factor Analysis Engine.

Cách chạy:
    cd project/
    streamlit run ui/app.py

4 trang:
  1. Tổng quan      — so sánh kết quả 10 ngành
  2. Chi tiết ngành — bảng factor + biểu đồ 1 ngành
  3. Tra cứu ticker — dữ liệu tài chính 1 công ty cụ thể
  4. Chatbot        — hỏi đáp với AI Agent (Groq/Llama)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ======================================================================
# CẤU HÌNH TRANG
# ======================================================================

st.set_page_config(
    page_title = "Factor Analysis — VNSTOCK",
    page_icon  = "📊",
    layout     = "wide",
    initial_sidebar_state = "expanded",
)

# ======================================================================
# CUSTOM THEME — fonts + colors nhất quán 
#   Headers : Source Serif 4  
#   Body    : IBM Plex Sans
#   Số liệu : IBM Plex Mono   
#   Palette : Navy #0D1B3E · Teal #028090 · Mint #02C39A
# ======================================================================

def inject_custom_css():
    st.markdown("""
    <style>
    /* ================================================================
       FINANCIAL FACTOR ANALYSIS — Custom Theme
       Fonts  : Source Serif 4 (headers) · IBM Plex Sans (body) · IBM Plex Mono (data)
       Palette: Navy #0D1B3E · Teal #028090 · Mint #02C39A · BG #F4F8FB
    ================================================================ */
    @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,600;0,700;1,400&family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

    :root {
        --navy:    #0D1B3E;
        --navy2:   #142040;
        --teal:    #028090;
        --teal2:   #03A0B2;
        --mint:    #02C39A;
        --bg:      #F4F8FB;
        --bg2:     #EBF3F7;
        --card:    #FFFFFF;
        --border:  #E2E8F0;
        --text:    #1E293B;
        --muted:   #64748B;
        --amber:   #D97706;
        --green:   #16A34A;
        --red:     #DC2626;
        --shadow:  0 2px 12px rgba(13,27,62,0.07);
        --shadow2: 0 4px 24px rgba(13,27,62,0.10);
    }

    /* ── RESET & BASE ─────────────────────────────────────────── */
    html, body { background-color: var(--bg) !important; }

    html, body, [class*="css"], p, span, div, label, input, select {
        font-family: 'IBM Plex Sans', sans-serif !important;
        color: var(--text);
    }

    /* Remove Streamlit default padding excess */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 1280px !important;
    }

    /* ── TYPOGRAPHY ───────────────────────────────────────────── */
    h1 {
        font-family: 'Source Serif 4', serif !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: var(--navy) !important;
        letter-spacing: -0.02em;
        line-height: 1.2 !important;
        margin-bottom: 0.25rem !important;
    }
    h2 {
        font-family: 'Source Serif 4', serif !important;
        font-size: 1.35rem !important;
        font-weight: 600 !important;
        color: var(--navy) !important;
        letter-spacing: -0.01em;
    }
    h3 {
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        color: var(--text) !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    p { line-height: 1.65 !important; }
    code, pre, .stCodeBlock, [data-testid="stCode"] * {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.85rem !important;
    }

    /* ── SIDEBAR ──────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--navy) 0%, #0A162E 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.06) !important;
    }
    [data-testid="stSidebarContent"] { padding: 1.2rem 1rem !important; }

    /* Sidebar text */
    [data-testid="stSidebar"] *:not(button):not(input) {
        color: rgba(224,240,245,0.9) !important;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2 {
        font-family: 'Source Serif 4', serif !important;
        color: #FFFFFF !important;
        font-size: 1.15rem !important;
    }
    [data-testid="stSidebar"] .stMarkdown p {
        font-size: 0.8rem !important;
        color: rgba(180,210,220,0.75) !important;
        line-height: 1.5 !important;
    }
    [data-testid="stSidebar"] hr {
        border: none !important;
        border-top: 1px solid rgba(255,255,255,0.1) !important;
        margin: 0.8rem 0 !important;
    }
    [data-testid="stSidebar"] .stCaption {
        color: rgba(150,195,210,0.65) !important;
        font-size: 0.72rem !important;
    }

    /* Sidebar nav — radio items styled as nav links */
    [data-testid="stSidebar"] [role="radiogroup"] {
        gap: 0.15rem !important;
        display: flex !important;
        flex-direction: column !important;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label {
        display: flex !important;
        align-items: center !important;
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        border-radius: 8px !important;
        padding: 0.6rem 0.85rem !important;
        margin: 0 !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        color: rgba(210,235,245,0.85) !important;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(2,128,144,0.2) !important;
        border-color: rgba(2,128,144,0.4) !important;
        color: #FFFFFF !important;
        transform: translateX(3px) !important;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"] {
        background: linear-gradient(90deg, rgba(2,128,144,0.5) 0%, rgba(2,128,144,0.25) 100%) !important;
        border-color: var(--teal) !important;
        border-left: 3px solid var(--mint) !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    /* Hide default radio circle */
    [data-testid="stSidebar"] [role="radiogroup"] input[type="radio"] {
        display: none !important;
    }

    /* ── MAIN CONTENT ─────────────────────────────────────────── */
    .main .block-container { background: var(--bg) !important; }

    /* Page title area */
    .page-header {
        background: linear-gradient(135deg, var(--navy) 0%, #1a3a5c 100%);
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: var(--shadow2);
        position: relative;
        overflow: hidden;
    }
    .page-header::before {
        content: '';
        position: absolute;
        top: -30px; right: -30px;
        width: 120px; height: 120px;
        background: var(--teal);
        border-radius: 50%;
        opacity: 0.08;
    }
    .page-header h1 {
        color: #FFFFFF !important;
        margin: 0 !important;
        font-size: 1.6rem !important;
    }
    .page-header p {
        color: rgba(180,220,235,0.75) !important;
        font-size: 0.85rem !important;
        margin: 0.3rem 0 0 0 !important;
    }
    .page-header .badge {
        display: inline-block;
        background: rgba(2,195,154,0.2);
        border: 1px solid rgba(2,195,154,0.4);
        color: var(--mint) !important;
        font-size: 0.7rem !important;
        font-weight: 600;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.5rem;
    }

    /* ── METRIC CARDS — signature element: left accent border ──── */
    [data-testid="stMetric"] {
        background: var(--card) !important;
        border: 1px solid var(--border) !important;
        border-left: 4px solid var(--teal) !important;
        border-radius: 12px !important;
        padding: 1rem 1.1rem 0.9rem !important;
        box-shadow: var(--shadow) !important;
        transition: box-shadow 0.2s ease, transform 0.2s ease !important;
    }
    [data-testid="stMetric"]:hover {
        box-shadow: var(--shadow2) !important;
        transform: translateY(-2px) !important;
    }
    [data-testid="stMetricValue"] {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 1.6rem !important;
        font-weight: 600 !important;
        color: var(--navy) !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.07em !important;
        color: var(--muted) !important;
    }
    [data-testid="stMetricDelta"] {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.8rem !important;
    }

    /* ── BUTTONS ──────────────────────────────────────────────── */
    .stButton > button {
        background: linear-gradient(135deg, var(--teal) 0%, var(--teal2) 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.2rem !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
        letter-spacing: 0.01em !important;
        box-shadow: 0 2px 8px rgba(2,128,144,0.3) !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(2,128,144,0.4) !important;
    }
    .stButton > button:active { transform: translateY(0) !important; }

    /* Secondary buttons (suggestions) */
    .stButton > button[kind="secondary"],
    div[data-testid="column"] .stButton > button {
        background: var(--card) !important;
        color: var(--teal) !important;
        border: 1px solid var(--border) !important;
        box-shadow: var(--shadow) !important;
    }
    div[data-testid="column"] .stButton > button:hover {
        background: var(--bg2) !important;
        border-color: var(--teal) !important;
        box-shadow: 0 4px 12px rgba(2,128,144,0.15) !important;
    }

    /* ── SELECTBOX / INPUT ────────────────────────────────────── */
    [data-testid="stSelectbox"] > div > div {
        border-radius: 8px !important;
        border: 1px solid var(--border) !important;
        background: var(--card) !important;
        box-shadow: var(--shadow) !important;
    }
    [data-testid="stSelectbox"] > div > div:focus-within {
        border-color: var(--teal) !important;
        box-shadow: 0 0 0 3px rgba(2,128,144,0.12) !important;
    }
    .stTextInput > div > div > input {
        border-radius: 8px !important;
        border: 1px solid var(--border) !important;
        background: var(--card) !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.95rem !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: var(--teal) !important;
        box-shadow: 0 0 0 3px rgba(2,128,144,0.12) !important;
    }

    /* ── TABS ─────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--card) !important;
        border-radius: 10px 10px 0 0 !important;
        padding: 0.3rem 0.4rem 0 !important;
        border-bottom: 2px solid var(--border) !important;
        gap: 0.2rem !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-weight: 500 !important;
        font-size: 0.88rem !important;
        padding: 0.55rem 1rem !important;
        border-radius: 8px 8px 0 0 !important;
        color: var(--muted) !important;
        background: transparent !important;
        border: none !important;
        transition: all 0.15s ease !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--teal) !important;
        background: rgba(2,128,144,0.06) !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--teal) !important;
        border-bottom: 2px solid var(--teal) !important;
        background: rgba(2,128,144,0.06) !important;
        font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        background: var(--card) !important;
        border: 1px solid var(--border) !important;
        border-top: none !important;
        border-radius: 0 0 10px 10px !important;
        padding: 1.2rem !important;
        box-shadow: var(--shadow) !important;
    }

    /* ── DATAFRAME ────────────────────────────────────────────── */
    [data-testid="stDataFrame"] {
        border-radius: 10px !important;
        border: 1px solid var(--border) !important;
        overflow: hidden !important;
        box-shadow: var(--shadow) !important;
    }
    [data-testid="stDataFrame"] thead th {
        background: var(--navy) !important;
        color: #FFFFFF !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        padding: 0.7rem 0.8rem !important;
    }
    [data-testid="stDataFrame"] tbody tr:nth-child(even) {
        background: var(--bg) !important;
    }
    [data-testid="stDataFrame"] tbody tr:hover {
        background: rgba(2,128,144,0.06) !important;
    }
    [data-testid="stDataFrame"] tbody td {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.82rem !important;
        padding: 0.55rem 0.8rem !important;
    }

    /* ── TOGGLE / CHECKBOX ────────────────────────────────────── */
    .stToggle > label, .stCheckbox > label {
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        color: var(--text) !important;
    }

    /* ── CHART CONTAINERS ─────────────────────────────────────── */
    [data-testid="stPlotlyChart"] {
        background: var(--card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        padding: 0.5rem !important;
        box-shadow: var(--shadow) !important;
    }

    /* ── CHAT — styled like modern AI chat ────────────────────── */
    [data-testid="stChatInput"] {
        border-radius: 12px !important;
        box-shadow: var(--shadow2) !important;
    }
    [data-testid="stChatInput"] textarea {
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 0.9rem !important;
        border-radius: 12px !important;
        border: 1.5px solid var(--border) !important;
        background: var(--card) !important;
        padding: 0.75rem 1rem !important;
        line-height: 1.5 !important;
        transition: border-color 0.15s ease !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: var(--teal) !important;
        box-shadow: 0 0 0 3px rgba(2,128,144,0.12) !important;
    }
    [data-testid="stChatMessage"] {
        border-radius: 14px !important;
        border: 1px solid var(--border) !important;
        box-shadow: var(--shadow) !important;
        margin-bottom: 0.6rem !important;
        padding: 0.2rem 0 !important;
        transition: box-shadow 0.15s ease !important;
    }
    [data-testid="stChatMessage"]:hover {
        box-shadow: var(--shadow2) !important;
    }
    /* User message: light teal tint */
    [data-testid="stChatMessage"][data-testid*="user"] {
        background: rgba(2,128,144,0.04) !important;
        border-left: 3px solid var(--teal) !important;
    }
    /* Assistant message: white */
    [data-testid="stChatMessage"]:not([data-testid*="user"]) {
        background: var(--card) !important;
        border-left: 3px solid var(--mint) !important;
    }
    /* Chat text */
    [data-testid="stChatMessage"] p {
        font-size: 0.92rem !important;
        line-height: 1.7 !important;
    }
    /* Spinner trong chat */
    .stSpinner > div {
        border-color: var(--teal) transparent transparent transparent !important;
    }

    /* ── MISC ─────────────────────────────────────────────────── */
    hr {
        border: none !important;
        border-top: 1px solid var(--border) !important;
        margin: 1rem 0 !important;
    }
    .stCaption, [data-testid="stCaptionContainer"] p {
        font-size: 0.75rem !important;
        color: var(--muted) !important;
        line-height: 1.5 !important;
    }
    /* Warning/error/info boxes */
    [data-testid="stAlert"] {
        border-radius: 10px !important;
        border-left-width: 4px !important;
    }
    /* Multiselect tags */
    [data-baseweb="tag"] {
        background: rgba(2,128,144,0.12) !important;
        color: var(--teal) !important;
        border-radius: 6px !important;
        border: 1px solid rgba(2,128,144,0.25) !important;
        font-size: 0.8rem !important;
    }

    /* ── SCROLLBAR ────────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb {
        background: #C4D7DF;
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover { background: var(--teal); }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ======================================================================
# CONSTANTS
# ======================================================================

SECTORS = {
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

DATA_ROOT    = Path("data")
OUTPUT_ROOT  = Path("outputs")

# ======================================================================
# DATA LOADING (cache để không đọc lại mỗi lần)
# ======================================================================

@st.cache_data
def load_factor_results(sector: str) -> pd.DataFrame:
    path = OUTPUT_ROOT / sector.lower() / f"{sector.lower()}_factor_results.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    # Chuẩn hoá boolean columns
    for col in ["có_ý_nghĩa_thống_kê", "có_ý_nghĩa_sau_bonferroni"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda v: str(v).strip().lower() == "true")
    # Parse correlation % thành số
    if "độ_tương_quan_%" in df.columns:
        df["corr_value"] = df["độ_tương_quan_%"].str.replace("%","").str.strip().astype(float)
    return df

@st.cache_data
def load_ticker_results(sector: str) -> pd.DataFrame:
    path = OUTPUT_ROOT / sector.lower() / f"{sector.lower()}_ticker_results.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    for col in ["có_ý_nghĩa_thống_kê", "có_ý_nghĩa_sau_bonferroni"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda v: str(v).strip().lower() == "true")
    if "độ_tương_quan_%" in df.columns:
        df["corr_value"] = df["độ_tương_quan_%"].str.replace("%","").str.strip().astype(float)
    return df

@st.cache_data
def load_gold_dataset(sector: str) -> pd.DataFrame:
    path = DATA_ROOT / sector.lower() / "gold_factors.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    for col in ["năm_chưa_kết_thúc", "thiếu_dữ_liệu"]:
        if col in df.columns:
            df = df.drop(columns=[col])
    return df

@st.cache_data
def load_all_sector_summary() -> pd.DataFrame:
    """Tạo bảng tóm tắt tất cả 10 ngành."""
    rows = []
    for sector_key, sector_label in SECTORS.items():
        df = load_factor_results(sector_key)
        if df.empty:
            rows.append({
                "Ngành": sector_label, "Mã": sector_key,
                "Factors tested": 0, "Obs (max)": 0,
                "Significant (p<0.05)": 0, "Significant (Bonferroni)": 0,
                "Factor mạnh nhất": "—", "Tương quan": "—",
            })
            continue
        top = df.iloc[0]
        rows.append({
            "Ngành":                   sector_label,
            "Mã":                      sector_key,
            "Factors tested":          len(df),
            "Obs (max)":               int(df["số_quan_sát"].max()),
            "Significant (p<0.05)":    int(df["có_ý_nghĩa_thống_kê"].sum()),
            "Significant (Bonferroni)":int(df["có_ý_nghĩa_sau_bonferroni"].sum()),
            "Factor mạnh nhất":        top["chỉ_báo"],
            "Tương quan":              top["độ_tương_quan_%"],
        })
    return pd.DataFrame(rows)


# ======================================================================
# SIDEBAR
# ======================================================================

with st.sidebar:
    # Brand block
    st.markdown("""
    <div style="padding:0.4rem 0 1rem 0">
        <div style="font-family:'Source Serif 4',serif;font-size:1.15rem;font-weight:700;color:#FFFFFF;letter-spacing:-0.01em;line-height:1.2">
            Factor Analysis
        </div>
        <div style="font-size:0.72rem;color:rgba(160,205,220,0.7);margin-top:0.25rem;letter-spacing:0.03em">
            VNSTOCK · VIỆT NAM
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    st.markdown('<div style="font-size:0.7rem;font-weight:600;color:rgba(150,195,210,0.55);letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.5rem">ĐIỀU HƯỚNG</div>', unsafe_allow_html=True)
    page = st.radio(
        "Trang",
        options=["🌐 Tổng quan", "🔍 Chi tiết ngành", "🏢 Tra cứu ticker", "🤖 Chatbot"],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("""
    <div style="font-size:0.7rem;font-weight:600;color:rgba(150,195,210,0.55);letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.5rem">
        DỰ ÁN
    </div>
    <div style="font-size:0.75rem;color:rgba(160,205,220,0.7);line-height:1.8">
        📅 Dữ liệu: 2018 – 2024<br>
        🏭 10 ngành kinh tế<br>
        📈 50 tickers<br>
        🔬 Spearman + Bonferroni<br>
        🤖 AI: Llama 3.3 70B / Groq
    </div>
    """, unsafe_allow_html=True)


# ======================================================================
# TRANG 1: TỔNG QUAN
# ======================================================================

if page == "🌐 Tổng quan":
    st.markdown("""
    <div class="page-header">
        <div class="badge">Phân tích nhân tố · 2018–2024</div>
        <h1>Tổng quan 10 ngành</h1>
        <p>Kết quả Spearman Rank Correlation giữa các chỉ báo tài chính và tỷ suất sinh lời cổ phiếu — Bonferroni Correction kiểm soát false positive.</p>
    </div>
    """, unsafe_allow_html=True)

    summary = load_all_sector_summary()

    if summary.empty:
        st.warning("Chưa có dữ liệu. Chạy pipeline trước: `python main.py --all`")
        st.stop()

    # --- KPI cards ---
    total_factors  = summary["Factors tested"].sum()
    total_sig_bonf = summary["Significant (Bonferroni)"].sum()
    total_sectors  = (summary["Factors tested"] > 0).sum()
    avg_obs        = int(summary[summary["Obs (max)"] > 0]["Obs (max)"].mean())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ngành phân tích",        f"{total_sectors}/10")
    c2.metric("Tổng factors kiểm định", f"{total_factors}")
    c3.metric("Significant (Bonferroni)", f"{total_sig_bonf}")
    c4.metric("Obs trung bình/ngành",   f"{avg_obs}")

    st.divider()

    # --- Bảng tóm tắt ---
    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.subheader("Kết quả theo ngành")
        display_cols = [
            "Ngành", "Obs (max)",
            "Significant (p<0.05)", "Significant (Bonferroni)",
            "Factor mạnh nhất", "Tương quan",
        ]
        df_display = summary[display_cols].copy()

        def highlight_bonf(val):
            if isinstance(val, int) and val > 0:
                return "background-color: #d4edda; color: #155724; font-weight: bold"
            return ""

        styled = df_display.style.map(
            highlight_bonf, subset=["Significant (Bonferroni)"]
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)

    with col_r:
        st.subheader("Significant factors (Bonferroni)")
        fig = px.bar(
            summary[summary["Significant (Bonferroni)"] > 0].sort_values("Significant (Bonferroni)", ascending=True),
            x="Significant (Bonferroni)",
            y="Ngành",
            orientation="h",
            color="Significant (Bonferroni)",
            color_continuous_scale="Blues",
            text="Significant (Bonferroni)",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=0, r=20, t=10, b=0),
            height=320,
            xaxis_title="",
            yaxis_title="",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Heatmap: top factor per sector ---
    st.subheader("Độ tương quan factor mạnh nhất theo ngành")

    heatmap_data = []
    all_factors = set()
    for sector_key, sector_label in SECTORS.items():
        df = load_factor_results(sector_key)
        if df.empty:
            continue
        top5 = df.head(5)
        for _, row in top5.iterrows():
            heatmap_data.append({
                "Ngành":   sector_label,
                "Factor":  row["chỉ_báo"],
                "Corr":    row.get("corr_value", 0),
                "Bonf":    row["có_ý_nghĩa_sau_bonferroni"],
            })
            all_factors.add(row["chỉ_báo"])

    if heatmap_data:
        df_heat = pd.DataFrame(heatmap_data)
        pivot   = df_heat.pivot_table(index="Ngành", columns="Factor", values="Corr", aggfunc="first").fillna(0)
        fig_heat = px.imshow(
            pivot,
            color_continuous_scale="RdBu",
            color_continuous_midpoint=0,
            aspect="auto",
            labels=dict(color="Tương quan (%)"),
        )
        fig_heat.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig_heat, use_container_width=True)
        st.caption("Top 5 factors mạnh nhất của mỗi ngành. Màu đỏ = đồng biến, màu xanh = nghịch biến.")


# ======================================================================
# TRANG 2: CHI TIẾT NGÀNH
# ======================================================================

elif page == "🔍 Chi tiết ngành":
    # Sector picker
    selected_label = st.selectbox(
        "Chọn ngành",
        options=list(SECTORS.values()),
        index=0,
    )
    selected_key = [k for k, v in SECTORS.items() if v == selected_label][0]

    df_factor = load_factor_results(selected_key)
    df_ticker = load_ticker_results(selected_key)

    if df_factor.empty:
        st.warning(f"Chưa có dữ liệu cho {selected_label}. Chạy: `python main.py --sector {selected_key}`")
        st.stop()

    st.markdown(f"""
    <div class="page-header">
        <div class="badge">Chi tiết ngành</div>
        <h1>{selected_label}</h1>
        <p>Kết quả phân tích correlation theo từng factor — sector level và ticker level.</p>
    </div>
    """, unsafe_allow_html=True)

    # KPIs
    bonf_thresh = df_factor["bonferroni_threshold"].iloc[0] if "bonferroni_threshold" in df_factor.columns else 0
    sig_std     = int(df_factor["có_ý_nghĩa_thống_kê"].sum())
    sig_bonf    = int(df_factor["có_ý_nghĩa_sau_bonferroni"].sum())
    obs_max     = int(df_factor["số_quan_sát"].max())
    n_factors   = len(df_factor)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Factors kiểm định", n_factors)
    c2.metric("Observations",      obs_max)
    c3.metric("Ngưỡng Bonferroni", f"p < {bonf_thresh:.4f}")
    c4.metric("Sig. (p<0.05)",     sig_std)
    c5.metric("Sig. (Bonferroni)", sig_bonf,
              delta="✔" if sig_bonf > 0 else None,
              delta_color="normal")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📋 Bảng ranking", "📈 Biểu đồ", "🏢 Từng công ty"])

    # --- Tab 1: Bảng ranking ---
    with tab1:
        filter_bonf = st.toggle("Chỉ hiển thị factors significant (Bonferroni)", value=False)
        df_show = df_factor[df_factor["có_ý_nghĩa_sau_bonferroni"]] if filter_bonf else df_factor

        display_cols = ["xếp_hạng", "chỉ_báo", "độ_tương_quan_%", "kết_luận",
                        "độ_mạnh", "p_value", "có_ý_nghĩa_thống_kê",
                        "có_ý_nghĩa_sau_bonferroni", "số_quan_sát"]
        df_table = df_show[[c for c in display_cols if c in df_show.columns]].copy()

        def color_row(row):
            if row.get("có_ý_nghĩa_sau_bonferroni"):
                return ["background-color: #d4edda"] * len(row)
            elif row.get("có_ý_nghĩa_thống_kê"):
                return ["background-color: #fff3cd"] * len(row)
            return [""] * len(row)

        styled_table = df_table.style.apply(color_row, axis=1)
        st.dataframe(styled_table, use_container_width=True, hide_index=True)
        st.caption("🟢 Xanh = significant sau Bonferroni | 🟡 Vàng = significant p<0.05 | Trắng = không significant")

    # --- Tab 2: Biểu đồ ---
    with tab2:
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("**Top factors theo độ tương quan**")
            df_plot = df_factor.copy()
            df_plot["abs_corr"] = df_plot["corr_value"].abs()
            df_plot = df_plot.sort_values("abs_corr", ascending=True).tail(15)
            df_plot["màu"] = df_plot["có_ý_nghĩa_sau_bonferroni"].map(
                {True: "#2ecc71", False: "#bdc3c7"}
            )

            fig_bar = go.Figure(go.Bar(
                x         = df_plot["corr_value"],
                y         = df_plot["chỉ_báo"],
                orientation = "h",
                marker_color = df_plot["màu"],
                text      = df_plot["độ_tương_quan_%"],
                textposition = "outside",
            ))
            fig_bar.add_vline(x=0, line_dash="dash", line_color="gray", line_width=1)
            fig_bar.update_layout(
                height=500,
                margin=dict(l=0, r=60, t=10, b=0),
                xaxis_title="Spearman correlation (%)",
                yaxis_title="",
                showlegend=False,
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            st.caption("🟢 Xanh = significant Bonferroni | ⚪ Xám = không significant")

        with col_r:
            st.markdown("**P-value vs Độ tương quan**")
            df_scatter = df_factor.copy()
            df_scatter["size"] = df_scatter["số_quan_sát"]
            df_scatter["sig"]  = df_scatter["có_ý_nghĩa_sau_bonferroni"].map(
                {True: "Significant", False: "Không significant"}
            )

            fig_sc = px.scatter(
                df_scatter,
                x         = "corr_value",
                y         = "p_value",
                color     = "sig",
                size      = "size",
                hover_name = "chỉ_báo",
                hover_data = {"corr_value": True, "p_value": True, "số_quan_sát": True},
                color_discrete_map = {
                    "Significant":      "#2ecc71",
                    "Không significant": "#bdc3c7",
                },
            )
            fig_sc.add_hline(
                y=bonf_thresh, line_dash="dash",
                line_color="red",
                annotation_text=f"Bonferroni p={bonf_thresh:.4f}",
                annotation_position="right",
            )
            fig_sc.update_layout(
                height=500,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis_title="Correlation (%)",
                yaxis_title="P-value",
                legend_title="",
            )
            st.plotly_chart(fig_sc, use_container_width=True)

    # --- Tab 3: Từng công ty ---
    with tab3:
        if df_ticker.empty:
            st.info("Không có dữ liệu ticker-level.")
        else:
            tickers_in_sector = sorted(df_ticker["mã_chứng_khoán"].unique().tolist())
            selected_ticker = st.selectbox("Chọn công ty", tickers_in_sector)

            df_one = df_ticker[df_ticker["mã_chứng_khoán"] == selected_ticker].copy()

            st.markdown(f"**Top factors của {selected_ticker}** *(chỉ mang tính tham khảo hướng — n nhỏ)*")

            if "corr_value" not in df_one.columns:
                df_one["corr_value"] = df_one["độ_tương_quan_%"].str.replace("%","").str.strip().astype(float)

            df_one = df_one.sort_values("corr_value", key=abs, ascending=True)

            fig_t = go.Figure(go.Bar(
                x=df_one["corr_value"],
                y=df_one["chỉ_báo"],
                orientation="h",
                marker_color=["#e74c3c" if v < 0 else "#3498db" for v in df_one["corr_value"]],
                text=df_one["độ_tương_quan_%"],
                textposition="outside",
            ))
            fig_t.add_vline(x=0, line_dash="dash", line_color="gray", line_width=1)
            fig_t.update_layout(
                height=max(300, len(df_one) * 35),
                margin=dict(l=0, r=60, t=10, b=0),
                xaxis_title="Spearman correlation (%)",
                yaxis_title="",
                showlegend=False,
            )
            st.plotly_chart(fig_t, use_container_width=True)
            st.caption("🔵 Xanh = đồng biến | 🔴 Đỏ = nghịch biến")


# ======================================================================
# TRANG 3: TRA CỨU TICKER
# ======================================================================

elif page == "🏢 Tra cứu ticker":
    st.markdown("""
    <div class="page-header">
        <div class="badge">Tra cứu</div>
        <h1>Tra cứu công ty</h1>
        <p>Xem dữ liệu tài chính chi tiết, tỷ suất sinh lời và xu hướng factors theo năm của từng mã cổ phiếu.</p>
    </div>
    """, unsafe_allow_html=True)

    # Build ticker → sector map từ config
    @st.cache_data
    def build_ticker_map():
        import yaml
        cfg_path = Path("configs/config.yaml")
        if not cfg_path.exists():
            return {}
        with open(cfg_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        mapping = {}
        for sector_key, sector_cfg in cfg.get("sectors", {}).items():
            for t in sector_cfg.get("tickers", []):
                mapping[t] = sector_key
        return mapping

    ticker_map = build_ticker_map()

    if not ticker_map:
        st.warning("Không đọc được config.yaml")
        st.stop()

    # Chọn ticker từ dropdown — hiển thị đầy đủ tất cả mã
    # Group tickers theo ngành để dễ tìm
    sector_groups = {}
    for t, sec in sorted(ticker_map.items()):
        label = SECTORS.get(sec, sec)
        if label not in sector_groups:
            sector_groups[label] = []
        sector_groups[label].append(t)

    # Tạo options dạng "FPT (Công nghệ)"
    options_display = ["— Chọn mã cổ phiếu —"]
    options_value   = [""]
    for label in sorted(sector_groups.keys()):
        for t in sorted(sector_groups[label]):
            options_display.append(f"{t}  ({label})")
            options_value.append(t)

    col_input, col_btn = st.columns([3, 1])
    with col_input:
        selected_idx = st.selectbox(
            "Chọn mã cổ phiếu",
            range(len(options_display)),
            format_func=lambda i: options_display[i],
        )
        ticker_input = options_value[selected_idx]
    with col_btn:
        st.write("")
        st.write("")
        search = st.button("🔍 Tra cứu", use_container_width=True)

    if ticker_input and (search or ticker_input):
        if ticker_input not in ticker_map:
            st.error(f"Không tìm thấy '{ticker_input}'. Vui lòng chọn từ danh sách bên trên.")
            st.stop()

        sector_key   = ticker_map[ticker_input]
        sector_label = SECTORS[sector_key]

        st.subheader(f"{ticker_input} — {sector_label}")

        # Load gold dataset
        df_gold = load_gold_dataset(sector_key)
        if df_gold.empty:
            st.warning(f"Không có gold dataset cho {sector_label}.")
            st.stop()

        df_ticker_gold = df_gold[df_gold["mã_chứng_khoán"] == ticker_input].copy()
        if df_ticker_gold.empty:
            st.warning(f"Không có dữ liệu cho {ticker_input}.")
            st.stop()

        df_ticker_gold = df_ticker_gold.sort_values("năm")

        tab_overview, tab_factors, tab_raw = st.tabs(
            ["📊 Tổng quan", "📈 Factors theo năm", "📋 Dữ liệu thô"]
        )

        # --- Tab overview ---
        with tab_overview:
            years    = df_ticker_gold["năm"].tolist()
            returns  = df_ticker_gold.get("lợi_nhuận_hàng_năm_%", pd.Series([None]*len(df_ticker_gold))).tolist()

            latest = df_ticker_gold.iloc[-1]
            prev   = df_ticker_gold.iloc[-2] if len(df_ticker_gold) > 1 else None

            # KPIs từ năm gần nhất
            kpi_cols = ["roa_%", "roe_%", "lợi_nhuận_hàng_năm_%"]
            kpi_labels = {"roa_%": "ROA", "roe_%": "ROE", "lợi_nhuận_hàng_năm_%": "Return năm gần nhất"}
            avail_kpis = [c for c in kpi_cols if c in df_ticker_gold.columns]

            if avail_kpis:
                cols = st.columns(len(avail_kpis))
                for i, col_name in enumerate(avail_kpis):
                    val  = latest.get(col_name)
                    dval = None
                    if prev is not None:
                        pval = prev.get(col_name)
                        if pd.notna(val) and pd.notna(pval) and pval != 0:
                            dval = round(val - pval, 2)
                    label = kpi_labels.get(col_name, col_name)
                    cols[i].metric(
                        label,
                        f"{val:.2f}%" if pd.notna(val) else "N/A",
                        delta=f"{dval:+.2f}pp" if dval is not None else None,
                    )

            # Biểu đồ return qua các năm
            if "lợi_nhuận_hàng_năm_%" in df_ticker_gold.columns:
                st.markdown("**Tỷ suất sinh lời hàng năm**")
                df_ret = df_ticker_gold[["năm", "lợi_nhuận_hàng_năm_%"]].dropna()
                if not df_ret.empty:
                    fig_ret = go.Figure(go.Bar(
                        x=df_ret["năm"],
                        y=df_ret["lợi_nhuận_hàng_năm_%"],
                        marker_color=["#e74c3c" if v < 0 else "#2ecc71"
                                      for v in df_ret["lợi_nhuận_hàng_năm_%"]],
                        text=[f"{v:+.1f}%" for v in df_ret["lợi_nhuận_hàng_năm_%"]],
                        textposition="outside",
                    ))
                    fig_ret.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
                    fig_ret.update_layout(
                        height=280,
                        margin=dict(l=0, r=0, t=10, b=0),
                        xaxis_title="",
                        yaxis_title="Return (%)",
                        showlegend=False,
                    )
                    st.plotly_chart(fig_ret, use_container_width=True)

        # --- Tab factors theo năm ---
        with tab_factors:
            # Chọn factor để vẽ trend
            factor_cols = [c for c in df_ticker_gold.columns
                           if c not in {"mã_chứng_khoán", "năm", "lợi_nhuận_hàng_năm_%"}
                           and not c.startswith("Unnamed")]

            selected_factors = st.multiselect(
                "Chọn factors để xem trend",
                options=factor_cols,
                default=factor_cols[:3] if len(factor_cols) >= 3 else factor_cols,
                max_selections=6,
            )

            if selected_factors:
                df_melt = df_ticker_gold[["năm"] + selected_factors].melt(
                    id_vars="năm", var_name="Factor", value_name="Giá trị"
                )
                fig_line = px.line(
                    df_melt,
                    x="năm", y="Giá trị",
                    color="Factor",
                    markers=True,
                    title=f"Trend factors của {ticker_input}",
                )
                fig_line.update_layout(
                    height=400,
                    margin=dict(l=0, r=0, t=40, b=0),
                    xaxis_title="Năm",
                    legend_title="",
                )
                st.plotly_chart(fig_line, use_container_width=True)

        # --- Tab raw data ---
        with tab_raw:
            st.dataframe(
                df_ticker_gold.set_index("năm").T,
                use_container_width=True,
            )
            st.caption(f"Dữ liệu {ticker_input} từ {df_ticker_gold['năm'].min()} đến {df_ticker_gold['năm'].max()}")


# ======================================================================
# TRANG 4: CHATBOT
# ======================================================================

elif page == "🤖 Chatbot":
    st.markdown("""
    <div class="page-header">
        <div class="badge">AI · Llama 3.3 70B · Groq</div>
        <h1>Chatbot phân tích tài chính</h1>
        <p>Hỏi bất kỳ câu hỏi nào về factors, chỉ số tài chính, so sánh công ty, hoặc giá cổ phiếu realtime.</p>
    </div>
    """, unsafe_allow_html=True)

    # ---- Kiểm tra API key ----
    GROQ_KEY = os.environ.get("GROQ_API_KEY")

    if not GROQ_KEY:
        st.error(
            "Chưa tìm thấy biến môi trường `GROQ_API_KEY`.\n\n"
            "Set trước khi chạy Streamlit:\n"
            "```\nset GROQ_API_KEY=gsk_...\nstreamlit run ui/app.py\n```"
        )
        st.stop()

    # ---- Import luôn ở module-level của trang để không bị mất khi rerun ----
    from agents.financial_agent import FinancialAgent, RateLimitError

    # ---- Khởi tạo agent 1 lần, lưu trong session_state ----
    if "agent" not in st.session_state:
        st.session_state.agent = FinancialAgent(
            provider    = "groq",
            model       = "qwen/qwen3.6-27b",
            data_root   = "data",
            output_root = "outputs",
            verbose     = True,
        )

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # ---- Sidebar nhỏ: reset hội thoại ----
    col_title, col_reset, col_cache = st.columns([4, 1, 1])
    with col_reset:
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.agent.reset()
            st.session_state.chat_messages = []
            st.rerun()
    with col_cache:
        if st.button("🗑️ Cache", use_container_width=True, help="Xóa cache câu trả lời cũ"):
            st.session_state.agent._cache.clear()
            st.toast("✔ Đã xóa cache", icon="✅")

    st.divider()

    # ---- Hiển thị lịch sử chat ----
    for msg in st.session_state.chat_messages:
        avatar = "🧑" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # ---- Gợi ý câu hỏi (chỉ hiện khi chưa chat) ----
    if not st.session_state.chat_messages:
        st.markdown("**Câu hỏi gợi ý:**")
        suggestions = [
            "Ngành nào có factor mạnh nhất sau Bonferroni?",
            "VCB có ROA bao nhiêu năm 2023?",
            "So sánh ROE của VCB và TCB năm 2023",
            "Giá FPT hiện tại là bao nhiêu?",
        ]
        cols = st.columns(2)
        for i, sug in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(sug, key=f"sug_{i}", use_container_width=True):
                    st.session_state.pending_question = sug
                    st.rerun()

    # ---- Input chat ----
    user_input = st.chat_input("Hỏi về factors, chỉ số tài chính, giá cổ phiếu...")

    # Câu hỏi từ nút gợi ý (nếu có)
    question = None
    if "pending_question" in st.session_state:
        question = st.session_state.pending_question
        del st.session_state.pending_question
    elif user_input:
        question = user_input

    if question:
        # Hiển thị câu hỏi user
        st.session_state.chat_messages.append({"role": "user", "content": question})
        with st.chat_message("user", avatar="🧑"):
            st.markdown(question)

        # Gọi agent
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("🤖 Đang phân tích dữ liệu..."):
                try:
                    answer = st.session_state.agent.ask(question)
                except RateLimitError:
                    answer = (
                        "⏳ **Groq API đang bận (rate limit).** "
                        "Mô hình Llama 70B miễn phí có giới hạn ~30 requests/phút.\n\n"
                        "Vui lòng **đợi 30-60 giây** rồi hỏi lại. "
                        "Trong lúc chờ, bạn có thể xem dữ liệu tại trang **Tổng quan** hoặc **Chi tiết ngành**."
                    )
                except Exception as e:
                    err = str(e)
                    if "rate" in err.lower() or "429" in err:
                        answer = "⏳ **Rate limit.** Đợi 30-60 giây rồi thử lại nhé."
                    elif "api key" in err.lower() or "auth" in err.lower():
                        answer = "🔑 **Lỗi API key.** Kiểm tra lại `GROQ_API_KEY` trong terminal."
                    else:
                        answer = f"⚠️ Lỗi: {err}"
            st.markdown(answer)

        st.session_state.chat_messages.append({"role": "assistant", "content": answer})
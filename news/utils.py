"""
news/utils.py
===================
"""
import os
import threading
import json
import hashlib
import re
from datetime import datetime

# 1. QUẢN LÝ ĐƯỜNG DẪN 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DATA_DIR = os.path.join(BASE_DIR, "runtime_data")
os.makedirs(APP_DATA_DIR, exist_ok=True)

DATA_FILE = os.path.join(APP_DATA_DIR, "data_warehouse.json")
WATCHLIST_FILE = os.path.join(APP_DATA_DIR, "smart_watchlist.json")
SUPPLY_CHAIN_FILE = os.path.join(APP_DATA_DIR, "supply_chain.json")
RESPONSE_CACHE_FILE = os.path.join(APP_DATA_DIR, "response_cache.json")

# 2. HỆ THỐNG Ổ KHÓA ĐỘC LẬP (MUTEX)
data_lock = threading.Lock()
watchlist_lock = threading.Lock()
cache_lock = threading.Lock()
sc_lock = threading.Lock()

# 3. BẢN ĐỒ NGÀNH NGHỀ (Từ danh mục 10 ngành kinh tế - Tính năng Top-Down)
AVAILABLE_SECTORS = {
    "Ngân hàng": ["VCB", "BID", "CTG", "TCB", "VPB"],
    "Bất động sản": ["VIC", "VHM", "KSF", "VRE", "BCM"],
    "Công nghệ": ["FPT", "CTR", "CMG", "SGT", "ELC"],
    "Thực phẩm & Đồ uống": ["MCH", "VNM", "MSN", "SAB", "SBT"],
    "Xây dựng": ["THD", "REE", "HUT", "LGC", "VCG"],
    "Vận tải": ["VJC", "HVN", "GMD", "VTP", "PVT"],
    "Hóa chất": ["GVR", "DCM", "DGC", "DPM", "BMP"],
    "Tiện ích": ["GAS", "POW", "PGV", "IDC", "SIP"],
    "Chứng khoán": ["SSI", "VND", "HCM", "MBS", "VCI"],
    "Chăm sóc Sức khỏe": ["DHG", "IMP", "DHT", "DBD", "TRA"]
}

def get_all_supported_tickers():
    tickers = []
    for sector_tickers in AVAILABLE_SECTORS.values():
        tickers.extend(sector_tickers)
    return tickers

def extract_tickers_from_query(query: str) -> list:
    """Tự động trích xuất các mã cổ phiếu xuất hiện trong câu hỏi của người dùng"""
    query_upper = query.upper()
    found_tickers = []
    # Dùng regex để tìm các từ có đúng 3 ký tự viết hoa hoặc số
    words = re.findall(r'\b[A-Z0-9]{3}\b', query_upper)
    supported = get_all_supported_tickers()
    for w in words:
        if w in supported and w not in found_tickers:
            found_tickers.append(w)
    return found_tickers

# 4. NHẬN DIỆN MÃ CỔ PHIẾU TỰ ĐỘNG (REGEX)
def is_valid_ticker(symbol: str) -> bool:
    """
    Không cần nhập tay danh sách! 
    Tự động kiểm tra: Nếu chuỗi nhập vào có đúng 3 ký tự (Chữ cái hoặc Số) 
    thì hợp lệ. Hỗ trợ toàn bộ mã trên HOSE, HNX, UPCOM.
    """
    if not symbol: 
        return False
    # Regex: ^ bắt đầu, [A-Z0-9] là chữ viết hoa hoặc số, {3} là có đúng 3 ký tự, $ là kết thúc
    return bool(re.match(r'^[A-Z0-9]{3}$', symbol.upper().strip()))

# 5. HỆ THỐNG CACHE THÔNG MINH (TTL ~ 1 Ngày)
def _generate_cache_key(prompt: str) -> str:
    date_str = datetime.now().strftime("%Y-%m-%d")
    hash_str = hashlib.md5(prompt.strip().lower().encode('utf-8')).hexdigest()
    return f"{date_str}_{hash_str}"

def get_from_cache(prompt: str):
    with cache_lock:
        if not os.path.exists(RESPONSE_CACHE_FILE): return None
        try:
            with open(RESPONSE_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            return cache.get(_generate_cache_key(prompt))
        except Exception: 
            return None

def save_to_cache(prompt: str, response: dict):
    with cache_lock:
        cache = {}
        if os.path.exists(RESPONSE_CACHE_FILE):
            try:
                with open(RESPONSE_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            except: pass
            
        # Dọn rác: Chỉ giữ lại cache của ngày hôm nay
        today = datetime.now().strftime("%Y-%m-%d")
        cache = {k: v for k, v in cache.items() if k.startswith(today)}
        
        cache[_generate_cache_key(prompt)] = response
        with open(RESPONSE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
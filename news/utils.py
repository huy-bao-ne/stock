"""
utils.py
===================
CẢI TIẾN: Thay vì dùng 1 ổ khóa chung, đã chia nhỏ thành 4 ổ khóa độc lập (Granular Locks)
giúp FastAPI và Agent1 không bị chặn lẫn nhau.
"""
import os
import threading
import json
import hashlib
from datetime import datetime

# ==========================================
# 1. QUẢN LÝ ĐƯỜNG DẪN 
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DATA_DIR = os.path.join(BASE_DIR, "runtime_data")
os.makedirs(APP_DATA_DIR, exist_ok=True)

DATA_FILE = os.path.join(APP_DATA_DIR, "data_warehouse.json")
WATCHLIST_FILE = os.path.join(APP_DATA_DIR, "smart_watchlist.json")
SUPPLY_CHAIN_FILE = os.path.join(APP_DATA_DIR, "supply_chain.json")
RESPONSE_CACHE_FILE = os.path.join(APP_DATA_DIR, "response_cache.json")

# ==========================================
# 2. HỆ THỐNG Ổ KHÓA ĐỘC LẬP (MUTEX)
# ==========================================
data_lock = threading.Lock()
watchlist_lock = threading.Lock()
cache_lock = threading.Lock()
sc_lock = threading.Lock()

# ==========================================
# 3. VALIDATE TICKER (O(1) Lookup)
# ==========================================
VALID_TICKERS = {
    'FPT', 'CMG', 'ELC', 'CTR', 'SGT', 'VCB', 'TCB', 'VPB', 'CTG', 'BID',
    'VNM', 'SAB', 'MSN', 'MCH', 'SBT', 'VRE', 'VIC', 'VHM', 'KSF', 'BCM',
    'DGC', 'DPM', 'DCM', 'GVR', 'BMP', 'VTP', 'HVN', 'VJC', 'PVT', 'GMD',
    'TRA', 'IMP', 'DHT', 'DHG', 'DBD', 'POW', 'PGV', 'IDC', 'GAS', 'SIP'
}

def is_valid_ticker(symbol: str) -> bool:
    return symbol.upper() in VALID_TICKERS

# ==========================================
# 4. HỆ THỐNG CACHE THÔNG MINH (TTL ~ 1 Ngày)
# ==========================================
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
            
        today = datetime.now().strftime("%Y-%m-%d")
        cache = {k: v for k, v in cache.items() if k.startswith(today)}
        
        cache[_generate_cache_key(prompt)] = response
        with open(RESPONSE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
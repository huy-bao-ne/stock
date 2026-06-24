import requests
import json
import time
import schedule
import os
import logging
from datetime import datetime

# IMPORT TỪ UTILS (Dùng chung bộ nhớ và file_lock với api.py)
from utils import file_lock, BASE_DIR, DATA_FILE, WATCHLIST_FILE

MAX_IDLE_DAYS  = 7
REQUEST_DELAY  = 1.5
MAX_RETRIES    = 3

logging.basicConfig(
    filename=os.path.join(BASE_DIR, "server.log"),
    level=logging.INFO,
    format="%(asctime)s [Agent1] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def _log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
    logging.info(msg)

def fetch_financial_data(symbol: str, retries: int = MAX_RETRIES) -> dict | None:
    _log(f"⚙️  Đang cào dữ liệu mã {symbol}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://finfo-api.vndirect.com.vn/v4/financial_indicators?q=ticker:{symbol}~reportType:QUARTER&sort=-reportDate&size=1"

    for attempt in range(1, retries + 1):
        try:
            res = requests.get(url, headers=headers, timeout=10, verify=False)
            if res.status_code == 200 and res.json().get("data"):
                item = res.json()["data"][0]
                doanh_thu = item.get("netRevenue", 0) or 0
                lnst      = item.get("netIncome",  0) or 0

                if doanh_thu == 0 and lnst == 0:
                    return None

                return {
                    "quy":          f"Quý {item.get('quarter')}/{item.get('year')}",
                    "doanh_thu":    doanh_thu,
                    "lnst":         lnst,
                    "no_phai_tra":  item.get("totalLiabilities", 0) or 0,
                    "eps":          item.get("eps", 0) or 0,
                    "bien_ln_gop":  item.get("grossProfitMargin", 0) or 0,
                    "roe":          item.get("roe", 0) or 0,
                    "pe":           item.get("pe", 0) or 0,
                    "source":       "vndirect",
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
        except Exception as e:
            wait = 2 ** attempt
            _log(f"  ⚠ {symbol} lần {attempt}/{retries}: Thử lại sau {wait}s...")
            time.sleep(wait)

    _log(f"  ✗ {symbol}: thất bại sau {retries} lần")
    return None

def _read_json(path: str, default) -> dict | list:
    """Sử dụng file_lock được import từ utils.py"""
    with file_lock:
        if not os.path.exists(path): return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return default

def _write_json(path: str, data):
    """Sử dụng file_lock được import từ utils.py"""
    with file_lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

def daily_job():
    _log("=" * 50); _log("BẮT ĐẦU CHU KỲ THU THẬP DỮ LIỆU"); _log("=" * 50)
    watchlist = _read_json(WATCHLIST_FILE, {})
    warehouse = _read_json(DATA_FILE, {})

    if not watchlist: return

    today = datetime.now()
    expired = []
    for symbol, last_accessed in watchlist.items():
        try:
            if (today - datetime.strptime(last_accessed, "%Y-%m-%d")).days > MAX_IDLE_DAYS:
                expired.append(symbol)
        except: expired.append(symbol)

    for symbol in expired:
        watchlist.pop(symbol, None)
        warehouse.pop(symbol, None)

    success_count = 0
    for symbol in list(watchlist.keys()):
        data = fetch_financial_data(symbol)
        if data:
            warehouse[symbol] = data
            success_count += 1
        time.sleep(REQUEST_DELAY)

    _write_json(WATCHLIST_FILE, watchlist)
    _write_json(DATA_FILE, warehouse)
    _log(f"HOÀN TẤT: {success_count}/{len(watchlist)} tickers cập nhật thành công")

if __name__ == "__main__":
    _log("Agent 1 khởi động...")
    daily_job()
    schedule.every().day.at("06:00").do(daily_job)
    while True:
        schedule.run_pending()
        time.sleep(60)
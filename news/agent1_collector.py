"""
news/agent1_collector.py
=========================
Agent 1 — Smart Data Collector

Nhiệm vụ:
  - Chạy nền theo lịch (6:00 sáng hàng ngày)
  - Tự động làm mới dữ liệu tài chính cho mọi ticker đang được theo dõi
  - Dọn dẹp tickers không được hỏi đến trong MAX_IDLE_DAYS ngày

Cải tiến so với bản gốc:
  - Thêm retry với exponential backoff (tránh bị block khi network lỗi)
  - Chuẩn hoá & validate dữ liệu trước khi lưu (loại bỏ giá trị 0/None vô nghĩa)
  - Thêm trường `source` để API biết dữ liệu đến từ đâu
  - Thread-safe file I/O (lock khi đọc/ghi tránh conflict với api.py)
  - Ghi log có timestamp ra server.log
"""

import requests
import json
import time
import schedule
import os
import logging
import threading
from datetime import datetime

# ======================================================================
# CẤU HÌNH
# ======================================================================

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
APP_DATA_DIR  = os.path.join(BASE_DIR, "runtime_data")
os.makedirs(APP_DATA_DIR, exist_ok=True)

WATCHLIST_FILE = os.path.join(APP_DATA_DIR, "smart_watchlist.json")
DATA_FILE      = os.path.join(APP_DATA_DIR, "data_warehouse.json")

MAX_IDLE_DAYS  = 7    # Số ngày tối đa giữ lại ticker nếu không ai hỏi
REQUEST_DELAY  = 1.5  # Giây chờ giữa các ticker để tránh rate limit
MAX_RETRIES    = 3    # Số lần retry tối đa mỗi ticker

# Lock dùng chung với api.py để tránh ghi đè file đồng thời
_file_lock = threading.Lock()

# ======================================================================
# LOGGING
# ======================================================================

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


# ======================================================================
# THU THẬP DỮ LIỆU TỪ VNDIRECT
# ======================================================================

def fetch_financial_data(symbol: str, retries: int = MAX_RETRIES) -> dict | None:
    """
    Cào dữ liệu tài chính quý gần nhất từ VNDirect API.
    Trả về dict chuẩn hoá, hoặc None nếu thất bại sau tất cả retries.

    Cải tiến:
      - Exponential backoff (2^attempt giây) khi retry
      - Validate: bỏ qua dữ liệu nếu doanh thu và lnst đều bằng 0
      - Thêm field `source` và `last_updated`
    """
    _log(f"⚙️  Đang cào dữ liệu mã {symbol}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    url = (
        f"https://finfo-api.vndirect.com.vn/v4/financial_indicators"
        f"?q=ticker:{symbol}~reportType:QUARTER&sort=-reportDate&size=1"
    )

    for attempt in range(1, retries + 1):
        try:
            res = requests.get(url, headers=headers, timeout=10, verify=False)
            if res.status_code == 200 and res.json().get("data"):
                item = res.json()["data"][0]
                doanh_thu = item.get("netRevenue", 0) or 0
                lnst      = item.get("netIncome",  0) or 0

                # Bỏ qua nếu cả 2 chỉ số chính đều bằng 0 (dữ liệu rỗng)
                if doanh_thu == 0 and lnst == 0:
                    _log(f"  ⚠ {symbol}: dữ liệu rỗng từ VNDirect")
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
            wait = 2 ** attempt  # exponential backoff: 2, 4, 8 giây
            _log(f"  ⚠ {symbol} lần {attempt}/{retries}: {e}. Thử lại sau {wait}s...")
            time.sleep(wait)

    _log(f"  ✗ {symbol}: thất bại sau {retries} lần")
    return None


# ======================================================================
# ĐỌC / GHI FILE THREAD-SAFE
# ======================================================================

def _read_json(path: str, default) -> dict | list:
    """Đọc JSON với lock, trả về default nếu file không tồn tại."""
    with _file_lock:
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            _log(f"  ⚠ Lỗi đọc {path}, dùng giá trị mặc định")
            return default


def _write_json(path: str, data):
    """Ghi JSON với lock."""
    with _file_lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)


# ======================================================================
# CÔNG VIỆC HÀNG NGÀY
# ======================================================================

def daily_job():
    """
    Chu kỳ bảo trì hàng ngày:
      1. Đọc watchlist
      2. Xóa tickers hết hạn (> MAX_IDLE_DAYS ngày không ai hỏi)
      3. Cập nhật dữ liệu tài chính cho tickers còn lại
      4. Lưu lại
    """
    _log("=" * 50)
    _log("BẮT ĐẦU CHU KỲ THU THẬP VÀ DỌN DẸP DỮ LIỆU")
    _log("=" * 50)

    watchlist = _read_json(WATCHLIST_FILE, default={})
    warehouse = _read_json(DATA_FILE,      default={})

    if not watchlist:
        _log("Sổ tay trống. Không có gì để cập nhật.")
        return

    today = datetime.now()

    # ------- BƯỚC 1: DỌN TICKER HẾT HẠN -------
    expired = []
    for symbol, last_accessed in watchlist.items():
        try:
            accessed_date = datetime.strptime(last_accessed, "%Y-%m-%d")
            if (today - accessed_date).days > MAX_IDLE_DAYS:
                expired.append(symbol)
        except ValueError:
            expired.append(symbol)  # ngày sai format → cũng xóa luôn

    for symbol in expired:
        _log(f"🗑  {symbol} đã {MAX_IDLE_DAYS}+ ngày không được hỏi → xóa khỏi hệ thống")
        watchlist.pop(symbol, None)
        warehouse.pop(symbol, None)

    if expired:
        _log(f"Đã xóa {len(expired)} tickers: {expired}")

    # ------- BƯỚC 2: CẬP NHẬT TICKER CÒN LẠI -------
    success_count = 0
    for symbol in list(watchlist.keys()):
        data = fetch_financial_data(symbol)
        if data:
            warehouse[symbol] = data
            _log(f"  ✔ Cập nhật thành công {symbol} ({data['quy']})")
            success_count += 1
        time.sleep(REQUEST_DELAY)

    # ------- LƯU -------
    _write_json(WATCHLIST_FILE, watchlist)
    _write_json(DATA_FILE,      warehouse)

    _log(f"HOÀN TẤT: {success_count}/{len(watchlist)} tickers cập nhật thành công")
    _log("=" * 50)


# ======================================================================
# KHỞI CHẠY
# ======================================================================

if __name__ == "__main__":
    # Chạy ngay 1 lần khi khởi động để có dữ liệu mới nhất
    _log("Agent 1 khởi động. Chạy chu kỳ đầu tiên ngay...")
    daily_job()

    # Lập lịch chạy 6:00 sáng hàng ngày
    schedule.every().day.at("06:00").do(daily_job)
    _log("Đã lên lịch: chạy lại lúc 06:00 hàng ngày")
    _log("Agent 1 đang chờ...")

    while True:
        schedule.run_pending()
        time.sleep(60)  # kiểm tra lịch mỗi 60 giây (đủ, không cần check từng giây)
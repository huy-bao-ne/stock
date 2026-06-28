"""
agent1_collector.py
===================
BẢN NÂNG CẤP: KÉO TOÀN BỘ LỊCH SỬ BCTC (NHƯ VIETSTOCK)
Cào 6-8 quý, tích hợp cả KQKD, Cân đối kế toán và Chỉ số tài chính.
"""
import json
import time
import os
import logging
from datetime import datetime
import pandas as pd
import re

pd.set_option('future.no_silent_downcasting', True)

try:
    from vnstock import Finance
except ImportError:
    raise ImportError("Vui lòng cài đặt vnstock: pip install vnstock")

from utils import data_lock, watchlist_lock, BASE_DIR, DATA_FILE, WATCHLIST_FILE

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

def parse_numeric(x):
    if x is None or (isinstance(x, float) and pd.isna(x)): return 0
    try:
        if isinstance(x, str):
            s = x.strip().replace('(', '-').replace(')', '')
            if s.endswith('%'): return float(re.sub(r"[^0-9\.-]", "", s.rstrip('%'))) / 100.0
            s = re.sub(r'[^0-9\.-]', '', s)
            return float(s) if s not in ['', '-', '.'] else 0
        return float(x)
    except: return 0

def fetch_financial_data(symbol: str) -> list | None:
    _log(f"⚙️ Đang kết nối Vnstock kéo Toàn bộ BCTC mã {symbol}...")
    
    try:
        finance = Finance(source='vci', symbol=symbol, period='quarter')
        try:
            df_is = finance.income_statement(lang='vi', dropna=True)
            if df_is is None or df_is.empty: raise ValueError("VCI IS Empty")
        except:
            finance = Finance(source='tcbs', symbol=symbol, period='quarter')
            df_is = finance.income_statement(lang='vi', dropna=True)

        if df_is is None or df_is.empty: return None

        try: df_bs = finance.balance_sheet(lang='vi', dropna=True)
        except: df_bs = None
        
        try: df_ratio = finance.ratio(lang='vi', dropna=True)
        except: df_ratio = None

        # Tiền xử lý DataFrames
        for df in [df_is, df_bs]:
            if df is not None and not df.empty:
                df.drop(columns=[c for c in ['item_en', 'item_id', 'Mã TTM'] if c in df.columns], inplace=True, errors='ignore')
                df.set_index(df.columns[0], inplace=True)

        if df_is is not None: df_is = df_is.T.sort_index().tail(6) # Lấy 6 quý gần nhất cho đẹp bảng
        if df_bs is not None: df_bs = df_bs.T

        if df_ratio is not None and not df_ratio.empty:
            df_ratio.drop(columns=[c for c in ['item_en', 'item_id', 'Mã TTM'] if c in df_ratio.columns], inplace=True, errors='ignore')

        real_data_list = []
        
        def get_val_transposed(df_source, row_idx, keywords):
            if df_source is None or df_source.empty: return 0
            for r_idx in df_source.index:
                if str(row_idx) in str(r_idx):
                    for col in df_source.columns:
                        if any(k.lower() in str(col).lower() for k in keywords):
                            val = parse_numeric(df_source.loc[r_idx, col])
                            if val != 0: return val
            return 0

        def get_val_ratio(df_r, y, q, keywords):
            if df_r is None or df_r.empty: return 0
            try:
                for col in [c for c in df_r.columns if re.search(r"20\d{2}", str(c))]:
                    if str(y) in str(col) and (f"q{q}" in str(col).lower() or f"quý {q}" in str(col).lower()):
                        for idx in range(len(df_r)):
                            row_text = ' '.join([str(df_r.iloc[idx].get(c, '')) for c in df_r.columns[:3]]).lower()
                            if any(k.lower() in row_text for k in keywords):
                                return parse_numeric(df_r.iloc[idx].get(col, 0))
            except: pass
            return 0

        for index_val, row in df_is.iterrows():
            quy_str = str(index_val).strip()
            if 'Q' not in quy_str and '20' not in quy_str: continue
                
            y_match = re.search(r'(20\d{2})', quy_str)
            q_match = re.search(r'Q([1-4])', quy_str.upper())
            year = y_match.group(1) if y_match else ''
            quarter = q_match.group(1) if q_match else ''

            doanh_thu = get_val_transposed(df_is, quy_str, ['doanh thu thuần', 'net sales'])
            ln_gop = get_val_transposed(df_is, quy_str, ['lợi nhuận gộp', 'gross profit'])
            lnst = get_val_transposed(df_is, quy_str, ['lợi nhuận của cổ đông', 'lợi nhuận sau thuế', 'net income'])
            
            tong_tai_san = get_val_transposed(df_bs, quy_str, ['tổng cộng tài sản', 'tổng tài sản'])
            no_phai_tra = get_val_transposed(df_bs, quy_str, ['nợ phải trả', 'tổng nợ'])
            von_csh = get_val_transposed(df_bs, quy_str, ['vốn chủ sở hữu', 'tổng vốn'])
            
            eps = get_val_transposed(df_is, quy_str, ['lãi cơ bản trên cổ phiếu', 'eps'])

            bien_ln_gop = get_val_ratio(df_ratio, year, quarter, ['biên ln gộp', 'biên lợi nhuận gộp'])
            if not bien_ln_gop and doanh_thu != 0: bien_ln_gop = ln_gop / doanh_thu

            roe = get_val_ratio(df_ratio, year, quarter, ['roe', 'tỷ suất lnst trên vốn'])
            pe = get_val_ratio(df_ratio, year, quarter, ['p/e', 'hệ số p/e'])

            if 0 < roe < 1: roe *= 100
            # Đồng bộ sang tỷ VNĐ cho gọn
            if 0 < doanh_thu < 10000000:
                doanh_thu *= 1000000000
                lnst *= 1000000000
                tong_tai_san *= 1000000000
                no_phai_tra *= 1000000000
                von_csh *= 1000000000

            real_data_list.append({
                'quy': quy_str.replace(' ', '/'),
                'doanh_thu': doanh_thu, 'ln_gop': ln_gop, 'lnst': lnst,
                'tong_tai_san': tong_tai_san, 'no_phai_tra': no_phai_tra, 'von_csh': von_csh,
                'eps': eps, 'bien_ln_gop': bien_ln_gop, 'roe': roe, 'pe': pe
            })
            
        return real_data_list

    except Exception as e:
        _log(f"  ✗ Lỗi trích xuất Vnstock mã {symbol}: {e}")
        return None

def _read_json(path: str, lock):
    with lock:
        if not os.path.exists(path): return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}

def _write_json(path: str, data, lock):
    with lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

def active_scanner():
    _log("🤖 Agent 1 đang thức và giám sát Watchlist liên tục mỗi 5 giây...")
    while True:
        watchlist = _read_json(WATCHLIST_FILE, watchlist_lock)
        warehouse = _read_json(DATA_FILE, data_lock)
        
        new_symbols = [sym for sym in watchlist.keys() if sym not in warehouse]
        
        if new_symbols:
            _log(f"🚨 PHÁT HIỆN LỆNH MỚI TỪ LỄ TÂN: Cần cào mã {new_symbols}")
            for sym in new_symbols:
                data_list = fetch_financial_data(sym)
                
                if data_list and len(data_list) > 0:
                    warehouse[sym] = data_list
                    _log(f"✅ Đã lưu Toàn bộ BCTC {sym} ({len(data_list)} quý) vào kho thành công!")
                else:
                    warehouse[sym] = [{"status": "error"}]
                    _log(f"⚠️ Cào {sym} thất bại. Đã ghi nhận lỗi!")
            
            _write_json(DATA_FILE, warehouse, data_lock)
            _log("Sẵn sàng cho AI phân tích!")
        
        time.sleep(5)

if __name__ == "__main__":
    active_scanner()
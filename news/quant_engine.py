import os
import pandas as pd
import json
import re

# Tắt cảnh báo Downcasting
pd.set_option('future.no_silent_downcasting', True)

def get_sector_of_ticker(ticker):
    ticker = ticker.upper()
    sector_map = {
        'FPT': 'technology', 'CMG': 'technology', 'ELC': 'technology', 'CTR': 'technology', 'SGT': 'technology',
        'VCB': 'banking', 'TCB': 'banking', 'VPB': 'banking', 'CTG': 'banking', 'BID': 'banking',
        'VNM': 'food', 'SAB': 'food', 'MSN': 'food', 'MCH': 'food', 'SBT': 'food',
        'VRE': 'realestate', 'VIC': 'realestate', 'VHM': 'realestate', 'KSF': 'realestate', 'BCM': 'realestate',
        'DGC': 'chemicals', 'DPM': 'chemicals', 'DCM': 'chemicals', 'GVR': 'chemicals', 'BMP': 'chemicals',
        'VTP': 'transport', 'HVN': 'transport', 'VJC': 'transport', 'PVT': 'transport', 'GMD': 'transport',
        'TRA': 'healthcare', 'IMP': 'healthcare', 'DHT': 'healthcare', 'DHG': 'healthcare', 'DBD': 'healthcare',
        'POW': 'utilities', 'PGV': 'utilities', 'IDC': 'utilities', 'GAS': 'utilities', 'SIP': 'utilities'
    }
    return sector_map.get(ticker, 'unknown')

def load_gold_factors(ticker, base_dir):
    """
    Lấy top 3 factors có độ tương quan mạnh nhất với giá cổ phiếu.

    Đọc từ: factor/outputs/{sector}/{sector}_factor_results.csv
    (KHÔNG phải gold_factors.csv — file đó là data tài chính, không có cột tương quan)

    Tên cột trong factor_results.csv:
      - "chỉ_báo"         : tên factor
      - "độ_tương_quan_%" : dạng "+57.5%" hoặc "-60.2%"
    """
    sector = get_sector_of_ticker(ticker)
    if sector == 'unknown':
        print(f"[quant_engine] {ticker} không có trong sector_map")
        return []

    # base_dir = .../news/ → root = .../Stock/ → factor/outputs/
    root_dir = os.path.dirname(base_dir)
    factor_results_path = os.path.join(
        root_dir, 'factor', 'outputs', sector,
        f'{sector}_factor_results.csv'
    )

    if not os.path.exists(factor_results_path):
        print(f"[quant_engine] Không tìm thấy: {factor_results_path}")
        return []

    try:
        df = pd.read_csv(factor_results_path, encoding='utf-8-sig')

        # Parse cột tương quan: "+57.5%" → float
        df['_corr_float'] = (
            df['độ_tương_quan_%']
            .astype(str)
            .str.replace('%', '', regex=False)
            .str.strip()
            .astype(float)
        )
        df['_abs_corr'] = df['_corr_float'].abs()

        # Lấy top 3 factor mạnh nhất
        top3 = df.nlargest(3, '_abs_corr')

        factors = []
        for _, row in top3.iterrows():
            factors.append({
                "name":        str(row['chỉ_báo']),
                "correlation": round(row['_corr_float'] / 100, 4),
            })
        return factors

    except Exception as e:
        print(f"[quant_engine] Lỗi đọc factor results: {e}")
        return []


def get_factor_trend_data(ticker: str, factor_name: str, base_dir: str) -> list:
    """
    Lấy chuỗi giá trị lịch sử của 1 factor cho 1 ticker từ gold_factors.csv.
    Dùng để tính trend thật thay vì hardcode.
    """
    sector = get_sector_of_ticker(ticker)
    if sector == 'unknown':
        return []

    root_dir  = os.path.dirname(base_dir)
    gold_path = os.path.join(root_dir, 'factor', 'data', sector, 'gold_factors.csv')

    if not os.path.exists(gold_path):
        return []

    try:
        df        = pd.read_csv(gold_path, encoding='utf-8-sig')
        df_ticker = df[df['mã_chứng_khoán'] == ticker.upper()].sort_values('năm')

        if factor_name not in df_ticker.columns:
            return []

        values = df_ticker[factor_name].dropna().tolist()
        return [float(v) for v in values if v != 0]

    except Exception as e:
        print(f"[quant_engine] Lỗi lấy trend data: {e}")
        return []
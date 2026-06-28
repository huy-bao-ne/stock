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
    sector = get_sector_of_ticker(ticker)
    if sector == 'unknown': return []
    csv_path = os.path.join(base_dir, '..', 'factor', 'data', sector, 'gold_factors.csv')
    
    if not os.path.exists(csv_path): return []
    try:
        df = pd.read_csv(csv_path, nrows=0) 
        ignore_cols = ['mã_chứng_khoán', 'năm', 'năm_chưa_kết_thúc', 'thiếu_dữ_liệu']
        factors = [col for col in df.columns if col.lower() not in ignore_cols]
        
        key_factors = []
        for f in factors:
            if 'doanh_thu' in f or 'lợi_nhuận' in f or 'roa' in f or 'roe' in f or 'margin' in f:
                key_factors.append(f)
                
        return key_factors[:4] if key_factors else factors[:4]
    except Exception as e:
        print(f"Lỗi đọc file factor: {e}")
        return []
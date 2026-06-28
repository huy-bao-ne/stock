import numpy as np
from scipy.stats import linregress
import pandas as pd

pd.set_option('future.no_silent_downcasting', True)

def calculate_historical_trend(data_series: list):
    valid_data = [float(x) for x in data_series if x is not None and str(x).strip() != '']
    
    if len(valid_data) < 3:
        return "→ CHƯA RÕ" 
        
    y = np.array(valid_data)
    x = np.arange(len(y))
    
    slope, intercept, r_value, p_value, std_err = linregress(x, y)
    
    mean_val = np.mean(y)
    if mean_val == 0:
        mean_val = 1e-9 
        
    growth_rate = (slope / abs(mean_val)) * 100
    
    if growth_rate > 3.0: return "↑ TĂNG"
    elif growth_rate < -3.0: return "↓ GIẢM"
    else: return "→ ĐI NGANG"
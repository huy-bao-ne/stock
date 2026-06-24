import numpy as np
from scipy.stats import linregress

def calculate_historical_trend(data_series: list):
    """
    Sử dụng Hồi quy tuyến tính (Simple Linear Regression) 
    để xác định xu hướng của một chuỗi dữ liệu tài chính (VD: EPS 5 năm qua).
    """
    # Lọc bỏ các giá trị None/Null
    valid_data = [float(x) for x in data_series if x is not None and str(x).strip() != '']
    
    if len(valid_data) < 3:
        return "→ CHƯA RÕ" # Không đủ data để chạy hồi quy
        
    y = np.array(valid_data)
    x = np.arange(len(y))
    
    # Tính hệ số góc (slope)
    slope, intercept, r_value, p_value, std_err = linregress(x, y)
    
    # Chuẩn hóa hệ số góc so với giá trị trung bình để tính % tăng trưởng
    mean_val = np.mean(y)
    if mean_val == 0:
        mean_val = 1e-9 # Tránh chia cho 0
        
    growth_rate = (slope / abs(mean_val)) * 100
    
    if growth_rate > 3.0:
        return "↑ TĂNG"
    elif growth_rate < -3.0:
        return "↓ GIẢM"
    else:
        return "→ ĐI NGANG"
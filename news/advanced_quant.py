import numpy as np
import pandas as pd

pd.set_option('future.no_silent_downcasting', True)

def calculate_valuation_zscore(current_pe: float, historical_pe_list: list):
    valid_pe = [pe for pe in historical_pe_list if pe is not None and pe > 0]
    if len(valid_pe) < 4:
        return {"z_score": 0, "status": "Không đủ dữ liệu định giá"}
        
    mean_pe = np.mean(valid_pe)
    std_pe = np.std(valid_pe)
    if std_pe == 0: std_pe = 0.01 
        
    z_score = (current_pe - mean_pe) / std_pe
    
    if z_score <= -1.5: status = "CỰC KỲ RẺ (Đáy định giá)"
    elif -1.5 < z_score <= -0.5: status = "RẺ (Dưới giá trị thực)"
    elif -0.5 < z_score <= 0.5: status = "ĐỊNH GIÁ HỢP LÝ (Fair Value)"
    elif 0.5 < z_score <= 1.5: status = "HƠI ĐẮT"
    else: status = "BONG BÓNG (Cực kỳ đắt)"
        
    return {"z_score": round(z_score, 2), "status": status, "mean_pe": round(mean_pe, 2)}

def calculate_piotroski_f_score(financial_data: dict):
    score = 0
    details = []
    
    if financial_data.get('roa_current', 0) > 0: score += 1; details.append("ROA dương")
    if financial_data.get('cfo_current', 0) > 0: score += 1; details.append("Dòng tiền CFO dương")
    if financial_data.get('roa_current', 0) > financial_data.get('roa_past', 0): score += 1; details.append("ROA tăng trưởng")
    if financial_data.get('cfo_current', 0) > financial_data.get('net_income', 0): score += 1; details.append("Chất lượng lợi nhuận cao")
    if financial_data.get('debt_ratio_current', 1) < financial_data.get('debt_ratio_past', 1): score += 1; details.append("Đang giảm nợ vay")
    if financial_data.get('current_ratio_current', 0) > financial_data.get('current_ratio_past', 0): score += 1; details.append("Thanh khoản cải thiện")
    if financial_data.get('shares_current', 0) <= financial_data.get('shares_past', 0): score += 1; details.append("Không pha loãng cổ phiếu")
    if financial_data.get('gross_margin_current', 0) > financial_data.get('gross_margin_past', 0): score += 1; details.append("Biên LN Gộp mở rộng")
    if financial_data.get('asset_turnover_current', 0) > financial_data.get('asset_turnover_past', 0): score += 1; details.append("Vòng quay tài sản hiệu quả")

    health_status = "TỐT (Đủ điều kiện phòng thủ)" if score >= 6 else ("TRUNG BÌNH" if score >= 4 else "RỦI RO CAO (Có thể phá sản)")
    return {"score": score, "max": 9, "status": health_status, "strengths": details}

def calculate_rsi_momentum(price_list: list, period=14):
    if len(price_list) < period + 1:
        return {"rsi": 50, "status": "Không đủ dữ liệu RSI"}
        
    deltas = np.diff(price_list)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    if avg_loss == 0: return {"rsi": 100, "status": "QUÁ MUA MẠNH"}
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    if rsi <= 30: status = "QUÁ BÁN (Tín hiệu bắt đáy cực tốt)"
    elif rsi <= 45: status = "VÙNG CHIẾT KHẤU (Nên gom dần)"
    elif rsi >= 70: status = "QUÁ MUA (Rủi ro đu đỉnh, chờ chỉnh)"
    else: status = "ĐI NGANG (Chờ tín hiệu xác nhận)"
        
    return {"rsi": round(rsi, 2), "status": status}
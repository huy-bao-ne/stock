import os
import pandas as pd
import json

def get_sector_of_ticker(ticker):
    """Bản đồ cứng map mã cổ phiếu về đúng thư mục ngành (tránh AI ảo giác)"""
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
    """Thuật toán tải top 3 chỉ số có độ tương quan mạnh nhất từ file CSV"""
    sector = get_sector_of_ticker(ticker)
    if sector == 'unknown':
        return []
    
    # Trỏ đường dẫn ngược ra thư mục factor/data
    csv_path = os.path.join(base_dir, '..', 'factor', 'data', sector, 'gold_factors.csv')
    
    if not os.path.exists(csv_path):
        return []
        
    try:
        df = pd.read_csv(csv_path)
        # Tìm cột Tên Factor và Cột Tương quan một cách linh hoạt
        col_factor = df.columns[0] # Thường cột đầu là tên factor
        col_corr = [c for c in df.columns if 'corr' in c.lower() or 'tương quan' in c.lower() or 'spearman' in c.lower()]
        
        if not col_corr:
            col_corr = df.columns[1] # Dự phòng cột thứ 2
        else:
            col_corr = col_corr[0]
            
        # Lấy Top 3 factor có giá trị tuyệt đối lớn nhất
        df['abs_corr'] = df[col_corr].abs()
        top_factors = df.sort_values(by='abs_corr', ascending=False).head(3)
        
        factors = []
        for _, row in top_factors.iterrows():
            factors.append({
                "name": str(row[col_factor]),
                "correlation": float(row[col_corr])
            })
        return factors
    except Exception as e:
        print(f"Lỗi đọc factor: {e}")
        return []

def get_sentiment_from_llm(groq_client, ticker, factors, news_text):
    """Ép LLM làm công nhân chấm điểm: Chỉ được trả về 1, 0, hoặc -1"""
    if not factors or not news_text:
        return {}
        
    factor_names = [f['name'] for f in factors]
    prompt = f"""
    Bạn là hệ thống máy tính chấm điểm Sentiment Định lượng.
    Mã cổ phiếu: {ticker}
    Các chỉ báo tài chính đang theo dõi: {factor_names}
    
    TIN TỨC VĨ MÔ:
    {news_text}
    
    NHIỆM VỤ: Dựa vào tin tức, chấm điểm tác động lên từng chỉ báo của {ticker}.
    - Score = 1: Nếu tin tức làm TĂNG chỉ báo.
    - Score = -1: Nếu tin tức làm GIẢM chỉ báo.
    - Score = 0: Nếu KHÔNG ẢNH HƯỞNG.
    
    TRẢ VỀ ĐÚNG ĐỊNH DẠNG JSON SAU (KHÔNG THÊM BẤT KỲ CHỮ NÀO KHÁC):
    {{
        "Tên Chỉ Báo 1": {{"score": 1, "reason": "Lý do < 15 chữ"}},
        "Tên Chỉ Báo 2": {{"score": 0, "reason": "Lý do < 15 chữ"}}
    }}
    """
    
    try:
        res = groq_client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        return json.loads(res.choices[0].message.content)
    except Exception as e:
        print(f"Lỗi LLM Sentiment: {e}")
        return {}

def calculate_quant_score(factors, sentiment_results):
    """CÔNG THỨC TOÁN HỌC: Điểm = Độ tương quan * Sentiment Tin tức"""
    total_impact_score = 0
    detailed_analysis = []
    
    for f in factors:
        name = f['name']
        corr = f['correlation']
        
        # Lấy điểm sentiment từ LLM (mặc định 0 nếu không có)
        llm_eval = sentiment_results.get(name, {})
        sentiment_score = float(llm_eval.get('score', 0))
        reason = llm_eval.get('reason', 'Không rõ tác động')
        
        # CÔNG THỨC LÕI
        impact = corr * sentiment_score
        total_impact_score += impact
        
        detailed_analysis.append({
            "factor": name,
            "correlation_with_price": round(corr, 2),
            "news_sentiment": sentiment_score,
            "calculated_impact": round(impact, 2),
            "reason": reason
        })
        
    # Chuẩn hóa tín hiệu
    if total_impact_score > 0.3: signal = "MUA MẠNH (POSITIVE)"
    elif total_impact_score > 0: signal = "TÍCH LŨY (SLIGHTLY POSITIVE)"
    elif total_impact_score < -0.3: signal = "BÁN MẠNH (NEGATIVE)"
    elif total_impact_score < 0: signal = "HẠ TỶ TRỌNG (SLIGHTLY NEGATIVE)"
    else: signal = "QUAN SÁT (NEUTRAL)"
        
    return {
        "total_score": round(total_impact_score, 2),
        "signal": signal,
        "details": detailed_analysis
    }
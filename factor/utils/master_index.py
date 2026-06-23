"""
utils/master_index.py
======================
Tạo và cập nhật file master_index.csv — điểm entry duy nhất cho AI Agent
sau này để biết:
  - Có những ticker nào trong hệ thống
  - Ticker đó thuộc ngành nào
  - Có data từ năm nào đến năm nào
  - File gold dataset nằm ở đâu

Format:
  mã_chứng_khoán | ngành | năm_đầu | năm_cuối | có_báo_cáo_tc | có_giá_cp | đường_dẫn_gold
"""

import pandas as pd
from pathlib import Path
from datetime import date


def build_master_index(
    sectors_config: dict,
    data_root: str = "data",
    output_path: str = "data/master/master_index.csv",
) -> pd.DataFrame:
    """
    Quét tất cả các sector đã có data → tạo master_index.csv.

    Parameters
    ----------
    sectors_config : dict từ config.yaml, key = sector name
    data_root      : thư mục gốc chứa data
    output_path    : nơi lưu master_index.csv
    """
    rows = []

    for sector_name, sector_cfg in sectors_config.items():
        data_dir = Path(data_root) / sector_name.lower()

        for ticker in sector_cfg.get("tickers", []):
            # Kiểm tra files có tồn tại không
            bs_exists     = (data_dir / "bảng_cân_đối_kế_toán.csv").exists()
            price_exists  = (data_dir / "yearly_return.csv").exists()
            gold_exists   = (data_dir / "gold_factors.csv").exists()

            # Đọc năm có data nếu file tồn tại
            năm_đầu = năm_cuối = None
            if bs_exists:
                try:
                    df_bs = pd.read_csv(data_dir / "bảng_cân_đối_kế_toán.csv")
                    ticker_data = df_bs[df_bs["mã_chứng_khoán"] == ticker]
                    if not ticker_data.empty:
                        năm_đầu  = int(ticker_data["năm"].min())
                        năm_cuối = int(ticker_data["năm"].max())
                except Exception:
                    pass

            rows.append({
                "mã_chứng_khoán":       ticker,
                "ngành":                sector_name,
                "năm_đầu":              năm_đầu,
                "năm_cuối":             năm_cuối,
                "có_báo_cáo_tài_chính": bs_exists,
                "có_giá_cổ_phiếu":      price_exists,
                "có_gold_dataset":      gold_exists,
                "đường_dẫn_gold":       str(data_dir / "gold_factors.csv") if gold_exists else "",
                "cập_nhật_lần_cuối":    str(date.today()),
            })

    df = pd.DataFrame(rows)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"  ✔ Master index: {len(df)} tickers → {output_path}")
    return df
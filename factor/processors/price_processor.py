"""
processors/price_processor.py
==============================
Xử lý dữ liệu giá cổ phiếu daily → yearly_return.csv

Output CSV columns:
  mã_chứng_khoán | năm | giá_đóng_cửa_đầu_kỳ | giá_đóng_cửa_cuối_kỳ
  | lợi_nhuận_hàng_năm | lợi_nhuận_hàng_năm_% | năm_chưa_kết_thúc | thiếu_dữ_liệu
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import date


CURRENT_YEAR = date.today().year


class PriceProcessor:
    """
    Chuyển daily price CSV → yearly return CSV.

    Logic:
      Return năm T = (Giá đóng cửa cuối năm T - Giá đóng cửa cuối năm T-1)
                     / Giá đóng cửa cuối năm T-1

    Dùng giá cuối năm T-1 làm base thay vì đầu năm T vì:
    - Ổn định hơn (đã qua cả năm giao dịch)
    - Tránh gap giá sau kỳ nghỉ Tết
    """

    def process(self, raw_csv_path: str, output_path: str) -> pd.DataFrame:
        """
        Parameters
        ----------
        raw_csv_path : path đến file CSV raw từ vnstock
        output_path  : path để lưu yearly_return.csv

        Returns
        -------
        pd.DataFrame với yearly returns
        """
        df = pd.read_csv(raw_csv_path)
        df = self._normalize_columns(df)
        df["ngày"] = pd.to_datetime(df["time"])
        df["năm"]  = df["ngày"].dt.year

        # Lấy giá đóng cửa của ngày giao dịch CUỐI CÙNG mỗi năm
        year_end = (
            df.sort_values("ngày")
            .groupby(["ticker", "năm"])
            .last()
            .reset_index()[["ticker", "năm", "close", "ngày"]]
            .rename(columns={
                "ticker": "mã_chứng_khoán",
                "close":  "giá_đóng_cửa_cuối_kỳ",
                "ngày":   "ngày_cuối_kỳ",
            })
        )

        rows = []
        for ticker, grp in year_end.groupby("mã_chứng_khoán"):
            grp = grp.sort_values("năm").reset_index(drop=True)

            for _, row in grp.iterrows():
                year      = int(row["năm"])
                close_end = row["giá_đóng_cửa_cuối_kỳ"]

                # Tìm giá cuối năm trước
                prev = grp[grp["năm"] == year - 1]

                if prev.empty:
                    close_start   = None
                    return_abs    = None
                    return_pct    = None
                    missing       = True
                else:
                    close_start = prev.iloc[0]["giá_đóng_cửa_cuối_kỳ"]
                    if pd.isna(close_start) or close_start == 0:
                        return_abs = None
                        return_pct = None
                        missing    = True
                    else:
                        return_abs = round(close_end - close_start, 2)
                        return_pct = round((close_end - close_start) / close_start * 100, 2)
                        missing    = False

                rows.append({
                    "mã_chứng_khoán":          ticker,
                    "năm":                     year,
                    "giá_đóng_cửa_đầu_kỳ":    close_start,
                    "giá_đóng_cửa_cuối_kỳ":   close_end,
                    "lợi_nhuận_hàng_năm":      return_abs,
                    "lợi_nhuận_hàng_năm_%":    return_pct,
                    "năm_chưa_kết_thúc":       year >= CURRENT_YEAR,
                    "thiếu_dữ_liệu":           missing,
                })

        result = (
            pd.DataFrame(rows)
            .sort_values(["mã_chứng_khoán", "năm"])
            .reset_index(drop=True)
        )

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(output_path, index=False, encoding="utf-8-sig")

        # Summary
        valid   = result[~result["thiếu_dữ_liệu"] & ~result["năm_chưa_kết_thúc"]]
        partial = result[result["năm_chưa_kết_thúc"]]
        print(f"  ✔ Yearly returns: {len(valid)} hợp lệ | "
              f"{result['thiếu_dữ_liệu'].sum()} thiếu | "
              f"{len(partial)} năm chưa xong")
        print(f"  ✔ Đã lưu → {output_path}")

        return result

    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Chuẩn hoá tên cột: lowercase, handle vnstock version khác nhau."""
        df.columns = [c.lower().strip() for c in df.columns]

        # vnstock đôi khi dùng 'date' thay 'time'
        if "date" in df.columns and "time" not in df.columns:
            df = df.rename(columns={"date": "time"})

        required = ["time", "close", "ticker"]
        missing  = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(
                f"Raw price CSV thiếu cột: {missing}. "
                f"Cột hiện có: {list(df.columns)}"
            )
        return df
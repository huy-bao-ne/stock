"""
processors/base_processor.py
==============================
Abstract base class cho tất cả sector processors.

Nhiệm vụ chính: chuyển vnstock long format → wide format chuẩn

vnstock trả về LONG FORMAT (mỗi dòng = 1 chỉ tiêu):
    item_id | item              | item_en        | 2024  | 2023  | 2022
    bsa53   | TỔNG CỘNG TÀI SẢN | Total Assets   | 2.4e15| 2.2e15| ...
    bsb113  | Tiền gửi KH       | Deposits from..| 1.6e15| 1.5e15| ...

Sau khi xử lý trả về WIDE FORMAT (mỗi dòng = 1 ticker × 1 năm):
    mã_chứng_khoán | năm  | tổng_tài_sản | tiền_gửi_khách_hàng | ...
    VCB            | 2022 | 1980         | 1380                | ...
    VCB            | 2023 | 2210         | 1510                | ...

Mỗi sector subclass chỉ cần khai báo:
    ITEM_ID_MAP = {"bsa53": "tổng_tài_sản", "bsb113": "tiền_gửi_khách_hàng", ...}
cho từng bảng (balance, income, cashflow).
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Optional

BILLION = 1_000_000_000


class BaseFinancialProcessor(ABC):
    """
    Base class cho tất cả sector processors.

    Subclass chỉ cần implement 3 property (ITEM_ID_MAP cho từng bảng)
    và 3 method _*_growth_targets() để chỉ định cột nào tính % YoY.
    """

    def __init__(self, unit_divisor: int = BILLION, round_decimals: int = 2):
        self.unit_divisor   = unit_divisor
        self.round_decimals = round_decimals

    # ------------------------------------------------------------------
    # PUBLIC: process toàn bộ sector (đọc raw files → xuất 3 CSV)
    # ------------------------------------------------------------------

    def process_sector(
        self,
        ticker_data: dict,
        output_dir: str,
        years: Optional[list] = None,
    ) -> dict:
        """
        Xử lý raw data của nhiều tickers → 3 CSV chuẩn.

        Parameters
        ----------
        ticker_data : {'VCB': {'balance': df, 'income': df, 'cashflow': df}, ...}
        output_dir  : nơi lưu CSV output
        years       : lọc chỉ những năm này (None = giữ tất cả)

        Returns
        -------
        dict: {'balance_sheet': df, 'income': df, 'cashflow': df}
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        bs_list, inc_list, cf_list = [], [], []

        for ticker, data in ticker_data.items():
            if data is None:
                continue

            # Process từng bảng cho ticker này
            df_bs  = self._process_one(data.get("balance"),  self.balance_item_map,  ticker)
            df_inc = self._process_one(data.get("income"),   self.income_item_map,   ticker)
            df_cf  = self._process_one(data.get("cashflow"), self.cashflow_item_map, ticker)

            if df_bs  is not None: bs_list.append(df_bs)
            if df_inc is not None: inc_list.append(df_inc)
            if df_cf  is not None: cf_list.append(df_cf)

        # Concat tất cả tickers
        df_bs  = self._concat_and_filter(bs_list,  years, "balance sheet")
        df_inc = self._concat_and_filter(inc_list, years, "income statement")
        df_cf  = self._concat_and_filter(cf_list,  years, "cash flow")

        # Thêm % tăng trưởng YoY
        df_bs  = self._add_growth_cols(df_bs,  self._bs_growth_targets())
        df_inc = self._add_growth_cols(df_inc, self._inc_growth_targets())
        df_cf  = self._add_growth_cols(df_cf,  self._cf_growth_targets())

        # Lưu CSV
        out = Path(output_dir)
        df_bs.to_csv( out / "bảng_cân_đối_kế_toán.csv",       index=False, encoding="utf-8-sig")
        df_inc.to_csv(out / "báo_cáo_kết_quả_kinh_doanh.csv", index=False, encoding="utf-8-sig")
        df_cf.to_csv( out / "báo_cáo_lưu_chuyển_tiền_tệ.csv", index=False, encoding="utf-8-sig")

        print(f"  ✔ CĐKT   : {df_bs.shape}  → bảng_cân_đối_kế_toán.csv")
        print(f"  ✔ KQKD   : {df_inc.shape} → báo_cáo_kết_quả_kinh_doanh.csv")
        print(f"  ✔ LCTT   : {df_cf.shape}  → báo_cáo_lưu_chuyển_tiền_tệ.csv")

        return {"balance_sheet": df_bs, "income": df_inc, "cashflow": df_cf}

    # ------------------------------------------------------------------
    # ABSTRACT PROPERTIES — subclass khai báo ITEM_ID_MAP cho từng bảng
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def balance_item_map(self) -> dict:
        """
        Dict mapping item_id → tên cột tiếng Việt cho balance sheet.
        Ví dụ: {"bsa53": "tổng_tài_sản", "bsb113": "tiền_gửi_khách_hàng"}
        """
        pass

    @property
    @abstractmethod
    def income_item_map(self) -> dict:
        """Dict mapping item_id → tên cột cho income statement."""
        pass

    @property
    @abstractmethod
    def cashflow_item_map(self) -> dict:
        """Dict mapping item_id → tên cột cho cash flow."""
        pass

    # ------------------------------------------------------------------
    # ABSTRACT METHODS — subclass khai báo cột nào tính % tăng trưởng
    # ------------------------------------------------------------------

    @abstractmethod
    def _bs_growth_targets(self) -> list:
        """Danh sách tên cột (sau rename) cần tính % tăng trưởng YoY trong BS."""
        pass

    @abstractmethod
    def _inc_growth_targets(self) -> list:
        pass

    @abstractmethod
    def _cf_growth_targets(self) -> list:
        pass

    # ------------------------------------------------------------------
    # CORE LOGIC: pivot long format → wide format
    # ------------------------------------------------------------------

    def _process_one(
        self,
        df_long: Optional[pd.DataFrame],
        item_map: dict,
        ticker: str,
    ) -> Optional[pd.DataFrame]:
        """
        Pivot 1 bảng tài chính (long) → wide format cho 1 ticker.

        INPUT  (long): item_id | item | item_en | 2024 | 2023 | 2022 | ...
        OUTPUT (wide): mã_chứng_khoán | năm | col1 | col2 | ...
        """
        if df_long is None or df_long.empty:
            return None
        if not item_map:
            return None

        try:
            # --- Bước 1: Lọc chỉ các item_id cần thiết ---
            if "item_id" not in df_long.columns:
                print(f"  ⚠ {ticker}: thiếu cột item_id")
                return None

            df_filtered = df_long[df_long["item_id"].isin(item_map.keys())].copy()

            if df_filtered.empty:
                print(f"  ⚠ {ticker}: không tìm thấy item_id nào trong map")
                return None

            # --- Bước 2: Xác định cột kỳ (năm hoặc quý) ---
            period_cols = self._get_period_cols(df_long.columns)

            if not period_cols:
                print(f"  ⚠ {ticker}: không tìm thấy cột kỳ")
                return None

            # --- Bước 3: Đổi tên item_id → tên tiếng Việt ---
            df_filtered["col_name"] = df_filtered["item_id"].map(item_map)

            # --- Bước 4: Pivot → mỗi cột = 1 chỉ tiêu, mỗi dòng = 1 kỳ ---
            df_pivot = df_filtered.set_index("col_name")[period_cols]

            # Transpose: rows = kỳ, cols = chỉ tiêu
            # Sau reset_index(), tên cột index = tên index cũ = "col_name"
            df_wide = df_pivot.T.reset_index()

            # Transpose: rows = kỳ, cols = chỉ tiêu
            # Dùng iloc để không phụ thuộc vào tên cột đầu sau reset_index()
            # (có thể là "index", "period", "col_name" tuỳ pandas/vnstock version)
            df_wide = df_pivot.T.reset_index()
            period_values = df_wide.iloc[:, 0].copy()   # cột 0 = giá trị kỳ
            df_wide = df_wide.iloc[:, 1:].copy()        # bỏ cột period

            # --- Bước 5: Parse kỳ → năm (xử lý cả "2024" lẫn "2024-Q4") ---
            df_wide["năm"] = period_values.apply(self._parse_year).values
            df_wide = df_wide.dropna(subset=["năm"])
            df_wide["năm"] = df_wide["năm"].astype(int)

            # --- Bước 6: Chia đơn vị (tỷ VNĐ) ---
            # EPS là VNĐ/cổ phiếu (~1000-5000 VNĐ) — KHÔNG chia tỷ
            # vì round(3500 / 1e9, 2) = 0.0 → mất dữ liệu hoàn toàn
            eps_cols = {c for c in df_wide.columns if "eps" in c.lower()}
            value_cols = [c for c in df_wide.columns if c != "năm"]
            for col in value_cols:
                df_wide[col] = pd.to_numeric(df_wide[col], errors="coerce")
                if col not in eps_cols:
                    df_wide[col] = (df_wide[col] / self.unit_divisor).round(self.round_decimals)
                else:
                    df_wide[col] = df_wide[col].round(0)  # giữ nguyên VNĐ, làm tròn số nguyên

            # --- Bước 7: Thêm ticker, sắp xếp ---
            df_wide.insert(0, "mã_chứng_khoán", ticker)
            df_wide = df_wide.sort_values("năm").reset_index(drop=True)

            # Sắp xếp cột: key cols trước
            key_cols   = ["mã_chứng_khoán", "năm"]
            other_cols = [c for c in df_wide.columns if c not in key_cols]
            df_wide    = df_wide[key_cols + other_cols]

            return df_wide

        except Exception as e:
            print(f"  ✗ Lỗi xử lý {ticker}: {e}")
            return None

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _get_period_cols(self, columns) -> list:
        """
        Xác định các cột kỳ từ danh sách cột.
        Nhận ra cả: '2024', '2024-Q4', '2024-Q1', '2023', ...
        Loại bỏ: 'item', 'item_en', 'item_id' và các cột metadata khác.
        """
        period_pattern = re.compile(r"^\d{4}(-Q[1-4])?$")
        period_cols = [
            c for c in columns
            if isinstance(c, str) and period_pattern.match(str(c))
        ]
        # Sắp xếp giảm dần (mới nhất trước)
        return sorted(period_cols, reverse=True)

    def _parse_year(self, period_str: str) -> Optional[int]:
        """
        Parse chuỗi kỳ → năm nguyên.
        '2024'    → 2024
        '2024-Q4' → 2024  (lấy Q4 = cuối năm)
        '2024-Q1' → None  (bỏ qua Q1, Q2, Q3 khi có yearly data)
        '2023-Q4' → 2023

        Logic: nếu là quarterly data, chỉ giữ Q4 (= số liệu cuối năm).
        Nếu là yearly data (không có -Q), giữ nguyên.
        """
        s = str(period_str).strip()

        # Yearly format: "2024"
        if re.match(r"^\d{4}$", s):
            return int(s)

        # Quarterly format: "2024-Q4"
        m = re.match(r"^(\d{4})-Q([1-4])$", s)
        if m:
            year    = int(m.group(1))
            quarter = int(m.group(2))
            # Chỉ giữ Q4 (cuối năm = gần nhất với year-end report)
            if quarter == 4:
                return year
            else:
                return None  # bỏ qua Q1, Q2, Q3

        return None

    def _concat_and_filter(
        self,
        df_list: list,
        years: Optional[list],
        name: str,
    ) -> pd.DataFrame:
        """Concat nhiều ticker DataFrames, lọc theo years nếu có."""
        if not df_list:
            print(f"  ⚠ Không có dữ liệu cho {name}")
            return pd.DataFrame()

        df = pd.concat(df_list, ignore_index=True)

        if years is not None:
            df = df[df["năm"].isin(years)]

        df = df.sort_values(["mã_chứng_khoán", "năm"]).reset_index(drop=True)
        return df

    def _add_growth_cols(self, df: pd.DataFrame, targets: list) -> pd.DataFrame:
        """
        Tính % tăng trưởng YoY (so với năm trước của cùng ticker).
        Tên cột mới: '{tên_cột}_% tăng trưởng'

        Công thức: (value_t - value_{t-1}) / |value_{t-1}| × 100
        Dùng abs(denominator) để tránh sign flip khi value âm.
        """
        if df.empty or not targets:
            return df

        df = df.sort_values(["mã_chứng_khoán", "năm"]).copy()

        for col in targets:
            if col not in df.columns:
                continue
            growth_col = f"{col}_% tăng trưởng"
            prev = df.groupby("mã_chứng_khoán")[col].shift(1)
            df[growth_col] = np.where(
                prev.isna() | (prev == 0),
                np.nan,
                ((df[col] - prev) / prev.abs() * 100).round(self.round_decimals),
            )

        return df
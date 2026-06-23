"""
factors/factor_builder.py
==========================
Đọc 3 CSV đã xử lý + yearly_return.csv → Gold Dataset cho correlation.

cập nhật:
  - Tên cột raw để match với output của processors mới (vnstock)
  - Thêm BankingFactorBuilder với tên cột mới
  - Thêm NonBankingFactorBuilder cho RE, Tech, Food
"""

import pandas as pd
import numpy as np
from pathlib import Path
from abc import ABC, abstractmethod


# ======================================================================
# RAW VALUE COLUMNS — loại khỏi gold dataset (giữ trong CSV gốc)
# ======================================================================

# Banking: tên cột raw (từ banking_processor.py)
BANKING_RAW_COLS = {
    # Balance sheet — raw monetary values
    "tiền_mặt_vàng_bạc",
    "tài_sản_cố_định",
    "tiền_gửi_tại_nhnn",
    "tiền_gửi_tại_tctd_khác",
    "cho_vay_khách_hàng_net",
    "cho_vay_khách_hàng",
    "dự_phòng_rủi_ro_cho_vay",
    "chứng_khoán_đầu_tư",
    "tổng_nợ_phải_trả",
    "nợ_chính_phủ_nhnn",
    "tiền_gửi_vay_tctd_khác",
    "tiền_gửi_khách_hàng",
    "giấy_tờ_có_giá_phát_hành",
    "tổng_vốn_chủ_sở_hữu",
    "vốn_điều_lệ",
    "lợi_nhuận_giữ_lại",
    "vốn_tctd",
    "quỹ_tctd",
    "tổng_tài_sản",
    # Income statement — raw monetary values
    "thu_nhập_lãi_và_tương_đương",
    "chi_phí_lãi_và_tương_đương",
    "thu_nhập_lãi_thuần",
    "lãi_thuần_dịch_vụ",
    "tổng_thu_nhập_hoạt_động",
    "chi_phí_quản_lý",
    "lợi_nhuận_trước_dự_phòng",
    "chi_phí_dự_phòng_tín_dụng",
    "lợi_nhuận_trước_thuế",
    "chi_phí_thuế",
    "lợi_nhuận_sau_thuế",
    "lợi_nhuận_cổ_đông_công_ty_mẹ",
    # Cash flow — raw monetary values
    "lưu_chuyển_tiền_hđkd",
    "mua_sắm_tscđ",
    "lưu_chuyển_tiền_hđ_đầu_tư",
    "cổ_tức_đã_trả",
    "tiền_đầu_kỳ",
    "tiền_cuối_kỳ",
}

# Non-banking: tên cột raw (từ nonbanking_processor.py)
NONBANKING_RAW_COLS = {
    # Balance sheet
    "tài_sản_ngắn_hạn",
    "tiền_và_tương_đương_tiền",
    "phải_thu_ngắn_hạn",
    "hàng_tồn_kho",
    "hàng_tồn_kho_net",
    "tài_sản_dài_hạn",
    "tài_sản_cố_định",
    "tổng_tài_sản",
    "tổng_nợ_phải_trả",
    "nợ_ngắn_hạn",
    "vay_ngắn_hạn",
    "phải_trả_người_bán_ngắn_hạn",
    "nợ_dài_hạn",
    "vay_dài_hạn",
    "tổng_vốn_chủ_sở_hữu",
    "vốn_điều_lệ",
        "lợi_nhuận_giữ_lại",
    "người_mua_trả_tiền_trước",
    "xây_dựng_dở_dang",
    "quỹ_phát_triển_khcn",
    # Income
    "doanh_thu_bán_hàng",
    "doanh_thu_thuần",
    "lợi_nhuận_gộp",
    "chi_phí_tài_chính",
    "chi_phí_lãi_vay",
    "chi_phí_bán_hàng",
    "chi_phí_quản_lý",
    "lợi_nhuận_từ_hđkd",
    "lợi_nhuận_trước_thuế",
    "chi_phí_thuế",
    "lợi_nhuận_sau_thuế",
    # Securities-specific income items
    "doanh_thu_hoạt_động",
    "kết_quả_hoạt_động",
    "lợi_nhuận_cổ_đông_công_ty_mẹ",
    "doanh_thu_môi_giới",
    "doanh_thu_bảo_lãnh",
    "doanh_thu_tư_vấn",
    "doanh_thu_lưu_ký",
    "lãi_tài_sản_fvtpl",
    "doanh_thu_tài_chính",
    # Cash flow
    "lưu_chuyển_tiền_hđkd",
    "mua_sắm_tscđ",
    "lưu_chuyển_tiền_hđ_đầu_tư",
    "cổ_tức_đã_trả",
    "lưu_chuyển_tiền_thuần_trong_kỳ",
    "tiền_đầu_kỳ",
    "tiền_cuối_kỳ",
}

# Metadata — không phải factor
META_COLS = {
    "mã_chứng_khoán", "năm",
    "lợi_nhuận_hàng_năm_%",
    "năm_chưa_kết_thúc", "thiếu_dữ_liệu",
}


# ======================================================================
# BASE CLASS
# ======================================================================

class BaseFactorBuilder(ABC):

    def build(
        self,
        df_bs:      pd.DataFrame,
        df_inc:     pd.DataFrame,
        df_cf:      pd.DataFrame,
        df_returns: pd.DataFrame,
        output_path: str,
    ) -> pd.DataFrame:
        """
        Merge 4 DataFrames → tính cross-table factors → lọc raw values → lưu Gold Dataset.
        """
        keys = ["mã_chứng_khoán", "năm"]

        # Chuẩn hoá tên cột return
        df_returns = df_returns.copy()
        if "mã_cổ_phiếu" in df_returns.columns:
            df_returns = df_returns.rename(columns={"mã_cổ_phiếu": "mã_chứng_khoán"})
        for old, new in [
            ("tỷ_suất_sinh_lời_hàng_năm_%", "lợi_nhuận_hàng_năm_%"),
            ("năm_chưa_hoàn_thành",          "năm_chưa_kết_thúc"),
        ]:
            if old in df_returns.columns and new not in df_returns.columns:
                df_returns = df_returns.rename(columns={old: new})

        # Merge 3 bảng tài chính
        df = df_bs.copy()
        for df_next in [df_inc, df_cf]:
            if df_next is None or df_next.empty:
                continue
            overlap = [c for c in df_next.columns if c in df.columns and c not in keys]
            df = df.merge(df_next.drop(columns=overlap), on=keys, how="outer")

        # Merge với return
        return_cols = [c for c in [
            "mã_chứng_khoán", "năm",
            "lợi_nhuận_hàng_năm_%",
            "năm_chưa_kết_thúc", "thiếu_dữ_liệu",
        ] if c in df_returns.columns]
        df = df.merge(df_returns[return_cols], on=keys, how="left")

        # Tính cross-table factors đặc thù sector
        df = self._add_sector_factors(df)

        # Lọc raw values
        raw_to_drop = [
            c for c in df.columns
            if c in self._raw_cols_to_exclude() and c not in META_COLS
        ]
        df_gold = df.drop(columns=raw_to_drop)
        df_gold = df_gold.sort_values(keys).reset_index(drop=True)

        # Lưu
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df_gold.to_csv(output_path, index=False, encoding="utf-8-sig")

        # Summary
        factor_cols = [
            c for c in df_gold.columns
            if c not in META_COLS
            and c not in {"lợi_nhuận_hàng_năm_%", "năm_chưa_kết_thúc", "thiếu_dữ_liệu"}
        ]
        print(f"  ✔ Gold dataset: {df_gold.shape[0]} rows × {df_gold.shape[1]} cols → {output_path}")
        print(f"  ✔ Factors đưa vào correlation: {len(factor_cols)}")
        print(f"     Đã loại {len(raw_to_drop)} raw value columns")
        print(f"  Factors: {factor_cols}")

        return df_gold

    @abstractmethod
    def _add_sector_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        pass

    @abstractmethod
    def _raw_cols_to_exclude(self) -> set:
        pass

    # Helper dùng chung
    def _safe_pct(self, df, num_col, den_col) -> pd.Series:
        """Tính num/den × 100, xử lý NaN và chia 0."""
        num = df.get(num_col, pd.Series([np.nan] * len(df), index=df.index))
        den = df.get(den_col, pd.Series([np.nan] * len(df), index=df.index))
        return pd.Series(np.where(
            den.isna() | (den == 0), np.nan,
            (num / den.abs() * 100).round(4)
        ), index=df.index)


# ======================================================================
# BANKING FACTOR BUILDER
# ======================================================================

class BankingFactorBuilder(BaseFactorBuilder):
    """
    Factors banking (cross-table ratios):
      roa_%           = lợi_nhuận_sau_thuế / tổng_tài_sản
      roe_%           = lợi_nhuận_sau_thuế / tổng_vốn_chủ_sở_hữu
      nim_%           = thu_nhập_lãi_thuần / tổng_tài_sản
      cir_%           = |chi_phí_quản_lý| / tổng_thu_nhập_hoạt_động
      ldr_%           = cho_vay_khách_hàng / tiền_gửi_khách_hàng
      tỷ_lệ_dự_phòng_%= |chi_phí_dự_phòng| / lợi_nhuận_trước_dự_phòng
      tỷ_lệ_nợ_%      = tổng_nợ_phải_trả / tổng_tài_sản
    """

    def _add_sector_factors(self, df: pd.DataFrame) -> pd.DataFrame:

        df["roa_%"] = self._safe_pct(df, "lợi_nhuận_sau_thuế", "tổng_tài_sản")
        df["roe_%"] = self._safe_pct(df, "lợi_nhuận_sau_thuế", "tổng_vốn_chủ_sở_hữu")
        df["nim_%"] = self._safe_pct(df, "thu_nhập_lãi_thuần",  "tổng_tài_sản")

        # CIR = |chi phí| / thu nhập (thấp = tốt)
        if "chi_phí_quản_lý" in df.columns and "tổng_thu_nhập_hoạt_động" in df.columns:
            df["cir_%"] = pd.Series(np.where(
                df["tổng_thu_nhập_hoạt_động"].isna() | (df["tổng_thu_nhập_hoạt_động"] == 0),
                np.nan,
                (df["chi_phí_quản_lý"].abs() / df["tổng_thu_nhập_hoạt_động"] * 100).round(2)
            ), index=df.index)

        # LDR = Cho vay / Tiền gửi
        df["ldr_%"] = self._safe_pct(df, "cho_vay_khách_hàng", "tiền_gửi_khách_hàng")

        # Tỷ lệ dự phòng
        if "chi_phí_dự_phòng_tín_dụng" in df.columns and "lợi_nhuận_trước_dự_phòng" in df.columns:
            df["tỷ_lệ_dự_phòng_%"] = pd.Series(np.where(
                df["lợi_nhuận_trước_dự_phòng"].isna() | (df["lợi_nhuận_trước_dự_phòng"] == 0),
                np.nan,
                (df["chi_phí_dự_phòng_tín_dụng"].abs() / df["lợi_nhuận_trước_dự_phòng"] * 100).round(2)
            ), index=df.index)

        # Tỷ lệ nợ / tài sản
        df["tỷ_lệ_nợ_%"] = self._safe_pct(df, "tổng_nợ_phải_trả", "tổng_tài_sản")

        return df

    def _raw_cols_to_exclude(self) -> set:
        return BANKING_RAW_COLS


# ======================================================================
# NON-BANKING FACTOR BUILDER (Real Estate, Tech, Food)
# ======================================================================

class NonBankingFactorBuilder(BaseFactorBuilder):
    """
    Base factor builder cho non-banking.
    Tính các ratios CHUNG cho mọi ngành: margin, ROA, ROE, debt, asset turnover.
    Subclass thêm factors đặc thù từng ngành.
    """

    def _add_common_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ratios chung — gọi từ mọi subclass."""
        df["gross_margin_%"]     = self._safe_pct(df, "lợi_nhuận_gộp",     "doanh_thu_thuần")
        df["net_margin_%"]       = self._safe_pct(df, "lợi_nhuận_sau_thuế", "doanh_thu_thuần")
        df["roa_%"]              = self._safe_pct(df, "lợi_nhuận_sau_thuế", "tổng_tài_sản")
        df["roe_%"]              = self._safe_pct(df, "lợi_nhuận_sau_thuế", "tổng_vốn_chủ_sở_hữu")
        df["debt_ratio_%"]       = self._safe_pct(df, "tổng_nợ_phải_trả",  "tổng_tài_sản")
        df["short_debt_ratio_%"] = self._safe_pct(df, "vay_ngắn_hạn",      "tổng_tài_sản")
        df["long_debt_ratio_%"]  = self._safe_pct(df, "vay_dài_hạn",       "tổng_tài_sản")
        df["de_ratio"]           = self._safe_pct(df, "tổng_nợ_phải_trả",  "tổng_vốn_chủ_sở_hữu")
        # Asset turnover (lần, không phải %)
        if "doanh_thu_thuần" in df.columns and "tổng_tài_sản" in df.columns:
            df["asset_turnover"] = np.where(
                df["tổng_tài_sản"].isna() | (df["tổng_tài_sản"] == 0), np.nan,
                (df["doanh_thu_thuần"] / df["tổng_tài_sản"]).round(4)
            )
        return df

    def _add_sector_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._add_common_factors(df)

    def _raw_cols_to_exclude(self) -> set:
        return NONBANKING_RAW_COLS


class RealEstateFactorBuilder(NonBankingFactorBuilder):
    """
    Real Estate factors:
      Chung    : gross_margin, net_margin, ROA, ROE, debt ratios, asset_turnover
      Đặc thù  : tỷ_lệ_đặt_cọc_% = người_mua_trả_tiền_trước / tổng_tài_sản
                  → Tỷ lệ đặt cọc cao = demand tốt = tín hiệu tích cực
    """

    def _add_sector_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._add_common_factors(df)
        # RE-specific: demand ratio
        df["tỷ_lệ_đặt_cọc_%"] = self._safe_pct(
            df, "người_mua_trả_tiền_trước", "tổng_tài_sản"
        )
        return df


class TechnologyFactorBuilder(NonBankingFactorBuilder):
    """
    Technology factors:
      Chung    : gross_margin, net_margin, ROA, ROE, debt ratios, asset_turnover
      Đặc thù  : tỷ_lệ_rd_% = quỹ_phát_triển_khcn / tổng_tài_sản
                  → Mức đầu tư R&D so với quy mô công ty
    """

    def _add_sector_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._add_common_factors(df)
        # Tech-specific: R&D ratio
        df["tỷ_lệ_rd_%"] = self._safe_pct(
            df, "quỹ_phát_triển_khcn", "tổng_tài_sản"
        )
        return df


class FoodFactorBuilder(NonBankingFactorBuilder):
    """
    Food & Beverage factors:
      Chung    : gross_margin, net_margin, ROA, ROE, debt ratios, asset_turnover
      Đặc thù  : inventory_turnover = doanh_thu_thuần / hàng_tồn_kho_net
                  → Vòng quay tồn kho — cao = bán nhanh = hiệu quả vận hành tốt
    """

    def _add_sector_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._add_common_factors(df)
        # Food-specific: inventory turnover (lần/năm, không phải %)
        if "doanh_thu_thuần" in df.columns and "hàng_tồn_kho_net" in df.columns:
            df["inventory_turnover"] = np.where(
                df["hàng_tồn_kho_net"].isna() | (df["hàng_tồn_kho_net"] == 0), np.nan,
                (df["doanh_thu_thuần"] / df["hàng_tồn_kho_net"]).round(2)
            )
        return df


# ======================================================================
# 6 NGÀNH MỚI — dùng chung NonBankingFactorBuilder base
# Mỗi ngành có thể override _add_sector_factors nếu cần sau này
# ======================================================================

class ConstructionFactorBuilder(NonBankingFactorBuilder):
    """
    Xây dựng: ratios chung + không có factor đặc thù riêng.
    Key factors kỳ vọng: asset_turnover, debt_ratio, revenue_growth.
    """
    pass

class TransportFactorBuilder(NonBankingFactorBuilder):
    """
    Vận tải - Kho bãi: ratios chung.
    Key factors kỳ vọng: asset_turnover, cash_flow_growth, revenue_growth.
    """
    pass

class ChemicalsFactorBuilder(NonBankingFactorBuilder):
    """
    SX Nhựa - Hóa chất: ratios chung + inventory turnover.
    Key factors kỳ vọng: gross_margin, inventory_turnover, revenue_growth.
    """

    def _add_sector_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._add_common_factors(df)
        # Chemicals cũng cần inventory turnover như Food
        if "doanh_thu_thuần" in df.columns and "hàng_tồn_kho_net" in df.columns:
            df["inventory_turnover"] = np.where(
                df["hàng_tồn_kho_net"].isna() | (df["hàng_tồn_kho_net"] == 0), np.nan,
                (df["doanh_thu_thuần"] / df["hàng_tồn_kho_net"]).round(2)
            )
        return df

class UtilitiesFactorBuilder(NonBankingFactorBuilder):
    """
    Tiện ích: ratios chung.
    Key factors kỳ vọng: ROA, ROE, debt_ratio (ngành vốn lớn, ổn định).
    """
    pass

class SecuritiesFactorBuilder(NonBankingFactorBuilder):
    """
    Chứng khoán: ratios chung + tỷ lệ doanh thu môi giới.
    Key factors kỳ vọng: ROE, net_margin, revenue_growth.
    Factor đặc thù: tỷ lệ doanh thu môi giới / tổng doanh thu
      → đo mức độ phụ thuộc vào hoạt động môi giới
    """

    def _add_sector_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._add_common_factors(df)
        # Securities-specific: tỷ lệ doanh thu môi giới / tổng doanh thu
        if "doanh_thu_môi_giới" in df.columns and "doanh_thu_thuần" in df.columns:
            df["tỷ_lệ_môi_giới_%"] = self._safe_pct(
                df, "doanh_thu_môi_giới", "doanh_thu_thuần"
            )
        return df

class HealthcareFactorBuilder(NonBankingFactorBuilder):
    """
    Chăm sóc sức khỏe: ratios chung.
    Key factors kỳ vọng: gross_margin, net_margin, ROE.
    """
    pass


# ======================================================================
# FACTORY — mỗi sector có builder riêng
# ======================================================================

BUILDER_REGISTRY = {
    "BANKING":      BankingFactorBuilder,
    "REALESTATE":   RealEstateFactorBuilder,
    "TECHNOLOGY":   TechnologyFactorBuilder,
    "FOOD":         FoodFactorBuilder,
    "CONSTRUCTION": ConstructionFactorBuilder,
    "TRANSPORT":    TransportFactorBuilder,
    "CHEMICALS":    ChemicalsFactorBuilder,
    "UTILITIES":    UtilitiesFactorBuilder,
    "SECURITIES":   SecuritiesFactorBuilder,
    "HEALTHCARE":   HealthcareFactorBuilder,
}

def get_factor_builder(sector: str) -> BaseFactorBuilder:
    cls = BUILDER_REGISTRY.get(sector.upper())
    if cls is None:
        raise ValueError(
            f"Sector '{sector}' chưa có FactorBuilder. "
            f"Hiện có: {list(BUILDER_REGISTRY.keys())}"
        )
    return cls()
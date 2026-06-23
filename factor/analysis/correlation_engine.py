"""
analysis/correlation_engine.py
================================
Tính Spearman correlation giữa factors và yearly return.

Output:
  1. Sector level  : pool toàn ngành → bảng ranking chỉ báo ngành
  2. Ticker level  : từng ticker riêng → top N factors mạnh nhất

Bonferroni Correction:
  Vấn đề: test 20 factors cùng lúc với p < 0.05 → xác suất thấy
  kết quả "significant" ngẫu nhiên ≈ 20 × 0.05 = 1 factor.

  Giải pháp: ngưỡng mới = 0.05 / số_factors_được_test
  Ví dụ: 20 factors → ngưỡng = 0.0025

  Output có 2 cột ý nghĩa:
    có_ý_nghĩa_thống_kê       : p < 0.05 (standard)
    có_ý_nghĩa_sau_bonferroni : p < 0.05/n_factors (chặt hơn)
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path


STRENGTH_MAP = [
    (0.8, "Rất mạnh"),
    (0.6, "Mạnh"),
    (0.4, "Trung bình"),
    (0.2, "Yếu"),
    (0.0, "Rất yếu"),
]

META_COLS = {
    "mã_chứng_khoán", "năm", "ngành", "companyType",
    "lợi_nhuận_hàng_năm_%", "lợi_nhuận_hàng_năm",
    "tỷ_suất_sinh_lời_hàng_năm_%",
    "năm_chưa_kết_thúc", "năm_chưa_hoàn_thành", "thiếu_dữ_liệu",
    "giá_đóng_cửa_đầu_kỳ", "giá_đóng_cửa_cuối_kỳ",
    "giá_đầu_kỳ", "giá_cuối_kỳ",
    "reportType", "audited",
}

RETURN_COLS = ["lợi_nhuận_hàng_năm_%", "tỷ_suất_sinh_lời_hàng_năm_%"]


class CorrelationEngine:

    def __init__(self, p_threshold: float = 0.05):
        self.p_threshold = p_threshold

    def compute_sector_level(self, df_gold, min_obs=8, exclude_partial=True):
        df, return_col = self._prepare(df_gold, exclude_partial)
        if df is None:
            return pd.DataFrame()
        factor_cols = self._get_factor_cols(df)
        n_factors   = len(factor_cols)
        rows = []
        for col in factor_cols:
            r = self._spearman_one(df, col, return_col, min_obs)
            if r:
                rows.append(r)
        if not rows:
            return pd.DataFrame()
        return self._rank_and_classify(pd.DataFrame(rows), n_factors_tested=n_factors)

    def compute_ticker_level(self, df_gold, min_obs=3, exclude_partial=True, top_n=5):
        df, return_col = self._prepare(df_gold, exclude_partial)
        if df is None:
            return pd.DataFrame()
        factor_cols = self._get_factor_cols(df)
        n_factors   = len(factor_cols)
        all_rows = []
        for ticker, grp in df.groupby("mã_chứng_khoán"):
            for col in factor_cols:
                r = self._spearman_one(grp, col, return_col, min_obs)
                if r:
                    r["mã_chứng_khoán"] = ticker
                    all_rows.append(r)
        if not all_rows:
            return pd.DataFrame()
        result = self._rank_and_classify(pd.DataFrame(all_rows), n_factors_tested=n_factors)
        result = (
            result
            .sort_values(["mã_chứng_khoán", "abs_tương_quan"], ascending=[True, False])
            .groupby("mã_chứng_khoán").head(top_n)
            .reset_index(drop=True)
        )
        final_cols = [
            "mã_chứng_khoán", "chỉ_báo", "độ_tương_quan_%",
            "kết_luận", "độ_mạnh", "p_value",
            "có_ý_nghĩa_thống_kê", "có_ý_nghĩa_sau_bonferroni", "số_quan_sát"
        ]
        return result[[c for c in final_cols if c in result.columns]]

    def _prepare(self, df, exclude_partial):
        df = df.copy()
        return_col = next((c for c in RETURN_COLS if c in df.columns), None)
        if return_col is None:
            print(f"  ⚠ Không tìm thấy cột return. Cần 1 trong: {RETURN_COLS}")
            return None, None
        partial_col = next(
            (c for c in ["năm_chưa_kết_thúc", "năm_chưa_hoàn_thành"] if c in df.columns), None
        )
        if exclude_partial and partial_col:
            # Chuẩn hoá về bool — cột có thể là bool hoặc string 'True'/'False'
            # khi gold_factors.csv được đọc lại từ disk
            raw = df[partial_col].fillna(False)
            bool_mask = raw.apply(lambda v: str(v).strip().lower() == "true").astype(bool)
            df = df[~bool_mask]
        return df.dropna(subset=[return_col]), return_col

    def _get_factor_cols(self, df):
        return [c for c in df.columns if c not in META_COLS]

    def _spearman_one(self, df, factor_col, return_col, min_obs):
        pair = df[[return_col, factor_col]].dropna()
        n    = len(pair)
        if n < min_obs:
            return None
        corr, p_val = stats.spearmanr(pair[return_col], pair[factor_col])
        if np.isnan(corr):
            return None
        return {
            "chỉ_báo":     factor_col,
            "tương_quan":  round(float(corr), 4),
            "p_value":     round(float(p_val), 4),
            "số_quan_sát": n,
        }

    def _rank_and_classify(self, df, n_factors_tested):
        df = df.copy()
        df["abs_tương_quan"]          = df["tương_quan"].abs()
        df["độ_tương_quan_%"]         = df["tương_quan"].apply(lambda r: f"{r*100:+.1f}%")
        df["kết_luận"]                = df["tương_quan"].apply(lambda r: "Đồng biến" if r > 0 else "Nghịch biến")
        df["độ_mạnh"]                 = df["abs_tương_quan"].apply(self._classify_strength)
        df["có_ý_nghĩa_thống_kê"]    = df["p_value"] < self.p_threshold
        bonferroni_threshold          = self.p_threshold / max(n_factors_tested, 1)
        df["có_ý_nghĩa_sau_bonferroni"] = df["p_value"] < bonferroni_threshold
        df["bonferroni_threshold"]    = round(bonferroni_threshold, 6)
        df = df.sort_values("abs_tương_quan", ascending=False).reset_index(drop=True)
        df["xếp_hạng"] = df.index + 1
        return df

    @staticmethod
    def _classify_strength(v):
        for threshold, label in STRENGTH_MAP:
            if v >= threshold:
                return label
        return "Rất yếu"


class FactorRanker:

    def export(self, df_sector, df_ticker, output_dir, sector_name):
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        if not df_sector.empty:
            cols = [
                "xếp_hạng", "chỉ_báo", "độ_tương_quan_%", "kết_luận",
                "độ_mạnh", "p_value",
                "có_ý_nghĩa_thống_kê", "có_ý_nghĩa_sau_bonferroni",
                "bonferroni_threshold", "số_quan_sát"
            ]
            df_sector[[c for c in cols if c in df_sector.columns]].to_csv(
                out / f"{sector_name.lower()}_factor_results.csv",
                index=False, encoding="utf-8-sig"
            )
            print(f"  ✔ Kết quả ngành  → {out}/{sector_name.lower()}_factor_results.csv")

            if "bonferroni_threshold" in df_sector.columns:
                n              = len(df_sector)
                thresh         = df_sector["bonferroni_threshold"].iloc[0]
                sig_standard   = df_sector["có_ý_nghĩa_thống_kê"].sum()
                sig_bonferroni = df_sector["có_ý_nghĩa_sau_bonferroni"].sum()
                print(f"\n  📊 Bonferroni correction ({n} factors tested):")
                print(f"     Ngưỡng standard  : p < 0.05    → {sig_standard} factors significant")
                print(f"     Ngưỡng Bonferroni: p < {thresh:.4f} → {sig_bonferroni} factors significant")

        if not df_ticker.empty:
            df_ticker.to_csv(
                out / f"{sector_name.lower()}_ticker_results.csv",
                index=False, encoding="utf-8-sig"
            )
            print(f"  ✔ Kết quả ticker → {out}/{sector_name.lower()}_ticker_results.csv")

            print(f"\n  📊 Preview (format Bước 2):")
            print(f"  {'Mã CP':<8} {'Chỉ báo':<45} {'Tương quan':<12} {'Kết luận'}")
            print(f"  {'-'*80}")
            for _, row in df_ticker.head(12).iterrows():
                print(
                    f"  {row.get('mã_chứng_khoán',''):<8} "
                    f"{str(row.get('chỉ_báo',''))[:45]:<45} "
                    f"{row.get('độ_tương_quan_%',''):<12} "
                    f"{row.get('kết_luận','')}"
                )
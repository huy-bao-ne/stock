"""
FactorVisualizer
=================
Tạo các biểu đồ từ factor correlation results.

Chart 1 — Factor Correlation Bar Chart:
    Horizontal bar chart, sorted by |correlation|.
    Màu xanh = positive, màu đỏ = negative.
    Hiển thị p-value significance (dấu * nếu p < 0.05).

Chart 2 — Factor Heatmap (per ticker per year):
    Heatmap của yearly_return × các factor chính.
    Giúp thấy pattern theo từng ngân hàng.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path


class FactorVisualizer:
    """
    Cách dùng:
        viz = FactorVisualizer(output_dir="outputs")
        viz.plot_correlation_bar(df_ranked)
        viz.plot_return_heatmap(df_gold)
    """

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Style đơn giản, không cần seaborn
        plt.rcParams.update({
            "font.family":   "sans-serif",
            "font.size":     11,
            "axes.spines.top":    False,
            "axes.spines.right":  False,
            "figure.dpi":         150,
        })

    # ------------------------------------------------------------------
    # CHART 1: Correlation Bar Chart
    # ------------------------------------------------------------------

    def plot_correlation_bar(
        self,
        df_ranked: pd.DataFrame,
        title: str = "Factor Correlation with Yearly Return (Banking)",
        filename: str = "factor_correlation_bar.png",
    ) -> Path:
        """
        Horizontal bar chart: mỗi bar = 1 factor, độ dài = |correlation|.

        Parameters
        ----------
        df_ranked : pd.DataFrame
            Output của FactorRanker.rank()
        """
        df = df_ranked.sort_values("abs_correlation", ascending=True)  # bottom = highest

        fig, ax = plt.subplots(figsize=(9, max(5, len(df) * 0.5)))

        colors = [
            "#2E86AB" if d == "Positive" else "#E84855"
            for d in df["direction"]
        ]

        bars = ax.barh(df["factor"], df["correlation"], color=colors, height=0.6)

        # Label giá trị + significance star
        for bar, (_, row) in zip(bars, df.iterrows()):
            x_end = row["correlation"]
            star = " *" if row.get("significant", False) else ""
            label = f"{x_end:.3f}{star}"
            x_pos = x_end + (0.01 if x_end >= 0 else -0.01)
            ha = "left" if x_end >= 0 else "right"
            ax.text(x_pos, bar.get_y() + bar.get_height() / 2,
                    label, va="center", ha=ha, fontsize=9)

        # Đường 0
        ax.axvline(0, color="black", linewidth=0.8, linestyle="-")

        # Vùng threshold (optional visual reference)
        for thresh, alpha in [(0.4, 0.04), (0.6, 0.04)]:
            ax.axvspan( thresh,  1.0, alpha=alpha, color="#2E86AB")
            ax.axvspan(-1.0, -thresh, alpha=alpha, color="#E84855")

        # Legend
        pos_patch = mpatches.Patch(color="#2E86AB", label="Positive effect")
        neg_patch = mpatches.Patch(color="#E84855", label="Negative effect")
        ax.legend(handles=[pos_patch, neg_patch], loc="lower right", fontsize=9)

        ax.set_xlabel("Spearman Correlation")
        ax.set_xlim(-1.05, 1.05)
        ax.set_title(title, fontsize=13, pad=12)
        ax.text(
            0.5, -0.08,
            "* = statistically significant (p < 0.05)",
            transform=ax.transAxes, ha="center", fontsize=8, color="gray"
        )

        plt.tight_layout()
        out_path = self.output_dir / filename
        plt.savefig(out_path, bbox_inches="tight")
        plt.close()
        print(f"✔ Saved: {out_path}")
        return out_path

    # ------------------------------------------------------------------
    # CHART 2: Yearly Return Heatmap per Ticker
    # ------------------------------------------------------------------

    def plot_return_heatmap(
        self,
        df_gold: pd.DataFrame,
        filename: str = "return_heatmap.png",
    ) -> Path:
        """
        Heatmap: rows = tickers, cols = years, values = yearly_return (%).

        Giúp thấy nhanh: ngân hàng nào tốt năm nào, có pattern không.
        """
        # Pivot: ticker × year
        pivot = df_gold.pivot_table(
            index="ticker", columns="year", values="yearly_return"
        )

        # Convert sang % cho dễ đọc
        pivot_pct = pivot * 100

        fig, ax = plt.subplots(figsize=(len(pivot.columns) * 1.4 + 2, len(pivot) * 0.7 + 1.5))

        # Colormap: đỏ = âm, xanh = dương, trắng = 0
        im = ax.imshow(pivot_pct.values, cmap="RdYlGn", aspect="auto", vmin=-50, vmax=50)

        # Ticks
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels(pivot.columns)
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index)

        # Giá trị trong ô
        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                val = pivot_pct.values[i, j]
                if not np.isnan(val):
                    text_color = "black" if abs(val) < 35 else "white"
                    ax.text(j, i, f"{val:.1f}%", ha="center", va="center",
                            fontsize=9, color=text_color)
                else:
                    ax.text(j, i, "N/A", ha="center", va="center",
                            fontsize=8, color="gray")

        plt.colorbar(im, ax=ax, label="Yearly Return (%)")
        ax.set_title("Yearly Stock Return by Ticker (Banking)", fontsize=13, pad=10)
        ax.set_xlabel("Year")
        ax.set_ylabel("Ticker")

        plt.tight_layout()
        out_path = self.output_dir / filename
        plt.savefig(out_path, bbox_inches="tight")
        plt.close()
        print(f"✔ Saved: {out_path}")
        return out_path
"""
main.py — Financial Factor Analysis Engine v3
===============================================
Orchestrate toàn bộ pipeline cho 1 hoặc nhiều sector:

  BƯỚC 1: Collect  — lấy raw data từ vnstock
  BƯỚC 2: Process  — pivot long→wide, tính growth rates
  BƯỚC 3: Prices   — lấy giá + tính yearly return
  BƯỚC 4: Factors  — tính cross-table ratios, tạo gold dataset
  BƯỚC 5: Analyze  — Spearman correlation + Bonferroni

Cách chạy:
    # Chạy 1 sector
    python main.py --sector BANKING

    # Chạy tất cả
    python main.py --all

    # Bỏ qua bước collect (đã có raw files)
    python main.py --sector BANKING --skip-collect

    # Debug: in thêm thông tin
    python main.py --sector BANKING --debug
"""

import argparse
import sys
import yaml
import pandas as pd
from pathlib import Path


def load_config(config_path: str = "configs/config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_sector(sector: str, cfg: dict, skip_collect: bool = False, debug: bool = False, refresh_prices: bool = False):
    """
    Chạy toàn bộ pipeline cho 1 sector.
    """
    from collectors.vnstock_collector      import VnStockFinancialCollector, VnStockPriceCollector
    from processors.processor_factory     import get_processor
    from factors.factor_builder           import get_factor_builder

    # Lazy import — price_processor và correlation_engine giữ nguyên từ v2
    # Nếu chưa có thì comment out và dùng placeholder
    try:
        from processors.price_processor   import PriceProcessor
        has_price_processor = True
    except ImportError:
        has_price_processor = False
        print("  ⚠ price_processor.py chưa có — bỏ qua bước tính return")

    try:
        from analysis.correlation_engine  import CorrelationEngine
        has_correlation = True
    except ImportError:
        has_correlation = False
        print("  ⚠ correlation_engine.py chưa có — bỏ qua bước correlation")

    sector_cfg  = cfg["sectors"][sector]
    tickers     = sector_cfg["tickers"]
    data_dir    = sector_cfg["data_dir"]
    years_fin   = cfg["years"]["financial"]
    price_start = cfg["years"]["price_start"]
    price_end   = cfg["years"]["price_end"]
    vnstock_cfg = cfg["vnstock"]
    proc_cfg    = cfg["processing"]

    print(f"\n{'#'*60}")
    print(f"  SECTOR: {sector}")
    print(f"  Tickers: {tickers}")
    print(f"  Years: {years_fin}")
    print(f"{'#'*60}")

    # ──────────────────────────────────────────────
    # BƯỚC 1: COLLECT tài chính
    # ──────────────────────────────────────────────
    print(f"\n[BƯỚC 1] Thu thập báo cáo tài chính...")

    if not skip_collect:
        collector = VnStockFinancialCollector(
            source           = vnstock_cfg["source"],
            delay_each_call  = vnstock_cfg["rate_limit"]["delay_each_call"],
            batch_size       = vnstock_cfg["rate_limit"]["batch_size"],
            batch_pause      = vnstock_cfg["rate_limit"]["batch_pause"],
            max_retries      = vnstock_cfg["rate_limit"]["max_retries"],
            retry_delay      = vnstock_cfg["rate_limit"]["retry_delay"],
        )
        ticker_data = collector.collect_sector(
            tickers     = tickers,
            output_dir  = data_dir,
            period      = "year",
            skip_existing = True,
        )
    else:
        # Load từ raw files đã có
        print("  ↷ --skip-collect: đọc raw files từ disk")
        ticker_data = {}
        for ticker in tickers:
            raw = {}
            for name in ["balance", "income", "cashflow"]:
                path = Path(data_dir) / f"raw_{ticker}_{name}.csv"
                if path.exists():
                    raw[name] = pd.read_csv(path, encoding="utf-8-sig")
                else:
                    print(f"  ⚠ Không tìm thấy: {path}")
                    raw[name] = None
            ticker_data[ticker] = raw

    if not ticker_data:
        print(f"  ✗ Không có dữ liệu, bỏ qua sector {sector}")
        return

    # ──────────────────────────────────────────────
    # BƯỚC 2: PROCESS tài chính
    # ──────────────────────────────────────────────
    print(f"\n[BƯỚC 2] Xử lý báo cáo tài chính...")

    processor = get_processor(
        sector,
        unit_divisor  = proc_cfg["unit_divisor"],
        round_decimals = proc_cfg["round_decimals"],
    )
    processed = processor.process_sector(
        ticker_data = ticker_data,
        output_dir  = data_dir,
        years       = years_fin,
    )

    df_bs  = processed["balance_sheet"]
    df_inc = processed["income"]
    df_cf  = processed["cashflow"]

    if debug:
        print(f"\n  [DEBUG] Balance Sheet columns: {list(df_bs.columns)}")
        print(f"  [DEBUG] Income columns: {list(df_inc.columns)}")
        print(f"  [DEBUG] Sample BS:\n{df_bs.head(3).to_string()}")

    # ──────────────────────────────────────────────
    # BƯỚC 3: GIÁ CỔ PHIẾU + YEARLY RETURN
    # ──────────────────────────────────────────────
    print(f"\n[BƯỚC 3] Thu thập giá và tính yearly return...")

    # Nếu --refresh-prices: xóa file cũ để collector lấy lại đúng tickers hiện tại
    price_file = Path(data_dir) / "raw_prices.csv"
    if refresh_prices and price_file.exists():
        price_file.unlink()
        print(f"  ↷ Đã xóa raw_prices.csv cũ → sẽ lấy lại")

    price_collector = VnStockPriceCollector(source=vnstock_cfg["source"])
    price_collector.collect_sector(
        tickers      = tickers,
        start_date   = price_start,
        end_date     = price_end,
        output_dir   = data_dir,
        skip_existing = not refresh_prices,
    )

    return_path = Path(data_dir) / "yearly_return.csv"

    if has_price_processor:
        price_proc = PriceProcessor()
        df_returns = price_proc.process(
            raw_csv_path = str(Path(data_dir) / "raw_prices.csv"),
            output_path  = str(return_path),
        )
    else:
        # Placeholder nếu chưa có price_processor
        if return_path.exists():
            df_returns = pd.read_csv(return_path, encoding="utf-8-sig")
            print(f"  ↷ Dùng yearly_return.csv đã có: {return_path}")
        else:
            print(f"  ⚠ Không có yearly_return.csv — bỏ qua factor + correlation")
            return

    # ──────────────────────────────────────────────
    # BƯỚC 4: FACTOR BUILDER → GOLD DATASET
    # ──────────────────────────────────────────────
    print(f"\n[BƯỚC 4] Tạo Gold Dataset...")

    gold_path = str(Path(data_dir) / "gold_factors.csv")
    builder   = get_factor_builder(sector)
    df_gold   = builder.build(
        df_bs      = df_bs,
        df_inc     = df_inc,
        df_cf      = df_cf,
        df_returns = df_returns,
        output_path = gold_path,
    )

    if debug:
        print(f"\n  [DEBUG] Gold dataset shape: {df_gold.shape}")
        print(f"  [DEBUG] Columns: {list(df_gold.columns)}")

    # ──────────────────────────────────────────────
    # BƯỚC 5: CORRELATION ANALYSIS
    # ──────────────────────────────────────────────
    print(f"\n[BƯỚC 5] Correlation analysis...")

    if has_correlation:
        from analysis.correlation_engine import FactorRanker

        output_dir_results = f"outputs/{sector.lower()}"
        Path(output_dir_results).mkdir(parents=True, exist_ok=True)

        p_threshold = cfg["analysis"].get("p_value_threshold", 0.05)
        min_obs     = cfg["analysis"].get("min_observations", 8)

        engine     = CorrelationEngine(p_threshold=p_threshold)
        df_sector  = engine.compute_sector_level(df_gold, min_obs=min_obs)
        df_ticker  = engine.compute_ticker_level(df_gold, min_obs=3, top_n=5)

        FactorRanker().export(
            df_sector   = df_sector,
            df_ticker   = df_ticker,
            output_dir  = output_dir_results,
            sector_name = sector,
        )
    else:
        print("  ↷ Bỏ qua (correlation_engine.py chưa có)")

    # ──────────────────────────────────────────────
    # BƯỚC 6: CẬP NHẬT MASTER INDEX
    # ──────────────────────────────────────────────
    print(f"\n[BƯỚC 6] Cập nhật master index...")
    try:
        from utils.master_index import build_master_index
        build_master_index(
            sectors_config = cfg["sectors"],
            data_root      = "data",
            output_path    = cfg["output"]["master_index"],
        )
    except Exception as e:
        print(f"  ⚠ master_index: {e}")

    print(f"\n  ✅ Hoàn thành sector {sector}!\n")


def main():
    parser = argparse.ArgumentParser(description="Financial Factor Analysis Engine v3")
    parser.add_argument("--sector",       type=str, help="Sector cần chạy: BANKING, REALESTATE, TECHNOLOGY, FOOD")
    parser.add_argument("--all",          action="store_true", help="Chạy tất cả sectors")
    parser.add_argument("--skip-collect", action="store_true", help="Bỏ qua bước collect, dùng raw files đã có")
    parser.add_argument("--debug",        action="store_true", help="In thêm thông tin debug")
    parser.add_argument("--refresh-prices", action="store_true", help="Xóa raw_prices.csv cũ và lấy lại giá mới")
    parser.add_argument("--config",       type=str, default="configs/config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)

    if args.all:
        sectors = list(cfg["sectors"].keys())
    elif args.sector:
        sectors = [args.sector.upper()]
    else:
        print("Cần chỉ định --sector hoặc --all")
        print("Ví dụ: python main.py --sector BANKING")
        sys.exit(1)

    for sector in sectors:
        if sector not in cfg["sectors"]:
            print(f"  ✗ Sector '{sector}' không có trong config. Bỏ qua.")
            continue
        try:
            run_sector(sector, cfg, skip_collect=args.skip_collect, debug=args.debug, refresh_prices=args.refresh_prices)
        except Exception as e:
            print(f"\n  ✗ Lỗi sector {sector}: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
            continue

    print("\n✅ Pipeline hoàn tất!")


if __name__ == "__main__":
    main()
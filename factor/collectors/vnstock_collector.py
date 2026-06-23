"""
collectors/vnstock_collector.py
================================
Lấy dữ liệu tài chính và giá cổ phiếu từ vnstock API.

Cách dùng độc lập:
    python collectors/vnstock_collector.py

Hoặc được gọi từ main.py.

Rate limit (Community account):
    - 60 requests/phút
    - Mỗi ticker cần 3 calls (balance, income, cashflow)
    - Logic: delay 1.5s mỗi call, nghỉ 65s sau mỗi 20 calls
"""

import time
import pandas as pd
from pathlib import Path
from typing import Optional


# ======================================================================
# FINANCIAL COLLECTOR — lấy báo cáo tài chính (long format)
# ======================================================================

class VnStockFinancialCollector:
    """
    Lấy balance sheet, income statement, cash flow từ vnstock.

    vnstock trả về LONG FORMAT:
      - Mỗi dòng = 1 chỉ tiêu tài chính
      - Mỗi cột = 1 kỳ (năm hoặc quý)
      - 3 cột định danh: item, item_en, item_id

    Raw data được lưu dưới dạng CSV:
      data/{sector}/raw_{ticker}_balance.csv
      data/{sector}/raw_{ticker}_income.csv
      data/{sector}/raw_{ticker}_cashflow.csv
    """

    def __init__(
        self,
        source: str = "VCI",
        delay_each_call: float = 1.5,
        batch_size: int = 20,
        batch_pause: float = 65.0,
        max_retries: int = 3,
        retry_delay: float = 10.0,
    ):
        self.source          = source
        self.delay_each_call = delay_each_call
        self.batch_size      = batch_size
        self.batch_pause     = batch_pause
        self.max_retries     = max_retries
        self.retry_delay     = retry_delay
        self._call_count     = 0   # đếm tổng số API calls trong session

    # ------------------------------------------------------------------
    # PUBLIC: collect toàn bộ sector
    # ------------------------------------------------------------------

    def collect_sector(
        self,
        tickers: list,
        output_dir: str,
        period: str = "year",
        skip_existing: bool = True,
    ) -> dict:
        """
        Lấy báo cáo tài chính cho tất cả tickers trong sector.

        Parameters
        ----------
        tickers       : ['VCB', 'BID', ...]
        output_dir    : thư mục lưu raw CSV, vd 'data/banking'
        period        : 'year' hoặc 'quarter'
        skip_existing : bỏ qua ticker đã có đủ 3 file raw

        Returns
        -------
        dict: {ticker: {'balance': df, 'income': df, 'cashflow': df}}
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        results = {}
        failed  = []

        print(f"\n{'='*60}")
        print(f"  Thu thập tài chính: {len(tickers)} tickers → {output_dir}")
        print(f"  Period: {period} | Source: {self.source}")
        print(f"{'='*60}")

        for i, ticker in enumerate(tickers, 1):
            print(f"\n[{i}/{len(tickers)}] {ticker}")

            # Kiểm tra skip
            if skip_existing and self._has_raw_files(ticker, output_dir):
                print(f"  ↷ Đã có raw files, bỏ qua")
                results[ticker] = self._load_raw_files(ticker, output_dir)
                continue

            ticker_data = self._collect_one_ticker(ticker, output_dir, period)

            if ticker_data is not None:
                results[ticker] = ticker_data
            else:
                failed.append(ticker)

        # Summary
        print(f"\n{'='*60}")
        print(f"  ✔ Thành công: {len(results)}/{len(tickers)} tickers")
        if failed:
            print(f"  ✗ Thất bại:  {failed}")
        print(f"  Tổng API calls: {self._call_count}")
        print(f"{'='*60}\n")

        return results

    # ------------------------------------------------------------------
    # PRIVATE: collect 1 ticker
    # ------------------------------------------------------------------

    def _collect_one_ticker(
        self,
        ticker: str,
        output_dir: str,
        period: str,
    ) -> Optional[dict]:
        """
        Lấy 3 báo cáo cho 1 ticker, lưu raw CSV.
        Trả về dict hoặc None nếu toàn bộ 3 bảng đều lỗi.
        """
        try:
            from vnstock import Vnstock
        except ImportError:
            raise ImportError("vnstock chưa được cài. Chạy: pip install vnstock")

        stock = Vnstock().stock(symbol=ticker, source=self.source)
        ticker_data = {}

        statements = [
            ("balance",  stock.finance.balance_sheet),
            ("income",   stock.finance.income_statement),
            ("cashflow", stock.finance.cash_flow),
        ]

        for name, fetch_fn in statements:
            df = self._fetch_with_retry(fetch_fn, period=period, ticker=ticker, name=name)

            if df is not None and not df.empty:
                # Chuẩn hoá: đảm bảo luôn có 3 cột định danh
                df = self._normalize_columns(df)
                # Lưu raw CSV
                out_path = Path(output_dir) / f"raw_{ticker}_{name}.csv"
                df.to_csv(out_path, index=False, encoding="utf-8-sig")
                ticker_data[name] = df
                print(f"  ✔ {name:10s}: {df.shape[0]} items × {df.shape[1]-3} periods → {out_path.name}")
            else:
                print(f"  ✗ {name:10s}: không có dữ liệu")
                ticker_data[name] = None

        # Trả về None chỉ khi cả 3 bảng đều fail
        if all(v is None for v in ticker_data.values()):
            return None
        return ticker_data

    # ------------------------------------------------------------------
    # PRIVATE: fetch với retry + rate limit
    # ------------------------------------------------------------------

    def _fetch_with_retry(self, fetch_fn, period: str, ticker: str, name: str):
        """
        Gọi API với retry logic và rate limit handling.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                # Rate limit: nghỉ sau mỗi batch_size calls
                self._call_count += 1
                if self._call_count > 1 and (self._call_count - 1) % self.batch_size == 0:
                    print(f"\n  ⏸  Đã {self._call_count - 1} calls — nghỉ {self.batch_pause}s...")
                    time.sleep(self.batch_pause)

                df = fetch_fn(period=period)

                # Delay bình thường sau mỗi call
                time.sleep(self.delay_each_call)

                return df

            except Exception as e:
                err_msg = str(e)
                if attempt < self.max_retries:
                    print(f"  ⚠ {name} attempt {attempt}/{self.max_retries}: {err_msg[:80]}")
                    print(f"     Thử lại sau {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                else:
                    print(f"  ✗ {name}: thất bại sau {self.max_retries} lần — {err_msg[:80]}")
                    return None

        return None

    # ------------------------------------------------------------------
    # PRIVATE: helpers
    # ------------------------------------------------------------------

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Đảm bảo DataFrame có đúng 3 cột định danh: item, item_en, item_id.
        Chuẩn hoá tên cột nếu vnstock thay đổi format.
        """
        # Map tên cột có thể khác nhau giữa các version vnstock
        col_aliases = {
            "name":    "item",
            "name_en": "item_en",
            "id":      "item_id",
        }
        df = df.rename(columns=col_aliases)

        # Đảm bảo 3 cột định danh tồn tại
        for required in ["item", "item_en", "item_id"]:
            if required not in df.columns:
                df[required] = ""

        return df

    def _has_raw_files(self, ticker: str, output_dir: str) -> bool:
        """Kiểm tra đủ 3 file raw cho ticker."""
        for name in ["balance", "income", "cashflow"]:
            if not (Path(output_dir) / f"raw_{ticker}_{name}.csv").exists():
                return False
        return True

    def _load_raw_files(self, ticker: str, output_dir: str) -> dict:
        """Load raw files đã có từ disk."""
        data = {}
        for name in ["balance", "income", "cashflow"]:
            path = Path(output_dir) / f"raw_{ticker}_{name}.csv"
            try:
                data[name] = pd.read_csv(path, encoding="utf-8-sig")
            except Exception:
                data[name] = None
        return data


# ======================================================================
# PRICE COLLECTOR — giữ nguyên logic từ v2
# ======================================================================

class VnStockPriceCollector:
    """
    Lấy giá cổ phiếu daily từ vnstock.
    Output: data/{sector}/raw_prices.csv

    Không thay đổi so với v2 — chỉ đổi tên class cho nhất quán.
    """

    def __init__(self, source: str = "VCI", delay_between_tickers: float = 0.5):
        self.source = source
        self.delay  = delay_between_tickers

    def collect_sector(
        self,
        tickers: list,
        start_date: str,
        end_date: str,
        output_dir: str,
        skip_existing: bool = True,
    ) -> pd.DataFrame:
        """
        Lấy daily OHLCV cho tất cả tickers, lưu raw_prices.csv.

        Parameters
        ----------
        tickers     : ['VCB', 'BID', ...]
        start_date  : '2020-01-01'
        end_date    : '2024-12-31'
        output_dir  : thư mục lưu, vd 'data/banking'
        skip_existing: bỏ qua nếu raw_prices.csv đã tồn tại
        """
        out_path = Path(output_dir) / "raw_prices.csv"

        if skip_existing and out_path.exists():
            print(f"  ↷ raw_prices.csv đã có, bỏ qua")
            return pd.read_csv(out_path, encoding="utf-8-sig")

        try:
            from vnstock import Vnstock
        except ImportError:
            raise ImportError("vnstock chưa được cài. Chạy: pip install vnstock")

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        all_data = []
        failed   = []

        print(f"\n  Thu thập giá: {len(tickers)} tickers ({start_date} → {end_date})")

        for ticker in tickers:
            print(f"  → {ticker}...", end=" ", flush=True)
            try:
                stock = Vnstock().stock(symbol=ticker, source=self.source)
                df = stock.quote.history(
                    start=start_date,
                    end=end_date,
                    interval="1D",
                )

                if df is None or df.empty:
                    print("⚠ không có dữ liệu")
                    failed.append(ticker)
                    continue

                df.columns = [c.lower().strip() for c in df.columns]
                df["ticker"] = ticker
                all_data.append(df)
                print(f"✔ {len(df)} ngày")

            except Exception as e:
                print(f"✗ {str(e)[:60]}")
                failed.append(ticker)

            time.sleep(self.delay)

        if not all_data:
            raise ValueError(f"Không lấy được giá cho bất kỳ ticker nào: {tickers}")

        combined = pd.concat(all_data, ignore_index=True)
        combined.to_csv(out_path, index=False, encoding="utf-8-sig")

        print(f"\n  ✔ Tổng {len(combined)} rows → {out_path}")
        if failed:
            print(f"  ⚠ Thất bại: {failed}")

        return combined
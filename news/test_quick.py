from quant_engine import load_gold_factors
import os

# base_dir phải là thư mục chứa news/ (= thư mục của utils.py khi chạy thật)
# Khi uvicorn chạy api.py từ news/, BASE_DIR = C:\Code\DA\Stock\news
base_dir = os.path.dirname(os.path.abspath(__file__))  # = .../news/
print(f"base_dir: {base_dir}")

root_dir = os.path.dirname(base_dir)  # = C:\Code\DA\Stock
print(f"root_dir (tính trong code): {root_dir}")
print(f"Đường dẫn thử: {os.path.join(root_dir, 'factor', 'outputs', 'technology', 'technology_factor_results.csv')}")

factors = load_gold_factors('FPT', base_dir)
print(f"Factors: {factors}")
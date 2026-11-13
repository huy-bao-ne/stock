"""
test_cache_debug.py
=====================
Kiểm tra cache hoạt động độc lập, không qua Groq API.
Chạy: python test_cache_debug.py
"""
import os
from agents.financial_agent import SimpleCache

cache_path = "data/agent_cache.json"
print(f"Cache file path: {os.path.abspath(cache_path)}")
print(f"File tồn tại trước test: {os.path.exists(cache_path)}")

c = SimpleCache(cache_path)
c.set("FPT hiện tại có nên mua không?", "Đây là câu trả lời test để kiểm tra cache")

print(f"File tồn tại sau khi set: {os.path.exists(cache_path)}")
if os.path.exists(cache_path):
    with open(cache_path, encoding="utf-8") as f:
        print("Nội dung file:")
        print(f.read())

result = c.get("FPT hiện tại có nên mua không?")
print(f"\nGet lại: {result}")
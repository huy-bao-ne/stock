"""
test_news_connection.py
========================
Test kết nối tới News Agent server và verify response format.
Đặt file này trong thư mục factor/ rồi chạy:

    set NEWS_AGENT_URL=http://localhost:8000
    python test_news_connection.py
"""

import os
import json
import urllib.request
import urllib.error

NEWS_URL = os.environ.get("NEWS_AGENT_URL", "http://localhost:8000")
ENDPOINT = f"{NEWS_URL}/api/ask_agent"

print("=" * 60)
print(f"NEWS_AGENT_URL : {NEWS_URL}")
print(f"Endpoint       : {ENDPOINT}")
print("=" * 60)

payload = json.dumps({
    "prompt":  "FPT hiện tại có nên mua không?",
    "history": [],
}).encode("utf-8")

try:
    req = urllib.request.Request(
        ENDPOINT,
        data    = payload,
        headers = {"Content-Type": "application/json"},
        method  = "POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    print(f"\n✔ Kết nối thành công (HTTP 200)")
    print(f"\n--- RESPONSE KEYS ---")
    print(list(data.keys()))

    print(f"\n--- KIỂM TRA FIELDS QUAN TRỌNG ---")

    # ai_analysis
    ai = data.get("ai_analysis", "")
    print(f"✔ ai_analysis      : {len(ai)} ký tự")
    print(f"  Preview          : {ai[:120]}...")

    # affected_factors
    af = data.get("affected_factors")
    if af is not None:
        print(f"✔ affected_factors : {af}")
    else:
        print(f"✗ affected_factors : THIẾU — bên factor/ không ghép được correlation")

    # direction
    d = data.get("direction")
    if d is not None:
        print(f"✔ direction        : {d}")
    else:
        print(f"✗ direction        : THIẾU")

    print(f"✔ symbol           : {data.get('symbol', 'THIẾU')}")
    print(f"✔ status           : {data.get('status', 'THIẾU')}")

    print(f"\n--- FULL RESPONSE (2000 ký tự đầu) ---")
    print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])

except urllib.error.HTTPError as e:
    print(f"\n✗ HTTP Error {e.code}: {e.reason}")
    print(f"  Body: {e.read().decode('utf-8', errors='ignore')[:500]}")

except urllib.error.URLError as e:
    print(f"\n✗ Không kết nối được: {e.reason}")
    print(f"  → Server có đang chạy không?")
    print(f"  → Đúng port chưa? (mặc định 8000)")

except Exception as e:
    print(f"\n✗ Lỗi: {type(e).__name__}: {e}")
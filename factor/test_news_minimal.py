"""
test_news_minimal.py
=====================
Test endpoint với câu hỏi đơn giản + in full traceback từ server.
Đặt trong thư mục factor/ và chạy:
    python test_news_minimal.py
"""
import os, json, urllib.request, urllib.error

URL = os.environ.get("NEWS_AGENT_URL", "http://localhost:8000")

# Test 1: Health check
print("=== TEST 1: Health check ===")
try:
    with urllib.request.urlopen(f"{URL}/docs", timeout=5) as r:
        print(f"✔ Server up, /docs = {r.status}")
except Exception as e:
    print(f"Server status: {e}")

# Test 2: Gọi với ticker rõ ràng, prompt ngắn
print("\n=== TEST 2: Gọi /api/ask_agent ===")
payload = json.dumps({"prompt": "FPT", "history": []}).encode()
try:
    req = urllib.request.Request(
        f"{URL}/api/ask_agent",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode())
    print(f"Response keys: {list(data.keys())}")
    print(f"Status: {data.get('status')}")
    print(f"Message: {data.get('message', '')[:300]}")
    print(f"affected_factors: {data.get('affected_factors')}")
    print(f"direction: {data.get('direction')}")
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8', errors='ignore')
    print(f"HTTP {e.code}: {body[:500]}")
except Exception as e:
    print(f"Lỗi: {type(e).__name__}: {e}")
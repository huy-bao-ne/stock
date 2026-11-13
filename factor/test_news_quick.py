"""Test nhanh News Agent đang trả về gì cho câu hỏi dự báo."""
import os, json, urllib.request

URL = os.environ.get("NEWS_AGENT_URL", "http://localhost:8000")
payload = json.dumps({"prompt": "FPT hiện tại có nên mua không?", "history": []}).encode()

req = urllib.request.Request(
    f"{URL}/api/ask_agent", data=payload,
    headers={"Content-Type": "application/json"}, method="POST",
)
with urllib.request.urlopen(req, timeout=60) as r:
    data = json.loads(r.read().decode())

print(json.dumps(data, ensure_ascii=False, indent=2))
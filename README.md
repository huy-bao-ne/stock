# VNSTOCK Factor AI — Định lượng Tài chính & AI Copilot

Hệ thống phân tích nhân tố tài chính định lượng (Spearman Rank Correlation & Bonferroni Correction) kết hợp AI Copilot (Groq / Llama 3.3 70B) cho 50 cổ phiếu thuộc 10 ngành kinh tế lớn tại Việt Nam giai đoạn 2018–2024.

---

## 🚀 1. Giao diện Web App Hiện đại (Next.js + Vercel 24/7)

Web App mới với giao diện Fintech sang trọng, mượt mà và chạy độc lập 24/7 trên Vercel:

### Chạy thử nghiệm Local:
```bash
cd web
npm run dev
```
Truy cập trình duyệt: [http://localhost:3000](http://localhost:3000)

### Triển khai lên Vercel:
Xem chi tiết tại hướng dẫn: [DEPLOY_VERCEL.md](file:///c:/Users/chien/Downloads/Stock-main/DEPLOY_VERCEL.md)
* **Cách 1 (GitHub)**: Import repo trên Vercel, chọn **Root Directory: `web`**, thêm `GROQ_API_KEY` và bấm **Deploy**.
* **Cách 2 (CLI)**: Chạy `cd web && npx vercel --prod`.

---

## 📊 2. Các Tính năng Cốt lõi trên Web App

1. **🌐 Tổng quan 10 ngành kinh tế**: So sánh số lượng nhân tố có ý nghĩa thống kê sau kiểm định Bonferroni, bảng lọc và xếp hạng sức mạnh tương quan.
2. **🔍 Chi tiết ngành**: Biểu đồ tương quan Spearman trực quan (xanh lá = đồng biến, đỏ = nghịch biến), bảng tra cứu p-value và ngưỡng sai số khắt khe.
3. **🏢 Tra cứu Ticker (50 mã cổ phiếu)**: Biểu đồ tỷ suất sinh lời hàng năm (2018–2024), biểu đồ xu hướng đa chỉ số (ROA, ROE, Biên LN, Nợ...) và bảng BCTC thô.
4. **🤖 AI Financial Copilot**: Chatbot định lượng thông minh sử dụng model Llama 3.3 70B qua Groq API, nạp sẵn context dữ liệu thực tế từ dự án, trả lời chính xác và phân tích chuyên sâu.

---

## 🛠️ 3. Chạy giao diện cũ (Streamlit & Python Backend)

Nếu bạn vẫn muốn chạy phiên bản Streamlit cục bộ:

```bash
# Bật venv và chạy backend tin tức (news)
cd news
uvicorn api:app --host 0.0.0.0 --port 8000

# Mở terminal thứ 2 để chạy Streamlit UI
set GROQ_API_KEY=gsk_...
set NEWS_AGENT_URL=http://localhost:8000
streamlit run factor/ui/app.py
```

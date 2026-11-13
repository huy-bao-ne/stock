# Hướng dẫn Triển khai Web App lên Vercel (24/7 Miễn phí)

Web App mới của bạn được xây dựng trên nền tảng **Next.js 14 + Tailwind CSS + Lucide Icons + Recharts**, tích hợp **Serverless AI Copilot (Groq / Llama 3.3 70B)**. 

Toàn bộ ứng dụng nằm trong thư mục [`web/`](file:///c:/Users/chien/Downloads/Stock-main/web), sẵn sàng deploy lên Vercel mà **không cần thuê VPS hay bật máy tính cá nhân 24/7**.

---

## Cách 1: Deploy qua GitHub & Vercel Dashboard (Khuyên dùng nhất ⭐)

Đây là cách phổ biến và ổn định nhất, mỗi khi bạn push code lên GitHub thì Vercel sẽ tự động cập nhật web app.

### Bước 1: Đẩy mã nguồn lên GitHub
Nếu bạn chưa đưa project lên GitHub, mở terminal tại thư mục gốc và chạy:
```bash
git add .
git commit -m "feat: add modern Next.js Fintech dashboard and Vercel support"
git push origin main
```

### Bước 2: Import vào Vercel
1. Truy cập [vercel.com](https://vercel.com) và đăng nhập (bằng tài khoản GitHub).
2. Bấm nút **"Add New..."** -> Chọn **"Project"**.
3. Tìm repository của bạn và bấm **"Import"**.

### Bước 3: Cấu hình Project trên Vercel
1. Tại phần **Root Directory**:
   - Bấm nút **"Edit"** -> Chọn thư mục **`web`** -> Bấm **"Continue"**.
2. Tại phần **Environment Variables**:
   - Thêm biến:
     - **Key**: `GROQ_API_KEY`
     - **Value**: API Key của bạn (ví dụ `gsk_...`) lấy miễn phí tại [console.groq.com](https://console.groq.com/keys).
     *(Lưu ý: Nếu không điền, hệ thống đã có sẵn fallback key để ứng dụng vẫn hoạt động ngay).*
3. Bấm **"Deploy"**.

Chỉ sau khoảng 1 phút, Vercel sẽ cấp cho bạn một đường link chính thức dạng:
👉 **`https://ten-du-an-cua-ban.vercel.app`**

Bất kỳ ai (bạn bè, đồng nghiệp, nhà tuyển dụng) cũng có thể truy cập bằng điện thoại hoặc máy tính để trải nghiệm ngay lập tức!

---

## Cách 2: Deploy trực tiếp bằng lệnh Vercel CLI (Nhanh chóng)

Nếu bạn muốn deploy ngay từ máy tính mà không cần qua GitHub:

1. Mở terminal và chuyển vào thư mục `web`:
   ```bash
   cd web
   ```
2. Chạy lệnh deploy:
   ```bash
   npx vercel
   ```
3. Đăng nhập Vercel (theo hướng dẫn trên màn hình) và trả lời các câu hỏi:
   - `Set up and deploy?` -> Gõ `y`
   - `Which scope do you want to deploy to?` -> Chọn tài khoản của bạn (Enter)
   - `Link to existing project?` -> Gõ `n`
   - `What's your project's name?` -> Nhập tên (ví dụ: `vnstock-factor-ai`)
   - `In which directory is your code located?` -> Giữ nguyên `./` (Enter)
4. Để deploy phiên bản chính thức (Production), chạy tiếp:
   ```bash
   npx vercel --prod
   ```

---

## Cách chạy thử nghiệm trên máy tính cá nhân (Local Dev)

Trước khi gửi cho người khác, bạn có thể tự mình mở xem trước trên máy:

```bash
cd web
npm run dev
```
Mở trình duyệt truy cập: [http://localhost:3000](http://localhost:3000)

---

## Các tính năng nổi bật trên Web App mới:
1. 🌐 **Tổng quan 10 ngành kinh tế**: KPI cards, biểu đồ so sánh nhân tố đạt chuẩn Bonferroni, bảng lọc và tìm kiếm ngành thông minh.
2. 🔍 **Chi tiết ngành (Deep Dive)**: Biểu đồ thanh tương quan Spearman (xanh lá = đồng biến, đỏ = nghịch biến), bảng phân tích chi tiết p-value và Bonferroni threshold.
3. 🏢 **Tra cứu Ticker (50 mã cổ phiếu)**: Tỷ suất sinh lời theo từng năm, biểu đồ đường so sánh đa chỉ số tài chính (ROA, ROE, Nợ...), bảng BCTC thô.
4. 🤖 **AI Financial Copilot**: Chatbot thông minh dùng Groq Llama 3.3 70B, có sẵn câu hỏi mẫu, trả lời số liệu chính xác từ dự án, hỗ trợ cài đặt API Key cá nhân.

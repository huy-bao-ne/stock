import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VNSTOCK Factor AI — Phân tích Định lượng & AI Copilot",
  description: "Hệ thống phân tích nhân tố tài chính định lượng Spearman & Bonferroni kết hợp AI Copilot Llama 3.3 cho 50 cổ phiếu hàng đầu Việt Nam 2018–2024.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" className="dark">
      <body className="min-h-screen bg-[#0B0F19] text-gray-100 antialiased selection:bg-teal-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}

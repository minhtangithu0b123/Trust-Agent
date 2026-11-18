import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trust Agent — Tra cứu pháp luật",
  description:
    "Tra cứu văn bản pháp luật Việt Nam trong dữ liệu hiện có, với điều khoản và căn cứ được hiển thị khi tìm thấy nguồn phù hợp.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}

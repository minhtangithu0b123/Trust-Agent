import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trust Agent — Tra cứu pháp luật",
  description: "Tra cứu pháp luật Việt Nam với câu trả lời có dẫn nguồn.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}

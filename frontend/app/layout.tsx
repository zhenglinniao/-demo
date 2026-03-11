import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Chat Minimal",
  description: "Minimal AI chat UI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI 小说转剧本工具",
  description: "基于大语言模型的小说自动转剧本工具",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased" style={{ colorScheme: "light" }}>
      <body style={{ background: "#faf7f0", color: "#2c2416" }} className="min-h-full flex flex-col">
        {children}
      </body>
    </html>
  );
}

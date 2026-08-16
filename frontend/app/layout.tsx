import type { Metadata } from "next";
import Nav from "../components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI 学习助手",
  description: "个人 AI 学习助手：上传资料、RAG 问答、自动总结、自动出题、错题本",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full">
        <Nav />
        <main className="lg:pl-52">
          <div className="mx-auto min-h-screen max-w-4xl px-4 py-6 pb-24 lg:px-8 lg:py-8 lg:pb-12">
            {children}
          </div>
        </main>
      </body>
    </html>
  );
}

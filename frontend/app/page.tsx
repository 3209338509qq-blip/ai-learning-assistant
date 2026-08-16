"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { formatTime } from "../lib/format";
import type { AppSettings, DocumentItem } from "../lib/types";
import { Card, StatusBadge } from "../components/ui";

const QUICK_ENTRIES = [
  { href: "/chat", title: "AI 对话", desc: "基于资料问答", icon: "💬", tone: "bg-indigo-50" },
  { href: "/summary", title: "自动总结", desc: "章节要点提炼", icon: "📝", tone: "bg-sky-50" },
  { href: "/quiz", title: "练习", desc: "自动出题判分", icon: "✏️", tone: "bg-emerald-50" },
  { href: "/wrong-questions", title: "错题本", desc: "复习巩固", icon: "📖", tone: "bg-amber-50" },
];

export default function HomePage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getSettings(), api.listDocuments()])
      .then(([s, d]) => {
        setSettings(s);
        setDocs(d.slice(0, 5));
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  const readyCount = docs.filter((d) => d.status === "ready").length;
  const hasReady = readyCount > 0;
  const aiReady = settings?.chat_configured && settings?.embedding_configured;

  return (
    <div>
      <div className="mb-6 rounded-2xl bg-gradient-to-br from-indigo-600 to-indigo-500 px-6 py-7 text-white">
        <h1 className="text-xl font-semibold">👋 欢迎回来</h1>
        <p className="mt-1.5 text-sm text-indigo-100">
          {hasReady
            ? `知识库中有 ${readyCount} 份资料（${settings?.chunk_count ?? 0} 个知识块），可以直接开始学习`
            : "上传学习资料，建立你的个人知识库"}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {hasReady ? (
            <Link
              href="/chat"
              className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50"
            >
              开始提问 →
            </Link>
          ) : (
            <Link
              href="/library"
              className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50"
            >
              上传资料 →
            </Link>
          )}
          {!aiReady && (
            <span className="rounded-lg bg-white/15 px-4 py-2 text-sm text-indigo-100">
              ⚠️ 尚未配置 AI 服务，前往设置页查看
            </span>
          )}
        </div>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "学习资料", value: settings?.document_count ?? 0 },
          { label: "知识块", value: settings?.chunk_count ?? 0 },
          { label: "错题", value: settings?.wrong_question_count ?? 0 },
          { label: "AI 服务", value: aiReady ? "已配置" : "未配置" },
        ].map((s) => (
          <Card key={s.label} className="p-4">
            <p className="text-xs text-zinc-400">{s.label}</p>
            <p className={`mt-1 text-xl font-semibold ${
              s.label === "AI 服务" ? (aiReady ? "text-emerald-600" : "text-amber-600") : "text-zinc-900"
            }`}>
              {s.value}
            </p>
          </Card>
        ))}
      </div>

      <h2 className="mb-3 text-sm font-semibold text-zinc-700">快速开始</h2>
      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {QUICK_ENTRIES.map((e) => (
          <Link key={e.href} href={e.href}>
            <Card className={`p-4 transition-colors hover:border-indigo-300 hover:bg-indigo-50/40 ${e.tone}`}>
              <div className="text-2xl">{e.icon}</div>
              <p className="mt-2 text-sm font-medium text-zinc-900">{e.title}</p>
              <p className="mt-0.5 text-xs text-zinc-500">{e.desc}</p>
            </Card>
          </Link>
        ))}
      </div>

      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-700">最近资料</h2>
        <Link href="/library" className="text-xs text-indigo-600 hover:underline">查看全部</Link>
      </div>
      {loading ? (
        <p className="text-sm text-zinc-400">加载中…</p>
      ) : docs.length === 0 ? (
        <Card className="text-sm text-zinc-400">暂无资料，去上传你的第一份学习资料吧</Card>
      ) : (
        <div className="space-y-2">
          {docs.map((d) => (
            <Card key={d.id} className="flex items-center gap-3 p-3.5">
              <span className="text-lg">{d.file_type === "pdf" ? "📕" : d.file_type === "docx" ? "📘" : "📄"}</span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-zinc-800">{d.original_name}</p>
                <p className="text-xs text-zinc-400">{formatTime(d.created_at)}</p>
              </div>
              <StatusBadge status={d.status} />
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

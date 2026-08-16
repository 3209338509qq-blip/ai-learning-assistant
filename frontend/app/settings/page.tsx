"use client";

import { useEffect, useState } from "react";
import { Badge, Card, ErrorNote, PageHeader } from "../../components/ui";
import { api } from "../../lib/api";
import type { AppSettings } from "../../lib/types";

function Row({ label, value, tone }: { label: string; value: string; tone?: "ok" | "warn" }) {
  return (
    <div className="flex items-center justify-between py-2.5">
      <span className="text-sm text-zinc-500">{label}</span>
      <span className={`text-sm font-medium ${
        tone === "ok" ? "text-emerald-600" : tone === "warn" ? "text-amber-600" : "text-zinc-800"
      }`}>{value}</span>
    </div>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getSettings().then(setSettings).catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
  }, []);

  const aiReady = settings?.chat_configured && settings?.embedding_configured;

  return (
    <div>
      <PageHeader title="设置" desc="查看 AI 服务与知识库状态" />

      <ErrorNote message={error} />

      <Card className="mb-5">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-900">AI 服务</h2>
          <Badge tone={aiReady ? "green" : "amber"}>{aiReady ? "已配置" : "未配置"}</Badge>
        </div>
        <div className="divide-y divide-zinc-100">
          <Row label="Provider" value={settings?.ai_provider ?? "-"} />
          <Row label="对话模型" value={settings?.chat_model ?? "-"} tone={settings?.chat_configured ? "ok" : "warn"} />
          <Row label="Embedding 模型" value={settings?.embedding_model ?? "-"} tone={settings?.embedding_configured ? "ok" : "warn"} />
        </div>
        {!aiReady && (
          <div className="mt-3 rounded-lg bg-amber-50 px-4 py-3 text-xs leading-relaxed text-amber-700">
            <p className="font-medium">配置方法：</p>
            <p className="mt-1">
              1. 将项目根目录的 <code>.env.example</code> 复制为 <code>.env</code>
              <br />
              2. 填入 <code>AI_API_KEY</code>（对话）与 <code>EMBEDDING_API_KEY</code>（向量化，DeepSeek 官方无 embedding，可用硅基流动等兼容服务）
              <br />
              3. 重启后端：<code>python -m uvicorn app.main:app --port 8000</code>（在 backend 目录下）
            </p>
          </div>
        )}
      </Card>

      <Card className="mb-5">
        <h2 className="mb-2 text-sm font-semibold text-zinc-900">知识库</h2>
        <div className="divide-y divide-zinc-100">
          <Row label="学习资料" value={`${settings?.document_count ?? 0} 份`} />
          <Row label="知识块" value={`${settings?.chunk_count ?? 0} 个`} />
          <Row label="错题" value={`${settings?.wrong_question_count ?? 0} 道`} />
        </div>
      </Card>

      <Card>
        <h2 className="mb-2 text-sm font-semibold text-zinc-900">数据存储</h2>
        <p className="text-sm leading-relaxed text-zinc-500">
          所有数据仅存储在本机：SQLite 数据库（资料/会话/错题）+ Chroma 向量库（知识块）+ 原始文件。
          删除资料会同步清理对应的向量与文件。备份时复制 <code>backend/data/</code> 目录即可。
        </p>
      </Card>
    </div>
  );
}

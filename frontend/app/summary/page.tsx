"use client";

import { useState } from "react";
import DocumentPicker from "../../components/DocumentPicker";
import { Button, Card, ErrorNote, PageHeader, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { formatTime } from "../../lib/format";
import type { Summary } from "../../lib/types";

function Section({ title, text }: { title: string; text: string }) {
  if (!text) return null;
  return (
    <div>
      <h3 className="mb-1.5 text-sm font-semibold text-zinc-900">{title}</h3>
      <div className="whitespace-pre-wrap rounded-lg bg-zinc-50 px-3.5 py-3 text-sm leading-relaxed text-zinc-700">
        {text}
      </div>
    </div>
  );
}

export default function SummaryPage() {
  const [pick, setPick] = useState<{ documentId: number | null; chapterPath: string }>({
    documentId: null,
    chapterPath: "",
  });
  const [result, setResult] = useState<Summary | null>(null);
  const [history, setHistory] = useState<Summary[]>([]);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [showHistory, setShowHistory] = useState(false);

  async function generate() {
    if (!pick.documentId) {
      setError("请先选择学习资料");
      return;
    }
    setGenerating(true);
    setError("");
    setResult(null);
    try {
      const s = await api.generateSummary(pick.documentId, pick.chapterPath);
      setResult(s);
      api.listSummaries(pick.documentId).then(setHistory).catch(() => undefined);
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setGenerating(false);
    }
  }

  function loadHistory() {
    if (!pick.documentId) return;
    setShowHistory(true);
    api.listSummaries(pick.documentId).then(setHistory).catch(() => setHistory([]));
  }

  return (
    <div>
      <PageHeader title="自动总结" desc="选择资料或章节，AI 生成核心知识点、重点概念、易错点与记忆要点" />

      <Card className="mb-6">
        <DocumentPicker value={pick} onChange={setPick} />
        <div className="mt-4 flex items-center gap-2">
          <Button onClick={generate} disabled={generating || !pick.documentId}>
            {generating ? <Spinner className="h-4 w-4" /> : "✨ 生成总结"}
          </Button>
          <Button variant="secondary" onClick={loadHistory} disabled={!pick.documentId}>
            查看历史总结
          </Button>
        </div>
        <div className="mt-3"><ErrorNote message={error} /></div>
      </Card>

      {generating && (
        <Card className="flex items-center gap-3 text-sm text-zinc-500">
          <Spinner /> AI 正在阅读资料并整理总结…
        </Card>
      )}

      {result && (
        <Card className="space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
            <h2 className="text-sm font-semibold text-zinc-900">{result.title}</h2>
            <span className="text-xs text-zinc-400">{formatTime(result.created_at)}</span>
          </div>
          <Section title="📌 核心知识点" text={result.core_points} />
          <Section title="🔑 重点概念" text={result.key_concepts} />
          <Section title="⚠️ 易错点" text={result.pitfalls} />
          <Section title="🧠 需要记忆的内容" text={result.memory_items} />
          <Section title="✍️ 简短总结" text={result.short_summary} />
        </Card>
      )}

      {showHistory && (
        <div className="mt-6">
          <h2 className="mb-3 text-sm font-semibold text-zinc-700">历史总结</h2>
          {history.length === 0 ? (
            <p className="text-sm text-zinc-400">还没有生成过总结</p>
          ) : (
            <div className="space-y-2">
              {history.map((s) => (
                <button
                  key={s.id}
                  className="w-full rounded-lg border border-zinc-200 bg-white px-4 py-3 text-left text-sm text-zinc-700 hover:bg-zinc-50"
                  onClick={() => setResult(s)}
                >
                  <span className="font-medium">{s.title}</span>
                  <span className="ml-2 text-xs text-zinc-400">{formatTime(s.created_at)}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

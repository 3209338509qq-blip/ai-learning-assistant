"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";
import { formatBytes, formatTime } from "../../lib/format";
import type { DocumentItem } from "../../lib/types";
import { Button, Card, EmptyState, ErrorNote, PageHeader, Spinner, StatusBadge } from "../../components/ui";

const ACCEPT = ".pdf,.docx,.md,.txt";

export default function LibraryPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [chaptersMap, setChaptersMap] = useState<Record<number, DocumentItem["chapters"]>>({});
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      const list = await api.listDocuments();
      setDocs(list);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  const [hasPending, setHasPending] = useState(false);

  useEffect(() => {
    setHasPending(docs.some((d) => d.status === "pending" || d.status === "processing"));
  }, [docs]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // 有资料在处理中时轮询状态
  useEffect(() => {
    if (!hasPending) return;
    const timer = setInterval(refresh, 2000);
    return () => clearInterval(timer);
  }, [hasPending, refresh]);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0 || uploading) return;
    setUploading(true);
    setError("");
    try {
      for (const file of Array.from(files)) {
        await api.uploadDocument(file);
      }
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "上传失败");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function toggleChapters(id: number) {
    const next = expanded === id ? null : id;
    setExpanded(next);
    if (next !== null && !chaptersMap[id]) {
      try {
        const detail = await api.getDocument(id);
        setChaptersMap((prev) => ({ ...prev, [id]: detail.chapters }));
      } catch {
        setChaptersMap((prev) => ({ ...prev, [id]: [] }));
      }
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("确定删除这份资料吗？知识库中的相关内容也会一并删除。")) return;
    try {
      await api.deleteDocument(id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  }

  return (
    <div>
      <PageHeader title="学习资料" desc="上传 PDF / Word / Markdown / TXT，系统会自动解析并建立知识库" />

      <div
        className={`mb-6 flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
          dragOver ? "border-indigo-500 bg-indigo-50" : "border-zinc-300 bg-white"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          accept={ACCEPT}
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <div className="text-3xl">{uploading ? <Spinner className="h-8 w-8" /> : "📥"}</div>
        <p className="mt-3 text-sm font-medium text-zinc-700">
          {uploading ? "正在上传…" : "拖拽文件到这里，或点击选择文件"}
        </p>
        <p className="mt-1 text-xs text-zinc-400">支持 PDF、DOCX、Markdown、TXT，可多选</p>
      </div>

      <ErrorNote message={error} />

      <div className="mt-5 space-y-3">
        {loading ? (
          <div className="flex justify-center py-10"><Spinner /></div>
        ) : docs.length === 0 ? (
          <EmptyState title="还没有资料" desc="上传第一份学习资料，开始建立你的知识库" />
        ) : (
          docs.map((doc) => (
            <Card key={doc.id} className="p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-zinc-100 text-lg">
                  {doc.file_type === "pdf" ? "📕" : doc.file_type === "docx" ? "📘" : "📄"}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-medium text-zinc-900">{doc.original_name}</span>
                    <StatusBadge status={doc.status} />
                  </div>
                  <div className="mt-0.5 text-xs text-zinc-400">
                    {formatBytes(doc.size_bytes)}
                    {doc.page_count > 0 && ` · ${doc.page_count} 页`}
                    {doc.status === "ready" && ` · ${doc.chunk_count} 个知识块`}
                    {` · ${formatTime(doc.created_at)}`}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <Button variant="secondary" className="px-2.5 py-1.5" onClick={() => toggleChapters(doc.id)}>
                    {expanded === doc.id ? "收起" : "章节"}
                  </Button>
                  <Button variant="danger" className="px-2.5 py-1.5" onClick={() => handleDelete(doc.id)}>
                    删除
                  </Button>
                </div>
              </div>
              {doc.status === "failed" && (
                <p className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">处理失败：{doc.error}</p>
              )}
              {expanded === doc.id && (
                <div className="mt-3 border-t border-zinc-100 pt-3">
                  <p className="mb-2 text-xs font-medium text-zinc-500">章节结构</p>
                  {(chaptersMap[doc.id] ?? doc.chapters ?? []).length === 0 ? (
                    <p className="text-xs text-zinc-400">未识别到章节（按全文处理）</p>
                  ) : (
                    <ul className="space-y-1">
                      {(chaptersMap[doc.id] ?? doc.chapters ?? []).map((c) => (
                        <li key={c.id} className="flex items-center gap-2 text-xs text-zinc-600">
                          <span style={{ marginLeft: (c.level - 1) * 12 }}>▸</span>
                          <span className="truncate">{c.path}</span>
                          {c.page > 0 && <span className="text-zinc-400">第 {c.page} 页</span>}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
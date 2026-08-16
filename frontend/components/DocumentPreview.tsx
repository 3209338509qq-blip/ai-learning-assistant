"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { DocumentContent } from "../lib/api";
import { Spinner } from "./ui";

export default function DocumentPreview({
  documentId,
  title,
  onClose,
}: {
  documentId: number;
  title: string;
  onClose: () => void;
}) {
  const [content, setContent] = useState<DocumentContent | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getDocumentContent(documentId)
      .then(setContent)
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
  }, [documentId]);

  // ESC 关闭
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  function scrollTo(path: string) {
    document.getElementById(`sec-${path}`)?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="flex h-[85vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between border-b border-zinc-200 px-5 py-3">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-zinc-900">{title}</h2>
            {content && (
              <p className="mt-0.5 text-xs text-zinc-400">
                {content.file_type.toUpperCase()} · {content.sections.length} 个章节
                {content.page_count > 0 && ` · ${content.page_count} 页`}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
            aria-label="关闭预览"
          >
            ✕
          </button>
        </div>

        {/* 正文区 */}
        <div className="flex min-h-0 flex-1">
          {/* 章节导航（桌面） */}
          {content && content.sections.length > 1 && (
            <aside className="hidden w-56 shrink-0 overflow-y-auto border-r border-zinc-100 p-3 md:block">
              <p className="mb-2 text-xs font-medium text-zinc-400">目录</p>
              <div className="space-y-0.5">
                {content.sections.map((s) => (
                  <button
                    key={s.path}
                    onClick={() => scrollTo(s.path)}
                    className="block w-full truncate rounded px-2 py-1 text-left text-xs text-zinc-600 hover:bg-zinc-100"
                    style={{ paddingLeft: 8 + Math.min(s.path.split(" / ").length - 1, 4) * 10 }}
                  >
                    {s.path}
                  </button>
                ))}
              </div>
            </aside>
          )}

          {/* 正文 */}
          <div className="min-w-0 flex-1 overflow-y-auto p-6">
            {!content && !error && (
              <div className="flex justify-center py-16">
                <Spinner />
              </div>
            )}
            {error && <p className="text-sm text-red-500">{error}</p>}
            {content && (
              <div className="space-y-6">
                {content.sections.map((s) => (
                  <section key={s.path} id={`sec-${s.path}`} className="scroll-mt-4">
                    <div className="mb-2 flex items-center gap-2">
                      <h3 className="text-sm font-semibold text-zinc-900">{s.path}</h3>
                      {s.page > 0 && (
                        <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] text-zinc-500">
                          第 {s.page} 页
                        </span>
                      )}
                    </div>
                    <div className="whitespace-pre-wrap rounded-lg bg-zinc-50 px-4 py-3 text-sm leading-relaxed text-zinc-700">
                      {s.text}
                    </div>
                  </section>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

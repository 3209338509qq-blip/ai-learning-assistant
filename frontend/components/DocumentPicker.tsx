"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { DocumentItem } from "../lib/types";

/**
 * 资料 + 章节选择器（总结/练习页共用）。
 * value: { documentId, chapterPath }，chapterPath="" 表示全文。
 */
export default function DocumentPicker({
  value,
  onChange,
}: {
  value: { documentId: number | null; chapterPath: string };
  onChange: (v: { documentId: number | null; chapterPath: string }) => void;
}) {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api
      .listDocuments()
      .then((list) => {
        setDocs(list.filter((d) => d.status === "ready"));
      })
      .catch(() => setDocs([]))
      .finally(() => setLoaded(true));
  }, []);

  const doc = docs.find((d) => d.id === value.documentId);

  // 已选文档被删除/失效时清空选择，避免提交过期 id
  useEffect(() => {
    if (value.documentId !== null && !doc && !docs.some((x) => x.id === value.documentId)) {
      onChange({ documentId: null, chapterPath: "" });
    }
  }, [docs, value.documentId, doc, onChange]);

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div>
        <label className="mb-1 block text-sm font-medium text-zinc-700">学习资料</label>
        <select
          className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-indigo-500 focus:outline-none"
          value={value.documentId ?? ""}
          onChange={(e) => {
            const id = e.target.value ? Number(e.target.value) : null;
            onChange({ documentId: id, chapterPath: "" });
          }}
        >
          <option value="">{loaded ? "（无已就绪的资料）" : "加载中…"}</option>
          {docs.map((d) => (
            <option key={d.id} value={d.id}>
              {d.original_name}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-zinc-700">范围（章节）</label>
        <select
          className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-indigo-500 focus:outline-none disabled:opacity-50"
          value={value.chapterPath}
          disabled={!doc}
          onChange={(e) => onChange({ ...value, chapterPath: e.target.value })}
        >
          <option value="">全文</option>
          {(doc?.chapters ?? []).map((c) => (
            <option key={c.id} value={c.path}>
              {c.path}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
"use client";

import { useEffect, useRef, useState } from "react";
import { api, streamChat } from "../../lib/api";
import { formatTime } from "../../lib/format";
import type { Conversation, Message, SourceRef } from "../../lib/types";
import { Button, ErrorNote, Spinner } from "../../components/ui";

interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
  sources: SourceRef[];
}

function SourceCard({ source }: { source: SourceRef }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50">
      <button
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs text-zinc-600"
        onClick={() => setOpen(!open)}
      >
        <span className="truncate font-medium text-indigo-700">📄 {source.document_name}</span>
        <span className="shrink-0 text-zinc-400">
          {source.chapter}
          {source.page > 0 && ` · 第 ${source.page} 页`}
        </span>
      </button>
      {open && (
        <p className="border-t border-zinc-200 px-3 py-2 text-xs leading-relaxed text-zinc-500">
          {source.excerpt}
        </p>
      )}
    </div>
  );
}

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentId, setCurrentId] = useState<number | null>(null);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.listConversations().then(setConversations).catch(() => setConversations([]));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function openConversation(id: number) {
    if (sending) return;
    setCurrentId(id);
    setError("");
    try {
      const hist = await api.getConversation(id);
      setMessages(
        hist.messages.map((m) => ({
          role: m.role,
          content: m.content,
          sources: m.sources ?? [],
        }))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载会话失败");
    }
  }

  async function newConversation() {
    if (sending) return;
    setCurrentId(null);
    setMessages([]);
    setError("");
  }

  async function send() {
    const text = input.trim();
    if (!text || sending) return;
    const targetConvId = currentId; // 记录目标会话，防止竞态
    setInput("");
    setError("");
    // 一次追加：用户消息 + 空的助手消息（流式内容累积到它上面）
    const aiIndex = messages.length + 1;
    setMessages((prev) => [
      ...prev,
      { role: "user", content: text, sources: [] },
      { role: "assistant", content: "", sources: [] },
    ]);
    setSending(true);
    try {
      await streamChat(text, targetConvId, {
        onDelta: (delta) => {
          setMessages((prev) =>
            prev.map((m, i) => (i === aiIndex ? { ...m, content: m.content + delta } : m))
          );
        },
        onDone: ({ conversation_id, sources }) => {
          setMessages((prev) =>
            prev.map((m, i) => (i === aiIndex ? { ...m, sources } : m))
          );
          setCurrentId(conversation_id);
          api.listConversations().then(setConversations).catch(() => undefined);
        },
        onError: (msg) => setError(msg),
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "发送失败");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-[calc(100dvh-12.5rem)] flex-col lg:h-[calc(100dvh-4rem)]">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900">AI 对话</h1>
          <p className="mt-1 text-sm text-zinc-500">优先基于你的学习资料回答，引用会标注来源</p>
        </div>
        <Button variant="secondary" onClick={newConversation} disabled={sending}>新对话</Button>
      </div>

      {/* 会话列表（移动端横向滚动） */}
      {conversations.length > 0 && (
        <div className="mb-3 flex gap-2 overflow-x-auto pb-1 md:hidden">
          <button
            onClick={newConversation}
            disabled={sending}
            className={`shrink-0 rounded-full border px-3 py-1.5 text-xs ${
              currentId === null ? "border-indigo-600 bg-indigo-600 text-white" : "border-zinc-300 text-zinc-600"
            }`}
          >
            + 新对话
          </button>
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => openConversation(c.id)}
              disabled={sending}
              className={`max-w-40 shrink-0 truncate rounded-full border px-3 py-1.5 text-xs ${
                currentId === c.id ? "border-indigo-600 bg-indigo-600 text-white" : "border-zinc-300 bg-white text-zinc-600"
              }`}
            >
              {c.title}
            </button>
          ))}
        </div>
      )}

      <div className="flex min-h-0 flex-1 gap-4">
        {/* 会话列表（桌面侧栏） */}
        {conversations.length > 0 && (
          <aside className="hidden w-48 shrink-0 flex-col space-y-1 overflow-y-auto rounded-xl border border-zinc-200 bg-white p-2 md:flex">
            {conversations.map((c) => (
              <button
                key={c.id}
                onClick={() => openConversation(c.id)}
                disabled={sending}
                className={`truncate rounded-lg px-3 py-2 text-left text-sm ${
                  currentId === c.id ? "bg-indigo-50 font-medium text-indigo-700" : "text-zinc-600 hover:bg-zinc-100"
                }`}
              >
                {c.title}
              </button>
            ))}
          </aside>
        )}

        {/* 消息区 */}
        <div className="flex min-w-0 flex-1 flex-col rounded-xl border border-zinc-200 bg-white">
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            {messages.length === 0 && !sending && (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <div className="text-4xl">💬</div>
                <p className="mt-3 text-sm font-medium text-zinc-600">向你的知识库提问</p>
                <p className="mt-1 max-w-xs text-xs text-zinc-400">
                  例如：解释一下 Python 中的装饰器？回答会注明来自哪份资料、哪一章、哪一页
                </p>
              </div>
            )}
            {messages.map((m, i) => {
              const isStreaming = sending && i === messages.length - 1 && m.role === "assistant";
              return (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[85%] space-y-2 ${m.role === "user" ? "" : "w-full"}`}>
                    <div
                      className={`whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                        m.role === "user"
                          ? "rounded-br-md bg-indigo-600 text-white"
                          : "rounded-bl-md border border-zinc-200 bg-zinc-50 text-zinc-800"
                      }`}
                    >
                      {m.content}
                      {isStreaming && m.content === "" && (
                        <span className="inline-flex items-center gap-2 text-zinc-400">
                          <Spinner className="h-4 w-4" /> 正在思考…
                        </span>
                      )}
                      {isStreaming && m.content !== "" && (
                        <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-indigo-500 align-middle" />
                      )}
                    </div>
                    {m.role === "assistant" && m.sources.length > 0 && (
                      <div className="space-y-1.5 pl-1">
                        <p className="text-[11px] text-zinc-400">来源引用（点击展开摘录）</p>
                        {m.sources.map((s, j) => (
                          <SourceCard key={j} source={s} />
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            <div ref={bottomRef} />
          </div>

          <div className="border-t border-zinc-200 p-3">
            <ErrorNote message={error} />
            <div className="mt-2 flex items-end gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  // isComposing: 中文输入法选词回车不发送
                  if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                    e.preventDefault();
                    send();
                  }
                }}
                rows={1}
                placeholder="输入问题，Enter 发送，Shift+Enter 换行"
                className="max-h-32 min-h-[44px] flex-1 resize-y rounded-lg border border-zinc-300 px-3 py-2.5 text-sm focus:border-indigo-500 focus:outline-none"
              />
              <Button onClick={send} disabled={sending || !input.trim()}>
                发送
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Card, EmptyState, ErrorNote, PageHeader, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import { formatTime } from "../../lib/format";
import type { WrongQuestion } from "../../lib/types";

const TYPE_LABELS: Record<string, string> = {
  choice: "选择题",
  true_false: "判断题",
  short_answer: "简答题",
};

export default function WrongQuestionsPage() {
  const [items, setItems] = useState<WrongQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [practicing, setPracticing] = useState<WrongQuestion | null>(null);
  const [practiceAnswer, setPracticeAnswer] = useState("");
  const [practiceFeedback, setPracticeFeedback] = useState<"correct" | "wrong" | null>(null);

  const refresh = useCallback(async () => {
    try {
      setItems(await api.listWrongQuestions());
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function remove(id: number) {
    if (!confirm("确定删除这道错题吗？")) return;
    try {
      await api.deleteWrongQuestion(id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  }

  function startPractice(wq: WrongQuestion) {
    setPracticing(wq);
    setPracticeAnswer("");
    setPracticeFeedback(null);
  }

  const [practicingBusy, setPracticingBusy] = useState(false);

  async function finishPractice(isCorrect: boolean) {
    if (!practicing || practicingBusy) return;
    setPracticingBusy(true);
    setPracticeFeedback(isCorrect ? "correct" : "wrong");
    try {
      await api.redoWrongQuestion(practicing.id, isCorrect);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "提交失败");
    } finally {
      setPracticingBusy(false);
    }
  }

  return (
    <div>
      <PageHeader title="错题本" desc="做错的题自动收录，可重新练习巩固" />

      <ErrorNote message={error} />

      {!practicing && (
        <>
          {loading ? (
            <div className="flex justify-center py-10"><Spinner /></div>
          ) : items.length === 0 ? (
            <EmptyState title="暂无错题" desc="做题时答错的题目会自动出现在这里" />
          ) : (
            <div className="space-y-3">
              {items.map((wq) => (
                <Card key={wq.id} className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-zinc-800">
                        {wq.question}
                        <Badge tone="zinc">{TYPE_LABELS[wq.qtype] ?? wq.qtype}</Badge>
                        {wq.difficulty === "hard" && <Badge tone="red">难</Badge>}
                      </p>
                      <p className="mt-2 text-sm">
                        <span className="text-red-500">你的答案：{wq.my_answer || "未作答"}</span>
                        <span className="mx-2 text-zinc-300">|</span>
                        <span className="text-emerald-600">正确答案：{wq.correct_answer}</span>
                      </p>
                      {wq.explanation && (
                        <p className="mt-1.5 text-xs text-zinc-500">解析：{wq.explanation}</p>
                      )}
                      <p className="mt-1.5 text-xs text-zinc-400">
                        {wq.knowledge_point && `知识点：${wq.knowledge_point} · `}
                        {wq.chapter && `章节：${wq.chapter} · `}
                        错 {wq.wrong_count} 次 · {formatTime(wq.last_wrong_at)}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-col gap-1.5">
                      <Button variant="secondary" className="px-2.5 py-1.5" onClick={() => startPractice(wq)}>
                        重新练习
                      </Button>
                      <Button variant="ghost" className="px-2.5 py-1.5 text-xs" onClick={() => remove(wq.id)}>
                        删除
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {practicing && (
        <Card className="space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
            <h2 className="text-sm font-semibold text-zinc-900">重新练习</h2>
            <button className="text-xs text-zinc-400 hover:text-zinc-600" onClick={() => setPracticing(null)}>
              ← 返回列表
            </button>
          </div>
          <p className="text-sm font-medium text-zinc-800">{practicing.question}</p>

          {practicing.qtype === "choice" && (
            <div className="grid gap-2 sm:grid-cols-2">
              {practicing.options.map((opt) => (
                <button
                  key={opt}
                  onClick={() => setPracticeAnswer(opt.split(".")[0].trim())}
                  className={`rounded-lg border px-3 py-2 text-left text-sm ${
                    practiceAnswer === opt.split(".")[0].trim()
                      ? "border-indigo-600 bg-indigo-50 text-indigo-800"
                      : "border-zinc-200 text-zinc-700 hover:bg-zinc-50"
                  }`}
                >
                  {opt}
                </button>
              ))}
            </div>
          )}
          {practicing.qtype === "true_false" && (
            <div className="flex gap-2">
              {["正确", "错误"].map((opt) => (
                <button
                  key={opt}
                  onClick={() => setPracticeAnswer(opt)}
                  className={`rounded-lg border px-5 py-2 text-sm ${
                    practiceAnswer === opt
                      ? "border-indigo-600 bg-indigo-50 text-indigo-800"
                      : "border-zinc-200 text-zinc-700 hover:bg-zinc-50"
                  }`}
                >
                  {opt}
                </button>
              ))}
            </div>
          )}
          {practicing.qtype === "short_answer" && (
            <textarea
              value={practiceAnswer}
              onChange={(e) => setPracticeAnswer(e.target.value)}
              rows={3}
              placeholder="写下你的答案…"
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm"
            />
          )}

          {practiceFeedback === null ? (
            <div className="flex flex-wrap items-center gap-2">
              {practicing.qtype === "short_answer" && (
                <span className="w-full rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
                  参考答案：{practicing.correct_answer}
                </span>
              )}
              <Button variant="secondary" onClick={() => finishPractice(true)} disabled={!practiceAnswer.trim() || practicingBusy}>
                ✓ 答对了
              </Button>
              <Button variant="danger" onClick={() => finishPractice(false)} disabled={!practiceAnswer.trim() || practicingBusy}>
                ✗ 答错了
              </Button>
            </div>
          ) : (
            <div className="rounded-lg bg-zinc-50 px-4 py-3 text-sm">
              {practiceFeedback === "correct" ? (
                <p className="text-emerald-600">🎉 答对了！这道错题已从错题本移除。</p>
              ) : (
                <p className="text-red-500">
                  还需巩固，错误次数已 +1。正确答案：{practicing.correct_answer}
                  {practicing.explanation && (
                    <span className="mt-1 block text-xs text-zinc-500">解析：{practicing.explanation}</span>
                  )}
                </p>
              )}
              <button className="mt-3 text-xs font-medium text-indigo-600 hover:underline" onClick={() => setPracticing(null)}>
                返回错题列表
              </button>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
"use client";

import { useState } from "react";
import DocumentPicker from "../../components/DocumentPicker";
import { Badge, Button, Card, ErrorNote, PageHeader, Spinner } from "../../components/ui";
import { api } from "../../lib/api";
import type { Question, QuizResult, QuizSet } from "../../lib/types";

const TYPE_LABELS: Record<string, string> = {
  choice: "选择题",
  true_false: "判断题",
  short_answer: "简答题",
};

interface AnswerState {
  [questionId: number]: { user_answer: string; self_evaluated?: boolean | null };
}

export default function QuizPage() {
  const [pick, setPick] = useState<{ documentId: number | null; chapterPath: string }>({
    documentId: null,
    chapterPath: "",
  });
  const [types, setTypes] = useState<string[]>(["choice", "true_false", "short_answer"]);
  const [count, setCount] = useState(5);
  const [quiz, setQuiz] = useState<QuizSet | null>(null);
  const [answers, setAnswers] = useState<AnswerState>({});
  const [result, setResult] = useState<QuizResult | null>(null);
  const [generating, setGenerating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function generate() {
    if (!pick.documentId) {
      setError("请先选择学习资料");
      return;
    }
    if (types.length === 0) {
      setError("请至少选择一种题型");
      return;
    }
    setGenerating(true);
    setError("");
    setQuiz(null);
    setResult(null);
    setAnswers({});
    try {
      const q = await api.generateQuiz(pick.documentId, pick.chapterPath, count, types);
      if (q.questions.length === 0) setError("生成题目为空，请重试");
      setQuiz(q);
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setGenerating(false);
    }
  }

  function setAnswer(qid: number, user_answer: string, self_evaluated?: boolean | null) {
    setAnswers((prev) => ({ ...prev, [qid]: { user_answer, self_evaluated } }));
  }

  async function submit() {
    if (!quiz) return;
    setSubmitting(true);
    setError("");
    try {
      const payload = quiz.questions.map((q) => {
        const a = answers[q.id];
        if (!a) return { question_id: q.id, user_answer: "", self_evaluated: null };
        return { question_id: q.id, user_answer: a.user_answer, self_evaluated: a.self_evaluated };
      });
      const r = await api.submitQuiz(quiz.id, payload);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  const answeredCount = quiz
    ? quiz.questions.filter((q) => {
        const a = answers[q.id];
        if (q.qtype === "short_answer") return a && a.self_evaluated != null;
        return a && a.user_answer !== "";
      }).length
    : 0;

  return (
    <div>
      <PageHeader title="练习" desc="根据资料自动出题：选择、判断、简答，做完自动判分并记录错题" />

      <Card className="mb-6">
        <DocumentPicker value={pick} onChange={setPick} />
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-700">题型</label>
            <div className="flex flex-wrap gap-2">
              {Object.entries(TYPE_LABELS).map(([k, v]) => (
                <button
                  key={k}
                  onClick={() =>
                    setTypes((prev) => (prev.includes(k) ? prev.filter((t) => t !== k) : [...prev, k]))
                  }
                  className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                    types.includes(k)
                      ? "border-indigo-600 bg-indigo-600 text-white"
                      : "border-zinc-300 text-zinc-600 hover:bg-zinc-50"
                  }`}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-700">题目数量</label>
            <select
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm"
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
            >
              {[3, 5, 10, 15].map((n) => (
                <option key={n} value={n}>{n} 题</option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-4">
          <Button onClick={generate} disabled={generating || !pick.documentId}>
            {generating ? <Spinner className="h-4 w-4" /> : "📝 生成练习"}
          </Button>
        </div>
        <div className="mt-3"><ErrorNote message={error} /></div>
      </Card>

      {generating && (
        <Card className="flex items-center gap-3 text-sm text-zinc-500">
          <Spinner /> AI 正在根据资料出题…
        </Card>
      )}

      {quiz && !result && (
        <Card className="space-y-6">
          <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
            <h2 className="text-sm font-semibold text-zinc-900">{quiz.title}</h2>
            <Badge tone="blue">
              已答 {answeredCount}/{quiz.questions.length}
            </Badge>
          </div>

          {quiz.questions.map((q, idx) => (
            <QuestionBlock
              key={q.id}
              q={q}
              index={idx}
              answer={answers[q.id]}
              onChange={setAnswer}
            />
          ))}

          <div className="border-t border-zinc-100 pt-4">
            <Button onClick={submit} disabled={submitting || answeredCount < quiz.questions.length} className="w-full sm:w-auto">
              {submitting ? <Spinner className="h-4 w-4" /> : "提交判分"}
            </Button>
            {answeredCount < quiz.questions.length && (
              <p className="mt-2 text-xs text-zinc-400">简答题需先对照参考答案自评，全部作答后才能提交</p>
            )}
          </div>
        </Card>
      )}

      {quiz && result && (
        <Card className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-100 pb-4">
            <div>
              <p className="text-sm text-zinc-500">得分</p>
              <p className={`text-3xl font-bold ${result.score >= 60 ? "text-emerald-600" : "text-red-500"}`}>
                {result.score}
                <span className="text-base font-normal text-zinc-400"> / 100</span>
              </p>
              <p className="mt-1 text-xs text-zinc-400">
                答对 {result.correct_count}/{result.total_count} · 新增错题 {result.wrong_question_count} 道
              </p>
            </div>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => setResult(null)}>查看详情</Button>
              <Button onClick={generate}>再出一套</Button>
            </div>
          </div>
          {quiz.questions.map((q, idx) => {
            const r = result.results.find((x) => x.question_id === q.id);
            return (
              <div key={q.id} className={`rounded-lg border p-4 ${
                r?.is_correct ? "border-emerald-200 bg-emerald-50/40" : "border-red-200 bg-red-50/40"
              }`}>
                <p className="text-sm font-medium text-zinc-800">
                  {idx + 1}. {q.question}
                  {r && (
                    <Badge tone={r.is_correct ? "green" : "red"}>
                      {r.is_correct ? "✓ 正确" : "✗ 错误"}
                    </Badge>
                  )}
                </p>
                {q.qtype === "choice" && (
                  <p className="mt-2 text-sm text-zinc-600">你的答案：{r?.user_answer || "未作答"}</p>
                )}
                {q.qtype === "true_false" && (
                  <p className="mt-2 text-sm text-zinc-600">你的答案：{r?.user_answer || "未作答"}</p>
                )}
                {q.qtype === "short_answer" && (
                  <p className="mt-2 whitespace-pre-wrap text-sm text-zinc-600">你的答案：{r?.user_answer || "未作答"}</p>
                )}
                <p className="mt-1.5 text-sm">
                  <span className="font-medium text-emerald-700">正确答案：{q.answer}</span>
                </p>
                {q.explanation && (
                  <p className="mt-2 rounded bg-white/70 px-3 py-2 text-xs leading-relaxed text-zinc-500">
                    解析：{q.explanation}
                  </p>
                )}
                {q.knowledge_point && (
                  <p className="mt-1.5 text-xs text-zinc-400">知识点：{q.knowledge_point}</p>
                )}
              </div>
            );
          })}
        </Card>
      )}
    </div>
  );
}

function QuestionBlock({
  q,
  index,
  answer,
  onChange,
}: {
  q: Question;
  index: number;
  answer: { user_answer: string; self_evaluated?: boolean | null } | undefined;
  onChange: (qid: number, user_answer: string, self_evaluated?: boolean | null) => void;
}) {
  return (
    <div>
      <p className="text-sm font-medium text-zinc-800">
        {index + 1}. {q.question}
        <Badge tone="zinc">{TYPE_LABELS[q.qtype] ?? q.qtype}</Badge>
        {q.difficulty === "hard" && <Badge tone="red">难</Badge>}
        {q.difficulty === "easy" && <Badge tone="blue">易</Badge>}
      </p>
      {q.qtype === "choice" && (
        <div className="mt-2.5 grid gap-2 sm:grid-cols-2">
          {q.options.map((opt) => (
            <button
              key={opt}
              onClick={() => onChange(q.id, opt.split(".")[0].trim())}
              className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                answer?.user_answer === opt.split(".")[0].trim()
                  ? "border-indigo-600 bg-indigo-50 text-indigo-800"
                  : "border-zinc-200 text-zinc-700 hover:bg-zinc-50"
              }`}
            >
              {opt}
            </button>
          ))}
        </div>
      )}
      {q.qtype === "true_false" && (
        <div className="mt-2.5 flex gap-2">
          {["正确", "错误"].map((opt) => (
            <button
              key={opt}
              onClick={() => onChange(q.id, opt)}
              className={`rounded-lg border px-5 py-2 text-sm transition-colors ${
                answer?.user_answer === opt
                  ? "border-indigo-600 bg-indigo-50 text-indigo-800"
                  : "border-zinc-200 text-zinc-700 hover:bg-zinc-50"
              }`}
            >
              {opt}
            </button>
          ))}
        </div>
      )}
      {q.qtype === "short_answer" && (
        <div className="mt-2.5 space-y-2">
          <textarea
            value={answer?.user_answer ?? ""}
            onChange={(e) => onChange(q.id, e.target.value, answer?.self_evaluated ?? null)}
            rows={3}
            placeholder="写下你的答案…"
            className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          />
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
            <p className="text-xs font-medium text-amber-700">参考答案：{q.answer}</p>
            <p className="mt-1 text-xs text-amber-600">对照参考答案，自评你的作答：</p>
            <div className="mt-1.5 flex gap-2">
              <button
                disabled={!answer?.user_answer?.trim()}
                onClick={() => onChange(q.id, answer?.user_answer ?? "", true)}
                className={`rounded-full px-3.5 py-1 text-xs font-medium transition-colors ${
                  answer?.self_evaluated === true
                    ? "bg-emerald-600 text-white"
                    : "bg-white text-emerald-700 border border-emerald-300"
                }`}
              >
                答对了
              </button>
              <button
                disabled={!answer?.user_answer?.trim()}
                onClick={() => onChange(q.id, answer?.user_answer ?? "", false)}
                className={`rounded-full px-3.5 py-1 text-xs font-medium transition-colors ${
                  answer?.self_evaluated === false
                    ? "bg-red-500 text-white"
                    : "bg-white text-red-600 border border-red-300"
                }`}
              >
                答错了
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
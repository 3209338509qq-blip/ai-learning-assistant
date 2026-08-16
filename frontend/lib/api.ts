// 后端 API 客户端：统一封装 fetch，类型安全
import type {
  AppSettings,
  ChatHistory,
  ChatResponse,
  Conversation,
  DocumentItem,
  QuizResult,
  QuizSet,
  SourceRef,
  Summary,
  WrongQuestion,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* 忽略解析失败 */
    }
    throw new Error(detail);
  }
  return resp.json() as Promise<T>;
}

export const api = {
  // ---- 资料 ----
  uploadDocument(file: File): Promise<DocumentItem> {
    const form = new FormData();
    form.append("file", file);
    return request("/api/documents/upload", { method: "POST", body: form });
  },
  listDocuments(): Promise<DocumentItem[]> {
    return request("/api/documents");
  },
  getDocument(id: number): Promise<DocumentItem> {
    return request(`/api/documents/${id}`);
  },
  deleteDocument(id: number): Promise<{ ok: boolean }> {
    return request(`/api/documents/${id}`, { method: "DELETE" });
  },

  // ---- 对话 ----
  chat(message: string, conversationId?: number): Promise<ChatResponse> {
    return request("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, conversation_id: conversationId ?? null }),
    });
  },
  listConversations(): Promise<Conversation[]> {
    return request("/api/chat/conversations");
  },
  getConversation(id: number): Promise<ChatHistory> {
    return request(`/api/chat/conversations/${id}`);
  },
  deleteConversation(id: number): Promise<{ ok: boolean }> {
    return request(`/api/chat/conversations/${id}`, { method: "DELETE" });
  },

  // ---- 总结 ----
  generateSummary(documentId: number, chapterPath = ""): Promise<Summary> {
    return request("/api/summaries/generate", {
      method: "POST",
      body: JSON.stringify({ document_id: documentId, chapter_path: chapterPath }),
    });
  },
  listSummaries(documentId: number): Promise<Summary[]> {
    return request(`/api/summaries/document/${documentId}`);
  },
  listAllSummaries(): Promise<Summary[]> {
    return request("/api/summaries");
  },

  // ---- 练习 ----
  generateQuiz(
    documentId: number,
    chapterPath: string,
    count: number,
    types: string[]
  ): Promise<QuizSet> {
    return request("/api/quizzes/generate", {
      method: "POST",
      body: JSON.stringify({
        document_id: documentId,
        chapter_path: chapterPath,
        count,
        types,
      }),
    });
  },
  listQuizSets(): Promise<QuizSet[]> {
    return request("/api/quizzes");
  },
  getQuizSet(id: number): Promise<QuizSet> {
    return request(`/api/quizzes/${id}`);
  },
  submitQuiz(
    quizId: number,
    answers: { question_id: number; user_answer: string; self_evaluated?: boolean | null }[]
  ): Promise<QuizResult> {
    return request(`/api/quizzes/${quizId}/submit`, {
      method: "POST",
      body: JSON.stringify({ answers }),
    });
  },

  // ---- 错题本 ----
  listWrongQuestions(): Promise<WrongQuestion[]> {
    return request("/api/wrong-questions");
  },
  deleteWrongQuestion(id: number): Promise<{ ok: boolean }> {
    return request(`/api/wrong-questions/${id}`, { method: "DELETE" });
  },
  redoWrongQuestion(id: number, isCorrect: boolean): Promise<WrongQuestion | null> {
    return request(`/api/wrong-questions/${id}/redo`, {
      method: "POST",
      body: JSON.stringify({ is_correct: isCorrect }),
    });
  },

  // ---- 设置 ----
  getSettings(): Promise<AppSettings> {
    return request("/api/settings");
  },
};

export type { SourceRef };

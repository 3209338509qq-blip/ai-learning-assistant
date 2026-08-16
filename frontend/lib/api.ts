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
  const isFormData = init?.body instanceof FormData;
  const resp = await fetch(`${API_BASE}${path}`, {
    // FormData 由浏览器自动生成 multipart boundary，不能手动指定 Content-Type
    ...init,
    headers: isFormData ? undefined : { "Content-Type": "application/json" },
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
  uploadDocument(file: File, subject = ""): Promise<DocumentItem> {
    const form = new FormData();
    form.append("file", file);
    if (subject) form.append("subject", subject);
    return request("/api/documents/upload", { method: "POST", body: form });
  },
  updateDocumentSubject(id: number, subject: string): Promise<DocumentItem> {
    return request(`/api/documents/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ subject }),
    });
  },
  listSubjects(): Promise<import("./types").SubjectCount[]> {
    return request("/api/documents/subjects");
  },
  listDocuments(): Promise<DocumentItem[]> {
    return request("/api/documents");
  },
  getDocument(id: number): Promise<DocumentItem> {
    return request(`/api/documents/${id}`);
  },
  getDocumentContent(id: number): Promise<DocumentContent> {
    return request(`/api/documents/${id}/content`);
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
  redoWrongQuestion(
    id: number,
    isCorrect: boolean
  ): Promise<{ deleted?: boolean } | WrongQuestion> {
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

export interface DocumentContent {
  document_id: number;
  original_name: string;
  file_type: string;
  page_count: number;
  sections: { path: string; page: number; text: string }[];
}

export interface StreamHandlers {
  onDelta: (text: string) => void;
  onDone: (payload: { conversation_id: number; sources: SourceRef[]; has_evidence: boolean }) => void;
  onError: (message: string) => void;
}

/** SSE 流式对话：逐段回调文本增量。 */
export async function streamChat(
  message: string,
  conversationId: number | null,
  subject: string,
  handlers: StreamHandlers
): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId, subject }),
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
  if (!resp.body) throw new Error("浏览器不支持流式响应");
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const raw = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      for (const line of raw.split("\n")) {
        if (!line.startsWith("data:")) continue;
        try {
          const payload = JSON.parse(line.slice(5).trim());
          if (payload.type === "delta") handlers.onDelta(payload.content ?? "");
          else if (payload.type === "done")
            handlers.onDone({
              conversation_id: payload.conversation_id,
              sources: payload.sources ?? [],
              has_evidence: payload.has_evidence ?? false,
            });
          else if (payload.type === "error") handlers.onError(payload.message ?? "生成失败");
        } catch {
          /* 忽略坏帧 */
        }
      }
    }
  }
}

export type { SourceRef };
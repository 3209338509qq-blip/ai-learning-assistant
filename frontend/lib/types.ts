// 与后端 schemas.py 对应的类型定义

export interface Chapter {
  id: number;
  title: string;
  level: number;
  path: string;
  page: number;
}

export interface DocumentItem {
  id: number;
  original_name: string;
  file_type: string;
  size_bytes: number;
  status: "pending" | "processing" | "ready" | "failed";
  error: string;
  chunk_count: number;
  page_count: number;
  created_at: string;
  updated_at: string;
  chapters?: Chapter[];
}

export interface SourceRef {
  document_id: number;
  document_name: string;
  chapter: string;
  page: number;
  excerpt: string;
}

export interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  sources: SourceRef[];
  created_at: string;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatResponse {
  conversation_id: number;
  message_id: number;
  answer: string;
  sources: SourceRef[];
  has_evidence: boolean;
}

export interface ChatHistory {
  conversation: Conversation;
  messages: Message[];
}

export interface Summary {
  id: number;
  document_id: number;
  chapter_path: string;
  title: string;
  core_points: string;
  key_concepts: string;
  pitfalls: string;
  memory_items: string;
  short_summary: string;
  created_at: string;
}

export type QuestionType = "choice" | "true_false" | "short_answer";

export interface Question {
  id: number;
  qtype: QuestionType;
  question: string;
  options: string[];
  answer: string;
  explanation: string;
  difficulty: "easy" | "medium" | "hard";
  knowledge_point: string;
  chapter: string;
  order_index: number;
}

export interface QuizSet {
  id: number;
  document_id: number;
  chapter_path: string;
  title: string;
  created_at: string;
  questions: Question[];
}

export interface AnswerResult {
  question_id: number;
  user_answer: string;
  is_correct: boolean;
  correct_answer: string;
  explanation: string;
}

export interface QuizResult {
  attempt_id: number;
  correct_count: number;
  total_count: number;
  score: number;
  wrong_question_count: number;
  results: AnswerResult[];
}

export interface WrongQuestion {
  id: number;
  qtype: QuestionType;
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
  difficulty: "easy" | "medium" | "hard";
  knowledge_point: string;
  chapter: string;
  my_answer: string;
  wrong_count: number;
  last_wrong_at: string;
  created_at: string;
}

export interface AppSettings {
  ai_provider: string;
  chat_model: string;
  embedding_model: string;
  chat_configured: boolean;
  embedding_configured: boolean;
  document_count: number;
  chunk_count: number;
  wrong_question_count: number;
}

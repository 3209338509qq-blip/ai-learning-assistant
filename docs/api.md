# API 文档

Base URL: `http://127.0.0.1:8000`（可通过 `BACKEND_HOST` / `BACKEND_PORT` 环境变量修改）

交互式文档（Swagger UI）：`/docs`

## 健康检查

### GET /api/health

返回服务状态。

```json
{"status": "ok"}
```

## 资料管理

### POST /api/documents/upload

上传学习资料（multipart/form-data），返回后**异步**解析建库。

| 参数 | 类型 | 说明 |
|---|---|---|
| file | File | PDF / DOCX / Markdown / TXT |

响应 `DocumentOut`：`{id, original_name, file_type, size_bytes, status, error, chunk_count, page_count, created_at, updated_at}`
（status: pending → ready / failed）

### GET /api/documents

资料列表（按创建时间倒序）。

### GET /api/documents/{id}

资料详情，含 `chapters`（章节树：title/level/path/page）。

### DELETE /api/documents/{id}

删除资料（同步清理向量与原始文件）。

## AI 对话

### POST /api/chat

RAG 问答。

| 参数 | 类型 | 说明 |
|---|---|---|
| message | string | 用户问题（必填） |
| conversation_id | int? | 会话 ID；不传则新建会话 |

响应 `ChatResponse`：`{conversation_id, message_id, answer, sources, has_evidence}`
- `sources`: 引用来源数组 `{document_name, chapter, page, excerpt}`
- `has_evidence`: 知识库是否检索到相关内容；无依据时 answer 为「当前知识库没有找到足够依据。」

### GET /api/chat/conversations

会话列表。

### GET /api/chat/conversations/{id}

会话历史（含消息与来源引用）。

### DELETE /api/chat/conversations/{id}

删除会话。

## 自动总结

### POST /api/summaries/generate

| 参数 | 类型 | 说明 |
|---|---|---|
| document_id | int | 资料 ID（必填，需已处理完成） |
| chapter_path | string | 章节路径；空 = 全文 |

响应 `SummaryOut`：`{id, document_id, chapter_path, title, core_points, key_concepts, pitfalls, memory_items, short_summary, created_at}`

### GET /api/summaries/document/{document_id}

某资料的总结历史。

### DELETE /api/summaries/{id}

删除总结。

## 练习

### POST /api/quizzes/generate

| 参数 | 类型 | 说明 |
|---|---|---|
| document_id | int | 资料 ID（必填） |
| chapter_path | string | 章节；空 = 全文 |
| count | int | 题目数量（1-30，默认 5） |
| types | string[] | 题型：`choice` / `true_false` / `short_answer` |

响应 `QuizSetOut`：`{id, document_id, chapter_path, title, created_at, questions[]}`
题目字段：`{id, qtype, question, options, answer, explanation, difficulty, knowledge_point, chapter}`

### GET /api/quizzes

题组列表。**GET /api/quizzes/{id}**：题组详情。**DELETE /api/quizzes/{id}**：删除题组。

### POST /api/quizzes/{id}/submit

提交作答并判分。

| 参数 | 类型 | 说明 |
|---|---|---|
| answers | array | `{question_id, user_answer, self_evaluated?}`；简答题须提供 `self_evaluated`（true=自评答对，false=答错），不提供则不计分不入错题 |

响应 `QuizResultOut`：`{attempt_id, correct_count, total_count, score, wrong_question_count, results[]}`
（results 含每题的 user_answer / is_correct / correct_answer / explanation）

## 错题本

### GET /api/wrong-questions

错题列表（按最近错误时间倒序）。字段：`{id, qtype, question, options, correct_answer, explanation, difficulty, knowledge_point, chapter, my_answer, wrong_count, last_wrong_at}`

### POST /api/wrong-questions/{id}/redo

重新练习。`{is_correct: boolean}`：答对 → 移除错题；答错 → 错误次数 +1。

### DELETE /api/wrong-questions/{id}

删除错题。

## 设置

### GET /api/settings

运行状态：`{ai_provider, chat_model, embedding_model, chat_configured, embedding_configured, document_count, chunk_count, wrong_question_count}`

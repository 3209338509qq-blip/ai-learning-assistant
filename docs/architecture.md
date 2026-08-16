# 系统架构

## 总体架构

```
┌────────────────────────────────────────────────────────────┐
│                       浏览器（PC / 手机）                    │
│   Next.js 前端（App Router, TypeScript, Tailwind CSS）      │
└──────────────────────────┬─────────────────────────────────┘
                           │ REST API (JSON)
┌──────────────────────────▼─────────────────────────────────┐
│                    FastAPI 后端 (Python)                    │
│                                                            │
│   /api/documents   资料上传/解析/管理                       │
│   /api/chat        RAG 对话（会话历史）                     │
│   /api/summaries   自动总结                                 │
│   /api/quizzes     自动出题 + 判分                          │
│   /api/wrong-questions  错题本                             │
│                                                            │
│   AIService ──► AIProvider（统一接口）                      │
│                    ├─ OpenAICompatibleProvider             │
│                    └─ FakeProvider（测试/演示）             │
│                                                            │
│   VectorStore ──► ChromaDB（持久化向量库）                  │
│   SQLAlchemy ──► SQLite（业务数据）                        │
└────────────────────────────────────────────────────────────┘
```

## 数据流：资料 → 知识库

```
上传文件 (PDF/DOCX/MD/TXT)
  │
  ▼ 解析器（parsers.py）
结构化文本：章节树 + 页码（PDF 页码，DOCX 标题样式，MD 标题层级）
  │
  ▼ 分块（chunker.py，默认 800 字/块，100 字重叠）
Chunk：{ text, chapter(章节路径), page(页码) }
  │
  ▼ Embedding（通过 AIProvider 统一接口）
向量
  │
  ▼ 写入
ChromaDB（持久化，元数据含 document_name/chapter/page）
```

## 数据流：RAG 问答

```
用户问题
  │
  ▼ 向量检索（ChromaDB，top_k=6）
相关片段（含来源元数据）
  │
  ▼ 组装提示词（参考资料 + 引用编号规则）
AIService
  │
  ▼ AIProvider.chat()
回答（带 [1][2] 来源标注；无依据时明确提示）
  │
  ▼ 保存会话（SQLite）＋ 返回来源列表（前端展示引用）
```

## AI Provider 可切换设计

业务代码只依赖 `app/providers/base.py` 的 `AIProvider` 接口：

```python
class AIProvider(ABC):
    def chat(self, messages, temperature) -> str: ...
    def embed(self, texts) -> list[list[float]]: ...
```

通过环境变量切换，**无需修改业务代码**：

| 环境变量 | 说明 |
|---|---|
| `AI_PROVIDER` | `openai_compatible`（默认）/ `fake` |
| `AI_BASE_URL` / `AI_API_KEY` / `AI_CHAT_MODEL` | 对话模型（DeepSeek/MiMo/OpenAI/硅基流动等兼容服务） |
| `EMBEDDING_BASE_URL` / `EMBEDDING_API_KEY` / `EMBEDDING_MODEL` | Embedding（可独立配置，如硅基流动 bge-m3） |

> 注意：DeepSeek 官方 API 不提供 Embedding 端点，因此 Embedding 服务单独配置；
> 留空时复用对话服务的地址与密钥。

## 存储设计

- **SQLite**（`backend/data/app.db`）：资料元数据、章节、会话、总结、题组、题目、作答记录、错题本
- **ChromaDB**（`backend/data/chroma/`）：向量 + 分块文本 + 溯源元数据（document_id / document_name / chapter / page）
- **上传文件**（`backend/data/uploads/`）：原始文件保留，供总结/出题时重新解析

删除资料时：向量 → 上传文件 → 数据库记录 三层同步清理。

## 关键技术决策

| 决策点 | 选择 | 理由 |
|---|---|---|
| 向量库 | ChromaDB（嵌入式） | 无需独立服务，个人项目最简单可靠 |
| PDF 解析 | PyMuPDF | 纯 Python，直接获取页码与字号（可识别标题） |
| DOCX 解析 | python-docx | 读取 Heading 样式还原章节 |
| 分块 | 自研递归分块 | 80 行代码，避免引入 LangChain |
| 异步处理 | FastAPI BackgroundTasks | 个人项目无需 Celery/Redis |
| 简答题判分 | 用户对照答案自评 | 不依赖 AI 判分的可靠性，简单可控 |
| 前端 | Next.js App Router | 按用户技术栈要求 |

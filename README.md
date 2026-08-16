# AI Learning Assistant（AI 学习助手）

> 个人 AI 学习助手：上传学习资料，AI 基于你的资料回答、总结、出题、记录错题。
> 本地优先，资料只属于你。支持手机与电脑。

## ✨ 功能

- **📚 学习资料**：上传 PDF / DOCX / Markdown / TXT，自动解析并保留 **文件名、章节结构、页码**
- **🧠 知识库**：解析 → 分块 → Embedding → 向量库（ChromaDB），检索结果可追溯到原始资料
- **💬 AI 对话**：优先基于你的资料回答，回答标注来源（哪份资料 / 哪一章 / 哪一页）；知识库没有依据时明确提示「当前知识库没有找到足够依据」
- **📝 自动总结**：按文件或章节生成核心知识点、重点概念、易错点、记忆要点、简短总结
- **✏️ 自动出题**：选择题 / 判断题 / 简答题，每道题含答案、解析、难度、知识点、来源章节
- **📖 错题本**：做错自动收录（我的答案 / 正确答案 / 解析 / 知识点 / 时间），支持重新练习
- **🔌 模型可切换**：统一 AIProvider 接口，轻松切换 DeepSeek / MiMo / OpenAI / 硅基流动 / 其他 OpenAI 兼容服务，也支持本地演示模式

## 🛠 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Next.js 16 (App Router) · TypeScript · Tailwind CSS 4 |
| 后端 | Python 3.12 · FastAPI · SQLAlchemy |
| 数据库 | SQLite |
| 向量库 | ChromaDB（嵌入式持久化，无需独立服务） |
| 文档解析 | PyMuPDF（PDF，含页码）· python-docx（DOCX 章节样式） |
| AI | 自研 AIProvider 抽象：OpenAI 兼容 API / Fake（测试演示） |

## 🏗 系统架构

```
浏览器（PC / 手机）
    │ REST API
    ▼
FastAPI 后端 ──► SQLite（资料/会话/总结/题目/错题）
    │            ChromaDB（向量知识库，含来源元数据）
    │
    ├── AIService ──► AIProvider ──► 具体模型（OpenAI 兼容 / Fake）
    ├── 解析器：PDF / DOCX / MD / TXT → 章节树 + 页码
    └── 分块器：800 字/块，100 字重叠，携带章节与页码
```

详细设计见 [docs/architecture.md](docs/architecture.md)。

## 📁 项目结构

```
ai-learning-assistant/
├── frontend/            # Next.js 前端
│   ├── app/             # 页面路由（/ /library /chat /summary /quiz /wrong-questions /settings）
│   ├── components/      # 导航、UI、资料选择器
│   └── lib/             # API client 与类型定义
├── backend/             # FastAPI 后端
│   ├── app/
│   │   ├── api/         # 路由层（documents/chat/summaries/quizzes/wrong-questions/settings）
│   │   ├── services/    # 业务层（解析/分块/向量库/AI 服务）
│   │   ├── providers/   # AI Provider 抽象（base/openai_compat/fake）
│   │   ├── models.py    # SQLAlchemy 模型
│   │   ├── schemas.py   # Pydantic 模型
│   │   ├── config.py    # 环境变量配置
│   │   └── main.py      # 应用入口
│   └── requirements.txt
├── docs/                # 架构文档、API 文档、开发计划
├── tests/               # 后端测试（pytest，28 个用例）
├── .env.example         # 环境变量示例
└── README.md
```

## 🚀 快速开始

### 环境要求

- Node.js 18+（建议 20+）
- Python 3.11+
- Git

### 1. 克隆并安装后端

```bash
git clone <repo-url> && cd ai-learning-assistant

cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env     # 项目根目录
```

编辑 `.env`，填入 AI 服务配置（见下表）。**不配置 API Key 也能跑**：设置 `AI_PROVIDER=fake` 即可体验完整流程（演示回答）。

### 3. 启动后端

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

打开 http://localhost:3000 开始使用。

## 🔑 环境变量说明

| 变量 | 必填 | 说明 |
|---|---|---|
| `AI_PROVIDER` | 否 | `openai_compatible`（默认）或 `fake`（演示/测试） |
| `AI_BASE_URL` | 是* | 对话模型 API 地址，如 `https://api.deepseek.com/v1` |
| `AI_API_KEY` | 是* | 对话模型 API Key（*fake 模式不需要） |
| `AI_CHAT_MODEL` | 是* | 对话模型名，如 `deepseek-chat` |
| `EMBEDDING_BASE_URL` | 否 | Embedding 服务地址，留空复用 `AI_BASE_URL` |
| `EMBEDDING_API_KEY` | 否 | Embedding Key，留空复用 `AI_API_KEY` |
| `EMBEDDING_MODEL` | 否 | Embedding 模型，如 `BAAI/bge-m3`（硅基流动） |
| `DATABASE_PATH` / `CHROMA_PATH` / `UPLOAD_DIR` | 否 | 存储位置（默认在 `backend/data/`） |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` / `RETRIEVAL_TOP_K` | 否 | 分块与检索参数 |

> ⚠️ DeepSeek 官方 API 不提供 Embedding 端点，向量化需另配兼容服务（如硅基流动 `BAAI/bge-m3`）；或者使用同时提供 chat + embedding 的服务（OpenAI、Ollama 等）。

## 📖 使用方法

1. **上传资料**：进入「学习资料」，拖拽或点击上传 PDF/DOCX/MD/TXT，等待状态变为「已就绪」
2. **AI 对话**：进入「AI 对话」，直接提问；回答下方会列出引用来源，点击可查看原文摘录
3. **自动总结**：进入「自动总结」，选择资料（可选章节）→ 生成总结
4. **练习**：进入「练习」，选择资料与题型 → 生成题目 → 作答 → 判分；简答题对照参考答案自评
5. **错题本**：做错的题自动收录，可重新练习（答对移除，答错累计次数）

## 📡 API 文档

完整端点说明见 [docs/api.md](docs/api.md)。启动后端后也可访问交互式文档：

- Swagger UI: http://127.0.0.1:8000/docs
- 健康检查: http://127.0.0.1:8000/api/health

## 🧪 测试

```bash
# 后端测试（无需 API Key，使用 FakeProvider）
cd ai-learning-assistant
.venv/bin/python -m pytest tests/backend -v
```

覆盖：文件上传、PDF/DOCX/Markdown 解析、文本分块、向量检索、RAG 问答、总结、出题、判分、错题保存。

## 📸 截图

`docs/screenshots/`（规划中，将在后续版本补充）

## 🗺 后续计划

- [ ] 前端自动化测试（Vitest + Playwright）
- [ ] 对话流式输出（SSE）
- [ ] 简答题 AI 智能判分（可选开关）
- [ ] 错题本导出（PDF/CSV）与间隔复习提醒
- [ ] 多知识库隔离（按学科/课程分类）
- [ ] 资料全文预览
- [ ] Docker Compose 一键部署

## 📄 License

MIT

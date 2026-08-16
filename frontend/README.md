# frontend

AI 学习助手前端（Next.js 16 + TypeScript + Tailwind CSS 4）。

完整说明见项目根目录 [README.md](../README.md)。

## 开发

```bash
npm install
npm run dev        # http://localhost:3000
```

后端地址默认为 `http://127.0.0.1:8000`，可用环境变量覆盖：

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev
```

## 页面

| 路由 | 说明 |
|---|---|
| / | 首页（统计 + 快速入口） |
| /library | 学习资料（上传/删除/章节查看） |
| /chat | AI 对话（RAG + 来源引用） |
| /summary | 自动总结 |
| /quiz | 练习（出题/作答/判分） |
| /wrong-questions | 错题本（重新练习） |
| /settings | 设置 |

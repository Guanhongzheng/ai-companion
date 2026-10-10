# 架构设计（ARCHITECTURE）

## 1. 总体分层

```text
┌──────────────────────────────────────────────────────────────┐
│  浏览器 (React 18 / Next.js 14 App Router)                    │
│  ┌───────────┬───────────┬───────────┬───────────┬─────────┐ │
│  │ 会话列表  │  对话窗口  │ 情绪主题   │  壁纸/音乐 │ 记忆面板 │ │
│  └───────────┴───────────┴───────────┴───────────┴─────────┘ │
│        Zustand（客户端状态）  │  TanStack Query（服务端状态）    │
└───────────────────────────┬──────────────────────────────────┘
                            │ REST + SSE（fetch stream）
┌───────────────────────────▼──────────────────────────────────┐
│  FastAPI (apps/api)                                           │
│  ┌──────────────┐  ┌──────────────────────────────────────┐  │
│  │ api/v1 路由层 │→ │ services 业务层                       │  │
│  └──────────────┘  └───────┬──────────────────┬───────────┘  │
│                            │                  │              │
│                   ┌────────▼───────┐  ┌───────▼──────────┐   │
│                   │ agents/        │  │ memory/ (RAG)    │   │
│                   │ LangGraph 编排  │  │ chunk→embed→     │   │
│                   │ + MCP tools    │  │ retrieve→rerank  │   │
│                   └────────┬───────┘  └───────┬──────────┘   │
│                            │                  │              │
│                   ┌────────▼──────────────────▼───────────┐  │
│                   │ LiteLLM（统一模型路由 / BYOK）          │  │
│                   └────────┬──────────────────────────────┘  │
└────────────────────────────┼─────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
   云端模型              本地模型            向量库 / 存储
 GPT/Claude/          Ollama / bge-m3     Chroma / Milvus
 DeepSeek/Qwen        Whisper …          SQLite / MinIO
```

## 2. 对话中枢（核心）

三类会话共用一套 `Session` 抽象，靠 `session.type` 分支能力：

| 会话类型 | `type` | 能力 |
| --- | --- | --- |
| AI 伴侣单聊 | `ai` | 全量 Agent：情感分析 + 记忆检索 + 工具调用 + 多模态生成 |
| 好友单聊 | `direct` | AI 仅作旁路辅助：润色 / 翻译 / 总结 / 建议回复 |
| 群聊 | `group` | AI 被 @ 唤醒、自动总结、情绪感知 |

统一消息模型（`packages/shared`）：

```ts
type SenderType = "user" | "ai" | "system";

interface Message {
  id: string;
  sessionId: string;
  senderType: SenderType;
  senderId: string;
  content: string;
  contentType: "text" | "image" | "audio" | "file";
  emotion?: EmotionTag;      // 情绪标签，驱动界面
  createdAt: string;
}
```

## 3. 情绪自适应链路

```text
用户输入（文本/语音/图像）
   └─ 多模态理解（ASR / OCR / 图像理解）
        └─ 情感分析 → EmotionTag
             ├─ 记忆检索（bge-m3 召回 → bge-reranker 重排）
             ├─ 意图识别 → 是否触发工具 / 生成
             ├─ 个性化回应生成（LiteLLM 路由到目标模型）
             └─ 情绪 → 前端 ThemeToken（主题色/壁纸/音乐/动效/布局）
```

前端接收情绪的方式：SSE 事件流中的 `emotion` 事件，落到 `features/theme` 的
`theme-store`，再映射为 CSS 变量与 framer-motion 变体。

## 4. RAG 记忆系统

- **写入**：对话结束后抽取候选记忆 → 去重（相似度过阈值则合并）→ 冲突检测 → 向量化入库
- **读取**：按 session 上下文召回 Top-K → rerank → 注入 prompt
- **管理**：记忆列表可视化，支持编辑、置顶、删除、一键导出/清空
- **隐私**：记忆内容落盘前用 `MEMORY_ENCRYPTION_KEY` 加密；删除即物理清除

## 5. 实时通信

- 首选 **SSE**（单向流式，实现最简单，Next.js 与 FastAPI 都原生友好）
- 群聊多人实时走 **Supabase Realtime** 或 **Socket.io**（`REALTIME_BACKEND` 切换）
- 前端统一封装在 `src/lib/sse-client.ts`，UI 层不直接碰 EventSource

## 6. Agent 与工具

- LangGraph 定义图：`agents/graphs/*.py`，节点在 `agents/nodes/*.py`
- 工具来源：内部函数 + **官方 MCP SDK** 接入的外部工具，注册在 `app/mcp/`
- 所有模型调用统一走 LiteLLM，禁止在业务代码里直接 `openai.ChatCompletion`

## 7. 安全与隐私

- 服务端密钥只存 `.env`，前端只能拿到 `NEXT_PUBLIC_*`（且不含密钥）
- BYOK：用户 Key 仅服务端内存使用，不落盘不写日志
- 输出前做安全过滤（`ENABLE_SAFETY_FILTER`）
- 生产强制 HTTPS/WSS

## 8. 部署拓扑

```text
Vercel / Render 静态 + SSR  →  apps/web
Render / Fly.io / Docker   →  apps/api
PostgreSQL + Chroma/MinIO  →  托管或自建
```

本地开发用 `docker compose up`，生产按需拆分到各平台。

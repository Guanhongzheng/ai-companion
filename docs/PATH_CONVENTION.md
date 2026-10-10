# 路径与命名规范（PATH_CONVENTION）

> 本文件是 ai-companion 仓库的**唯一路径权威**。新增任何文件/目录前先读这里，
> 出现冲突时以本文件为准，并同步更新本文件。

---

## 1. 总原则

1. **按业务域切分，不按文件类型切分**。前端不做 `src/services`、`src/components/chat` 这种全局分散，
   而是 `src/features/<domain>/` 内部自带 `components / hooks / api / types`。
2. **就近放置**（colocation）。只被一个功能用到的组件、类型、hook，就放在那个 feature 里；
   只有被 2 个以上 feature 复用，才提升到 `src/components`、`src/hooks`、`src/types`。
3. **目录名一律 kebab-case**（`user-profile/`，不是 `UserProfile/`、`user_profile/`）。
4. **一个文件一个职责**，文件行数超过 300 行就该考虑拆分。
5. **路径即文档**：从路径就能读出"这是什么层、属于哪个域"。

---

## 2. 命名规则对照表

| 对象 | 规则 | 正例 | 反例 |
| --- | --- | --- | --- |
| 目录 | kebab-case | `chat-window/` | `ChatWindow/`、`chat_window/` |
| React 组件文件 | PascalCase.tsx | `MessageBubble.tsx` | `messageBubble.tsx` |
| 普通 TS 模块 | kebab-case.ts | `use-sse-stream.ts` | `useSseStream.ts` |
| React Hook | `use-<name>.ts` | `use-emotion-theme.ts` | `emotionTheme.ts` |
| Zustand store | `<domain>-store.ts` | `chat-store.ts` | `store1.ts` |
| zod schema | `<name>.schema.ts` | `message.schema.ts` | `schema.ts` |
| 类型声明 | `<name>.types.ts` | `companion.types.ts` | `types.ts`（全局除外） |
| 常量 | `<name>.constants.ts` | `emotion.constants.ts` | `const.ts` |
| Python 模块 | snake_case.py | `memory_service.py` | `memoryService.py` |
| Python 类 | PascalCase | `MemoryRetriever` | `memory_retriever` |
| Pydantic Schema | `<Entity><Action>` | `MessageCreate` | `message_create` |
| 测试文件 | `<被测文件>.test.ts` / `test_<模块>.py` | `chat-store.test.ts` | `test1.ts` |

---

## 3. 顶层目录职责

```text
ai-companion/
├─ apps/         可独立部署的应用（每个 app 有自己的 package.json / 依赖）
├─ packages/     被 apps 复用的库（无独立部署能力）
├─ docs/         文档（架构、规范、路线图、接口）
├─ scripts/      本地开发 / 运维脚本（见下表）
├─ data/         运行时数据，**不入库**，仅保留 .gitkeep
└─ .github/      CI 与协作模板
```

**判断标准**：能单独 `run` 起来对外提供服务的 → `apps/`；只被 import 的 → `packages/`。

### `scripts/` 现有脚本

| 文件 | 用途 |
| --- | --- |
| `dev-web.mjs` | 启动前端开发服务（next dev），不依赖 pnpm/npm |
| `dev-api.mjs` | 启动后端开发服务（uvicorn --reload），自动探测 Python 解释器 |
| `dev-music.mjs` | 启动网易云音乐 API（可选功能，依赖项目外的第三方服务源码） |

`scripts/` 下的启动脚本统一写成 **Node 脚本**（`*.mjs`）而不是 shell 脚本：
Windows / macOS / Linux 都能直接 `node xxx.mjs` 运行，不必分别维护 `.sh` 和 `.bat`。

> ⚠️ 启动脚本**不要在内部调用 `pnpm`**。不同 shell 的 PATH 不一致（PowerShell 用系统 Node，
> Git Bash 可能用另一套 Node），嵌套调用包管理器容易出现「某个终端里找不到 pnpm」的问题。
> 脚本直接用 `process.execPath` 执行目标二进制即可。

---

## 4. 前端 `apps/web/src/`

```text
src/
├─ app/                     Next.js App Router：只放路由、布局、页面
│  ├─ layout.tsx            根布局
│  ├─ page.tsx              首页
│  ├─ globals.css
│  ├─ (marketing)/          路由分组，括号 = 不进 URL
│  ├─ chat/
│  │  ├─ page.tsx
│  │  └─ [sessionId]/page.tsx
│  └─ api/                  仅放需要跑在 Next 侧的 BFF 路由
│     └─ health/route.ts
│
├─ components/              跨 feature 复用的通用组件
│  ├─ ui/                   shadcn/ui 生成物，**只允许通过 CLI 新增，不手改**
│  └─ layout/               页壳：Sidebar、TopBar、ThemeToggle…
│
├─ features/                ★ 业务主战场，按域划分
│  ├─ chat/                 个性化对话中枢
│  │  ├─ components/        仅本域使用的组件
│  │  ├─ hooks/
│  │  ├─ api/               调后端接口的封装
│  │  ├─ lib/               本域纯函数
│  │  ├─ constants.ts
│  │  ├─ types.ts
│  │  └─ index.ts           对外出口（可选，避免深层相对路径）
│  ├─ companion/            AI 伴侣与情绪自适应
│  ├─ social/               真实社交辅助（润色 / 翻译 / 建议回复）
│  ├─ memory/               记忆面板：查看、语义搜索、编辑、导出、清空
│  ├─ settings/             设置：自带 API Key（BYOK）
│  ├─ multimodal/           语音输入、图片上传与预览
│  ├─ theme/                情绪驱动的主题系统
│  ├─ music/                音乐播放与联动
│  └─ wallpaper/            Three.js 动态壁纸 + 音频可视化
│
├─ hooks/                   跨 feature 的通用 Hook（use-media-query 等）
├─ lib/                     无状态基础设施：cn()、fetcher、sse-client、env
├─ stores/                  Zustand 全局 store（跨 feature 共享的状态）
├─ styles/                  全局样式片段（动画、滚动条、字体）
└─ types/                   全局类型（api.d.ts、env.d.ts）
```

### 路由文件命名（App Router 特例）

路由段的**目录名**可以是 URL 需要的形态，但请遵守：

- 动态段统一 `[param]`，catch-all 用 `[...slug]`，可选 catch-all 用 `[[...slug]]`
- 路由分组用 `(group)`，不要用来做权限（权限走 middleware）
- 同一目录下只允许一个 `page.tsx` / `route.ts` / `layout.tsx` / `loading.tsx` / `error.tsx`

### 导入别名

`tsconfig.json` 已配置：

```jsonc
"paths": {
  "@/*": ["./src/*"],
  "@ai-companion/shared": ["../../packages/shared/src/index.ts"]
}
```

- **跨目录一律用 `@/` 绝对别名**，禁止 `../../../`
- 同目录兄弟文件可用 `./`

---

## 5. 后端 `apps/api/`

```text
apps/api/
├─ app/
│  ├─ main.py               FastAPI 实例、中间件、路由挂载
│  ├─ api/
│  │  └─ v1/                版本化路由，文件按资源命名
│  │     ├─ router.py       汇总子路由
│  │     ├─ chat.py         对话 / SSE 流式
│  │     ├─ memory.py       记忆
│  │     ├─ companion.py    AI 伴侣
│  │     ├─ social.py       群聊与社交辅助
│  │     └─ media.py        多模态上传与生成
│  ├─ agents/               LangGraph 编排
│  │  ├─ graphs/            图定义（*.py，每个图一个文件）
│  │  ├─ nodes/             节点函数
│  │  ├─ prompts/           提示词（*.jinja 或 *.md）
│  │  └─ tools/             工具（含 MCP 适配）
│  ├─ services/             业务逻辑层，路由只做参数校验 + 调 service
│  ├─ memory/               RAG：embedding / extractor / store / retriever
│  ├─ multimodal/           asr / ocr / emotion / image_gen / tts
│  ├─ models/               ORM 实体（SQLAlchemy）
│  ├─ schemas/              Pydantic 出入参
│  ├─ db/                   session / base / repositories / migrations
│  ├─ core/                 config、logging、security、exceptions
│  ├─ mcp/                  MCP server 接入与工具注册
│  └─ utils/                纯工具函数
├─ tests/                   与 app/ 镜像的目录结构
├─ requirements.txt         运行依赖（锁定到小版本）
├─ pyproject.toml           工具配置（ruff / mypy / pytest）
└─ Dockerfile
```

**分层铁律**：`api → services → (memory | multimodal | db)`，**禁止反向依赖**，
`schemas` 不 import `models`，`services` 不 import `fastapi.Request`。

### 命名约定

- 提示词文件：`<用途>.jinja`，如 `companion_system.jinja`
- LangGraph 图：`<流程>_graph.py`，如 `chat_graph.py`
- 节点函数：`<动作>_node`，如 `retrieve_memory_node`
- 仓储类：`<Entity>Repository`

---

## 6. 共享包 `packages/shared/`

只放**前后端都要用**的东西：API 出入参类型、枚举、常量、zod schema（前端校验 + 后端对齐）。

```text
packages/shared/src/
├─ index.ts          统一出口
├─ types/            实体类型
├─ schemas/          zod schema
├─ constants/        枚举与常量（情绪标签、会话类型…）
└─ utils/            同构纯函数
```

禁止在 shared 里 import React、Next、FastAPI 相关的东西。

---

## 7. 文档与数据目录

- `docs/` 一律 **大写文件名 + `.md`**：`ARCHITECTURE.md`、`PATH_CONVENTION.md`、`ROADMAP.md`、`API.md`
- 图片资源放 `docs/assets/`，用 kebab-case 命名
- `data/` 下四个子目录固定用途，**不入库**：
  - `data/uploads/` 用户上传原始文件
  - `data/chroma/` 向量库持久化
  - `data/sqlite/` 本地数据库
  - `data/minio/` 对象存储本地落盘

---

## 8. Git 相关约定

- 分支：`main`（稳定）/ `dev`（集成）/ `feat/…` / `fix/…` / `docs/…` / `chore/…`
- 提交：Conventional Commits，scope 见 CONTRIBUTING.md
- 大文件不要直接提交：模型权重、音视频素材走 Git LFS 或对象存储
- `.env` 永不入库，新增配置项必须同步更新 `.env.example`

---

## 9. 新增文件时的检查清单

- [ ] 目录名是 kebab-case 吗？
- [ ] 文件放对层了吗（feature 就近 vs 全局复用）？
- [ ] 跨目录导入用的是 `@/` 别名吗？
- [ ] 后端是否遵守 `api → services → db` 单向依赖？
- [ ] 有对应的测试文件吗（位置与被测文件镜像）？
- [ ] 新增配置项是否同步到 `.env.example`？

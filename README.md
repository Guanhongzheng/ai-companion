# ai-companion

> 个性化多模态 AI 伴侣与社交对话平台 —— 把 AI 单聊、真实用户单聊、群聊收进同一套对话中枢，
> 用长期个人记忆和情绪自适应界面，让 AI 真正"认识你"。

<p>
  <img alt="license" src="https://img.shields.io/badge/license-MIT-blue.svg" />
  <img alt="next" src="https://img.shields.io/badge/Next.js-14-black.svg" />
  <img alt="react" src="https://img.shields.io/badge/React-18-61dafb.svg" />
  <img alt="typescript" src="https://img.shields.io/badge/TypeScript-5.4-3178c6.svg" />
  <img alt="python" src="https://img.shields.io/badge/Python-3.11+-3776ab.svg" />
  <img alt="fastapi" src="https://img.shields.io/badge/FastAPI-0.115-009688.svg" />
</p>

---

## ✨ 核心卖点

| 卖点 | 说明 |
| --- | --- |
| 🎭 情绪自适应界面 | 情绪结果实时驱动主题色、字体、动效、布局，以及 Three.js 粒子壁纸与 Web Audio 频谱 |
| 🧠 长期个人记忆 | RAG 全链路：抽取 → 去重 → 向量化 → 召回 → 重排，记忆可查看/编辑/导出/一键清空 |
| 💞 个性化 AI 伴侣 | 多模态输入（文本 / 语音 / 图像）+ 意图识别 + 个性化回应 + 成长记录 |
| 👥 AI 辅助真实社交 | 群聊中 AI 可被 @ 唤醒、自动总结、情绪感知，辅助而非替代真人交流 |
| 🌌 动态壁纸与音乐联动 | Three.js + Web Audio API 做音频可视化，音乐随情绪与壁纸联动 |
| 🔌 用户自带 AI 接口 | BYOK：用户可填入自己的模型 Key，后端统一经 LiteLLM 路由 |

## 🧩 功能模块

1. **个性化对话中枢** —— 统一 AI 对话与用户对话
   - 左侧会话列表：`AI 伴侣` / `好友单聊` / `群聊` 三类
   - 右侧对话窗口按会话类型自动切换能力
   - AI 单聊 = 全量 Agent 能力；用户单聊 = 润色 / 翻译 / 总结 / 建议回复
   - 混合群聊 = AI 被 @ 唤醒 + 自动总结 + 情绪感知
2. **AI 伴侣与情绪自适应** —— 情感分析 → 意图识别 → 记忆检索 → 个性化回应 → 创意生成 → 成长记录 → 隐私保护
3. **RAG 个人记忆系统** —— 记忆抽取、去重、向量化、检索重排、遗忘与导出
4. **多模态理解与轻量生成** —— Whisper 转写、OCR、图像理解、SD 轻量出图、TTS
5. **AI 安全与隐私保护** —— 内容过滤、敏感信息脱敏、记忆加密、数据可一键删除
6. **实时社交对话** —— SSE / Supabase Realtime / Socket.io 三选一

## 🛠 技术栈

**前端**：React 18 · Next.js 14 (App Router) · TypeScript (strict) · Tailwind CSS · shadcn/ui ·
Zustand · TanStack Query · react-hook-form + zod · framer-motion · Recharts · next-themes · react-virtuoso · SSE / fetch stream

**后端**：FastAPI (或 Next.js API Routes) · LangGraph · LiteLLM · Chroma / Milvus Lite ·
SQLite / PostgreSQL · 本地文件系统 / MinIO · 官方 MCP SDK · Supabase Realtime / Socket.io

**模型**：Qwen / DeepSeek / GPT / Claude / Gemini / Ollama
**向量**：Embedding `bge-m3` · Reranker `bge-reranker`
**多模态**：Whisper（ASR）· OCR · 情感分析 · Stable Diffusion · TTS
**音乐**：NeteaseCloudMusicApi Enhanced
**壁纸**：Three.js + Web Audio API + CSS Gradient
**部署**：Docker Compose + Vercel / Render

## 📁 仓库结构

```text
ai-companion/
├─ apps/
│  ├─ web/                        # Next.js 14 前端
│  │  ├─ src/app/                 # App Router 路由
│  │  ├─ src/components/          # 全局组件（ui = shadcn 生成物）
│  │  ├─ src/features/            # 按业务域划分的功能模块
│  │  ├─ src/lib/                 # 无状态工具与外部客户端
│  │  ├─ src/hooks/               # 通用 React Hooks
│  │  ├─ src/stores/              # Zustand 全局状态
│  │  ├─ src/types/               # 前端本地类型
│  │  ├─ public/                  # 静态资源
│  │  └─ tests/                   # 前端测试
│  └─ api/                        # FastAPI 后端
│     ├─ app/api/v1/              # 对外 REST / SSE 路由
│     ├─ app/agents/              # LangGraph Agent 与工作流
│     ├─ app/services/            # 业务服务（对话、记忆、音乐…）
│     ├─ app/memory/              # RAG 记忆：切分 / 向量化 / 检索 / 重排
│     ├─ app/multimodal/          # ASR / OCR / 情感分析 / 生成
│     ├─ app/models/              # ORM 模型
│     ├─ app/schemas/             # Pydantic 出入参
│     ├─ app/db/                  # 连接、迁移、仓储
│     ├─ app/core/                # 配置、日志、安全
│     ├─ app/mcp/                 # MCP 工具接入
│     └─ tests/                   # 后端测试
├─ packages/
│  ├─ shared/                     # 前后端共享类型与常量
├─ patches/                       # pnpm patch（第三方包修复，见「已知补丁」）
├─ docs/                          # 架构、路径规范、路线图、接口文档
├─ scripts/                       # 本地开发与运维脚本
├─ data/                          # 本地运行时数据（不入库）
└─ .github/                       # CI、Issue / PR 模板
```

### 已知补丁

`patches/next@14.2.15.patch` 修的是 Next.js 一个上游竞态：构建时多个事件批次并发初始化
`.next/trace` 写流（`await mkdir` 让出事件循环之后才赋值），Windows 上会重复打开同一文件并抛出
`EPERM: operation not permitted, open '.next/trace'`，导致 `next build` 直接失败。
上游直到 14.2.35 仍未修复，因此用 `pnpm patch` 把初始化守卫固化进仓库
（配置在 `package.json` 的 `pnpm.patchedDependencies`）。
**升级 Next 大版本后需要重新验证，必要时重新打补丁。**

> 📐 目录与命名细则见 [`docs/PATH_CONVENTION.md`](docs/PATH_CONVENTION.md)。
> 🏗 架构设计见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

## 🚀 快速开始

### 0. 环境要求

- Node.js >= 20（22 / 24 都实测可用），npm >= 10
- Python >= 3.11
- （可选）Docker Desktop

包管理用 **pnpm**（workspace 模式，版本由 `package.json` 的 `packageManager` 锁定为 9.12.0）。
如果提示找不到 pnpm，任选一种：

```bash
# 方式 A：让 corepack 生成 pnpm 命令（推荐，需管理员权限写入 node 安装目录）
corepack enable pnpm

# 方式 B：不安装，直接用 corepack 调用
corepack pnpm install
```

> ⚠️ 不同终端的 PATH 可能不同：PowerShell 通常用 `C:\Program Files\nodejs` 下的系统 Node，
> 而其他终端可能用别的 Node 安装目录，`corepack enable` 生成的 pnpm 只在其中一个可见。
> **日常开发不依赖 pnpm**，`npm run dev:web` / `npm run dev:api` 在任何终端都能用。

### 1. 安装依赖

```bash
git clone https://github.com/<your-name>/ai-companion.git
cd ai-companion

pnpm install                       # 前端 + 共享包

cd apps/api
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
# 可选：本地向量模型（会装 PyTorch，约 2-3GB），不用云端 embedding 时再装
# pip install -r requirements-ml.txt
```

> 依赖分三层：`requirements.txt`（核心，装了就能跑）/ `requirements-ml.txt`（本地 bge-m3、bge-reranker，体积大）/
> `requirements-dev.txt`（pytest、ruff、mypy）。`pnpm` 未安装时可用 `corepack enable pnpm` 装好。

### 3.5 国内网络加速

仓库已默认配置好国内镜像，不需要额外操作：

| 生态 | 镜像 | 配置位置 |
| --- | --- | --- |
| npm / pnpm | [npmmirror](https://registry.npmmirror.com) | 根目录 `.npmrc`（已提交，可直接改或注释掉） |
| pip | [清华源](https://pypi.tuna.tsinghua.edu.cn/simple) | venv 内 `pip.ini`（阿里云源见文件注释） |
| HuggingFace 模型 | [hf-mirror](https://hf-mirror.com) | 见下方 `HF_ENDPOINT` |

pip 的镜像写在 **venv 内部**（`apps/api/.venv/pip.ini`，已被 git 忽略），换机器重建环境时补上即可：

```ini
; 必须纯 ASCII，Windows 的 pip 按 cp936 解码，写中文会让所有 pip 命令报错
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
```

`pnpm dev:api` 会按 `AI_COMPANION_PYTHON` → `apps/api/.venv` → PATH 上 `python` 的顺序
自动找解释器，所以正常情况下直接 `pnpm dev:api` 即可，不用手动激活虚拟环境。

`pnpm` 默认走 corepack，仓库里锁定了版本（`package.json` 的 `packageManager: pnpm@9.12.0`）。
首次使用先执行一次 `corepack enable pnpm` 让它进入 PATH。

下载本地向量模型（bge-m3、bge-reranker）时加国内 HF 镜像：

```bash
# Linux / macOS
export HF_ENDPOINT=https://hf-mirror.com
# Windows PowerShell
$env:HF_ENDPOINT="https://hf-mirror.com"

pip install -r apps/api/requirements-ml.txt
```

> ⚠️ 写 `pip.ini` / `pip.conf` 时**不要加中文注释**：Windows 上 pip 按系统 locale（zh-CN 为 cp936）
> 解码配置文件，含非 ASCII 字符会让所有 pip 命令直接报错。

### 2. 配置环境变量

```bash
cp .env.example apps/web/.env.local     # 前端：保留 NEXT_PUBLIC_* 即可
cp .env.example apps/api/.env           # 后端：填模型 Key、数据库、存储
```

> 至少需要配置一个模型 Provider 的 API Key（或本地 Ollama）才能跑通对话。

### 3. 启动开发环境

```bash
npm run dev:web      # http://localhost:3000
npm run dev:api      # http://localhost:8000  (Swagger: /docs)
```

> 启动脚本内部不调用 pnpm，所以 `npm run` / `pnpm run` / 直接 `node scripts/dev-web.mjs`
> 三种方式都能用，不受某个终端里有没有装 pnpm 的影响。

打开 http://localhost:3000 后点「进入对话中枢」，或直接访问 http://localhost:3000/chat。
长期记忆面板在 http://localhost:3000/memory。

**记忆联动看效果**：在 `/chat` 里问一句「我住的地方附近有什么好吃的」，回复上方的
「AI 想起了：」会列出它召回的记忆；换到 `/memory` 页面可以搜索、编辑、删除、导出，
也能粘贴一段话让 AI 自动抽取其中的自述信息。

**关于检索质量**：向量化实现是**可插拔**的 —— 装了 `requirements-ml.txt` 会用本地 bge-m3，
配了模型 Key 会走云端 Embedding，两者都没有时降级为哈希实现（纯字面匹配，零依赖）。
想要「宠物 → 猫」这类语义召回，装 bge-m3 或配一个 Embedding Key 即可，上层代码不用改。

**没配模型 Key 也能跑**：后端会自动降级为本地模拟回复，情绪识别、SSE 流式、消息落库全链路
照常工作，界面右上角会显示「模拟模式」。想接真实模型，在 `apps/api/.env` 里填上任意一个
`DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` /
`GEMINI_API_KEY`，或设 `OLLAMA_BASE_URL` 走本地模型，重启即可自动切换。

**情绪联动看效果**：在 `/chat` 里发一句「今天太累了」，界面会同时发生这些变化——
字体切到衬线、字重变细、字距拉开、气泡变圆变小、消息入场变慢、壁纸粒子从 180 降到 70
几乎静止、背景渐变转成暗蓝色系。再发「气死我了」，字体变粗体、字距收紧、粒子暴涨到
340 个并剧烈抖动。再发「好期待啊」，圆体放大、粒子加速到最快。

**音乐联动**（可选，纯加分项，不影响其他功能）：

需要单独跑一个网易云音乐 API 服务。推荐用 Node 直接跑，不需要 Docker / WSL / 重启：

```bash
# 一次性准备（放在项目外的 tools 目录，避免污染仓库）
git clone --depth 1 https://github.com/neteasecloudmusicapienhanced/api-enhanced.git
cd api-enhanced
npm install --ignore-scripts        # 国内源见下方注意事项

# 每次启动（在 ai-companion 项目根目录执行）
npm run dev:music                    # 监听 3001
```

服务默认在 `../../tools/api-enhanced` 找，放别处就用环境变量指定：

```bash
AI_COMPANION_MUSIC_DIR=/你的路径 npm run dev:music
```

> ⚠️ 三个踩过的坑：
> 1. **用 `npm install` 而不是 `pnpm install`** —— 该项目的 `prepare` 脚本会调 `husky install`，
>    失败后 pnpm 只装上 devDependencies，生产依赖全部缺失且不报错
> 2. **必须 `--ignore-scripts`**，否则 husky 那步会中断安装
> 3. 该服务内部的 HTTP 客户端会读代理环境变量，指向不可用的代理会导致全部请求失败；
>    `dev-music.mjs` 已经帮你清空了，手动启动的话记得自己处理

也可以用 Docker（`docker compose --profile infra up -d music-api`），但需要先装好 WSL2
并在 Docker Desktop 配置 registry-mirrors，详见 `docker-compose.yml` 顶部注释。

服务起来后，右下角「情绪歌单」面板会自动探测并按当前情绪检索歌曲；播放时音频频谱接管
壁纸，低频越强粒子越大、整体呼吸越明显。服务没启动时面板会提示启动命令。

### 4. Docker Compose 一键启动（可选）

```bash
docker compose up -d            # web + api
docker compose --profile infra up -d    # 额外拉起 postgres + chroma
```

## 🤝 贡献

欢迎提 Issue 与 PR，请先阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md)。
提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)。
安全问题请走 [`SECURITY.md`](SECURITY.md) 描述的私下渠道，不要直接开公开 Issue。

## 📄 许可

本项目基于 [MIT License](LICENSE) 开源。

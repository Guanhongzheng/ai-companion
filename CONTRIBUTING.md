# 贡献指南

感谢你愿意参与 ai-companion。以下是本仓库的协作约定，请尽量遵守。

## 1. 分支模型

| 分支 | 用途 |
| --- | --- |
| `main` | 稳定分支，随时可部署；只接受通过 CI 的 PR |
| `dev` | 集成分支，日常开发合并到这里 |
| `feat/<scope>-<desc>` | 新功能，例：`feat/chat-sse-stream` |
| `fix/<scope>-<desc>` | 缺陷修复，例：`fix/memory-rerank-empty` |
| `chore/<desc>` | 构建、依赖、配置类改动 |
| `docs/<desc>` | 纯文档改动 |

> 分支名一律 kebab-case，禁止中文与空格。

## 2. 提交信息（Conventional Commits）

```text
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

- `type` ∈ `feat` `fix` `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` `revert`
- `scope` 建议取值：`web` `api` `agent` `memory` `multimodal` `theme` `music` `shared` `deps` `ci`
- `subject` 使用中文或英文均可，**不要**以句号结尾，控制在 50 字符内

示例：

```text
feat(memory): 接入 bge-reranker 对检索结果重排
fix(web): 修复群聊窗口切换后 SSE 未断开的问题
docs(path): 补充 features 目录的划分原则
```

## 3. 提交前自检

```bash
pnpm lint
pnpm typecheck
pnpm format:check

cd apps/api && pytest
```

## 4. 代码规范速览

- 目录一律 `kebab-case`，React 组件文件 `PascalCase.tsx`，Python 模块 `snake_case.py`
- TypeScript 开启 `strict`，禁止裸 `any`（必要时写 `unknown` + 收窄）
- 组件只做展示，业务逻辑放 `src/features/<domain>/` 的 hooks 或 service
- 禁止把密钥、真实用户数据、`.env` 提交进仓库
- 新增依赖请在 PR 描述里说明理由与体积影响

完整路径规范见 [`docs/PATH_CONVENTION.md`](docs/PATH_CONVENTION.md)。

## 5. PR 要求

- 一个 PR 只做一个主题，标题同 commit 规范
- 描述里写清：改动内容 / 为什么这么改 / 如何验证 / 关联 Issue
- 截图或录屏对 UI 改动是必填项
- 至少通过 CI 后再请求 review

# 更新日志

本文件记录项目的所有重要变更，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added

- 初始化 monorepo 骨架：`apps/web`（Next.js 14）+ `apps/api`（FastAPI）+ `packages/shared`
- 工程规范文件：`.gitignore` / `.gitattributes` / `.editorconfig` / Prettier 配置
- 国内镜像配置：`.npmrc`（npmmirror）
- 环境变量模板 `.env.example`，覆盖模型、向量库、存储、实时通道等全部配置项
- 仓库文档：README、CONTRIBUTING、SECURITY、docs/ARCHITECTURE、docs/PATH_CONVENTION、docs/ROADMAP、docs/API
- GitHub 协作模板：CI 工作流、PR 模板、Issue 模板
- Docker Compose 本地编排（web / api，可选 postgres / chroma）
- `patches/next@14.2.15.patch`：修复 Windows 上 `next build` 因 `.next/trace` 竞态报 EPERM 的问题

### Changed

- Python 依赖拆成三层：`requirements.txt`（核心）/ `requirements-ml.txt`（本地向量模型，带 PyTorch）/
  `requirements-dev.txt`（pytest、ruff、mypy）
- CI 改为安装 `requirements.txt` + `requirements-dev.txt`

<!--
## [0.1.0] - YYYY-MM-DD
### Added
### Changed
### Fixed
### Removed
-->

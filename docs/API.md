# 接口文档（API）

Base URL：`http://localhost:8000`
在线文档：`/docs`（Swagger UI）、`/redoc`（ReDoc）
所有业务接口统一挂在 `/api/v1` 下。

## 通用约定

- 请求 / 响应均为 JSON（文件上传除外，走 `multipart/form-data`）
- 时间统一 ISO 8601 UTC 字符串
- 错误响应：

```json
{ "detail": "错误说明" }
```

## 系统

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查，返回 `{status, version, env}` |

## 会话

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/sessions` | 会话列表（置顶优先、按最近活跃排序） |
| POST | `/api/v1/sessions` | 创建会话，body `{ type, title, memberCount? }` |
| GET | `/api/v1/sessions/{id}/messages` | 消息历史 |
| PATCH | `/api/v1/sessions/{id}` | 重命名，body `{ title }` |
| DELETE | `/api/v1/sessions/{id}` | 删除会话（级联删除消息） |

首次启动会自动灌入三条示例会话（AI 伴侣 / 好友 / 群聊各一），界面一打开就有内容。

## 记忆

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/memory` | 记忆列表，可 `?type=profile` 按类型过滤 |
| GET | `/api/v1/memory/stats` | 统计：总数、分类、是否加密、向量化实现 |
| GET | `/api/v1/memory/search?q=&top_n=` | 语义搜索，返回命中分数与重排方式 |
| POST | `/api/v1/memory` | 手动新增，body `{ content, type }`，重复内容自动去重 |
| POST | `/api/v1/memory/ingest` | 从一段文本自动抽取记忆，body `{ text }` |
| PATCH | `/api/v1/memory/{id}` | 编辑，body `{ content?, type?, pinned? }` |
| DELETE | `/api/v1/memory/{id}` | 删除单条（SQL 与向量库同时删） |
| GET | `/api/v1/memory/export` | 导出 JSON（正文解密） |
| DELETE | `/api/v1/memory` | 一键清空全部 |

记忆类型：`profile`（身份）/ `preference`（喜好）/ `fact`（事实）/ `event`（事件）。

### 向量化实现的自动选择

| 优先级 | 实现 | 启用条件 |
| --- | --- | --- |
| 1 | 本地 `bge-m3` | 装了 `requirements-ml.txt` |
| 2 | 云端 Embedding | 配了任意模型 API Key，经 LiteLLM 路由 |
| 3 | 哈希兜底 | 都没有时，零依赖、毫秒级 |

哈希实现是**纯字面匹配**（字符 n-gram 特征哈希），能处理「我做什么工作」这类有字面重叠的
查询，但理解不了「宠物 → 猫」这种语义关系。想要语义检索质量，装 bge-m3 或配一个
Embedding Key 即可，**上层代码一行都不用改**。

可用 `MEMORY_EMBEDDING_PROVIDER` 强制指定实现（`hashing` / `sentence-transformers` / `cloud`）。

### 加密

设 `MEMORY_ENCRYPT=true` 与 `MEMORY_ENCRYPTION_KEY` 后，正文以 Fernet 加密落库。
**未配置密钥时不会静默降级为明文**，接口 `/stats` 的 `encrypted` 字段会如实告知当前状态。

## 多媒体

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/media/image` | 上传图片（multipart，字段名 `file`） |
| POST | `/api/v1/media/audio` | 上传音频 |
| POST | `/api/v1/media/transcribe` | 音频转文字，服务端 ASR 兜底 |
| POST | `/api/v1/media/vision` | 单独调一次图片理解 |
| GET | `/api/v1/media/{filename}` | 读取已上传的文件 |

支持类型：图片 png / jpeg / webp / gif；音频 webm / ogg / mp3 / m4a / wav
（mime 允许带 `;codecs=...` 参数，Chrome 录音默认就是这种）。

**安全约束**：

* 落盘文件名完全由服务端用 uuid 生成，**不采用用户提交的原始文件名**
* 磁盘扩展名由**类型白名单**推导 —— 把脚本伪装成 `image/png` 上传，存下来仍是 `.png`
* 读取接口做目录穿越校验，`..` 一律 404
* 图片大小上限 `MAX_IMAGE_MB`（默认 10MB），音频 `MAX_AUDIO_MB`（默认 25MB）

聊天时消息里带 `attachments` 字段即可携带图片或语音：图片会自动做视觉理解、
语音会用 `transcript` 一起注入上下文。**没配视觉 / ASR 能力时不会报错**，
图片照常保存显示，对话里会带上「当前模型无法理解图片内容」的说明。

## 设置（BYOK）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/settings/status` | 查看当前生效的模型来源（Key 脱敏） |
| POST | `/api/v1/settings/validate` | 用最小 token 实测 Key 与模型是否可用 |

### 用户自带 Key 的传参方式

这些接口**自身不带 Key**，Key 通过请求头传入，与对话接口共用同一套头：

| 请求头 | 说明 |
| --- | --- |
| `X-Model-Key` | 对话模型的 API Key |
| `X-Model-Name` | 模型名，可带 provider 前缀（`deepseek-chat` 等价于 `deepseek/deepseek-chat`） |
| `X-Embedding-Key` | Embedding Key，留空则复用 `X-Model-Key` |
| `X-Embedding-Model` | Embedding 模型名，如 `text-embedding-v3` |

**安全边界**：Key 只存在于浏览器的 localStorage，请求时通过上述头传给本地后端，
后端**不落盘、不入库、不写日志**，只在该次请求的生命周期内存在于内存。
日志里只以 `sk-a***1234` 的形式出现。

Key 无效、模型不存在、余额不足、超时等异常会被翻译成中文短句
（见 `app/core/errors.py`），不会把厂商原始堆栈或 Key 片段返回给前端。

## 对话

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/chat` | 非流式对话 |
| POST | `/api/v1/chat/stream` | SSE 流式对话 |

### POST `/api/v1/chat/stream`

请求体：

```json
{
  "session_id": "s_123",
  "messages": [{ "role": "user", "content": "今天有点累" }],
  "model": "deepseek-chat",
  "stream": true
}
```

响应为 `text/event-stream`，事件类型：

| event | data 结构 | 说明 |
| --- | --- | --- |
| `meta` | `{ "session_id", "model", "mocked" }` | 会话元信息。`mocked=true` 表示未配置 Key、走本地降级 |
| `action` | `{ "action": "polish", "waiting_for_mention": false }` | 本轮意图判定。群聊未被 @ 时 `action=skipped` 且不产生任何 token |
| `emotion` | `{ "tag": "tired", "confidence": 0.65 }` | 情绪标签，前端据此切换主题 |
| `memory` | `{ "items": [{ "id", "content", "score", "reranker" }] }` | 本轮召回的长期记忆，前端展示「AI 想起了什么」 |
| `token` | `{ "text": "辛苦" }` | 增量文本，中文按 1-2 字切块推送 |
| `done` | `{ "finish_reason": "stop" }` | 流结束 |
| `error` | `{ "message": "..." }` | 出错（随后连接关闭） |

> SSE 规范用 `\r\n` 分隔事件块，客户端解析时记得先归一化。

事件类型定义与前端消费逻辑共享自 `@ai-companion/shared`。

### 未配置模型 Key 时

服务不会报错，而是走**本地降级**：`emotion` 照常识别，`token` 推送一段按情绪挑选的
模拟回复，并在 `meta.mocked` 里标记。这样演示现场没网、没 Key 也能完整走通链路。
在 `apps/api/.env` 填入任意一个模型 Key 后重启即自动切换为真实模型。

## 规划中

- `/api/v1/memory` 记忆的增删改查与导出
- `/api/v1/companion` 伴侣人设、成长记录
- `/api/v1/social` 群聊总结、@AI 唤醒
- `/api/v1/media` 语音转写、OCR、图像生成

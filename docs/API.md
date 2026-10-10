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
| `emotion` | `{ "tag": "tired", "confidence": 0.65 }` | 情绪标签，前端据此切换主题 |
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

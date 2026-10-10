# 路线图（ROADMAP）

## M0 · 骨架与跑通（当前）

- [x] Monorepo 结构、路径规范、工程配置
- [ ] `apps/web` 起一个 Next.js 页面，`apps/api` 起一个 `/health`
- [ ] 前端能通过 SSE 拿到后端的流式假数据
- [ ] Docker Compose 本地一把起

## M1 · 对话中枢 MVP（已完成第一轮）

- [x] 会话列表（AI / 好友 / 群聊三类）+ 对话窗口
- [x] 消息持久化（SQLite + SQLAlchemy 2.0）
- [x] SSE 流式渲染（自研 fetch 流解析，非 EventSource）
- [x] 情绪识别接入，emotion 事件驱动前端主题
- [x] react-virtuoso 虚拟滚动承载长会话
- [x] LiteLLM 统一路由 + **无 Key 自动降级**（演示现场永不断链）
- [ ] 接入真实模型 Key（等用户配置后即生效）
- [ ] 乐观更新与断线重连

## M2 · 长期记忆（RAG）

- [ ] 记忆抽取 → 去重 → 向量化 → 入库
- [ ] bge-m3 召回 + bge-reranker 重排
- [ ] 记忆面板：查看 / 编辑 / 删除 / 导出
- [ ] 记忆加密与一键清除

## M3 · 情绪自适应

- [ ] 情感分析接入，产出 EmotionTag
- [ ] 情绪 → 主题色 / 字体 / 动效联动
- [ ] 情绪 → 壁纸联动（CSS Gradient 起步）
- [ ] 情绪 → 音乐联动（NeteaseCloudMusicApi Enhanced）

## M4 · 多模态与动态壁纸

- [ ] 语音输入（Whisper → 文本）
- [ ] 图像上传与理解（OCR + 视觉模型）
- [ ] Three.js + Web Audio API 音频可视化壁纸
- [ ] 轻量图像生成 / TTS 输出

## M5 · AI 辅助社交

- [ ] 好友单聊旁路助手：润色 / 翻译 / 总结 / 建议回复
- [ ] 群聊 @AI 唤醒 + 自动总结 + 情绪感知
- [ ] 多人实时同步（Supabase Realtime / Socket.io）

## M6 · Agent 与工具化

- [ ] LangGraph 多节点编排
- [ ] MCP 工具接入
- [ ] 用户自带模型接口（BYOK）
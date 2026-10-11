/**
 * 会话与消息的共享类型定义
 * 前后端必须引用同一份，避免字段漂移
 */

export const SESSION_TYPES = ["ai", "direct", "group"] as const;
export type SessionType = (typeof SESSION_TYPES)[number];

export const SENDER_TYPES = ["user", "ai", "system"] as const;
export type SenderType = (typeof SENDER_TYPES)[number];

export const CONTENT_TYPES = ["text", "image", "audio", "file"] as const;
export type ContentType = (typeof CONTENT_TYPES)[number];

export interface Session {
  id: string;
  type: SessionType;
  title: string;
  /** 头像地址；AI 伴侣可为空，前端按类型渲染默认头像 */
  avatarUrl?: string;
  /** 群聊成员数 / 单聊固定为 2 */
  memberCount: number;
  lastMessagePreview?: string;
  updatedAt: string;
  unreadCount: number;
  pinned?: boolean;
}

export interface Message {
  id: string;
  sessionId: string;
  senderType: SenderType;
  senderId: string;
  /**
   * 群聊里这条消息的发言人显示名（如「张三」）。
   *
   * 写入时就定好而不是读时从 senderId 推导 —— 否则改了 id 名字就跟着变。
   * AI 伴侣 / 好友单聊下为空。
   */
  senderLabel?: string;
  content: string;
  contentType: ContentType;
  /** 情绪标签，驱动前端主题 / 壁纸 / 音乐联动 */
  emotion?: EmotionTag;
  /** 多模态附件地址 */
  attachments?: Attachment[];
  createdAt: string;
  /** 流式生成中标记 */
  streaming?: boolean;
}

export interface Attachment {
  /** image / audio */
  kind: "image" | "audio";
  url: string;
  /** 用户可见的原始文件名 */
  name?: string;
  mimeType?: string;
  size?: number;
  /** 语音转写结果 */
  transcript?: string | null;
  /** 图像理解结果 */
  description?: string | null;
}

// ---- 情绪 ----

export const EMOTION_TAGS = [
  "joy",
  "calm",
  "neutral",
  "sad",
  "anxious",
  "angry",
  "excited",
  "tired",
] as const;
export type EmotionTag = (typeof EMOTION_TAGS)[number];

export interface EmotionResult {
  tag: EmotionTag;
  confidence: number;
  /** 触发情绪分析的原始文本 / 语音片段引用 */
  sourceRef?: string;
  detectedAt?: string;
}

// ---- SSE 事件协议 ----

export type ChatStreamEventName = "meta" | "token" | "emotion" | "error" | "done";

export interface ChatStreamMeta {
  sessionId: string;
  model?: string;
}

export interface ChatStreamToken {
  text: string;
}

export interface ChatStreamEmotion {
  tag: EmotionTag;
  confidence: number;
}

export interface ChatStreamDone {
  finishReason: "stop" | "length" | "error";
}

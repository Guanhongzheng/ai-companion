/**
 * 对话中枢的类型与映射。
 *
 * 后端返回 snake_case（FastAPI 默认），共享包里是 camelCase，
 * 这里做一次显式转换，避免把脏字段直接扩散到组件层。
 */

import type { Attachment, EmotionTag, Message, Session } from "@ai-companion/shared";

/** 后端原始返回结构 */
export interface SessionDto {
  id: string;
  type: string;
  title: string;
  avatar_url: string | null;
  member_count: number;
  unread_count: number;
  pinned: boolean;
  created_at: string;
  updated_at: string;
}

export interface MessageDto {
  id: string;
  session_id: string;
  sender_type: string;
  sender_id: string;
  content: string;
  content_type: string;
  emotion: string | null;
  attachments: Attachment[];
  created_at: string;
}

export function toSession(dto: SessionDto): Session {
  return {
    id: dto.id,
    type: dto.type as Session["type"],
    title: dto.title,
    avatarUrl: dto.avatar_url ?? undefined,
    memberCount: dto.member_count,
    unreadCount: dto.unread_count,
    pinned: dto.pinned,
    updatedAt: dto.updated_at,
  };
}

export function toMessage(dto: MessageDto): Message {
  return {
    id: dto.id,
    sessionId: dto.session_id,
    senderType: dto.sender_type as Message["senderType"],
    senderId: dto.sender_id,
    content: dto.content,
    contentType: dto.content_type as Message["contentType"],
    emotion: (dto.emotion as EmotionTag | null) ?? undefined,
    attachments: dto.attachments ?? [],
    createdAt: dto.created_at,
  };
}

/** 会话类型的中文标签与分组顺序 */
export const SESSION_TYPE_META = {
  ai: { label: "AI 伴侣", hint: "全量 Agent 能力", order: 0 },
  direct: { label: "好友", hint: "AI 辅助回复", order: 1 },
  group: { label: "群聊", hint: "可 @ AI 唤醒", order: 2 },
} as const satisfies Record<Session["type"], { label: string; hint: string; order: number }>;

export const SESSION_TYPE_ORDER: Session["type"][] = ["ai", "direct", "group"];

/** SSE 事件负载 */
export interface StreamMetaPayload {
  sessionId: string;
  model: string;
  mocked: boolean;
}

/** 会话意图：正常聊天 / 辅助动作 / 群聊未@跳过 */
export interface StreamActionPayload {
  action: "chat" | "polish" | "translate" | "summarize" | "suggest" | "skipped";
  waiting_for_mention: boolean;
}

export interface StreamEmotionPayload {
  tag: EmotionTag;
  confidence: number;
}

export interface StreamTokenPayload {
  text: string;
}

export interface StreamDonePayload {
  finishReason: string;
}

export interface StreamErrorPayload {
  message: string;
}
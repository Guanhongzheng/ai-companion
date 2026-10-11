/**
 * 对话中枢的接口封装。只负责 HTTP，不含任何 UI 逻辑。
 */

import { apiFetch } from "@/lib/api-client";
import type { GroupSummary, MessageDto, SessionDto } from "../types";

// 走统一封装，才能带上用户自己填的 API Key
const request = apiFetch;

export const chatApi = {
  listSessions: () => request<SessionDto[]>("/api/v1/sessions"),

  createSession: (input: { type: string; title: string; memberCount?: number }) =>
    request<SessionDto>("/api/v1/sessions", {
      method: "POST",
      body: JSON.stringify({ type: input.type, title: input.title, member_count: input.memberCount ?? 2 }),
    }),

  renameSession: (id: string, title: string) =>
    request<SessionDto>(`/api/v1/sessions/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),

  deleteSession: (id: string) => request<void>(`/api/v1/sessions/${id}`, { method: "DELETE" }),

  listMessages: (sessionId: string) =>
    request<MessageDto[]>(`/api/v1/sessions/${sessionId}/messages`),

  /** 群聊总结。模型不可用时后端会退回规则版，照样返回结果 */
  summarize: (sessionId: string) =>
    request<GroupSummary>(`/api/v1/sessions/${sessionId}/summarize`, { method: "POST" }),

  streamUrl: "/api/v1/chat/stream",
};
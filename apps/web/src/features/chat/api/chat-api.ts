/**
 * 对话中枢的接口封装。只负责 HTTP，不含任何 UI 逻辑。
 */

import { absoluteUrl } from "@/lib/utils";
import type { MessageDto, SessionDto } from "../types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(absoluteUrl(path), {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${detail}`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

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

  streamUrl: "/api/v1/chat/stream",
};
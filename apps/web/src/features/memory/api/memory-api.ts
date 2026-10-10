/**
 * 记忆接口封装。
 */

import { absoluteUrl } from "@/lib/utils";
import type { MemoryDto, MemorySearchHitDto, MemoryStats } from "../types";

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

export const memoryApi = {
  list: (type?: string) =>
    request<MemoryDto[]>(`/api/v1/memory${type ? `?type=${encodeURIComponent(type)}` : ""}`),

  stats: () => request<MemoryStats>("/api/v1/memory/stats"),

  search: (q: string, topN = 10) =>
    request<MemorySearchHitDto[]>(
      `/api/v1/memory/search?q=${encodeURIComponent(q)}&top_n=${topN}`,
    ),

  create: (content: string, type: string) =>
    request<MemoryDto>("/api/v1/memory", {
      method: "POST",
      body: JSON.stringify({ content, type }),
    }),

  ingest: (text: string) =>
    request<MemoryDto[]>("/api/v1/memory/ingest", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  update: (id: string, patch: { content?: string; type?: string; pinned?: boolean }) =>
    request<MemoryDto>(`/api/v1/memory/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),

  remove: (id: string) => request<void>(`/api/v1/memory/${id}`, { method: "DELETE" }),

  clear: () => request<{ deleted: number }>("/api/v1/memory", { method: "DELETE" }),

  exportUrl: "/api/v1/memory/export",
};
/**
 * 记忆接口封装。
 */

import { apiFetch } from "@/lib/api-client";
import type { MemoryDto, MemorySearchHitDto, MemoryStats, ScrubResult } from "../types";

// 走统一封装，才能带上用户自己填的 API Key
const request = apiFetch;

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

  /** 清洗记忆里的敏感信息（手机号、身份证等），会同步重建向量 */
  scrub: () =>
    request<ScrubResult>("/api/v1/memory/scrub", { method: "POST" }),

  clear: () => request<{ deleted: number }>("/api/v1/memory", { method: "DELETE" }),

  exportUrl: "/api/v1/memory/export",
};
/**
 * 统一的后端请求封装。
 *
 * 存在的唯一理由：**把用户在设置页填的 API Key 注入到每次请求的头里**。
 * 所有 feature 的 api/*.ts 都必须走这里，不要自己写 fetch ——
 * 漏掉一处就意味着那条链路用不上用户自己的 Key。
 */

import { absoluteUrl } from "@/lib/utils";

/** 与后端 app/core/overrides.py 的请求头保持一致 */
export const HEADER_MODEL_KEY = "X-Model-Key";
export const HEADER_MODEL_NAME = "X-Model-Name";
export const HEADER_EMBEDDING_KEY = "X-Embedding-Key";
export const HEADER_EMBEDDING_MODEL = "X-Embedding-Model";

export interface ByokConfig {
  modelKey: string;
  modelName: string;
  embeddingKey: string;
  embeddingModel: string;
}

/**
 * 从 localStorage 读当前配置。
 * 单独抽出来是因为 SSE 也需要用（原生 EventSource 不能自定义 header，
 * 所以我们用 fetch 流，那里要手动加头）。
 */
export function readByokHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem("ai-companion.byok");
    if (!raw) return {};
    const cfg = JSON.parse(raw) as Partial<ByokConfig>;
    const headers: Record<string, string> = {};
    if (cfg.modelKey && cfg.modelName) {
      headers[HEADER_MODEL_KEY] = cfg.modelKey;
      headers[HEADER_MODEL_NAME] = cfg.modelName;
    }
    if (cfg.embeddingModel) {
      // 没单独填 Embedding Key 时复用对话的 Key，多数平台是同一个
      headers[HEADER_EMBEDDING_MODEL] = cfg.embeddingModel;
      if (cfg.embeddingKey || cfg.modelKey) {
        headers[HEADER_EMBEDDING_KEY] = cfg.embeddingKey || cfg.modelKey || "";
      }
    }
    return headers;
  } catch {
    // localStorage 里的数据坏了也不能让页面崩，当作没配置处理
    return {};
  }
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(absoluteUrl(path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...readByokHeaders(),
      ...(init.headers as Record<string, string> | undefined),
    },
  });

  if (!response.ok) {
    throw new ApiError(await describeError(response), response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function describeError(response: Response): Promise<string> {
  const text = await response.text();
  // FastAPI 的校验错误是 JSON，尽量提取可读信息
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    const detail = parsed.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string; loc?: unknown[] };
      const field = Array.isArray(first.loc) ? first.loc.slice(-1).join(".") : "";
      return field ? `${field}: ${first.msg ?? "参数不合法"}` : (first.msg ?? "参数不合法");
    }
  } catch {
    // 不是 JSON，用原文
  }
  return `${response.status} ${response.statusText}`;
}
"use client";

/**
 * 校验与状态查询。请求头由 api-client 统一注入。
 */

import { apiFetch } from "@/lib/api-client";

export interface ValidateResult {
  ok: boolean;
  model?: string;
  message: string;
}

export interface StatusResult {
  using_user_key: boolean;
  model: string;
  key_hint: string;
  server_default_model: string;
  server_has_any_key: boolean;
  memory_encrypted: boolean;
}

export const settingsApi = {
  status: () => apiFetch<StatusResult>("/api/v1/settings/status"),

  validate: () => apiFetch<ValidateResult>("/api/v1/settings/validate", { method: "POST" }),
};
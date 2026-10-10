"use client";

/**
 * BYOK 配置的存取。
 *
 * ⚠️ 安全边界：Key **只存在浏览器 localStorage 里**，不发给任何第三方，
 * 也只通过请求头传给本地后端。后端不落盘、不入库。
 * 因此这个状态不放在其它 store 里，而是独立的、可随时清除的模块。
 */

import { MODEL_PROVIDERS, providerById, type ModelProvider } from "@ai-companion/shared";
import { create } from "zustand";

import type { ByokConfig } from "@/lib/api-client";

const STORAGE_KEY = "ai-companion.byok";

export interface SettingsState extends ByokConfig {
  /** 是否启用了用户自带 Key（关掉后完全走服务端配置） */
  enabled: boolean;
  /** 对话模型服务商 id */
  providerId: string;
  /** 向量化模型（可选，留空则用服务端默认） */
  embeddingEnabled: boolean;

  /** 是否已校验通过 */
  validated: boolean;
  validating: boolean;
  message: string | null;

  load: () => void;
  setProvider: (providerId: string) => void;
  setModelKey: (key: string) => void;
  setModelName: (name: string) => void;
  setEmbeddingKey: (key: string) => void;
  setEmbeddingModel: (name: string) => void;
  setEnabled: (enabled: boolean) => void;
  setEmbeddingEnabled: (on: boolean) => void;
  setValidating: (on: boolean, ok: boolean, message: string | null) => void;
  clear: () => void;
}

interface Persisted {
  enabled: boolean;
  providerId: string;
  modelKey: string;
  modelName: string;
  embeddingKey: string;
  embeddingModel: string;
  embeddingEnabled: boolean;
}

const DEFAULT_PROVIDER = "deepseek";

function loadPersisted(): Persisted {
  const fallback: Persisted = {
    enabled: false,
    providerId: DEFAULT_PROVIDER,
    modelKey: "",
    modelName: "",
    embeddingKey: "",
    embeddingModel: "",
    embeddingEnabled: false,
  };
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return fallback;
    return { ...fallback, ...(JSON.parse(raw) as Partial<Persisted>) };
  } catch {
    return fallback;
  }
}

export const useSettingsStore = create<SettingsState>()((set, get) => {
  const persist = () => {
    const s = get();
    if (typeof window === "undefined") return;
    const payload: Persisted = {
      // 关掉开关时保留 Key，重开后不用重填
      enabled: s.enabled,
      providerId: s.providerId,
      modelKey: s.modelKey,
      modelName: s.modelName,
      embeddingKey: s.embeddingKey,
      embeddingModel: s.embeddingModel,
      embeddingEnabled: s.embeddingEnabled,
    };
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    } catch {
      // 隐私模式下 localStorage 可能不可写，忽略即可（内存里仍可用）
    }
  };

  const after = () => {
    persist();
  };

  return {
    ...loadPersisted(),
    validated: false,
    validating: false,
    message: null,

    load() {
      set({ ...loadPersisted(), validated: false, message: null });
    },

    setProvider(providerId) {
      const provider = providerById(providerId);
      set({
        providerId,
        // 换服务商时把模型名换成该服务商的默认模型，避免留下上一个的模型名
        modelName: provider?.defaultModel ?? get().modelName,
        validated: false,
        message: null,
      });
      after();
    },

    setModelKey(modelKey) {
      set({ modelKey, validated: false, message: null });
      after();
    },

    setModelName(modelName) {
      set({ modelName, validated: false, message: null });
      after();
    },

    setEmbeddingKey(embeddingKey) {
      set({ embeddingKey });
      after();
    },

    setEmbeddingModel(embeddingModel) {
      set({ embeddingModel });
      after();
    },

    setEnabled(enabled) {
      set({ enabled, validated: false, message: null });
      after();
    },

    setEmbeddingEnabled(embeddingEnabled) {
      set({ embeddingEnabled });
      after();
    },

    setValidating(validating, validated, message) {
      set({ validating, validated, message });
    },

    clear() {
      if (typeof window !== "undefined") {
        try {
          window.localStorage.removeItem(STORAGE_KEY);
        } catch {
          /* 忽略 */
        }
      }
      set({
        enabled: false,
        providerId: DEFAULT_PROVIDER,
        modelKey: "",
        modelName: "",
        embeddingKey: "",
        embeddingModel: "",
        embeddingEnabled: false,
        validated: false,
        message: null,
      });
    },
  };
});

/** 当前生效的完整模型名（带 provider 前缀），供请求头使用 */
export function currentModelName(s: Pick<SettingsState, "enabled" | "providerId" | "modelName">): string {
  if (!s.enabled || !s.modelName) return "";
  // 模型名自带 provider 前缀时不再拼，避免出现 dashscope/dashscope/xxx
  if (s.modelName.includes("/")) return s.modelName;
  return `${s.providerId}/${s.modelName}`;
}

export function currentProvider(s: Pick<SettingsState, "providerId">): ModelProvider {
  return (
    providerById(s.providerId) ?? {
      id: s.providerId,
      label: s.providerId,
      envKey: "",
      defaultModel: "",
      models: [],
      keyHint: "",
    }
  );
}

export { MODEL_PROVIDERS };
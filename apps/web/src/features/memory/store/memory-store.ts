"use client";

/**
 * 记忆的全局状态：列表、搜索结果、统计、增删改。
 */

import { create } from "zustand";

import { memoryApi } from "../api/memory-api";
import {
  toHit,
  toMemory,
  type Memory,
  type MemoryHit,
  type MemoryStats,
  type MemoryType,
} from "../types";

interface MemoryState {
  items: Memory[];
  hits: MemoryHit[];
  stats: MemoryStats | null;
  query: string;
  loading: boolean;
  saving: boolean;
  error: string | null;

  load: () => Promise<void>;
  search: (query: string) => Promise<void>;
  create: (content: string, type: MemoryType) => Promise<boolean>;
  ingest: (text: string) => Promise<number>;
  update: (id: string, patch: { content?: string; type?: string; pinned?: boolean }) => Promise<void>;
  remove: (id: string) => Promise<void>;
  clearAll: () => Promise<void>;
  clearError: () => void;
}

export const useMemoryStore = create<MemoryState>()((set, get) => ({
  items: [],
  hits: [],
  stats: null,
  query: "",
  loading: false,
  saving: false,
  error: null,

  async load() {
    set({ loading: true, error: null });
    try {
      const [dtos, stats] = await Promise.all([memoryApi.list(), memoryApi.stats()]);
      set({ items: dtos.map(toMemory), stats });
    } catch (error) {
      set({ error: describe(error) });
    } finally {
      set({ loading: false });
    }
  },

  async search(query) {
    const trimmed = query.trim();
    set({ query: trimmed });
    if (!trimmed) {
      set({ hits: [] });
      return;
    }
    set({ loading: true, error: null });
    try {
      const hits = await memoryApi.search(trimmed);
      set({ hits: hits.map(toHit) });
    } catch (error) {
      set({ error: describe(error) });
    } finally {
      set({ loading: false });
    }
  },

  async create(content, type) {
    const trimmed = content.trim();
    if (!trimmed) return false;
    set({ saving: true, error: null });
    try {
      const created = toMemory(await memoryApi.create(trimmed, type));
      set((state) => ({ items: [created, ...state.items] }));
      return true;
    } catch (error) {
      set({ error: describe(error) });
      return false;
    } finally {
      set({ saving: false });
    }
  },

  async ingest(text) {
    const trimmed = text.trim();
    if (!trimmed) return 0;
    set({ saving: true, error: null });
    try {
      const created = (await memoryApi.ingest(trimmed)).map(toMemory);
      set((state) => ({ items: [...created, ...state.items] }));
      return created.length;
    } catch (error) {
      set({ error: describe(error) });
      return 0;
    } finally {
      set({ saving: false });
    }
  },

  async update(id, patch) {
    set({ saving: true, error: null });
    try {
      const updated = toMemory(await memoryApi.update(id, patch));
      set((state) => ({
        items: state.items.map((m) => (m.id === id ? updated : m)),
        hits: state.hits.map((h) => (h.memory.id === id ? { ...h, memory: updated } : h)),
      }));
    } catch (error) {
      set({ error: describe(error) });
    } finally {
      set({ saving: false });
    }
  },

  async remove(id) {
    set({ error: null });
    try {
      await memoryApi.remove(id);
      set((state) => ({
        items: state.items.filter((m) => m.id !== id),
        hits: state.hits.filter((h) => h.memory.id !== id),
      }));
    } catch (error) {
      set({ error: describe(error) });
    }
  },

  async clearAll() {
    set({ saving: true, error: null });
    try {
      await memoryApi.clear();
      set({ items: [], hits: [], stats: null });
      void get().load();
    } catch (error) {
      set({ error: describe(error) });
    } finally {
      set({ saving: false });
    }
  },

  clearError() {
    set({ error: null });
  },
}));

function describe(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
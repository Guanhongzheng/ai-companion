/**
 * 记忆模块的类型与映射。后端返回 snake_case，这里统一转成 camelCase。
 */

export const MEMORY_TYPES = ["profile", "preference", "fact", "event"] as const;
export type MemoryType = (typeof MEMORY_TYPES)[number];

export const MEMORY_TYPE_META: Record<
  MemoryType,
  { label: string; hint: string }
> = {
  profile: { label: "身份", hint: "职业、居住、家人、宠物" },
  preference: { label: "喜好", hint: "喜欢与讨厌的东西" },
  fact: { label: "事实", hint: "其他长期稳定的信息" },
  event: { label: "事件", hint: "近期的计划与安排" },
};

export interface MemoryDto {
  id: string;
  type: string;
  content: string;
  source: string;
  confidence: number;
  hit_count: number;
  pinned: boolean;
  encrypted: boolean;
  created_at: string;
  updated_at: string;
}

export interface Memory {
  id: string;
  type: MemoryType;
  content: string;
  source: string;
  confidence: number;
  hitCount: number;
  pinned: boolean;
  encrypted: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface MemorySearchHitDto {
  memory: MemoryDto;
  score: number;
  vector_score: number;
  lexical_score: number;
  reranker: string;
}

/** 搜索命中项（已转成 camelCase） */
export interface MemoryHit {
  memory: Memory;
  score: number;
  vector_score: number;
  lexical_score: number;
  reranker: string;
}

export interface MemoryStats {
  total: number;
  by_type: Record<string, number>;
  encrypted: boolean;
  vector_store: string;
  embedder: string;
}

/** 对话时召回的记忆（SSE memory 事件） */
export interface RecalledMemory {
  id: string;
  content: string;
  score: number;
  reranker: string;
}

export function toMemory(dto: MemoryDto): Memory {
  return {
    id: dto.id,
    type: (MEMORY_TYPES.includes(dto.type as MemoryType) ? dto.type : "fact") as MemoryType,
    content: dto.content,
    source: dto.source,
    confidence: dto.confidence,
    hitCount: dto.hit_count,
    pinned: dto.pinned,
    encrypted: dto.encrypted,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export function toHit(dto: MemorySearchHitDto): MemoryHit {
  return { ...dto, memory: toMemory(dto.memory) };
}

export const SOURCE_LABELS: Record<string, string> = {
  rules: "规则抽取",
  llm: "模型抽取",
  manual: "手动添加",
  seed: "示例数据",
};
"use client";

import {
  AlertCircle,
  Brain,
  Download,
  Loader2,
  Pin,
  PinOff,
  Plus,
  Search,
  ShieldCheck,
  Trash2,
  Wand2,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { absoluteUrl } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { memoryApi } from "../api/memory-api";
import { useMemoryStore } from "../store/memory-store";
import {
  MEMORY_TYPES,
  MEMORY_TYPE_META,
  SOURCE_LABELS,
  type Memory,
  type MemoryType,
} from "../types";

export function MemoryPanel() {
  const {
    items,
    hits,
    stats,
    query,
    loading,
    saving,
    error,
    load,
    search,
    create,
    ingest,
    update,
    remove,
    clearAll,
    clearError,
  } = useMemoryStore();

  const [draft, setDraft] = useState("");
  const [newType, setNewType] = useState<MemoryType>("fact");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState("");
  const [confirmClear, setConfirmClear] = useState(false);
  const [scrubbing, setScrubbing] = useState(false);
  const [scrubNote, setScrubNote] = useState<string | null>(null);

  useEffect(() => {
    void load();
  }, [load]);

  const handleScrub = async () => {
    setScrubbing(true);
    setScrubNote(null);
    try {
      const result = await memoryApi.scrub();
      setScrubNote(
        result.cleaned > 0
          ? `已脱敏 ${result.cleaned} 条（${result.kinds.join("、")}）`
          : "没有需要脱敏的记忆",
      );
      // 清洗会改内容，必须重新拉列表，否则看到的还是旧正文
      await load();
    } catch (error) {
      setScrubNote(error instanceof Error ? error.message : "清洗失败");
    } finally {
      setScrubbing(false);
    }
  };

  const grouped = useMemo(() => {
    const source = query.trim() ? hits.map((h) => h.memory) : items;
    return MEMORY_TYPES.map((type) => ({
      type,
      items: source.filter((m) => m.type === type),
    })).filter((g) => g.items.length > 0);
  }, [items, hits, query]);

  const scoreOf = (id: string) => hits.find((h) => h.memory.id === id)?.score;

  const handleCreate = async () => {
    if (await create(draft, newType)) setDraft("");
  };

  const handleIngest = async () => {
    if (!draft.trim()) return;
    // 手动输入的一长段话走抽取；短句直接当一条记忆存
    const saved =
      draft.trim().length > 24 ? await ingest(draft) : (await create(draft, newType)) ? 1 : 0;
    if (saved > 0) setDraft("");
  };

  const handleExport = () => {
    window.open(absoluteUrl(memoryApi.exportUrl), "_blank");
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4 py-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-lg font-medium">
            <Brain className="h-5 w-5" />
            长期记忆
          </h1>
          <p className="mt-1 text-xs text-muted-foreground">
            AI 从对话中提炼的、关于你的稳定信息。会用于个性化回复，也可以随时删除。
          </p>
        </div>
        <div className="flex shrink-0 gap-1">
          <button
            type="button"
            onClick={handleExport}
            title="导出为 JSON"
            className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <Download className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => setConfirmClear(true)}
            title="清空全部"
            className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </header>

      {stats && (
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
          <span className="rounded-full bg-muted px-2 py-0.5">共 {stats.total} 条</span>
          <span className="rounded-full bg-muted px-2 py-0.5">
            向量库 {stats.vector_store}
          </span>
          <span className="rounded-full bg-muted px-2 py-0.5">
            向量化 {stats.embedder === "hashing" ? "哈希（本地）" : stats.embedder}
          </span>
          <span
            className={cn(
              "rounded-full px-2 py-0.5",
              stats.encrypted ? "bg-emotion-primary/15" : "bg-amber-500/15",
            )}
          >
            {stats.encrypted ? "正文已加密" : "正文未加密"}
          </span>
          <span
            className={cn(
              "rounded-full px-2 py-0.5",
              stats.sensitive > 0 ? "bg-destructive/15 text-destructive" : "bg-emotion-primary/15",
            )}
          >
            {stats.safety_filter ? "自动脱敏已开" : "自动脱敏已关"}
            {stats.sensitive > 0 && ` · ${stats.sensitive} 条待清洗`}
          </span>
        </div>
      )}

      {/* 有待清洗的敏感信息时才出现，避免平时占地方 */}
      {stats && stats.sensitive > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/5 p-3">
          <AlertCircle className="h-4 w-4 shrink-0 text-destructive" />
          <p className="mr-auto text-xs leading-relaxed">
            有 {stats.sensitive} 条记忆里还留着手机号、身份证这类信息。
            新写入的记忆会自动脱敏，但这些是之前存进去的。
          </p>
          <button
            type="button"
            onClick={() => void handleScrub()}
            disabled={scrubbing}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-white transition-opacity",
              scrubbing ? "cursor-not-allowed opacity-50" : "bg-destructive hover:opacity-90",
            )}
          >
            {scrubbing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
            {scrubbing ? "清洗中" : "立即脱敏"}
          </button>
          {scrubNote && <span className="text-xs text-muted-foreground">{scrubNote}</span>}
        </div>
      )}

      {/* 搜索 + 新增 */}
      <div className="flex flex-col gap-2">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => void search(e.target.value)}
            placeholder="语义搜索记忆，比如「我住在哪里」"
            className="w-full rounded-xl border border-border bg-background py-2 pl-9 pr-3 text-sm outline-none transition-colors focus:border-emotion-primary/60"
          />
        </div>

        <div className="flex gap-2">
          <select
            value={newType}
            onChange={(e) => setNewType(e.target.value as MemoryType)}
            className="rounded-lg border border-border bg-background px-2 text-xs outline-none"
          >
            {MEMORY_TYPES.map((t) => (
              <option key={t} value={t}>
                {MEMORY_TYPE_META[t].label}
              </option>
            ))}
          </select>
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.nativeEvent.isComposing) void handleCreate();
            }}
            placeholder="手动添加一条记忆（超过 24 字会走自动抽取）"
            className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none transition-colors focus:border-emotion-primary/60"
          />
          <button
            type="button"
            onClick={() => void handleCreate()}
            disabled={!draft.trim() || saving}
            title="添加"
            className="rounded-lg bg-emotion-primary px-3 text-white disabled:opacity-40"
          >
            <Plus className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => void handleIngest()}
            disabled={!draft.trim() || saving}
            title="从这段话里自动抽取记忆"
            className="rounded-lg border border-border px-3 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-40"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-lg bg-destructive/10 p-2.5 text-xs text-destructive">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span className="flex-1">{error}</span>
          <button type="button" onClick={clearError}>
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {loading && items.length === 0 && (
        <p className="py-8 text-center text-xs text-muted-foreground">加载中…</p>
      )}

      {!loading && grouped.length === 0 && (
        <p className="py-8 text-center text-xs text-muted-foreground">
          {query.trim() ? "没有找到相关记忆" : "还没有记忆，去聊几句，AI 会自动记住关于你的事"}
        </p>
      )}

      {grouped.map((group) => (
        <section key={group.type}>
          <h2 className="mb-1.5 text-[11px] uppercase tracking-wide text-muted-foreground">
            {MEMORY_TYPE_META[group.type].label}
            <span className="ml-1.5 normal-case tracking-normal opacity-70">
              {MEMORY_TYPE_META[group.type].hint}
            </span>
          </h2>
          <ul className="space-y-1.5">
            {group.items.map((memory) => (
              <MemoryRow
                key={memory.id}
                memory={memory}
                score={scoreOf(memory.id)}
                editing={editingId === memory.id}
                editingText={editingText}
                onEditStart={() => {
                  setEditingId(memory.id);
                  setEditingText(memory.content);
                }}
                onEditText={setEditingText}
                onEditCancel={() => setEditingId(null)}
                onEditSave={async () => {
                  await update(memory.id, { content: editingText });
                  setEditingId(null);
                }}
                onPin={() => void update(memory.id, { pinned: !memory.pinned })}
                onDelete={() => void remove(memory.id)}
              />
            ))}
          </ul>
        </section>
      ))}

      {confirmClear && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-5">
            <h3 className="text-sm font-medium">清空全部记忆？</h3>
            <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
              这会永久删除全部 {items.length} 条记忆，包括向量库里的索引，且无法恢复。
              建议先导出备份。
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmClear(false)}
                className="rounded-lg border border-border px-3 py-1.5 text-xs"
              >
                取消
              </button>
              <button
                type="button"
                onClick={async () => {
                  await clearAll();
                  setConfirmClear(false);
                }}
                className="rounded-lg bg-destructive px-3 py-1.5 text-xs text-white"
              >
                确认清空
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface RowProps {
  memory: Memory;
  score?: number;
  editing: boolean;
  editingText: string;
  onEditStart: () => void;
  onEditText: (text: string) => void;
  onEditCancel: () => void;
  onEditSave: () => Promise<void>;
  onPin: () => void;
  onDelete: () => void;
}

function MemoryRow({
  memory,
  score,
  editing,
  editingText,
  onEditStart,
  onEditText,
  onEditCancel,
  onEditSave,
  onPin,
  onDelete,
}: RowProps) {
  return (
    <li
      className={cn(
        "group rounded-xl border border-border bg-card px-3 py-2 transition-colors",
        memory.pinned && "border-emotion-primary/40 bg-emotion-primary/5",
      )}
    >
      {editing ? (
        <div className="flex gap-2">
          <input
            autoFocus
            value={editingText}
            onChange={(e) => onEditText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.nativeEvent.isComposing) void onEditSave();
              if (e.key === "Escape") onEditCancel();
            }}
            className="flex-1 rounded-lg border border-border bg-background px-2.5 py-1.5 text-sm outline-none focus:border-emotion-primary/60"
          />
          <button
            type="button"
            onClick={() => void onEditSave()}
            className="rounded-lg bg-emotion-primary px-2.5 text-xs text-white"
          >
            保存
          </button>
          <button
            type="button"
            onClick={onEditCancel}
            className="rounded-lg border border-border px-2.5 text-xs"
          >
            取消
          </button>
        </div>
      ) : (
        <>
          <div className="flex items-start gap-2">
            <p className="flex-1 text-sm leading-relaxed">{memory.content}</p>
            <div className="flex shrink-0 gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
              <button
                type="button"
                onClick={onEditStart}
                title="编辑"
                className="rounded p-1 text-muted-foreground hover:text-foreground"
              >
                <PencilIcon />
              </button>
              <button
                type="button"
                onClick={onPin}
                title={memory.pinned ? "取消置顶" : "置顶"}
                className="rounded p-1 text-muted-foreground hover:text-foreground"
              >
                {memory.pinned ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
              </button>
              <button
                type="button"
                onClick={onDelete}
                title="删除"
                className="rounded p-1 text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
            <span>{SOURCE_LABELS[memory.source] ?? memory.source}</span>
            <span>置信度 {(memory.confidence * 100).toFixed(0)}%</span>
            {memory.hitCount > 0 && <span>被想起 {memory.hitCount} 次</span>}
            {score !== undefined && (
              <span className="rounded bg-emotion-primary/15 px-1.5 text-emotion-primary">
                匹配 {(score * 100).toFixed(0)}%
              </span>
            )}
            {memory.encrypted && <span>🔒</span>}
          </p>
        </>
      )}
    </li>
  );
}

function PencilIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="h-3.5 w-3.5"
      aria-hidden
    >
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  );
}
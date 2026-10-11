"use client";

/**
 * 群聊摘要：触发按钮 + 展示面板。
 *
 * 定位：**AI 不参与讨论，只负责收拢信息**。
 * 所以它只读、只展示，不做任何「自动发到群里」的事 ——
 * AI 擅自往群里发言恰恰是它最不该做的事。
 *
 * ⚠️ 面板渲染在**消息区**，不在输入框附近。
 * 最初整个卡片被塞在 GroupMentionBar 里（输入框正上方），结果被右下角
 * 浮动的 MusicDock 整个盖住 —— 真实浏览器端到端验证时才发现。
 * 摘要是对对话内容的整理，属于消息流的一部分，放在消息区也更合逻辑。
 * 按钮与面板通过 chat-store 解耦。
 */

import { AlertCircle, ClipboardList, Loader2, Users, X } from "lucide-react";

import { useChatStore } from "@/stores/chat-store";
import { cn } from "@/lib/utils";

/** 消息区的摘要面板 */
export function GroupSummaryPanel() {
  const summary = useChatStore((s) => s.groupSummary);
  const loading = useChatStore((s) => s.summarizeLoading);
  const open = useChatStore((s) => s.groupSummaryOpen);
  const close = useChatStore((s) => s.closeSummary);

  if (!open) return null;

  return (
    <div className="border-b border-border bg-emotion-secondary/5 px-4 py-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-xs font-medium">
          <ClipboardList className="h-3.5 w-3.5" />
          群聊摘要
        </span>
        <button
          type="button"
          onClick={close}
          aria-label="关闭摘要"
          className="text-muted-foreground transition-colors hover:text-foreground"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      {loading && (
        <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          正在收拢讨论…
        </p>
      )}

      {!loading && !summary && (
        <p className="flex items-center gap-1.5 text-[11px] text-destructive">
          <AlertCircle className="h-3 w-3 shrink-0" />
          暂时无法生成摘要
        </p>
      )}

      {!loading && summary && (
        <div className="flex flex-col gap-2.5 text-[11px] leading-relaxed">
          {summary.topic && <p className="font-medium">【{summary.topic}】</p>}

          {summary.participants.length > 0 && (
            <p className="flex items-center gap-1.5 text-muted-foreground">
              <Users className="h-3 w-3 shrink-0" />
              {summary.participants
                .slice(0, 5)
                .map((p) => `${p.name}(${p.count})`)
                .join("、")}
            </p>
          )}

          {summary.conclusions.length > 0 && (
            <div>
              <p className="mb-1 text-muted-foreground">结论</p>
              <ul className="flex flex-col gap-0.5">
                {summary.conclusions.map((c) => (
                  <li key={c}>· {c}</li>
                ))}
              </ul>
            </div>
          )}

          {summary.todos.length > 0 && (
            <div>
              <p className="mb-1 text-muted-foreground">待办</p>
              <ul className="flex flex-col gap-0.5">
                {summary.todos.map((t) => (
                  <li key={t}>· {t}</li>
                ))}
              </ul>
            </div>
          )}

          <p className="text-muted-foreground/70">
            覆盖 {summary.message_count} 条发言 ·{" "}
            {summary.source === "llm" ? "模型总结" : "规则总结（未接模型）"}
          </p>
        </div>
      )}
    </div>
  );
}

/** 输入框旁的触发按钮 */
export function GroupSummaryButton() {
  const loading = useChatStore((s) => s.summarizeLoading);
  const run = useChatStore((s) => s.runSummary);

  return (
    <button
      type="button"
      onClick={() => void run()}
      disabled={loading}
      className={cn(
        "shrink-0 rounded-full px-2.5 py-1 text-[11px] transition-colors",
        loading
          ? "cursor-not-allowed bg-muted text-muted-foreground"
          : "bg-muted text-muted-foreground hover:bg-emotion-secondary/20 hover:text-foreground",
      )}
    >
      {loading ? "总结中…" : "总结群聊"}
    </button>
  );
}

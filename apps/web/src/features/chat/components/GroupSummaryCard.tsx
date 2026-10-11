"use client";

/**
 * 群聊总结卡片。
 *
 * 定位很清楚：**AI 不参与讨论，只负责收拢信息**。
 * 所以这里只读、只展示，不做任何「自动发到群里」的骚操作 ——
 * AI 擅自往群里发言恰恰是它最不该做的事。
 */

import { AlertCircle, ClipboardList, Loader2, Users, X } from "lucide-react";
import { useState } from "react";

import { chatApi } from "@/features/chat/api/chat-api";
import { cn } from "@/lib/utils";
import type { GroupSummary } from "@/features/chat/types";

interface Props {
  sessionId: string;
}

export function GroupSummaryCard({ sessionId }: Props) {
  const [summary, setSummary] = useState<GroupSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  const run = async () => {
    setLoading(true);
    setError(null);
    setOpen(true);
    try {
      setSummary(await chatApi.summarize(sessionId));
    } catch (err) {
      setSummary(null);
      setError(err instanceof Error ? err.message : "总结失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => void run()}
        disabled={loading}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] transition-colors",
          loading
            ? "cursor-not-allowed bg-muted text-muted-foreground"
            : "bg-emotion-secondary/15 text-muted-foreground hover:text-foreground",
        )}
      >
        {loading ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <ClipboardList className="h-3 w-3" />
        )}
        {loading ? "总结中" : "总结群聊"}
      </button>

      {open && (
        <div className="border-b border-border bg-emotion-secondary/5 px-4 py-3">
          <div className="mb-2 flex items-center justify-between gap-2">
            <span className="flex items-center gap-1.5 text-xs font-medium">
              <ClipboardList className="h-3.5 w-3.5" />
              群聊摘要
            </span>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="关闭摘要"
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>

          {loading && <p className="text-[11px] text-muted-foreground">正在收拢讨论…</p>}

          {error && (
            <p className="flex items-center gap-1.5 text-[11px] text-destructive">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              {error}
            </p>
          )}

          {summary && !loading && (
            <div className="flex flex-col gap-2.5 text-[11px] leading-relaxed">
              {summary.topic && (
                <p className="font-medium">【{summary.topic}】</p>
              )}

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
                覆盖 {summary.message_count} 条发言 ·
                {summary.source === "llm" ? " 模型总结" : " 规则总结（未接模型）"}
              </p>
            </div>
          )}
        </div>
      )}
    </>
  );
}
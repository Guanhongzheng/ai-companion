"use client";

import type { Session } from "@ai-companion/shared";
import { Bot, MessageSquare, Plus, Trash2, Users } from "lucide-react";
import { useMemo } from "react";

import { useChatStore } from "@/stores/chat-store";
import { cn } from "@/lib/utils";
import { SESSION_TYPE_META, SESSION_TYPE_ORDER } from "../types";

const TYPE_ICON = {
  ai: Bot,
  direct: MessageSquare,
  group: Users,
} as const satisfies Record<Session["type"], typeof Bot>;

export function SessionList() {
  const sessions = useChatStore((s) => s.sessions);
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const loading = useChatStore((s) => s.loading);
  const selectSession = useChatStore((s) => s.selectSession);
  const createSession = useChatStore((s) => s.createSession);
  const removeSession = useChatStore((s) => s.removeSession);

  const grouped = useMemo(
    () =>
      SESSION_TYPE_ORDER.map((type) => ({
        type,
        meta: SESSION_TYPE_META[type],
        items: sessions.filter((s) => s.type === type),
      })).filter((group) => group.items.length > 0),
    [sessions],
  );

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-border bg-card/40">
      <header className="flex items-center justify-between px-4 py-3">
        <h2 className="text-sm font-medium">会话</h2>
        <div className="flex gap-1">
          {SESSION_TYPE_ORDER.map((type) => {
            const Icon = TYPE_ICON[type];
            return (
              <button
                key={type}
                type="button"
                title={`新建${SESSION_TYPE_META[type].label}`}
                onClick={() => void createSession(type)}
                className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <Icon className="h-4 w-4" />
                <Plus className="h-2.5 w-2.5 -ml-1 -mt-1" />
              </button>
            );
          })}
        </div>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto px-2 pb-4">
        {loading && sessions.length === 0 && (
          <p className="px-2 py-4 text-xs text-muted-foreground">加载中…</p>
        )}

        {!loading && sessions.length === 0 && (
          <p className="px-2 py-4 text-xs text-muted-foreground">
            还没有会话，点右上角图标新建一个。
          </p>
        )}

        {grouped.map((group) => (
          <section key={group.type}>
            <h3 className="px-2 pb-1 text-[11px] uppercase tracking-wide text-muted-foreground">
              {group.meta.label}
              <span className="ml-1.5 normal-case tracking-normal opacity-70">
                {group.meta.hint}
              </span>
            </h3>
            <ul className="space-y-0.5">
              {group.items.map((session) => (
                <li key={session.id}>
                  <div
                    className={cn(
                      "group flex items-center gap-2 rounded-md px-2 py-2 transition-colors",
                      session.id === activeSessionId
                        ? "bg-emotion-primary/15 text-foreground"
                        : "hover:bg-muted",
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => void selectSession(session.id)}
                      className="flex min-w-0 flex-1 items-center gap-2 text-left"
                    >
                      <span
                        className={cn(
                          "h-1.5 w-1.5 shrink-0 rounded-full",
                          session.unreadCount > 0 ? "bg-emotion-primary" : "bg-transparent",
                        )}
                      />
                      <span className="truncate text-sm">{session.title}</span>
                      {session.memberCount > 2 && (
                        <span className="shrink-0 text-[10px] text-muted-foreground">
                          {session.memberCount}
                        </span>
                      )}
                    </button>
                    <button
                      type="button"
                      title="删除会话"
                      onClick={() => void removeSession(session.id)}
                      className="shrink-0 rounded p-1 text-muted-foreground opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </aside>
  );
}
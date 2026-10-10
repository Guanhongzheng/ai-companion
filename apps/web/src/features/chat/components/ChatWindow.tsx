"use client";

import { emotionThemeOf } from "@ai-companion/shared";
import { AlertCircle, Sparkles, X } from "lucide-react";
import { useEffect } from "react";

import { useChatStore } from "@/stores/chat-store";
import { applyEmotionTheme } from "@/features/theme/lib/apply-emotion-theme";
import { cn } from "@/lib/utils";
import { ChatComposer } from "./ChatComposer";
import { MessageList } from "./MessageList";
import { SessionList } from "./SessionList";

export function ChatWindow() {
  const sessions = useChatStore((s) => s.sessions);
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const emotion = useChatStore((s) => s.emotion);
  const emotionConfidence = useChatStore((s) => s.emotionConfidence);
  const model = useChatStore((s) => s.model);
  const mocked = useChatStore((s) => s.mocked);
  const error = useChatStore((s) => s.error);
  const clearError = useChatStore((s) => s.clearError);
  const loadSessions = useChatStore((s) => s.loadSessions);

  // 首屏拉会话
  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  // 情绪一变，主题色 / 壁纸渐变立刻跟随
  useEffect(() => {
    applyEmotionTheme(emotion);
  }, [emotion]);

  const active = sessions.find((s) => s.id === activeSessionId);
  const theme = emotionThemeOf(emotion);

  return (
    <div className="relative flex h-screen overflow-hidden">
      {/* 动态壁纸：先用 CSS Gradient 占位，M4 再接 Three.js + Web Audio */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10 transition-[background] duration-700"
        style={{ backgroundImage: "var(--wallpaper-gradient)" }}
      />

      <SessionList />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 backdrop-blur">
          <div className="min-w-0">
            <h1 className="truncate text-sm font-medium">{active?.title ?? "对话中枢"}</h1>
            <p className="truncate text-xs text-muted-foreground">
              {active?.memberCount && active.memberCount > 2
                ? `${active.memberCount} 人群聊`
                : active?.type === "ai"
                  ? "AI 伴侣 · 全量能力"
                  : "好友单聊 · AI 辅助"}
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <span
              className={cn(
                "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs",
                "bg-muted text-muted-foreground",
              )}
              style={{ boxShadow: emotion === "neutral" ? undefined : `0 0 0 1px hsl(${theme.primary} / .35)` }}
            >
              <span
                aria-hidden
                className="h-1.5 w-1.5 rounded-full"
                style={{ backgroundColor: `hsl(${theme.primary})` }}
              />
              {theme.label}
              <span className="opacity-60">{Math.round(emotionConfidence * 100)}%</span>
            </span>

            {model && (
              <span
                title={mocked ? "未检测到模型 Key，当前为本地模拟回复" : `实际调用模型：${model}`}
                className="flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground"
              >
                <Sparkles className="h-3 w-3" />
                {mocked ? "模拟模式" : model.split("/").pop()}
              </span>
            )}
          </div>
        </header>

        {error && (
          <div className="flex items-start gap-2 border-b border-destructive/30 bg-destructive/10 px-4 py-2 text-xs text-destructive">
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span className="flex-1">{error}</span>
            <button type="button" onClick={clearError} aria-label="关闭提示">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        <MessageList />
        <ChatComposer />
      </main>
    </div>
  );
}
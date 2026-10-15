"use client";

import { emotionThemeOf } from "@ai-companion/shared";
import { AlertCircle, Brain, KeyRound, Menu, Settings, Sparkles, Users, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useChatStore, type AssistantAction } from "@/stores/chat-store";
import { MusicDock } from "@/features/music/components/MusicDock";
import { currentModelName, useSettingsStore } from "@/features/settings/store/settings-store";
import { applyEmotionTheme, watchViewport } from "@/features/theme/lib/apply-emotion-theme";
import { EmotionWallpaper } from "@/features/wallpaper/components/EmotionWallpaper";
import { cn } from "@/lib/utils";
import { ChatComposer } from "./ChatComposer";
import { GroupSummaryPanel } from "./GroupSummaryCard";
import { MessageList } from "./MessageList";
import { SessionList } from "./SessionList";

export function ChatWindow() {
  const sessions = useChatStore((s) => s.sessions);
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const emotion = useChatStore((s) => s.emotion);
  const emotionConfidence = useChatStore((s) => s.emotionConfidence);
  const model = useChatStore((s) => s.model);
  const mocked = useChatStore((s) => s.mocked);
  const recalledMemories = useChatStore((s) => s.recalledMemories);
  const learnedMemories = useChatStore((s) => s.learnedMemories);
  const waitingForMention = useChatStore((s) => s.waitingForMention);
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
    // 屏幕尺寸变化后重算：气泡宽度是行内样式，不会自己更新
    watchViewport(emotion);
  }, [emotion]);

  const [assistantAction, setAssistantAction] = useState<AssistantAction | null>(null);
  // 移动端侧栏抽屉。桌面端（lg 以上）侧栏常驻，这个状态不起作用。
  const [drawerOpen, setDrawerOpen] = useState(false);
  const byokEnabled = useSettingsStore((s) => s.enabled);
  const byokProvider = useSettingsStore((s) => s.providerId);
  const byokModelName = useSettingsStore((s) => s.modelName);
  const byokModel = byokEnabled ? currentModelName({ enabled: byokEnabled, providerId: byokProvider, modelName: byokModelName }) : "";

  const active = sessions.find((s) => s.id === activeSessionId);
  const theme = emotionThemeOf(emotion);

  return (
    <div className="relative flex h-screen overflow-hidden">
      {/* 动态壁纸：Three.js 粒子场，WebGL 不可用时自动退回 CSS Gradient */}
      <EmotionWallpaper />

      {/*
        🔴 侧栏在移动端是**抽屉**，不是常驻列。
        原来它是 `w-72 shrink-0` 固定宽度且没有断点 —— 手机上直接占满 288px
        且无法收起，聊天区被完全挤出屏幕，整站等于不可用。

        ⚠️ 遮罩必须和抽屉**平级**，不能塞进抽屉容器里。
        塞进去时父容器的 z-30 会建立层叠上下文，遮罩的 -z-10 就被压到
        这个上下文的最底部，结果被 <main> 拦截 —— 遮罩看得见但点不动，
        抽屉关不掉。这正是浏览器点击测试抓出来的。
        */}
      {drawerOpen && (
        <button
          type="button"
          aria-label="关闭会话列表"
          onClick={() => setDrawerOpen(false)}
          className="fixed inset-0 z-20 bg-black/50 backdrop-blur-sm lg:hidden"
        />
      )}

      <div
        className={cn(
          "fixed inset-y-0 left-0 z-30 lg:static lg:z-auto",
          "transition-transform duration-200 ease-out",
          drawerOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
        )}
      >
        <SessionList onNavigate={() => setDrawerOpen(false)} />
      </div>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-2 border-b border-border px-3 py-2.5 backdrop-blur sm:px-4 sm:py-3">
          {/* 汉堡按钮只在移动端出现 */}
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            aria-label="打开会话列表"
            className="-ml-1 shrink-0 rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="min-w-0">
            <h1 className="truncate text-sm font-medium">{active?.title ?? "对话中枢"}</h1>
            <p className="truncate text-xs text-muted-foreground">
              {active?.memberCount && active.memberCount > 2
                ? `${active.memberCount} 人群聊`
                : active?.type === "group"
                  ? "AI 只在被 @ 时回复"
                  : active?.type === "direct"
                    ? "AI 辅助，不冒充你的朋友"
                    : "AI 伴侣 · 全量能力"}
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

            {byokModel && (
              <span
                title={`正在使用你自己填的 Key 调用 ${byokModel}`}
                className="flex items-center gap-1 rounded-full bg-emotion-primary/15 px-2.5 py-1 text-xs text-emotion-primary"
              >
                <KeyRound className="h-3 w-3" />
                自带 Key
              </span>
            )}

            <Link
              href="/memory"
              title="管理长期记忆"
              className="flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted/70 hover:text-foreground"
            >
              <Brain className="h-3 w-3" />
              记忆
            </Link>

            <Link
              href="/settings"
              title="设置：自带 API Key"
              className="rounded-full bg-muted p-1.5 text-muted-foreground transition-colors hover:bg-muted/70 hover:text-foreground"
            >
              <Settings className="h-3.5 w-3.5" />
            </Link>
          </div>
        </header>

        {active?.type === "group" && active.memberCount > 2 && (
          <div className="flex items-center gap-1.5 border-b border-border px-4 py-1.5 text-[11px] text-muted-foreground">
            <Users className="h-3 w-3" />
            群里有 {active.memberCount - 1} 位其他成员
            {waitingForMention && <span className="text-emotion-primary">· 试试 @ 它</span>}
          </div>
        )}

        {/* 群聊摘要与「想起了/记住了」同属消息区：
            放输入框上方会被右下角浮动的 MusicDock 盖住 */}
        <GroupSummaryPanel />

        {recalledMemories.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 border-b border-border border-l-2 border-l-emotion-primary bg-emotion-primary/5 px-4 py-2 text-[11px]">
            <span className="text-muted-foreground">AI 想起了：</span>
            {recalledMemories.map((m) => (
              <span
                key={m.id}
                className="rounded-full bg-background px-2 py-0.5 ring-1 ring-border"
              >
                {m.content}
                <span className="ml-1 opacity-50">{(m.score * 100).toFixed(0)}%</span>
              </span>
            ))}
          </div>
        )}

        {/* 「记住了」是后台抽取的结果，做不到实时推送，
            所以它必然比正文晚一点出现 —— 但必须看得见，
            否则 AI 学到了东西用户毫无感知，抽取失败也一样静悄悄。 */}
        {learnedMemories.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 border-b border-border border-l-2 border-l-emotion-secondary bg-muted/40 px-4 py-2 text-[11px]">
            <span className="flex items-center gap-1 text-muted-foreground">
              <Brain className="h-3 w-3" />
              我记住了：
            </span>
            {learnedMemories.map((m) => (
              <span
                key={m.id}
                className="rounded-full bg-background px-2 py-0.5 ring-1 ring-border"
              >
                {m.content}
              </span>
            ))}
          </div>
        )}

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
        <ChatComposer
          sessionType={(active?.type ?? "ai") as "ai" | "direct" | "group"}
          action={assistantAction}
          onActionChange={setAssistantAction}
        />
      </main>

      {/*
        情绪歌单：播放中的音频会被壁纸的频谱分析器接管。

        ⚠️ 位置定在聊天区**右上角**而不是原来的右下角。
        右下角会和输入框右上角重叠 —— 群聊的「总结群聊」按钮正好在那儿，
        而 MusicDock 内部是 pointer-events-auto（它本身要可点），
        结果它把那个按钮整个挡住，真实用户点不动。
        这个问题是通过浏览器端到端点击测试发现的，截图上看不出异常。
      */}
      <div className="pointer-events-none fixed right-4 top-16 z-10">
        <MusicDock />
      </div>
    </div>
  );
}
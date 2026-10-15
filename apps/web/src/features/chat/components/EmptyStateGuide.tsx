"use client";

/**
 * 首屏引导 / 空状态。
 *
 * 此前这里只有一句「还没有会话，点右上角图标新建一个」——
 * 告诉用户**怎么做**，但没说这东西**能干什么**。
 * 三类会话行为差异很大（AI 伴侣全量能力 / 好友不冒充真人 / 群聊只被 @ 时说话），
 * 用户不理解这个差异，就只能靠乱试来发现，等于把产品说明书推给了用户自己。
 *
 * 设计取舍：
 * * 不做多步向导 —— 那���东西对「只是想试试」的用户是灾难，一次性把差异摆出来更有效
 * * 每张卡片可以直接建对应会话 —— 看完就能上手，不用再回头找新建按钮
 * * 真的没有会话才显示（有过会话就不打扰）
 */

import { Bot, MessageSquareQuote, Users } from "lucide-react";

import { useChatStore } from "@/stores/chat-store";
import { cn } from "@/lib/utils";
import type { Session } from "@ai-companion/shared";

interface GuideCard {
  type: Session["type"];
  icon: typeof Bot;
  title: string;
  /** 一句话说清「它和别的有什么不同」 */
  lead: string;
  /** 具体能做什么 */
  points: string[];
}

const CARDS: GuideCard[] = [
  {
    type: "ai",
    icon: Bot,
    title: "AI 伴侣",
    lead: "全量能力，像真人一样聊天",
    points: ["会记住你的偏好与近况", "情绪自适应主题与壁纸", "支持语音、图片输入"],
  },
  {
    type: "direct",
    icon: MessageSquareQuote,
    title: "好友单聊",
    lead: "AI 辅助你回复，不冒充你的朋友",
    points: ["润色、改写、翻译", "总结长文要点", "给建议回复"],
  },
  {
    type: "group",
    icon: Users,
    title: "群聊",
    lead: "只在被 @ 时开口，绝不抢话",
    points: ["多成员各自发言", "一键总结议题与待办", "情绪感知"],
  },
];

export function EmptyStateGuide() {
  const sessions = useChatStore((s) => s.sessions);
  const loading = useChatStore((s) => s.loading);
  const createSession = useChatStore((s) => s.createSession);

  // 有过会话就不打扰 —— 引导是给新用户的，不是常驻装饰
  if (loading || sessions.length > 0) return null;

  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-6 overflow-y-auto px-4 py-8">
      <div className="text-center">
        <h2 className="text-base font-medium">选一个开始</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          三种会话里 AI 的角色不一样，按场景选
        </p>
      </div>

      <div className="grid w-full max-w-2xl grid-cols-1 gap-3 sm:grid-cols-3">
        {CARDS.map((card) => {
          const Icon = card.icon;
          return (
            <button
              key={card.type}
              type="button"
              onClick={() => void createSession(card.type)}
              className={cn(
                "group flex flex-col gap-2 rounded-2xl border border-border bg-card/60 p-4 text-left",
                "transition-colors hover:border-emotion-primary/50 hover:bg-card",
              )}
            >
              <span className="flex items-center gap-2">
                <span
                  className="flex h-7 w-7 items-center justify-center rounded-lg bg-emotion-primary/15"
                  aria-hidden
                >
                  <Icon className="h-4 w-4 text-emotion-primary" />
                </span>
                <span className="text-sm font-medium">{card.title}</span>
              </span>

              <span className="text-xs leading-relaxed text-muted-foreground">
                {card.lead}
              </span>

              <ul className="flex flex-col gap-0.5">
                {card.points.map((point) => (
                  <li key={point} className="flex items-start gap-1.5 text-[11px] text-muted-foreground/80">
                    <span aria-hidden className="mt-1.5 inline-block h-1 w-1 shrink-0 rounded-full bg-current" />
                    {point}
                  </li>
                ))}
              </ul>

              <span className="mt-1 text-[11px] text-emotion-primary opacity-0 transition-opacity group-hover:opacity-100">
                新建{card.title}会话 →
              </span>
            </button>
          );
        })}
      </div>

      <p className="text-[11px] text-muted-foreground/70">
        对话内容只存在本机，随时可在设置里导出或一键清空
      </p>
    </div>
  );
}
"use client";

/**
 * 会话类型对应的辅助能力提示。
 *
 * 好友单聊：AI 不冒充真人，而是提供润色 / 翻译 / 总结 / 建议回复
 * 群聊：AI 只在被 @ 时才说话，不抢话
 */

import { Languages, MessageSquareQuote, Sparkles, Wand2 } from "lucide-react";

import { GroupSummaryButton } from "@/features/chat/components/GroupSummaryCard";
import { IdentityPicker } from "@/features/group/components/IdentityPicker";
import type { AssistantAction } from "@/stores/chat-store";
import { cn } from "@/lib/utils";

export const ASSISTANT_ACTIONS: Array<{
  action: AssistantAction;
  label: string;
  hint: string;
  icon: typeof Wand2;
}> = [
  { action: "polish", label: "润色", hint: "把这段话改得更得体", icon: Wand2 },
  { action: "translate", label: "翻译", hint: "中英互译", icon: Languages },
  { action: "summarize", label: "总结", hint: "提炼要点", icon: Sparkles },
  { action: "suggest", label: "建议回复", hint: "这条该怎么回", icon: MessageSquareQuote },
];

export interface ActionBarProps {
  /** 选中的动作，null 表示按内容自动判断 */
  value: AssistantAction | null;
  onChange: (action: AssistantAction | null) => void;
  disabled?: boolean;
}

/** 好友单聊的动作栏 */
export function AssistantActionBar({ value, onChange, disabled }: ActionBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-1.5 border-t border-border bg-card/40 px-4 py-2">
      <span className="mr-1 text-[11px] text-muted-foreground">让 AI 帮你：</span>
      {ASSISTANT_ACTIONS.map((item) => {
        const Icon = item.icon;
        const active = value === item.action;
        return (
          <button
            key={item.action}
            type="button"
            title={item.hint}
            disabled={disabled}
            onClick={() => onChange(active ? null : item.action)}
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] transition-colors disabled:opacity-40",
              active
                ? "bg-emotion-primary text-white"
                : "bg-muted text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className="h-3 w-3" />
            {item.label}
          </button>
        );
      })}
      {value && (
        <button
          type="button"
          onClick={() => onChange(null)}
          className="ml-1 text-[11px] text-muted-foreground underline underline-offset-2 hover:text-foreground"
        >
          改为自动判断
        </button>
      )}
    </div>
  );
}

export interface MentionBarProps {
  /** AI 是否正在等待被 @ */
  waiting: boolean;
  /** 点击后在输入框插入 @AI */
  onMention: () => void;
}

/** 群聊的 @ 提示栏 + 总结入口 */
export function GroupMentionBar({ waiting, onMention }: MentionBarProps) {
  return (
    <div className="flex flex-col gap-1.5 border-t border-border bg-card/40 px-4 py-2">
      {/* 身份选择器单独一行：提示语说的是 AI 的行为，这里说的是「我是谁」，两件事 */}
      <div className="flex items-center justify-between gap-2">
        <IdentityPicker />
        <GroupSummaryButton />
      </div>
      <div className="flex items-center justify-between gap-2">
        <p
          className={cn(
            "text-[11px] transition-colors",
            waiting ? "text-emotion-primary" : "text-muted-foreground",
          )}
        >
          {waiting ? "AI 听到了，需要 @ 它才会回复" : "AI 只在被 @ 时才回复，不会抢话"}
        </p>
        <button
          type="button"
          onClick={onMention}
          className="shrink-0 rounded-full bg-muted px-2.5 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-emotion-primary/15 hover:text-foreground"
        >
          @ AI
        </button>
      </div>
    </div>
  );
}
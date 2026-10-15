"use client";

/**
 * 群聊身份选择器。
 *
 * 没有它，群聊就只是「一个人自言自语」—— 后端分不清发言人，
 * 群聊总结的参与者列表永远只有一个人。选一个身份后，
 * 后续发出的消息都会带上这个人的名字。
 *
 * 只在群聊会话显示：AI 伴侣和好友单聊是两个人对话，不存在这个问题。
 */

import { Check, Users } from "lucide-react";

import { GROUP_IDENTITIES, useIdentityStore } from "@/features/group/store/identity-store";
import { cn } from "@/lib/utils";

export function IdentityPicker() {
  const identityId = useIdentityStore((s) => s.identityId);
  const setIdentity = useIdentityStore((s) => s.setIdentity);

  return (
    // flex-wrap：窄屏上四个身份一行放不下，必须能换行而不是横向溢出
    <div className="flex min-w-0 flex-wrap items-center gap-1">
      <Users className="h-3 w-3 shrink-0 text-muted-foreground" />
      {GROUP_IDENTITIES.map((identity) => {
        const active = identity.id === identityId;
        return (
          <button
            key={identity.id}
            type="button"
            onClick={() => setIdentity(identity.id)}
            aria-pressed={active}
            className={cn(
              "rounded-full px-2 py-0.5 text-[11px] transition-colors",
              active
                ? "bg-emotion-primary/15 text-emotion-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <span className="mr-0.5" aria-hidden>
              {identity.emoji}
            </span>
            {identity.name}
            {active && <Check className="ml-0.5 inline h-2.5 w-2.5" />}
          </button>
        );
      })}
    </div>
  );
}
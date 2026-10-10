"use client";

import { emotionThemeOf, type Message } from "@ai-companion/shared";

import { cn } from "@/lib/utils";

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.senderType === "user";
  const emotion = message.emotion;

  return (
    <div className={cn("flex w-full gap-2 px-4 py-1.5", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[min(42rem,80%)] rounded-2xl px-3.5 py-2 text-sm leading-relaxed",
          isUser
            ? "rounded-br-sm bg-emotion-primary text-white"
            : "rounded-bl-sm bg-muted text-foreground",
        )}
      >
        <p className="whitespace-pre-wrap break-words">{message.content}</p>
        {message.streaming && (
          <span className="ml-0.5 inline-block h-4 w-[2px] animate-pulse bg-current align-text-bottom" />
        )}
        {!isUser && emotion && (
          <p className="mt-1 flex items-center gap-1 text-[11px] opacity-70">
            <span
              aria-hidden
              className="inline-block h-1.5 w-1.5 rounded-full"
              style={{ backgroundColor: `hsl(${emotionThemeOf(emotion).primary})` }}
            />
            {emotionThemeOf(emotion).label}
          </p>
        )}
      </div>
    </div>
  );
}
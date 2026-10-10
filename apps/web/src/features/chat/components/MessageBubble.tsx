"use client";

import { emotionThemeOf, type Message } from "@ai-companion/shared";
import { motion } from "framer-motion";

import { useEmotionMotion } from "@/features/theme/hooks/use-emotion-motion";
import { absoluteUrl, cn } from "@/lib/utils";

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const { transition, variants } = useEmotionMotion();

  const isUser = message.senderType === "user";
  const emotion = message.emotion;
  const emotionTheme = emotion ? emotionThemeOf(emotion) : null;

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={variants}
      transition={transition}
      className={cn(
        "flex w-full gap-2 px-4 py-emotion",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={cn(
          "max-w-[var(--emotion-bubble-width)] rounded-emotion px-3.5 py-2 leading-relaxed",
          isUser
            ? "rounded-br-sm bg-emotion-primary text-white"
            : "rounded-bl-sm bg-muted text-foreground",
          // 愤怒时气泡更硬朗，平静疲惫时更圆润柔和
          emotion === "angry" && !isUser && "ring-1 ring-emotion-primary/40",
        )}
        style={{
          fontSize: `calc(1rem * var(--emotion-font-scale) * 0.875)`,
          letterSpacing: "var(--emotion-letter-spacing)",
        }}
      >
        {message.attachments && message.attachments.length > 0 && (
          <ul className="mb-1.5 flex flex-wrap gap-1.5">
            {message.attachments
              .filter((a) => a.kind === "image")
              .map((a) => (
                <li key={a.url}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={absoluteUrl(a.url)}
                    alt={a.name || "图片"}
                    title={a.description ?? a.name}
                    className="max-h-40 rounded-lg border border-white/20 object-cover"
                  />
                </li>
              ))}
            {message.attachments
              .filter((a) => a.kind === "audio")
              .map((a) => (
                <li key={a.url}>
                  {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                  <audio controls src={absoluteUrl(a.url)} className="h-8 max-w-full" />
                </li>
              ))}
          </ul>
        )}

        <p className="whitespace-pre-wrap break-words">{message.content}</p>
        {message.streaming && (
          <span className="ml-0.5 inline-block h-4 w-[2px] animate-pulse bg-current align-text-bottom" />
        )}
        {!isUser && emotionTheme && (
          <p className="mt-1 flex items-center gap-1 text-[11px] opacity-70">
            <span
              aria-hidden
              className="inline-block h-1.5 w-1.5 rounded-full"
              style={{ backgroundColor: `hsl(${emotionTheme.primary})` }}
            />
            {emotionTheme.label}
          </p>
        )}
      </div>
    </motion.div>
  );
}
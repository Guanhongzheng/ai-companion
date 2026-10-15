"use client";

import { emotionThemeOf, type Message } from "@ai-companion/shared";
import { motion } from "framer-motion";

import { useChatStore } from "@/stores/chat-store";
import { useEmotionMotion } from "@/features/theme/hooks/use-emotion-motion";
import { absoluteUrl, cn } from "@/lib/utils";
import { MessageActions } from "./MessageActions";

interface Props {
  message: Message;
  /** 群聊会话：显示发言人标签，且用户气泡靠左（多人轮流的群像） */
  isGroup?: boolean;
}

export function MessageBubble({ message, isGroup = false }: Props) {
  const { transition, variants } = useEmotionMotion();

  const isUser = message.senderType === "user";
  // 群聊里所有人的消息都来自「用户」侧，user 气泡靠右会让人以为是同一个人在自问自答
  const alignRight = isUser && !isGroup;
  const emotion = message.emotion;
  const emotionTheme = emotion ? emotionThemeOf(emotion) : null;

  const removeMessage = useChatStore((s) => s.removeMessage);
  const regenerate = useChatStore((s) => s.regenerate);
  const sending = useChatStore((s) => s.sending);
  // 流式生成中不给操作 —— 那条消息还没定型
  const actionable = !message.streaming;

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={variants}
      transition={transition}
      className={cn(
        "group flex w-full gap-1 px-4 py-emotion",
        alignRight ? "justify-end" : "justify-start",
      )}
    >
      <div className="flex min-w-0 flex-col gap-0.5">
        {isGroup && isUser && message.senderLabel && (
          <span className="px-1 text-[10px] text-muted-foreground">{message.senderLabel}</span>
        )}
        <div
        className={cn(
          "max-w-[var(--emotion-bubble-width)] rounded-emotion px-3.5 py-2 leading-relaxed",
          alignRight
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

        {/*
          🔴 内容还没来时必须有明确的「正在思考」反馈。
          实测首字延迟 330–580ms，此前这段时间气泡里只有一根几乎看不见的
          光标竖线 —— 用户分不清是「没发出去」还是「卡了」。
          这里用三点动画 + 文案，占位高度与正常气泡一致，不会有布局跳动。
        */}
        {message.streaming && !message.content ? (
          <span className="flex items-center gap-1.5 text-sm opacity-80">
            <span className="sr-only">AI 正在思考</span>
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                aria-hidden
                className="animate-thinking inline-block h-1.5 w-1.5 rounded-full bg-current"
                style={{ animationDelay: `${i * 160}ms` }}
              />
            ))}
          </span>
        ) : (
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        )}
        {message.streaming && message.content && (
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
      </div>

      {actionable && (
        <MessageActions
          copyText={message.content}
          onRegenerate={!isUser ? () => void regenerate() : undefined}
          onDelete={() => void removeMessage(message.id)}
          regenerating={!isUser && sending}
        />
      )}
    </motion.div>
  );
}
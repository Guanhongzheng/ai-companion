"use client";

import { Virtuoso } from "react-virtuoso";

import { useChatStore } from "@/stores/chat-store";
import { EmptyStateGuide } from "./EmptyStateGuide";
import { MessageBubble } from "./MessageBubble";

export function MessageList() {
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const messages = useChatStore((s) => (activeSessionId ? s.messages[activeSessionId] : undefined));
  // 群聊里要显示发言人、并让所有人的气泡统一靠左
  const isGroup = useChatStore((s) => s.sessions.find((x) => x.id === activeSessionId)?.type === "group");

  // 一个会话都没有 —— 引导用户挑一个开始，而不是干巴巴一句「新建一个」
  if (!activeSessionId) {
    return <EmptyStateGuide />;
  }

  if (!messages || messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-1.5 text-sm text-muted-foreground">
        <p>还没有消息</p>
        <p className="text-xs opacity-70">说点什么吧，情绪识别会自动切换主题</p>
      </div>
    );
  }

  return (
    <Virtuoso
      className="flex-1"
      data={messages}
      // 流式输出时始终贴底跟随
      followOutput
      increaseViewportBy={240}
      itemContent={(_index, message) => (
        <MessageBubble message={message} isGroup={isGroup} />
      )}
    />
  );
}
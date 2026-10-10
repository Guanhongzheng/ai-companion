"use client";

import { Virtuoso } from "react-virtuoso";

import { useChatStore } from "@/stores/chat-store";
import { MessageBubble } from "./MessageBubble";

export function MessageList() {
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const messages = useChatStore((s) => (activeSessionId ? s.messages[activeSessionId] : undefined));

  if (!activeSessionId) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
        左侧选择一个会话开始聊天
      </div>
    );
  }

  if (!messages || messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 text-sm text-muted-foreground">
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
      itemContent={(_index, message) => <MessageBubble message={message} />}
    />
  );
}
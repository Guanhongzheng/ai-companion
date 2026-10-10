"use client";

import { Send, Square } from "lucide-react";
import { useState } from "react";

import { useChatStore } from "@/stores/chat-store";
import { cn } from "@/lib/utils";

export function ChatComposer() {
  const [text, setText] = useState("");
  const sending = useChatStore((s) => s.sending);
  const sendMessage = useChatStore((s) => s.sendMessage);

  const canSend = text.trim().length > 0 && !sending;

  const handleSubmit = () => {
    if (!canSend) return;
    void sendMessage(text);
    setText("");
  };

  return (
    <div className="border-t border-border bg-card/40 px-4 py-3">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            // Enter 发送，Shift+Enter 换行
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          rows={1}
          placeholder="说点什么…（Enter 发送 / Shift+Enter 换行）"
          className={cn(
            "max-h-40 min-h-[2.75rem] flex-1 resize-none rounded-2xl border border-border bg-background px-4 py-2.5",
            "text-sm leading-relaxed outline-none transition-colors",
            "placeholder:text-muted-foreground focus:border-emotion-primary/60",
          )}
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSend}
          aria-label={sending ? "生成中" : "发送"}
          className={cn(
            "flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl transition-all",
            canSend
              ? "bg-emotion-primary text-white hover:opacity-90"
              : "bg-muted text-muted-foreground",
          )}
        >
          {sending ? (
            <Square className="h-4 w-4 animate-pulse fill-current" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}
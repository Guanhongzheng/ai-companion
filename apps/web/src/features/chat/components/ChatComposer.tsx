"use client";

import { Send, Square } from "lucide-react";
import { useEffect, useState } from "react";

import type { Attachment } from "@ai-companion/shared";
import { useChatStore, type AssistantAction } from "@/stores/chat-store";
import { ImagePicker } from "@/features/multimodal/components/ImagePicker";
import { VoiceInput } from "@/features/multimodal/components/VoiceInput";
import { cn } from "@/lib/utils";
import { AssistantActionBar, GroupMentionBar } from "./ActionBar";

interface Props {
  /** 当前会话类型，决定输入框上方的辅助区 */
  sessionType: "ai" | "direct" | "group";
  /** 选中的辅助动作 */
  action: AssistantAction | null;
  onActionChange: (action: AssistantAction | null) => void;
}

export function ChatComposer({ sessionType, action, onActionChange }: Props) {
  const [text, setText] = useState("");
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const sending = useChatStore((s) => s.sending);
  const waitingForMention = useChatStore((s) => s.waitingForMention);
  const sendMessage = useChatStore((s) => s.sendMessage);

  // 切会话时清掉动作，避免把「润色」带到 AI 伴侣会话里
  useEffect(() => {
    onActionChange(null);
    setAttachments([]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionType]);

  const canSend = (text.trim().length > 0 || attachments.length > 0) && !sending;

  const handleSubmit = () => {
    if (!canSend) return;
    void sendMessage(text, action ?? undefined, attachments);
    setText("");
    setAttachments([]);
    onActionChange(null);
  };

  return (
    <div className="border-t border-border bg-card/40">
      {sessionType === "direct" && (
        <AssistantActionBar value={action} onChange={onActionChange} disabled={sending} />
      )}
      {sessionType === "group" && (
        <GroupMentionBar
          waiting={waitingForMention}
          onMention={() => setText((t) => (t.startsWith("@AI") ? t : `@AI ${t}`.trimEnd()))}
        />
      )}

      {attachments.length > 0 && (
        <ImagePicker attachments={attachments} onChange={setAttachments} disabled={sending} />
      )}

      <div className="px-4 pb-3">
        <div className="mx-auto flex max-w-3xl items-end gap-2">
          <ImagePicker attachments={attachments} onChange={setAttachments} disabled={sending} />
          <VoiceInput
            disabled={sending}
            onText={(t) => setText((prev) => (prev ? `${prev} ${t}` : t))}
            onAttachment={(a) => setAttachments((prev) => [...prev, a])}
          />
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
            placeholder={
              sessionType === "group"
                ? "群聊里 AI 只在被 @ 时回复…"
                : "说点什么…（Enter 发送 / Shift+Enter 换行）"
            }
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
    </div>
  );
}
"use client";

/**
 * 消息操作菜单。
 *
 * 此前气泡是零操作的 —— AI 说错话、想复制一句话、想让它重答一次，
 * 用户只能干看着。这三个动作是任何聊天产品的基本预期。
 *
 * ⚠️ 交互设计上的关键取舍：**不能只在 hover 时出现**。
 * 移动端根本没有 hover，触屏也没有；只做 hover 的话手机上完全用不了。
 * 这里的做法是：桌面 hover / 聚焦浮出，触摸设备（`lg:hidden` 的操作条）
 * 常驻显示在气泡旁。
 *
 * 延迟浮出是刻意的 —— 鼠标划过时菜单立刻出现会让整条消息都在闪。
 */

import { Check, Copy, RefreshCw, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

interface Props {
  /** 复制的内容。空字符串时隐藏复制按钮 */
  copyText: string;
  /** 重新生成（仅 AI 消息可用） */
  onRegenerate?: () => void;
  onDelete: () => void;
  regenerating?: boolean;
}

export function MessageActions({
  copyText,
  onRegenerate,
  onDelete,
  regenerating = false,
}: Props) {
  const [copied, setCopied] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(copyText);
      setCopied(true);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 1600);
    } catch {
      // 剪贴板不可用（无 HTTPS / 无权限）时静默失败，
      // 弹一个 alert 反而比复制不了更让人困惑
    }
  };

  return (
    <div
      className={cn(
        "flex items-center gap-0.5 transition-opacity duration-150",
        // 触摸设备没有 hover，操作条**常驻**（opacity-70）；
        // lg 以上才交给 hover / focus-within 浮出。
        // 用 CSS 断点而不是 JS 判断 width —— 省掉一个 resize 监听，
        // 而且断点行为在 SSR 与客户端一致，不会闪烁。
        "opacity-70 lg:opacity-0",
        "lg:focus-within:opacity-100 lg:group-hover:opacity-100 lg:hover:opacity-100",
      )}
    >
      {copyText && (
        <button
          type="button"
          onClick={() => void copy()}
          title="复制"
          aria-label="复制消息"
          className="rounded p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-emotion-primary" /> : <Copy className="h-3.5 w-3.5" />}
        </button>
      )}

      {onRegenerate && (
        <button
          type="button"
          onClick={onRegenerate}
          disabled={regenerating}
          title="重新生成"
          aria-label="重新生成回复"
          className="rounded p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", regenerating && "animate-spin")} />
        </button>
      )}

      {confirming ? (
        // 删除不可撤销（附件文件会被真删），所以要二次确认
        <button
          type="button"
          onClick={onDelete}
          onBlur={() => setConfirming(false)}
          className="rounded px-1.5 py-0.5 text-[10px] text-destructive transition-colors hover:bg-destructive/10"
        >
          确认删除
        </button>
      ) : (
        <button
          type="button"
          onClick={() => setConfirming(true)}
          title="删除"
          aria-label="删除消息"
          className="rounded p-1 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}
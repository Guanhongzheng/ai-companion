"use client";

/**
 * 当前情绪的完整设计令牌。
 *
 * 组件想读情绪相关的任何参数（配色 / 字体 / 圆角 / 动效）都从这里拿，
 * 不要自己再去读 store 或算 CSS 变量。
 */

import { emotionThemeOf, type EmotionTag, type EmotionTheme } from "@ai-companion/shared";
import { useMemo } from "react";

import { useChatStore } from "@/stores/chat-store";

export interface EmotionTokens extends EmotionTheme {
  tag: EmotionTag;
  /** 供 style 属性直接使用的 hsl 颜色 */
  primaryColor: string;
  secondaryColor: string;
}

export function useEmotionTokens(): EmotionTokens {
  const tag = useChatStore((s) => s.emotion);

  return useMemo(() => {
    const theme = emotionThemeOf(tag);
    return {
      ...theme,
      tag,
      primaryColor: `hsl(${theme.primary})`,
      secondaryColor: `hsl(${theme.secondary})`,
    };
  }, [tag]);
}
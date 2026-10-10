/**
 * 把情绪映射写进 CSS 变量。
 *
 * 情绪自适应链路的「最后一公里」：
 *   后端 SSE 发 emotion 事件 → chat-store 更新 → 这里写入 CSS 变量
 *   → Tailwind 的 emotion.* 色板、字体、圆角、密度、壁纸渐变全部跟随。
 *
 * 只写变量、不写具体样式，好处是 CSS / Tailwind 配置能保持静态可分析。
 */

import { emotionThemeOf, type EmotionTag } from "@ai-companion/shared";

type TokenMap = Record<string, string>;

function buildTokens(tag: EmotionTag): TokenMap {
  const theme = emotionThemeOf(tag);
  return {
    // 颜色
    "--emotion-primary": theme.primary,
    "--emotion-secondary": theme.secondary,
    "--emotion-glow": theme.glow,
    "--wallpaper-gradient": theme.gradient,

    // 字体
    "--emotion-font-family": theme.font.family,
    "--emotion-font-scale": String(theme.font.scale),
    "--emotion-font-weight": String(theme.font.weight),
    "--emotion-letter-spacing": theme.font.letterSpacing,

    // 布局
    "--emotion-radius": theme.layout.radius,
    "--emotion-density": String(theme.layout.density),
    "--emotion-bubble-width": `${Math.round(theme.layout.bubbleWidth * 100)}%`,

    // 动效
    "--emotion-motion-scale": String(theme.motion.scale),
    "--emotion-enter-offset": `${theme.motion.enterOffset}px`,
  };
}

function root(): HTMLElement {
  if (typeof document === "undefined") {
    throw new Error("applyEmotionTheme 只能在浏览器中调用");
  }
  return document.documentElement;
}

export function applyEmotionTheme(tag: EmotionTag): void {
  const el = root();
  for (const [name, value] of Object.entries(buildTokens(tag))) {
    el.style.setProperty(name, value);
  }
  el.dataset["emotion"] = tag;
}

export function resetEmotionTheme(): void {
  const el = root();
  for (const [name, value] of Object.entries(buildTokens("neutral"))) {
    el.style.setProperty(name, value);
  }
  el.dataset["emotion"] = "neutral";
}
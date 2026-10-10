/**
 * 把情绪映射写进 CSS 变量。
 *
 * 情绪自适应链路的「最后一公里」：后端 SSE 发 emotion 事件 → store 更新 →
 * 这里写入 --emotion-* → Tailwind 的 emotion.* 色板与壁纸渐变自动跟随。
 */

import { emotionThemeOf, type EmotionTag } from "@ai-companion/shared";

const VARIABLES = {
  "--emotion-primary": "primary",
  "--emotion-secondary": "secondary",
  "--emotion-glow": "glow",
} as const;

function target(): HTMLElement {
  if (typeof document === "undefined") throw new Error("applyEmotionTheme 只能在浏览器中调用");
  return document.documentElement;
}

export function applyEmotionTheme(tag: EmotionTag): void {
  const theme = emotionThemeOf(tag);
  const el = target();
  for (const [cssVar, key] of Object.entries(VARIABLES)) {
    el.style.setProperty(cssVar, theme[key]);
  }
  el.style.setProperty("--wallpaper-gradient", theme.gradient);
  // 供 Tailwind / 组件读取动效强度
  el.dataset["motionScale"] = String(theme.motionScale);
  el.dataset["emotion"] = tag;
}

export function resetEmotionTheme(): void {
  const theme = emotionThemeOf("neutral");
  const el = target();
  for (const [cssVar, key] of Object.entries(VARIABLES)) {
    el.style.setProperty(cssVar, theme[key]);
  }
  el.style.setProperty("--wallpaper-gradient", theme.gradient);
  delete el.dataset["emotion"];
}
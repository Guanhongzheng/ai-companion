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
    // 窄屏不让情绪影响气泡宽度：情绪表里的 0.38–0.48 是照桌面调的，
    // 手机上只剩三四成屏宽，中文一字一行。详见 bubbleWidthFor()。
    "--emotion-bubble-width": bubbleWidthFor(theme.layout.bubbleWidth),

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

/**
 * 情绪决定气泡宽度只在宽屏成立。
 *
 * 🔴 这些值写进了 `document.documentElement.style`，属于**行内样式**，
 * 优先级高于任何 CSS 规则 —— 所以 globals.css 里的 media query 盖不住它，
 * 必须在这里判断屏幕宽度。
 *
 * 窄屏下情绪差异本来也看不出来（气泡已经占满），固定宽度即可。
 * 顺带监听 resize：手机横竖屏切换时桌面值会重新生效。
 */
function bubbleWidthFor(emotionWidth: number): string {
  const width = typeof window === "undefined" ? 1440 : window.innerWidth;
  if (width < 640) return "88%";
  if (width < 1024) return "84%";
  return `${Math.round(emotionWidth * 100)}%`;
}

export function applyEmotionTheme(tag: EmotionTag): void {
  const el = root();
  for (const [name, value] of Object.entries(buildTokens(tag))) {
    el.style.setProperty(name, value);
  }
  el.dataset["emotion"] = tag;
}

/**
 * 屏幕尺寸变化后重算一次。
 *
 * 气泡宽度是行内样式，横竖屏切换 / 拖动窗口时不会自己更新 ——
 * 不监听的话，从桌面缩到手机宽度的那一刻，气泡还是那个「桌面宽度」。
 */
let lastTag: EmotionTag | null = null;
let resizeBound = false;

export function watchViewport(tag: EmotionTag): void {
  lastTag = tag;
  if (resizeBound || typeof window === "undefined") return;
  resizeBound = true;
  window.addEventListener("resize", () => {
    if (lastTag) applyEmotionTheme(lastTag);
  });
}

export function resetEmotionTheme(): void {
  const el = root();
  for (const [name, value] of Object.entries(buildTokens("neutral"))) {
    el.style.setProperty(name, value);
  }
  el.dataset["emotion"] = "neutral";
}
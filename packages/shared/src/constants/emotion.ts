/**
 * 情绪 → 视觉 / 听觉表现 的映射表。
 *
 * 前端 features/theme、features/wallpaper、features/music 直接消费；
 * 后端可用于生成情绪摘要文案。**这里是情绪自适应的唯一数据源**，
 * 八类情绪的字体、动效、布局、壁纸粒子参数都在这里定义。
 *
 * 标签集合必须与后端 app/core/emotion.py 保持一致。
 */

import type { EmotionTag } from "../types/session";

/** 情绪字体 */
export interface EmotionFont {
  /** 字体族（含中文回退） */
  family: string;
  /** 字号缩放倍率 */
  scale: number;
  /** 字重 */
  weight: number;
  /** 字距 */
  letterSpacing: string;
}

/** 情绪动效参数 */
export interface EmotionMotion {
  /** 动效总强度，0.6 ~ 1.6，越大越快越弹 */
  scale: number;
  /** framer-motion spring 刚度 */
  springStiffness: number;
  /** 阻尼 */
  springDamping: number;
  /** 消息入场纵向位移 px */
  enterOffset: number;
}

/** 情绪布局参数 */
export interface EmotionLayout {
  /** 间距密度倍率，0.85 ~ 1.15 */
  density: number;
  /** 圆角 */
  radius: string;
  /** 气泡最大宽度占可用宽度的比例 */
  bubbleWidth: number;
}

/** 壁纸粒子参数 */
export interface EmotionParticles {
  /** 粒子数量 */
  count: number;
  /** 运动速度倍率 */
  speed: number;
  /** 扰动强度，越大越躁动 */
  turbulence: number;
  /** 空间铺开程度 */
  spread: number;
}

export interface EmotionTheme {
  /** 中文展示名 */
  label: string;
  /** HSL 三段式字符串，写入 CSS 变量 --emotion-* */
  primary: string;
  secondary: string;
  glow: string;
  /** 背景渐变（CSS Gradient 兜底壁纸） */
  gradient: string;
  /** 动效强度简写，保留给 Tailwind keyframes 用 */
  motionScale: number;
  font: EmotionFont;
  motion: EmotionMotion;
  layout: EmotionLayout;
  particles: EmotionParticles;
}

// ---- 字体族 ----

const SANS = 'system-ui, -apple-system, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif';
const ROUNDED = '"PingFang SC", "Hiragino Maru Gothic ProN", "Microsoft YaHei", system-ui, sans-serif';
const SERIF = '"Songti SC", "Noto Serif SC", "SimSun", Georgia, serif';
const MONO = '"JetBrains Mono", "Fira Code", "Cascadia Code", Consolas, monospace';

export const EMOTION_THEME: Record<EmotionTag, EmotionTheme> = {
  joy: {
    label: "愉悦",
    primary: "45 93% 58%",
    secondary: "28 90% 58%",
    glow: "45 93% 58%",
    gradient: "linear-gradient(135deg, hsl(45 93% 58% / .32), hsl(28 90% 58% / .22))",
    motionScale: 1.15,
    font: { family: ROUNDED, scale: 1.02, weight: 500, letterSpacing: "0.005em" },
    motion: { scale: 1.15, springStiffness: 340, springDamping: 22, enterOffset: 12 },
    layout: { density: 1.08, radius: "1.25rem", bubbleWidth: 0.44 },
    particles: { count: 260, speed: 1.0, turbulence: 0.25, spread: 1.0 },
  },

  calm: {
    label: "平静",
    primary: "199 89% 48%",
    secondary: "172 66% 50%",
    glow: "199 89% 48%",
    gradient: "linear-gradient(135deg, hsl(199 89% 48% / .28), hsl(172 66% 50% / .2))",
    motionScale: 0.85,
    font: { family: SANS, scale: 1, weight: 400, letterSpacing: "0.01em" },
    motion: { scale: 0.85, springStiffness: 120, springDamping: 26, enterOffset: 6 },
    layout: { density: 1, radius: "0.875rem", bubbleWidth: 0.42 },
    particles: { count: 160, speed: 0.45, turbulence: 0.12, spread: 1.15 },
  },

  neutral: {
    label: "平静如常",
    primary: "262 83% 58%",
    secondary: "199 89% 48%",
    glow: "262 83% 58%",
    gradient: "linear-gradient(135deg, hsl(262 83% 58% / .25), hsl(199 89% 48% / .2))",
    motionScale: 1,
    font: { family: SANS, scale: 1, weight: 400, letterSpacing: "0" },
    motion: { scale: 1, springStiffness: 210, springDamping: 24, enterOffset: 8 },
    layout: { density: 1, radius: "0.875rem", bubbleWidth: 0.42 },
    particles: { count: 180, speed: 0.6, turbulence: 0.18, spread: 1.05 },
  },

  sad: {
    label: "低落",
    primary: "215 45% 45%",
    secondary: "230 35% 38%",
    glow: "215 45% 45%",
    gradient: "linear-gradient(135deg, hsl(215 45% 45% / .3), hsl(230 35% 38% / .22))",
    motionScale: 0.7,
    // 衬线 + 放大字距：读起来更慢、更疏离
    font: { family: SERIF, scale: 0.99, weight: 400, letterSpacing: "0.02em" },
    motion: { scale: 0.7, springStiffness: 80, springDamping: 30, enterOffset: 4 },
    layout: { density: 0.92, radius: "0.75rem", bubbleWidth: 0.38 },
    particles: { count: 90, speed: 0.22, turbulence: 0.08, spread: 1.3 },
  },

  anxious: {
    label: "焦虑",
    primary: "280 60% 55%",
    secondary: "320 55% 52%",
    glow: "320 55% 52%",
    gradient: "linear-gradient(135deg, hsl(280 60% 55% / .3), hsl(320 55% 52% / .24))",
    motionScale: 1.35,
    font: { family: MONO, scale: 0.99, weight: 400, letterSpacing: "0" },
    motion: { scale: 1.35, springStiffness: 420, springDamping: 18, enterOffset: 16 },
    layout: { density: 0.95, radius: "0.625rem", bubbleWidth: 0.46 },
    particles: { count: 300, speed: 1.35, turbulence: 0.85, spread: 0.85 },
  },

  angry: {
    label: "愤怒",
    primary: "0 72% 52%",
    secondary: "15 80% 50%",
    glow: "0 72% 52%",
    gradient: "linear-gradient(135deg, hsl(0 72% 52% / .3), hsl(15 80% 50% / .24))",
    motionScale: 1.5,
    // 粗体 + 收紧字距：压迫感
    font: { family: SANS, scale: 1.04, weight: 700, letterSpacing: "-0.008em" },
    motion: { scale: 1.5, springStiffness: 520, springDamping: 16, enterOffset: 20 },
    layout: { density: 1.12, radius: "0.5rem", bubbleWidth: 0.48 },
    particles: { count: 340, speed: 1.6, turbulence: 1, spread: 0.7 },
  },

  excited: {
    label: "兴奋",
    primary: "330 80% 58%",
    secondary: "45 93% 58%",
    glow: "330 80% 58%",
    gradient: "linear-gradient(135deg, hsl(330 80% 58% / .32), hsl(45 93% 58% / .24))",
    motionScale: 1.45,
    font: { family: ROUNDED, scale: 1.05, weight: 600, letterSpacing: "0.008em" },
    motion: { scale: 1.45, springStiffness: 460, springDamping: 15, enterOffset: 22 },
    layout: { density: 1.1, radius: "1.5rem", bubbleWidth: 0.46 },
    particles: { count: 380, speed: 1.8, turbulence: 0.6, spread: 1.2 },
  },

  tired: {
    label: "疲惫",
    primary: "240 20% 48%",
    secondary: "255 25% 44%",
    glow: "240 20% 48%",
    gradient: "linear-gradient(135deg, hsl(240 20% 48% / .3), hsl(255 25% 44% / .22))",
    motionScale: 0.65,
    // 衬线 + 大字距 + 细字重：松垮、飘忽
    font: { family: SERIF, scale: 0.97, weight: 300, letterSpacing: "0.03em" },
    motion: { scale: 0.65, springStiffness: 70, springDamping: 32, enterOffset: 3 },
    layout: { density: 0.88, radius: "1rem", bubbleWidth: 0.4 },
    particles: { count: 70, speed: 0.18, turbulence: 0.06, spread: 1.35 },
  },
};

export function emotionThemeOf(tag: EmotionTag | undefined): EmotionTheme {
  return EMOTION_THEME[tag ?? "neutral"];
}

/** 情绪 → 音乐检索关键词，供 features/music 直接使用 */
export const EMOTION_MOOD_KEYWORDS: Record<EmotionTag, string[]> = {
  joy: ["欢快", "明亮", "治愈"],
  calm: ["安静", "治愈", "助眠"],
  neutral: ["轻音乐", "钢琴", "日常"],
  sad: ["抒情", "伤感", "纯音乐"],
  anxious: ["解压", "治愈", "氛围"],
  angry: ["摇滚", "燃", "力量"],
  excited: ["电子", "动感", "嗨"],
  tired: ["助眠", "慵懒", "轻音乐"],
};
/**
 * 情绪 → 视觉 / 听觉表现 的映射表
 * 前端 features/theme 直接消费；后端可用于生成情绪摘要文案
 */

import type { EmotionTag } from "../types/session";

export interface EmotionTheme {
  /** 中文展示名 */
  label: string;
  /** HSL 三段式字符串，写入 CSS 变量 --emotion-* */
  primary: string;
  secondary: string;
  glow: string;
  /** 建议的背景渐变（CSS Gradient 兜底壁纸） */
  gradient: string;
  /** framer-motion 时长系数，情绪越激烈动效越快 */
  motionScale: number;
}

export const EMOTION_THEME: Record<EmotionTag, EmotionTheme> = {
  joy: {
    label: "愉悦",
    primary: "45 93% 58%",
    secondary: "28 90% 58%",
    glow: "45 93% 58%",
    gradient: "linear-gradient(135deg, hsl(45 93% 58% / .32), hsl(28 90% 58% / .22))",
    motionScale: 1.15,
  },
  calm: {
    label: "平静",
    primary: "199 89% 48%",
    secondary: "172 66% 50%",
    glow: "199 89% 48%",
    gradient: "linear-gradient(135deg, hsl(199 89% 48% / .28), hsl(172 66% 50% / .2))",
    motionScale: 0.85,
  },
  neutral: {
    label: "平静如常",
    primary: "262 83% 58%",
    secondary: "199 89% 48%",
    glow: "262 83% 58%",
    gradient: "linear-gradient(135deg, hsl(262 83% 58% / .25), hsl(199 89% 48% / .2))",
    motionScale: 1,
  },
  sad: {
    label: "低落",
    primary: "215 45% 45%",
    secondary: "230 35% 38%",
    glow: "215 45% 45%",
    gradient: "linear-gradient(135deg, hsl(215 45% 45% / .3), hsl(230 35% 38% / .22))",
    motionScale: 0.7,
  },
  anxious: {
    label: "焦虑",
    primary: "280 60% 55%",
    secondary: "320 55% 52%",
    glow: "320 55% 52%",
    gradient: "linear-gradient(135deg, hsl(280 60% 55% / .3), hsl(320 55% 52% / .24))",
    motionScale: 1.35,
  },
  angry: {
    label: "愤怒",
    primary: "0 72% 52%",
    secondary: "15 80% 50%",
    glow: "0 72% 52%",
    gradient: "linear-gradient(135deg, hsl(0 72% 52% / .3), hsl(15 80% 50% / .24))",
    motionScale: 1.5,
  },
  excited: {
    label: "兴奋",
    primary: "330 80% 58%",
    secondary: "45 93% 58%",
    glow: "330 80% 58%",
    gradient: "linear-gradient(135deg, hsl(330 80% 58% / .32), hsl(45 93% 58% / .24))",
    motionScale: 1.45,
  },
  tired: {
    label: "疲惫",
    primary: "240 20% 48%",
    secondary: "255 25% 44%",
    glow: "240 20% 48%",
    gradient: "linear-gradient(135deg, hsl(240 20% 48% / .3), hsl(255 25% 44% / .22))",
    motionScale: 0.65,
  },
};

export function emotionThemeOf(tag: EmotionTag | undefined): EmotionTheme {
  return EMOTION_THEME[tag ?? "neutral"];
}

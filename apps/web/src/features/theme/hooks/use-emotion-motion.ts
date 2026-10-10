"use client";

/**
 * 情绪驱动的 framer-motion 动效参数。
 *
 * 情绪越激烈，弹簧越硬、入场位移越大；平静/疲惫则慢而轻。
 * 用法：`<motion.div {...motionProps}>` 或取 transition 单独用。
 */

import type { Transition, Variants } from "framer-motion";
import { useMemo } from "react";

import { useEmotionTokens } from "./use-emotion-tokens";

export interface EmotionMotionProps {
  transition: Transition;
  variants: Variants;
  /** 容器用的柔和脉冲动画（情绪越强越明显） */
  pulse: Variants;
}

export function useEmotionMotion(): EmotionMotionProps {
  const tokens = useEmotionTokens();

  return useMemo(() => {
    const { springStiffness, springDamping, scale, enterOffset } = tokens.motion;

    const transition: Transition = {
      type: "spring",
      stiffness: springStiffness,
      damping: springDamping,
      mass: 1 / Math.max(scale, 0.4),
    };

    const variants: Variants = {
      hidden: { opacity: 0, y: enterOffset, scale: 0.98 },
      visible: { opacity: 1, y: 0, scale: 1 },
    };

    const pulse: Variants = {
      idle: { opacity: 0.35 },
      glow: { opacity: 0.85 },
    };

    return { transition, variants, pulse };
  }, [tokens]);
}
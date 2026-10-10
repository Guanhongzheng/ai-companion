"use client";

/**
 * 情绪粒子动态壁纸。
 *
 * 只在浏览器挂载后动态 import three —— 该模块依赖 document/canvas，进 SSR 会炸。
 * 降级链：
 *   three 加载失败 / WebGL 不可用 → 退回 CSS Gradient 壁纸（--wallpaper-gradient）
 *   prefers-reduced-motion        → 不跑动画，只画静态帧
 *
 * 音频联动：订阅 music-store，audio 元素一出现就接进 Web Audio 分析器，
 * 由壁纸自己的 RAF 循环每帧采样，避免两个循环不同步。
 */

import { useEffect, useRef } from "react";

import { useMusicStore } from "@/features/music/store/music-store";
import { useEmotionTokens } from "@/features/theme/hooks/use-emotion-tokens";
import { createAudioAnalyzer, type AudioAnalyzer } from "../lib/audio-analyzer";
import type { WallpaperScene } from "../lib/wallpaper-scene";

const HOST_ID = "emotion-wallpaper";

export function EmotionWallpaper() {
  const tokens = useEmotionTokens();
  const sceneRef = useRef<WallpaperScene | null>(null);
  const analyzerRef = useRef<AudioAnalyzer | null>(null);
  const failedRef = useRef(false);

  // ---- 场景创建 / 销毁（只跑一次）----
  useEffect(() => {
    let disposed = false;

    const host = document.createElement("div");
    host.id = HOST_ID;
    host.setAttribute("aria-hidden", "true");
    host.style.cssText = [
      "position:fixed",
      "inset:0",
      "z-index:-10",
      "overflow:hidden",
      "pointer-events:none",
      "transition:background 700ms",
      "background-image:var(--wallpaper-gradient)",
    ].join(";");

    const canvas = document.createElement("canvas");
    canvas.style.cssText = "width:100%;height:100%;display:block";
    host.appendChild(canvas);
    document.body.appendChild(host);

    const reduced =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    void (async () => {
      try {
        const { createWallpaperScene } = await import("../lib/wallpaper-scene");
        if (disposed) return;

        const analyzer = createAudioAnalyzer();
        analyzerRef.current = analyzer;

        const scene = createWallpaperScene(canvas);
        sceneRef.current = scene;
        scene.setAudioSource(() => analyzer.sample());
        scene.applyTheme({
          primary: tokens.primary,
          secondary: tokens.secondary,
          particles: tokens.particles,
        });

        if (reduced) {
          // 降低动态：缩小粒子量并停掉持续动画
          scene.applyTheme({
            primary: tokens.primary,
            secondary: tokens.secondary,
            particles: { count: 60, speed: 0, turbulence: 0, spread: tokens.particles.spread },
          });
        }
      } catch {
        failedRef.current = true;
      }
    })();

    const onResize = () => sceneRef.current?.resize(window.innerWidth, window.innerHeight);
    window.addEventListener("resize", onResize);

    return () => {
      disposed = true;
      window.removeEventListener("resize", onResize);
      sceneRef.current?.dispose();
      sceneRef.current = null;
      analyzerRef.current?.dispose();
      analyzerRef.current = null;
      if (host.parentNode) host.parentNode.removeChild(host);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- 情绪变化：更新场景参数 ----
  useEffect(() => {
    sceneRef.current?.applyTheme({
      primary: tokens.primary,
      secondary: tokens.secondary,
      particles: tokens.particles,
    });
  }, [tokens.primary, tokens.secondary, tokens.particles]);

  // ---- 音乐接入：一有 audio 元素就挂上频谱分析 ----
  const audioElement = useMusicStore((s) => s.audioElement);
  useEffect(() => {
    const analyzer = analyzerRef.current;
    if (!audioElement || !analyzer) return;
    void analyzer.resume().then(() => analyzer.attach(audioElement));
  }, [audioElement]);

  return null;
}
"use client";

/**
 * Web Audio API 频谱分析器。
 *
 * 用途：把正在播放的音频拆成低/中/高频能量，喂给 Three.js 壁纸做可视化。
 *
 * 三个现实约束，都在这里优雅降级：
 * 1. 跨域音频没有 CORS 头时，MediaElementSource 会直接抛错 —— 捕获后返回全零能量
 * 2. 同一个 audio 元素只能 createMediaElementSource 一次 —— 用 WeakMap 记住已绑定的
 * 3. 浏览器要求用户手势后才能启动 AudioContext —— resume 失败就静默停用
 */

export interface AudioBands {
  bass: number;
  mid: number;
  treble: number;
  /** 总体能量，壁纸据此做呼吸感缩放 */
  overall: number;
}

export interface AudioAnalyzer {
  /** 绑定一个媒体元素（同一元素重复调用安全） */
  attach: (el: HTMLMediaElement) => boolean;
  resume: () => Promise<void>;
  /** 每帧调用，返回 0~1 归一化的频段能量 */
  sample: () => AudioBands;
  dispose: () => void;
  readonly active: boolean;
}

const EMPTY_BANDS: AudioBands = { bass: 0, mid: 0, treble: 0, overall: 0 };

/** 已绑定的元素 → AnalyserNode，避免重复 createMediaElementSource */
const boundSources = new WeakMap<HTMLMediaElement, AnalyserNode>();

function getAudioContextCtor(): typeof AudioContext | null {
  if (typeof window === "undefined") return null;
  const w = window as typeof window & { webkitAudioContext?: typeof AudioContext };
  return window.AudioContext ?? w.webkitAudioContext ?? null;
}

/** 把某个区间的字节频谱取平均并归一化到 0~1 */
function bandAverage(data: Uint8Array, from: number, to: number): number {
  const start = Math.floor(from * data.length);
  const end = Math.min(Math.floor(to * data.length), data.length);
  if (end <= start) return 0;
  let sum = 0;
  for (let i = start; i < end; i += 1) sum += data[i] ?? 0;
  return sum / (end - start) / 255;
}

export function createAudioAnalyzer(): AudioAnalyzer {
  const Ctor = getAudioContextCtor();

  let ctx: AudioContext | null = null;
  let analyser: AnalyserNode | null = null;
  // TS 5.7 起 Uint8Array 是泛型；AnalyserNode 要求 ArrayBuffer 承载的版本
  let data: Uint8Array<ArrayBuffer> | null = null;
  let disabled = !Ctor;

  function ensure(): boolean {
    if (disabled || !Ctor) return false;
    if (!ctx) {
      try {
        ctx = new Ctor();
        analyser = ctx.createAnalyser();
        analyser.fftSize = 512;
        analyser.smoothingTimeConstant = 0.75;
        data = new Uint8Array(new ArrayBuffer(analyser.frequencyBinCount));
      } catch {
        disabled = true;
        return false;
      }
    }
    return true;
  }

  return {
    attach(el) {
      if (!ensure() || !ctx || !analyser) return false;
      // 已经绑定过同一个节点说明接过，直接用
      if (boundSources.has(el)) return true;
      try {
        const source = ctx.createMediaElementSource(el);
        source.connect(analyser);
        // 注意：analyser 不再回连 destination，音量由 audio 元素自己控制，
        // 避免二次输出造成回声
        boundSources.set(el, analyser);
        return true;
      } catch {
        // 典型原因：音频跨域且服务端没给 CORS 头
        disabled = true;
        return false;
      }
    },

    async resume() {
      if (!ensure() || !ctx) return;
      try {
        if (ctx.state === "suspended") await ctx.resume();
      } catch {
        disabled = true;
      }
    },

    sample() {
      if (disabled || !analyser || !data || ctx?.state !== "running") return EMPTY_BANDS;
      analyser.getByteFrequencyData(data);
      const bass = bandAverage(data, 0, 0.12);
      const mid = bandAverage(data, 0.12, 0.35);
      const treble = bandAverage(data, 0.35, 0.8);
      const overall = (bass * 0.5 + mid * 0.35 + treble * 0.15) * 1.6;
      return {
        bass,
        mid,
        treble,
        overall: Math.min(1, overall),
      };
    },

    dispose() {
      try {
        void ctx?.close();
      } catch {
        /* 关闭失败无所谓 */
      }
      ctx = null;
      analyser = null;
      data = null;
    },

    get active() {
      return !disabled && ctx?.state === "running";
    },
  };
}
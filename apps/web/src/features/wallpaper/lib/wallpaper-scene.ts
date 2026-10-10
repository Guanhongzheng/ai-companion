/**
 * Three.js 情绪粒子壁纸。
 *
 * 设计取舍：
 * - 用 Points + 预生成的柔光贴图，而不是自定义 Shader —— 视觉效果够用且不易出错
 * - 粒子数在情绪间差异很大（疲惫 70 / 兴奋 380），用「预留最大容量 + 改 drawRange」
 *   的方式复用同一个 BufferAttribute，避免每次切情绪都重建 GPU 缓冲
 * - 音频能量驱动粒子尺寸与整体呼吸，AnalyserNode 没数据时静默退化为纯情绪动效
 */

import * as THREE from "three";

import type { EmotionParticles } from "@ai-companion/shared";

import type { AudioBands } from "./audio-analyzer";

const MAX_PARTICLES = 420;
const DEPTH = 14;

export interface WallpaperTheme {
  primary: string;
  secondary: string;
  particles: EmotionParticles;
}

export interface WallpaperScene {
  applyTheme: (theme: WallpaperTheme) => void;
  /** 注册音频采样函数，每帧由场景自己调用，避免两个 RAF 循环不同步 */
  setAudioSource: (sample: () => AudioBands) => void;
  resize: (width: number, height: number) => void;
  dispose: () => void;
}

/** 生成柔光圆点贴图，替代额外的 glsl */
function createSpriteTexture(): THREE.Texture {
  const size = 64;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    g.addColorStop(0, "rgba(255,255,255,1)");
    g.addColorStop(0.35, "rgba(255,255,255,0.55)");
    g.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, size, size);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

function hslToColor(hsl: string): THREE.Color {
  return new THREE.Color(`hsl(${hsl})`);
}

export function createWallpaperScene(canvas: HTMLCanvasElement): WallpaperScene {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    alpha: true,
    antialias: false,
    powerPreference: "low-power",
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 100);
  camera.position.z = DEPTH / 2;

  // 预分配最大容量
  const positions = new Float32Array(MAX_PARTICLES * 3);
  const colors = new Float32Array(MAX_PARTICLES * 3);
  const velocities = new Float32Array(MAX_PARTICLES * 3);

  for (let i = 0; i < MAX_PARTICLES; i += 1) {
    positions[i * 3] = (Math.random() - 0.5) * 40;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 24;
    positions[i * 3 + 2] = (Math.random() - 0.5) * DEPTH;
    velocities[i * 3] = (Math.random() - 0.5) * 0.4;
    velocities[i * 3 + 1] = (Math.random() - 0.5) * 0.4;
    velocities[i * 3 + 2] = 0;
  }

const geometry = new THREE.BufferGeometry();
const positionAttr = new THREE.BufferAttribute(positions, 3);
const colorAttr = new THREE.BufferAttribute(colors, 3);
geometry.setAttribute("position", positionAttr);
geometry.setAttribute("color", colorAttr);

  const material = new THREE.PointsMaterial({
    size: 0.22,
    map: createSpriteTexture(),
    vertexColors: true,
    transparent: true,
    opacity: 0.85,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    sizeAttenuation: true,
  });

  const points = new THREE.Points(geometry, material);
  points.frustumCulled = false;
  scene.add(points);

  // ---- 运行态参数（情绪驱动，带平滑过渡） ----
  let targetCount = 180;
  let currentCount = 180;
  let speed = 0.6;
  let targetSpeed = 0.6;
  let turbulence = 0.18;
  let targetTurbulence = 0.18;
  let spread = 1.05;
  let targetSpread = 1.05;
  const colorA = new THREE.Color("hsl(262 83% 58%)");
  const targetColorA = colorA.clone();
  const colorB = new THREE.Color("hsl(199 89% 48%)");
  const targetColorB = colorB.clone();

  let audio: AudioBands = { bass: 0, mid: 0, treble: 0, overall: 0 };
  let sampleAudio: (() => AudioBands) | null = null;

  let raf = 0;
  let disposed = false;
  let width = 1;
  let height = 1;

  function applyColors() {
    const n = Math.max(1, Math.round(currentCount));
    for (let i = 0; i < n; i += 1) {
      const t = Math.random() * 0.6 + 0.2;
      const r = colorA.r + (colorB.r - colorA.r) * t;
      const g = colorA.g + (colorB.g - colorA.g) * t;
      const b = colorA.b + (colorB.b - colorA.b) * t;
      colors[i * 3] = r;
      colors[i * 3 + 1] = g;
      colors[i * 3 + 2] = b;
    }
    colorAttr.needsUpdate = true;
    geometry.setDrawRange(0, Math.max(1, Math.round(targetCount)));
  }

  function resize(w: number, h: number) {
    width = Math.max(1, w);
    height = Math.max(1, h);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    // 竖屏时把视野拉宽，避免粒子被裁掉
    camera.position.z = width < height ? DEPTH * 0.75 : DEPTH / 2;
    camera.updateProjectionMatrix();
  }

  let last = performance.now();

  function frame(now: number) {
    if (disposed) return;
    raf = requestAnimationFrame(frame);

    const dt = Math.min((now - last) / 16.67, 3);
    last = now;

    // 每帧取一次音频能量；没有音频源时保持上一次的值
    if (sampleAudio) audio = sampleAudio();

    // 参数缓动，避免情绪切换时突变
    currentCount += (targetCount - currentCount) * 0.06;
    speed += (targetSpeed - speed) * 0.05;
    turbulence += (targetTurbulence - turbulence) * 0.05;
    spread += (targetSpread - spread) * 0.05;
    colorA.lerp(targetColorA, 0.05);
    colorB.lerp(targetColorB, 0.05);

    const n = Math.max(1, Math.min(MAX_PARTICLES, Math.round(currentCount)));
    const halfW = 20 * spread;
    const halfH = 12 * spread;
    const halfD = DEPTH / 2;
    // 低频越大整体越活跃
    const boost = 1 + audio.bass * 2.2;
    const drift = speed * 0.04 * dt * boost;

    for (let i = 0; i < n; i += 1) {
      const ix = i * 3;
      positions[ix] = (positions[ix] ?? 0) + (velocities[ix] ?? 0) * drift;
      positions[ix + 1] =
        (positions[ix + 1] ?? 0) + (velocities[ix + 1] ?? 0) * drift - audio.mid * 0.02 * dt;

      // 越界回绕
      if ((positions[ix] ?? 0) > halfW) positions[ix] = -halfW;
      if ((positions[ix] ?? 0) < -halfW) positions[ix] = halfW;
      if ((positions[ix + 1] ?? 0) > halfH) positions[ix + 1] = -halfH;
      if ((positions[ix + 1] ?? 0) < -halfH) positions[ix + 1] = halfH;
      const z = positions[ix + 2] ?? 0;
      if (z > halfD) positions[ix + 2] = -halfD;
      else if (z < -halfD) positions[ix + 2] = halfD;

      // 扰动：情绪越激烈，粒子越"抖"
      if (turbulence > 0.01) {
        positions[ix] = (positions[ix] ?? 0) + (Math.random() - 0.5) * turbulence * 0.06;
        positions[ix + 1] =
          (positions[ix + 1] ?? 0) + (Math.random() - 0.5) * turbulence * 0.06;
      }
    }

    positionAttr.needsUpdate = true;
    geometry.setDrawRange(0, n);

    // 音频能量驱动粒子大小与整体呼吸
    material.size = 0.18 + audio.bass * 0.42 + audio.overall * 0.1;
    material.opacity = 0.6 + audio.overall * 0.35;
    points.rotation.y += 0.0004 * speed * boost;
    points.rotation.x = Math.sin(now / 4000) * 0.05 * spread;

    renderer.render(scene, camera);
  }

  resize(canvas.clientWidth || window.innerWidth, canvas.clientHeight || window.innerHeight);
  applyColors();
  raf = requestAnimationFrame(frame);

  return {
    applyTheme(theme) {
      targetCount = Math.min(MAX_PARTICLES, theme.particles.count);
      targetSpeed = theme.particles.speed;
      targetTurbulence = theme.particles.turbulence;
      targetSpread = theme.particles.spread;
      targetColorA.copy(hslToColor(theme.primary));
      targetColorB.copy(hslToColor(theme.secondary));
      applyColors();
    },

    setAudioSource(sample) {
      sampleAudio = sample;
    },

    resize,

    dispose() {
      disposed = true;
      cancelAnimationFrame(raf);
      geometry.dispose();
      (material.map as THREE.Texture | null)?.dispose();
      material.dispose();
      renderer.dispose();
    },
  };
}
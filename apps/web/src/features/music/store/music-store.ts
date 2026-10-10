"use client";

/**
 * 音乐播放状态。
 *
 * audio 元素直接挂在 store 里，供 features/wallpaper 的频谱分析器接管 ——
 * 壁纸需要真实的 HTMLMediaElement 才能接 Web Audio。
 */

import { create } from "zustand";

import { EMOTION_MOOD_KEYWORDS, type EmotionTag } from "@ai-companion/shared";
import { MUSIC_API_BASE_URL, musicApi, type Track } from "../api/music-api";

interface MusicState {
  /** null= 还没探测过服务 */
  available: boolean | null;
  keyword: string;
  tracks: Track[];
  currentId: number | null;
  playing: boolean;
  loading: boolean;
  error: string | null;
  audioElement: HTMLAudioElement | null;

  probe: () => Promise<void>;
  searchByEmotion: (tag: EmotionTag) => Promise<void>;
  search: (keyword: string) => Promise<void>;
  play: (id: number) => Promise<void>;
  toggle: () => void;
  setPlaying: (playing: boolean) => void;
  reset: () => void;
}

/** 复用同一个 audio 元素，切歌不重建（重建会导致 Web Audio source 失效） */
let sharedAudio: HTMLAudioElement | null = null;

function ensureAudio(): HTMLAudioElement {
  if (sharedAudio) return sharedAudio;
  sharedAudio = new Audio();
  sharedAudio.crossOrigin = "anonymous";
  sharedAudio.loop = true;
  sharedAudio.preload = "none";
  return sharedAudio;
}

function pickMoodKeyword(tag: EmotionTag): string {
  const pool = EMOTION_MOOD_KEYWORDS[tag] ?? EMOTION_MOOD_KEYWORDS.neutral;
  return pool[Math.floor(Math.random() * pool.length)] ?? "轻音乐";
}

export const useMusicStore = create<MusicState>()((set, get) => ({
  available: null,
  keyword: "",
  tracks: [],
  currentId: null,
  playing: false,
  loading: false,
  error: null,
  audioElement: null,

  async probe() {
    const ok = await musicApi.health();
    set({ available: ok });
    if (!ok) {
      set({
        error: `音乐服务未启动。执行 docker compose --profile infra up -d music-api 后重试（地址 ${MUSIC_API_BASE_URL}）。`,
      });
    }
  },

  async search(keyword) {
    const trimmed = keyword.trim();
    if (!trimmed) return;
    set({ loading: true, error: null, keyword: trimmed });
    try {
      const tracks = await musicApi.search(trimmed);
      set({ tracks, available: true });
      if (tracks.length === 0) {
        set({ error: `没有搜到「${trimmed}」相关歌曲，换个关键词试试。` });
      }
    } catch (error) {
      set({
        available: false,
        tracks: [],
        error: `音乐服务未启动或请求失败：${error instanceof Error ? error.message : String(error)}`,
      });
    } finally {
      set({ loading: false });
    }
  },

  searchByEmotion(tag) {
    return get().search(pickMoodKeyword(tag));
  },

  async play(id) {
    const track = get().tracks.find((t) => t.id === id);
    if (!track) return;

    set({ currentId: id, loading: true, error: null });
    try {
      let url = track.url;
      if (!url) url = await musicApi.songUrl(id);
      if (!url) {
        set({ error: "这条歌曲没有可播放的地址（多半是 VIP 或地区限制）。" });
        return;
      }

      const audio = ensureAudio();
      audio.src = url;
      await audio.play();
      set({ audioElement: audio, playing: true });
    } catch (error) {
      set({ error: `播放失败：${error instanceof Error ? error.message : String(error)}` });
    } finally {
      set({ loading: false });
    }
  },

  toggle() {
    const audio = get().audioElement;
    if (!audio) {
      void get().probe().then(() => get().searchByEmotion("neutral"));
      return;
    }
    if (audio.paused) void audio.play();
    else audio.pause();
  },

  setPlaying(playing) {
    set({ playing });
  },

  reset() {
    get().audioElement?.pause();
    set({ currentId: null, playing: false, tracks: [], error: null });
  },
}));
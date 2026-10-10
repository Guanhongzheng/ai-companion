"use client";

/**
 * 音乐联动面板。
 *
 * 定位是「情绪驱动的背景乐」：一键按当前情绪搜歌、播放，
 * 播放中的音频会被壁纸的 Web Audio 分析器接管做可视化。
 */

import { Music4, Pause, Play, RefreshCw, X } from "lucide-react";
import { useEffect } from "react";

import { useEmotionTokens } from "@/features/theme/hooks/use-emotion-tokens";
import { cn } from "@/lib/utils";
import { useMusicStore } from "../store/music-store";

function formatDuration(ms: number): string {
  if (!ms) return "--:--";
  const total = Math.round(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function MusicDock() {
  const tokens = useEmotionTokens();
  const {
    available,
    tracks,
    currentId,
    playing,
    loading,
    error,
    audioElement,
    probe,
    searchByEmotion,
    play,
    toggle,
    setPlaying,
  } = useMusicStore();

  // 首次挂载探测服务；同步 audio 播放状态
  useEffect(() => {
    void probe();
  }, [probe]);

  useEffect(() => {
    const el = audioElement;
    if (!el) return;
    const onPlay = () => setPlaying(true);
    const onPause = () => setPlaying(false);
    const onEnded = () => setPlaying(false);
    el.addEventListener("play", onPlay);
    el.addEventListener("pause", onPause);
    el.addEventListener("ended", onEnded);
    return () => {
      el.removeEventListener("play", onPlay);
      el.removeEventListener("pause", onPause);
      el.removeEventListener("ended", onEnded);
    };
  }, [audioElement, setPlaying]);

  const current = tracks.find((t) => t.id === currentId);

  return (
    <section className="pointer-events-auto w-72 rounded-2xl border border-border bg-card/80 p-3 shadow-lg backdrop-blur">
      <header className="mb-2 flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-xs font-medium">
          <Music4 className="h-3.5 w-3.5" style={{ color: tokens.primaryColor }} />
          情绪歌单
          <span className="text-[10px] font-normal text-muted-foreground">· {tokens.label}</span>
        </h3>
        <button
          type="button"
          title="按当前情绪重新推荐"
          onClick={() => void searchByEmotion(tokens.tag)}
          className="rounded p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
        </button>
      </header>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => {
            const id = tracks.find((t) => t.id === currentId)?.id ?? tracks[0]?.id;
            if (id) void play(id);
          }}
          disabled={!tracks.length}
          className={cn(
            "flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition-opacity",
            tracks.length
              ? "bg-emotion-primary text-white hover:opacity-90"
              : "bg-muted text-muted-foreground",
          )}
        >
          {playing ? <Pause className="h-4 w-4" /> : <Play className="ml-0.5 h-4 w-4" />}
        </button>

        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-medium">{current?.name ?? "还没放歌"}</p>
          <p className="truncate text-[11px] text-muted-foreground">
            {current ? `${current.artist} · ${formatDuration(current.durationMs)}` : "点播放键按情绪推荐"}
          </p>
        </div>
      </div>

      {available === false && error && (
        <p className="mt-2 flex items-start gap-1.5 rounded-lg bg-destructive/10 p-2 text-[11px] leading-relaxed text-destructive">
          <span className="flex-1">{error}</span>
          <X className="mt-0.5 h-3 w-3 shrink-0" />
        </p>
      )}

      {tracks.length > 0 && (
        <ul className="mt-2 max-h-40 space-y-0.5 overflow-y-auto">
          {tracks.slice(0, 8).map((track) => (
            <li key={track.id}>
              <button
                type="button"
                onClick={() => void play(track.id)}
                className={cn(
                  "flex w-full items-center gap-2 rounded-md px-2 py-1 text-left text-xs transition-colors",
                  track.id === currentId ? "bg-emotion-primary/15 text-foreground" : "hover:bg-muted",
                )}
              >
                <span className="min-w-0 flex-1 truncate">{track.name}</span>
                <span className="shrink-0 text-[10px] text-muted-foreground">
                  {formatDuration(track.durationMs)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <button
        type="button"
        onClick={toggle}
        className="mt-2 w-full rounded-md py-1 text-[11px] text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      >
        {audioElement ? (playing ? "暂停" : "继续播放") : "启用音乐联动"}
      </button>
    </section>
  );
}
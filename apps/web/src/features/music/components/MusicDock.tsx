"use client";

/**
 * 音乐联动面板。
 *
 * 定位是「情绪驱动的背景乐」：一键按当前情绪搜歌、播放，
 * 播放中的音频会被壁纸的 Web Audio 分析器接管做可视化。
 */

import { ChevronUp, Music4, Pause, Play, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

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
  // 默认收起。音乐是可选功能，不该在每次页面加载时就发起探测请求 ——
  // 那会在控制台留下一串 ERR_CONNECTION_REFUSED，用户看到的是「系统有错」。
  const [open, setOpen] = useState(false);
  const {
    available,
    tracks,
    currentId,
    playing,
    loading,
    audioElement,
    probe,
    searchByEmotion,
    play,
    toggle,
    setPlaying,
  } = useMusicStore();

  // 只在用户展开时才探测服务
  useEffect(() => {
    if (open) void probe();
  }, [open, probe]);

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

  // 收起态：只留一个小圆钮，不探测服务、不占空间
  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        title="打开情绪歌单"
        className="pointer-events-auto flex h-9 w-9 items-center justify-center rounded-full border border-border bg-card/80 shadow-lg backdrop-blur transition-colors hover:bg-card"
      >
        <Music4 className="h-4 w-4" style={{ color: tokens.primaryColor }} />
      </button>
    );
  }

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
          title="收起"
          onClick={() => setOpen(false)}
          className="rounded p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <ChevronUp className="h-3.5 w-3.5" />
        </button>
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

      {/*
        服务没起时只给一行轻量提示。
        原来这里直接渲染 store 里的 error —— 那段文本是给开发者看的
        （含 docker 命令和端口号），整块红横幅糊在聊天界面右下角，
        既抢眼又对终端用户毫无意义。音乐本来就是可选功能。
      */}
      {available === false && (
        <p className="mt-2 rounded-lg bg-muted/60 px-2 py-1.5 text-[11px] text-muted-foreground">
          音乐服务未启动，不影响对话
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
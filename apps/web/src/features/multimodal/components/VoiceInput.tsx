"use client";

/**
 * 语音输入。
 *
 * 优先用浏览器的 Web Speech API（Chrome / Edge / Safari 支持）—— 免费、即时、
 * 不需要任何 Key。只有浏览器不支持时才退回「录音 + 服务端 ASR」。
 *
 * Web Speech API 也有坑：中文识别需要 lang="zh-CN"，而且部分浏览器在无网络时
 * 静默返回空结果，这里都做了兜底。
 */

import { Loader2, Mic, MicOff, Square } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import { mediaApi, toAttachment, type Attachment } from "../api/media-api";

/** 浏览器是否原生支持语音识别 */
export function hasSpeechRecognition(): boolean {
  if (typeof window === "undefined") return false;
  const w = window as typeof window & { webkitSpeechRecognition?: unknown };
  return typeof window.SpeechRecognition !== "undefined" || Boolean(w.webkitSpeechRecognition);
}

interface Props {
  /** 识别结果回调，文字会追加到输入框 */
  onText: (text: string) => void;
  /** 服务端 ASR 兜底时用：上传音频后拿到转写文本 */
  onAttachment?: (attachment: Attachment) => void;
  disabled?: boolean;
}

type Mode = "idle" | "listening" | "uploading";

export function VoiceInput({ onText, onAttachment, disabled }: Props) {
  // 🔴 能力探测必须等挂载后再做。
  // `hasSpeechRecognition()` 读的是浏览器 API：SSR 阶段必然返回 false，
  // 客户端 hydrate 后可能变 true —— 服务端渲染出「需服务端配置」、
  // 客户端是「语音输入」，两套文案不一致就是一条 hydration 报错。
  // 所以 mounted 之前统一用中性文案，挂载后再切真实能力。
  const [mounted, setMounted] = useState(false);
  const supported = mounted && hasSpeechRecognition();
  const [mode, setMode] = useState<Mode>("idle");
  const [hint, setHint] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
      recorderRef.current?.stop();
    };
  }, []);

  // ---- 浏览器原生识别 ----
  const startRecognition = useCallback(() => {
    const Ctor =
      window.SpeechRecognition ??
      (window as typeof window & { webkitSpeechRecognition?: new () => SpeechRecognitionLike })
        .webkitSpeechRecognition;
    if (!Ctor) return false;

    const recognition = new Ctor();
    recognition.lang = "zh-CN";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = (event) => {
      const last = event.results[event.results.length - 1];
      const text = last?.[0]?.transcript?.trim();
      if (text) {
        onText(text);
        setHint(null);
      } else {
        setHint("没听清，再说一次试试");
      }
    };
    recognition.onerror = (event) => {
      setHint(errorHint(event.error));
      setMode("idle");
    };
    recognition.onend = () => setMode("idle");

    try {
      recognition.start();
      recognitionRef.current = recognition;
      return true;
    } catch {
      setHint("无法启动语音识别，请检查麦克风权限");
      return false;
    }
  }, [onText]);

  // ---- 录音 + 服务端 ASR ----
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = pickRecorderMime();
      const recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        setMode("uploading");
        try {
          const out = await mediaApi.transcribe(blob);
          if (out.transcript) {
            onText(out.transcript);
            setHint(null);
          } else {
            // 没识别出来也把音频挂上，至少用户知道发过什么
            onAttachment?.({ ...toAttachment(out), kind: "audio", transcript: null });
            setHint(out.hint ?? "语音识别不可用");
          }
        } catch {
          setHint("语音转写失败，可以直接打字");
        } finally {
          setMode("idle");
        }
      };

      recorder.start();
      recorderRef.current = recorder;
      return true;
    } catch {
      setHint("拿不到麦克风权限，请在浏览器地址栏左侧允许");
      setMode("idle");
      return false;
    }
  }, [onAttachment, onText]);

  const handleToggle = async () => {
    if (mode === "listening") {
      recognitionRef.current?.stop();
      setMode("idle");
      return;
    }
    if (mode === "uploading") return;

    setHint(null);
    setMode("listening");
    // 原生识别优先；不支持就录音走服务端
    if (!startRecognition()) {
      const ok = await startRecording();
      if (!ok) setMode("idle");
    }
  };

  const busy = mode === "uploading";

  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={() => void handleToggle()}
        disabled={disabled || busy}
        title={
          !mounted
            ? "语音输入"
            : supported
              ? "语音输入"
              : "语音输入（浏览器不支持，改用服务端识别）"
        }
        aria-label={mode === "listening" ? "停止录音" : "语音输入"}
        className={cn(
          "flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl transition-all",
          disabled || busy
            ? "cursor-not-allowed bg-muted text-muted-foreground"
            : mode === "listening"
              ? "bg-destructive text-white animate-pulse"
              : "bg-muted text-muted-foreground hover:text-foreground",
        )}
      >
        {busy ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : mode === "listening" ? (
          <Square className="h-4 w-4 fill-current" />
        ) : (
          <Mic className="h-4 w-4" />
        )}
      </button>

      {hint && (
        <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
          <MicOff className="h-3 w-3" />
          {hint}
        </span>
      )}
    </div>
  );
}

function pickRecorderMime(): string {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"];
  return candidates.find((m) => MediaRecorder.isTypeSupported?.(m)) ?? "";
}

function errorHint(code: string): string {
  switch (code) {
    case "not-allowed":
    case "service-not-allowed":
      return "麦克风权限被拒绝，请在地址栏左侧允许";
    case "no-speech":
      return "没听到声音";
    case "audio-capture":
      return "找不到麦克风设备";
    case "network":
      return "语音识别需要联网，当前网络不可用";
    case "not-recognizable":
      return "没听清，换个说法试试";
    default:
      return "语音识别出错，可以直接打字";
  }
}

/** 只声明我们实际用到的成员，避免依赖 lib.dom 里的实验性类型 */
interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognitionLike;
  }
}
import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/utils";

export default function HomePage() {
  const modules = [
    { title: "个性化对话中枢", desc: "AI 伴侣 / 好友单聊 / 群聊，同一套会话系统" },
    { title: "情绪自适应界面", desc: "情绪驱动主题色、壁纸、音乐、动效" },
    { title: "RAG 个人记忆", desc: "bge-m3 召回 + bge-reranker 重排" },
    { title: "多模态理解与生成", desc: "Whisper / OCR / 情感分析 / 轻量出图" },
    { title: "AI 安全与隐私", desc: "内容过滤、记忆加密、一键删除" },
    { title: "实时社交对话", desc: "SSE / Supabase Realtime / Socket.io" },
  ];

  return (
    <main className="min-h-screen bg-background">
      <div className="container flex flex-col items-center gap-10 py-24">
        <header className="flex flex-col items-center gap-4 text-center">
          <span className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
            Next.js 14 · FastAPI · LangGraph · RAG
          </span>
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
            <span className="bg-gradient-to-r from-emotion-primary to-emotion-secondary bg-clip-text text-transparent">
              ai-companion
            </span>
          </h1>
          <p className="max-w-xl text-balance text-muted-foreground">
            个性化多模态 AI 伴侣与社交对话平台 —— 让 AI 记住你、理解你，并随你的情绪而改变。
          </p>
          <div className="mt-2 flex flex-wrap items-center justify-center gap-2">
            <Link
              href="/chat"
              className="inline-flex items-center gap-2 rounded-full bg-emotion-primary px-5 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
            >
              进入对话中枢
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/memory"
              className="inline-flex items-center gap-2 rounded-full border border-border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-muted"
            >
              查看长期记忆
            </Link>
          </div>
        </header>

        <section className="grid w-full max-w-4xl gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {modules.map((item) => (
            <div
              key={item.title}
              className={cn(
                "rounded-lg border border-border bg-card p-5 text-card-foreground",
                "transition-colors hover:border-emotion-primary/50",
              )}
            >
              <h2 className="text-sm font-medium">{item.title}</h2>
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{item.desc}</p>
            </div>
          ))}
        </section>

        <footer className="text-xs text-muted-foreground">
          脚手架已就绪，从 <code className="rounded bg-muted px-1.5 py-0.5">src/features</code> 开始实现
        </footer>
      </div>
    </main>
  );
}

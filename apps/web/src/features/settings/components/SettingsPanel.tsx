"use client";

import {
  AlertCircle,
  CheckCircle2,
  Eye,
  EyeOff,
  Loader2,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { MODEL_PROVIDERS } from "@ai-companion/shared";
import { cn } from "@/lib/utils";
import { settingsApi, type StatusResult } from "../api/settings-api";
import { currentProvider, useSettingsStore } from "../store/settings-store";

export function SettingsPanel() {
  const s = useSettingsStore();
  const [revealKey, setRevealKey] = useState(false);
  const [status, setStatus] = useState<StatusResult | null>(null);

  const provider = currentProvider(s);
  const needsKey = provider.id !== "ollama";

  useEffect(() => {
    void settingsApi
      .status()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  const handleValidate = async () => {
    s.setValidating(true, false, null);
    try {
      const result = await settingsApi.validate();
      s.setValidating(false, result.ok, result.message);
      void settingsApi.status().then(setStatus).catch(() => undefined);
    } catch (error) {
      s.setValidating(false, false, error instanceof Error ? error.message : "校验失败");
    }
  };

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5 py-8">
      <header>
        <h1 className="text-lg font-medium">设置</h1>
        <p className="mt-1 text-xs text-muted-foreground">
          自带 API Key（BYOK）—— 填上就能用你自己的模型额度，不用改任何配置文件。
        </p>
      </header>

      {/* 隐私说明放最显眼的位置，避免用户误以为 Key 会被存到服务端 */}
      <div className="flex items-start gap-2 rounded-xl border border-emotion-primary/30 bg-emotion-primary/5 p-3">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emotion-primary" />
        <p className="text-xs leading-relaxed">
          你的 Key <strong>只保存在这台设备的浏览器里</strong>，每次请求通过请求头传给本地后端，
          后端不落盘、不入库、不写日志。清除下面的「清除全部配置」即可彻底删除。
        </p>
      </div>

      {/* ---- 对话模型 ---- */}
      <Section
        title="对话模型"
        action={
          <Toggle
            checked={s.enabled}
            onChange={(v) => s.setEnabled(v)}
            label={s.enabled ? "已启用" : "使用服务端配置"}
          />
        }
      >
        <div className={cn("flex flex-col gap-3", !s.enabled && "pointer-events-none opacity-50")}>
          <Field label="服务商">
            <select
              value={s.providerId}
              onChange={(e) => s.setProvider(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-emotion-primary/60"
            >
              {MODEL_PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                  {p.freeTier ? "（有免费额度）" : ""}
                </option>
              ))}
            </select>
          </Field>

          {provider.consoleUrl && (
            <p className="text-[11px] text-muted-foreground">
              没有 Key？去
              <a
                href={provider.consoleUrl}
                target="_blank"
                rel="noreferrer noopener"
                className="mx-1 text-emotion-primary underline underline-offset-2"
              >
                {provider.label} 控制台
              </a>
              申请（{provider.keyHint}）
            </p>
          )}

          {needsKey && (
            <Field label="API Key">
              <div className="relative">
                <input
                  type={revealKey ? "text" : "password"}
                  value={s.modelKey}
                  onChange={(e) => s.setModelKey(e.target.value)}
                  placeholder={provider.keyHint}
                  autoComplete="off"
                  spellCheck={false}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 pr-9 font-mono text-xs outline-none focus:border-emotion-primary/60"
                />
                <button
                  type="button"
                  onClick={() => setRevealKey((v) => !v)}
                  title={revealKey ? "隐藏" : "显示"}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {revealKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </Field>
          )}

          <Field label="模型">
            <div className="flex gap-2">
              <input
                list="model-options"
                value={s.modelName}
                onChange={(e) => s.setModelName(e.target.value)}
                placeholder={provider.defaultModel}
                spellCheck={false}
                className="flex-1 rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs outline-none focus:border-emotion-primary/60"
              />
              <datalist id="model-options">
                {provider.models.map((m) => (
                  <option key={m} value={m} />
                ))}
              </datalist>
              <button
                type="button"
                onClick={() => s.setModelName(provider.defaultModel)}
                className="shrink-0 rounded-lg border border-border px-2.5 text-[11px] text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                常用
              </button>
            </div>
          </Field>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void handleValidate()}
              disabled={s.validating || (needsKey && !s.modelKey) || !s.modelName}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-white transition-opacity",
                s.validating || (needsKey && !s.modelKey) || !s.modelName
                  ? "cursor-not-allowed opacity-40"
                  : "bg-emotion-primary hover:opacity-90",
              )}
            >
              {s.validating ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : s.validated ? (
                <CheckCircle2 className="h-3.5 w-3.5" />
              ) : (
                <ShieldCheck className="h-3.5 w-3.5" />
              )}
              {s.validating ? "校验中" : "测试连接"}
            </button>

            {s.message && (
              <span
                className={cn(
                  "flex items-center gap-1 text-xs",
                  s.validated ? "text-emotion-primary" : "text-destructive",
                )}
              >
                {!s.validated && <AlertCircle className="h-3.5 w-3.5" />}
                {s.message}
              </span>
            )}
          </div>
        </div>
      </Section>

      {/* ---- Embedding ---- */}
      <Section
        title="记忆向量化"
        action={
          <Toggle
            checked={s.embeddingEnabled}
            onChange={(v) => s.setEmbeddingEnabled(v)}
            label={s.embeddingEnabled ? "已启用" : "使用服务端默认"}
          />
        }
      >
        <div
          className={cn(
            "flex flex-col gap-3",
            !s.embeddingEnabled && "pointer-events-none opacity-50",
          )}
        >
          <p className="text-xs leading-relaxed text-muted-foreground">
            默认用零依赖的哈希实现，只能字面匹配。启用云端 Embedding 后，
            记忆检索才能理解「宠物 → 猫」这类语义关系。
          </p>
          <Field label="Embedding 模型">
            <input
              list="embedding-options"
              value={s.embeddingModel}
              onChange={(e) => s.setEmbeddingModel(e.target.value)}
              placeholder="text-embedding-v3（阿里云百炼）"
              spellCheck={false}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs outline-none focus:border-emotion-primary/60"
            />
            <datalist id="embedding-options">
              <option value="text-embedding-v3" />
              <option value="BAAI/bge-m3" />
              <option value="text-embedding-3-small" />
            </datalist>
          </Field>
          <Field label="Embedding Key" hint="留空则复用上面的对话 Key">
            <input
              type={revealKey ? "text" : "password"}
              value={s.embeddingKey}
              onChange={(e) => s.setEmbeddingKey(e.target.value)}
              placeholder={s.modelKey ? "复用对话 Key" : "sk- 开头"}
              autoComplete="off"
              spellCheck={false}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs outline-none focus:border-emotion-primary/60"
            />
          </Field>
        </div>
      </Section>

      {/* ---- 服务端状态 ---- */}
      {status && (
        <Section title="当前生效配置">
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-xs">
            <dt className="text-muted-foreground">模型来源</dt>
            <dd>{status.using_user_key ? "你填的 Key" : "服务端 .env"}</dd>
            <dt className="text-muted-foreground">生效模型</dt>
            <dd className="font-mono">{status.model}</dd>
            {status.key_hint !== "<空>" && (
              <>
                <dt className="text-muted-foreground">Key</dt>
                <dd className="font-mono">{status.key_hint}</dd>
              </>
            )}
            <dt className="text-muted-foreground">服务端已配 Key</dt>
            <dd>{status.server_has_any_key ? "是" : "否（未配则走本地模拟）"}</dd>
          </dl>
        </Section>
      )}

      <Section title="数据管理">
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href="/memory"
            className="rounded-lg border border-border px-3 py-1.5 text-xs transition-colors hover:bg-muted"
          >
            管理长期记忆
          </Link>
          <button
            type="button"
            onClick={() => {
              if (window.confirm("清除本机保存的全部 API 配置？此操作不可撤销。")) s.clear();
            }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-destructive/40 px-3 py-1.5 text-xs text-destructive transition-colors hover:bg-destructive/10"
          >
            <Trash2 className="h-3.5 w-3.5" />
            清除全部配置
          </button>
        </div>
      </Section>
    </div>
  );
}

function Section({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-border bg-card/50 p-4">
      <header className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-sm font-medium">{title}</h2>
        {action}
      </header>
      {children}
    </section>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[11px] text-muted-foreground">
        {label}
        {hint && <span className="ml-1 opacity-70">（{hint}）</span>}
      </span>
      {children}
    </label>
  );
}

function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex items-center gap-1.5 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
    >
      <span
        className={cn(
          "relative h-4 w-7 rounded-full transition-colors",
          checked ? "bg-emotion-primary" : "bg-muted",
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 h-3 w-3 rounded-full bg-white transition-transform",
            checked ? "translate-x-3.5" : "translate-x-0.5",
          )}
        />
      </span>
      {label}
    </button>
  );
}
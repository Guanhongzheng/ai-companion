/**
 * 多媒体接口封装。
 *
 * 注意：上传必须用 FormData，此时**不能**手动设置 Content-Type，
 * 交给浏览器自己带 boundary，否则 multipart 会被解析失败。
 */

import type { Attachment } from "@ai-companion/shared";

import { absoluteUrl } from "@/lib/utils";
import { apiFetch, readByokHeaders } from "@/lib/api-client";

export type { Attachment };

export interface MediaUploadOut {
  kind: string;
  url: string;
  name: string;
  size: number;
  mime: string;
}

export interface TranscribeOut {
  url: string;
  name: string;
  transcript: string | null;
  available: boolean;
  hint: string | null;
}

export interface VisionOut {
  url: string;
  name: string;
  description: string | null;
  available: boolean;
  hint: string | null;
}

/** 上传目录的占用情况 */
export interface MediaStats {
  file_count: number;
  total_bytes: number;
  referenced_count: number;
  orphan_count: number;
  orphan_bytes: number;
  directory: string;
}

/** 一次清理的结果 */
export interface CleanupResult {
  scanned: number;
  deleted: number;
  freed_bytes: number;
  kept_referenced: number;
  kept_recent: number;
  failed: number;
}

/** FormData 上传：不能带 Content-Type，必须让浏览器自己生成 boundary */
async function upload<T>(path: string, file: File | Blob, fieldName = "file"): Promise<T> {
  const form = new FormData();
  form.append(fieldName, file);

  const response = await fetch(absoluteUrl(path), {
    method: "POST",
    headers: {
      ...readByokHeaders(),
      // 这里刻意不写 Content-Type
    },
    body: form,
  });

  if (!response.ok) {
    let detail = `${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // 保留状态码
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export const mediaApi = {
  uploadImage: (file: File | Blob) =>
    upload<MediaUploadOut>("/api/v1/media/image", file),

  uploadAudio: (file: File | Blob) =>
    upload<MediaUploadOut>("/api/v1/media/audio", file),

  /** 服务端 ASR 兜底，浏览器能本地识别时不需要走这里 */
  transcribe: (file: File | Blob) =>
    upload<TranscribeOut>("/api/v1/media/transcribe", file),

  /** 单独预览图片理解结果 */
  describeImage: (file: File | Blob) => upload<VisionOut>("/api/v1/media/vision", file),

  /** 上传目录占用情况（文件数、可清理量） */
  stats: () => apiFetch<MediaStats>("/api/v1/media/stats"),

  /**
   * 清理没有被任何消息引用的上传文件。
   *
   * 默认留 1 小时宽限期：此刻可能正有人把图片放在输入框里还没发出去。
   */
  cleanup: (graceHours = 1) =>
    apiFetch<CleanupResult>(`/api/v1/media/cleanup?grace_hours=${graceHours}`, {
      method: "POST",
    }),

  /**
   * 删除单个上传文件。用户在发送前移除附件时调用。
   * 已被消息引用的文件后端会返回 409，这里当失败处理即可（不影响移除 UI）。
   */
  remove: (filename: string) =>
    apiFetch<void>(`/api/v1/media/${encodeURIComponent(filename)}`, { method: "DELETE" }),
};

/** 从附件 url 里取出磁盘文件名（与后端 filename_of_attachment 规则一致） */
export function filenameOfUrl(url: string): string | null {
  const name = url.replace(/\/+$/, "").split("/").pop();
  if (!name || name === "." || name === ".." || name.includes("\\")) return null;
  return name;
}

/** 移除附件时的尽力删除：删不掉也无所谓，后端的启动清理会兜底回收 */
export function discardUpload(url: string): void {
  const name = filenameOfUrl(url);
  if (!name) return;
  void mediaApi.remove(name).catch(() => undefined);
}

/** 把后端返回的上传结果转成消息附件 */
export function toAttachment(out: MediaUploadOut | TranscribeOut): Attachment {
  const mime = "mime" in out ? out.mime : undefined;
  return {
    kind: "kind" in out && out.kind === "audio" ? "audio" : "image",
    url: out.url,
    name: out.name,
    mimeType: mime,
    transcript: "transcript" in out ? out.transcript : null,
  };
}
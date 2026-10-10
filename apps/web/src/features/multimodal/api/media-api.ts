/**
 * 多媒体接口封装。
 *
 * 注意：上传必须用 FormData，此时**不能**手动设置 Content-Type，
 * 交给浏览器自己带 boundary，否则 multipart 会被解析失败。
 */

import type { Attachment } from "@ai-companion/shared";

import { absoluteUrl } from "@/lib/utils";
import { readByokHeaders } from "@/lib/api-client";

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
};

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
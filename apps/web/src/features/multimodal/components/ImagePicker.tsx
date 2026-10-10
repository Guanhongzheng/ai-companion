"use client";

/**
 * 图片选择与预览。
 *
 * 三种入口：点按钮选文件、直接粘贴截图（Ctrl+V）、拖拽到输入区。
 * 粘贴这个入口最顺手 —— 截图后直接 Ctrl+V 就能发。
 */

import { ImagePlus, Loader2, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import { absoluteUrl } from "@/lib/utils";
import { mediaApi, toAttachment, type Attachment } from "../api/media-api";

const MAX_MB = 10;

interface Props {
  attachments: Attachment[];
  onChange: (attachments: Attachment[]) => void;
  disabled?: boolean;
}

export function ImagePicker({ attachments, onChange, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const images = attachments.filter((a) => a.kind === "image");

  const handleFiles = useCallback(
    async (files: FileList | File[]) => {
      const picked = Array.from(files).filter((f) => f.type.startsWith("image/"));
      if (picked.length === 0) return;

      setError(null);
      setUploading(true);
      const uploaded: Attachment[] = [];
      for (const file of picked) {
        if (file.size > MAX_MB * 1024 * 1024) {
          setError(`「${file.name}」超过 ${MAX_MB}MB，已跳过`);
          continue;
        }
        try {
          uploaded.push(toAttachment(await mediaApi.uploadImage(file)));
        } catch (err) {
          setError(err instanceof Error ? err.message : "图片上传失败");
        }
      }
      if (uploaded.length > 0) onChange([...attachments, ...uploaded]);
      setUploading(false);
    },
    [attachments, onChange],
  );

  // 全局粘贴：截图后直接 Ctrl+V
  useEffect(() => {
    const onPaste = (event: ClipboardEvent) => {
      const files = event.clipboardData?.files;
      if (!files || files.length === 0) return;
      const images = Array.from(files).filter((f) => f.type.startsWith("image/"));
      if (images.length === 0) return;
      event.preventDefault();
      void handleFiles(images);
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [handleFiles]);

  const remove = (url: string) => onChange(attachments.filter((a) => a.url !== url));

  return (
    <div className="flex flex-col gap-1.5 px-4 pb-1">
      {images.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {images.map((image) => (
            <li key={image.url} className="group relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={absoluteUrl(image.url)}
                alt={image.name || "已上传图片"}
                className="h-16 w-16 rounded-lg border border-border object-cover"
              />
              <button
                type="button"
                onClick={() => remove(image.url)}
                title="移除"
                className="absolute -right-1.5 -top-1.5 rounded-full bg-card p-0.5 text-muted-foreground opacity-0 shadow transition-opacity group-hover:opacity-100 hover:text-destructive"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (disabled) return;
          void handleFiles(e.dataTransfer.files);
        }}
        className={cn(
          "flex items-center gap-1.5",
          dragOver && "rounded-lg bg-emotion-primary/10",
        )}
      >
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={disabled || uploading}
          title="添加图片（也可以直接粘贴截图）"
          className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-40"
        >
          {uploading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <ImagePlus className="h-4 w-4" />
          )}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          multiple
          hidden
          onChange={(e) => {
            if (e.target.files) void handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
        <span className="text-[11px] text-muted-foreground">
          {dragOver ? "松手即可添加图片" : "截图后可直接 Ctrl+V 粘贴"}
          {error && <span className="ml-2 text-destructive">{error}</span>}
        </span>
      </div>
    </div>
  );
}
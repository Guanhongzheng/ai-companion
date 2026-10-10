import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** 合并 Tailwind 类名，冲突时后者优先 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** 后端 API 基地址（浏览器侧） */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export function absoluteUrl(path: string) {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

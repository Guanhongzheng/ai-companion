"use client";

/**
 * 群聊身份。
 *
 * 为什么需要：群聊的本质是**多人说话**。后端 `sender_id` / `sender_name`
 * 支持不同发言人，前端不传的话所有消息都会被记成"我" ——
 * 群聊总结的参与者列表就永远只有一个人，整个功能等于没接上。
 *
 * 这里存的是「我在这场对话里扮演谁」，存在 localStorage：
 * 换设备/清缓存回到默认，不会跟服务端数据打架。
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * 群成员预设。
 *
 * id 会被后端写成 sender_id，name 是显示名（优先于 id 推导）。
 * 「我」用 ``local-user`` 而不是 ``u_me`` —— 后端对这个 id 有特殊处理，
 * 兜底推导时显示成「我」而不是 "me"。
 */
export const GROUP_IDENTITIES = [
  { id: "local-user", name: "我", emoji: "🙂" },
  { id: "u_lin", name: "林小满", emoji: "👩‍🎤" },
  { id: "u_zhou", name: "周叙", emoji: "🧑‍💻" },
  { id: "u_chen", name: "陈默", emoji: "🎧" },
] as const;

export type GroupIdentityId = (typeof GROUP_IDENTITIES)[number]["id"];

interface IdentityState {
  /** 当前身份 id */
  identityId: GroupIdentityId;
  /** 是否已被用户主动改过。false 时不打扰（AI 伴侣 / 好友单聊用不到） */
  touched: boolean;
  setIdentity: (id: GroupIdentityId) => void;
}

export const useIdentityStore = create<IdentityState>()(
  persist(
    (set) => ({
      identityId: "local-user",
      touched: false,
      setIdentity: (id) => set({ identityId: id, touched: true }),
    }),
    { name: "ai-companion-identity" },
  ),
);

/** 拿到当前身份的完整信息 */
export function currentIdentity(id: GroupIdentityId) {
  return GROUP_IDENTITIES.find((i) => i.id === id) ?? GROUP_IDENTITIES[0];
}
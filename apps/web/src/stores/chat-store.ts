"use client";

/**
 * 对话中枢的全局状态。
 *
 * 划分原则（与 PATH_CONVENTION 一致）：
 *   - sessions / activeSessionId / messages 等跨组件共享的状态放这里
 *   - 组件自己的展开、滚动等局部状态留在组件内部
 */

import type { Attachment, EmotionTag, Message, Session } from "@ai-companion/shared";
import { create } from "zustand";

import { absoluteUrl } from "@/lib/utils";
import { readByokHeaders } from "@/lib/api-client";
import { streamPost } from "@/lib/sse-client";
import { chatApi } from "@/features/chat/api/chat-api";
import type { LearnedMemory, RecalledMemory } from "@/features/memory/types";
import type { GroupSummary } from "@/features/chat/types";
import { currentIdentity, useIdentityStore } from "@/features/group/store/identity-store";
import {
  toMessage,
  toSession,
  type StreamActionPayload,
  type StreamDonePayload,
  type StreamEmotionPayload,
  type StreamErrorPayload,
  type StreamMetaPayload,
  type StreamTokenPayload,
} from "@/features/chat/types";

/** 好友单聊的辅助动作 */
export type AssistantAction = "polish" | "translate" | "summarize" | "suggest";

const LOCAL_USER_ID = "local-user";
const STREAMING_ID = "__streaming__";

interface ChatState {
  sessions: Session[];
  activeSessionId: string | null;
  messages: Record<string, Message[]>;
  loading: boolean;
  sending: boolean;
  emotion: EmotionTag;
  emotionConfidence: number;
  /** 实际调用的模型，未发送前为 null */
  model: string | null;
  /** 后端是否在无 Key 情况下走了本地降级 */
  mocked: boolean;
  /** 本轮召回的长期记忆，用来在界面上展示「AI 想起了什么」 */
  recalledMemories: RecalledMemory[];
  /** 本轮新记住的记忆，展示「我记住了：xxx」 */
  learnedMemories: LearnedMemory[];
  /** 群聊摘要。渲染在消息区而非输入框附近 —— 那里被 MusicDock 挡住过 */
  groupSummary: GroupSummary | null;
  summarizeLoading: boolean;
  /** 摘要卡片是否展开（与内容分开，切会话时收起） */
  groupSummaryOpen: boolean;
  /** 本轮意图判定结果 */
  lastAction: StreamActionPayload["action"];
  /** 群聊里 AI 是否在等你 @ 它 */
  waitingForMention: boolean;
  error: string | null;

  loadSessions: () => Promise<void>;
  selectSession: (sessionId: string) => Promise<void>;
  createSession: (type: Session["type"]) => Promise<void>;
  removeSession: (sessionId: string) => Promise<void>;
  sendMessage: (
    text: string,
    action?: AssistantAction,
    attachments?: Attachment[],
  ) => Promise<void>;
  clearError: () => void;
  /** 删一条消息 */
  removeMessage: (messageId: string) => Promise<void>;
  /** 重新生成 AI 回复：删掉旧回复，把上一条用户消息再发一遍 */
  regenerate: () => Promise<void>;
  /** 请求群聊摘要。失败只提示，不清空已有摘要 */
  runSummary: () => Promise<void>;
  closeSummary: () => void;
}

export const useChatStore = create<ChatState>()((set, get) => ({
  sessions: [],
  activeSessionId: null,
  messages: {},
  loading: false,
  sending: false,
  emotion: "neutral",
  emotionConfidence: 0,
  model: null,
  mocked: false,
  recalledMemories: [],
  learnedMemories: [],
  groupSummary: null,
  summarizeLoading: false,
  groupSummaryOpen: false,
  lastAction: "chat",
  waitingForMention: false,
  error: null,

  async loadSessions() {
    set({ loading: true, error: null });
    try {
      const sessions = (await chatApi.listSessions()).map(toSession);
      set({ sessions });
      const active = get().activeSessionId ?? sessions[0]?.id ?? null;
      if (active) await get().selectSession(active);
    } catch (error) {
      set({ error: `加载会话失败：${describe(error)}` });
    } finally {
      set({ loading: false });
    }
  },

  async selectSession(sessionId) {
    set({ activeSessionId: sessionId });
    try {
      const messages = (await chatApi.listMessages(sessionId)).map(toMessage);
      set((state) => ({ messages: { ...state.messages, [sessionId]: messages } }));
    } catch (error) {
      set({ error: `加载消息失败：${describe(error)}` });
    }
  },

  async createSession(type) {
    try {
      const created = toSession(await chatApi.createSession({ type, title: defaultTitle(type) }));
      set((state) => ({
        sessions: [created, ...state.sessions],
        messages: { ...state.messages, [created.id]: [] },
      }));
      await get().selectSession(created.id);
    } catch (error) {
      set({ error: `创建会话失败：${describe(error)}` });
    }
  },

  async removeSession(sessionId) {
    try {
      await chatApi.deleteSession(sessionId);
      set((state) => {
        const messages = { ...state.messages };
        delete messages[sessionId];
        const sessions = state.sessions.filter((s) => s.id !== sessionId);
        return {
          sessions,
          messages,
          activeSessionId: state.activeSessionId === sessionId ? (sessions[0]?.id ?? null) : state.activeSessionId,
        };
      });
      const next = get().activeSessionId;
      if (next) await get().selectSession(next);
    } catch (error) {
      set({ error: `删除会话失败：${describe(error)}` });
    }
  },

  async sendMessage(text, action, attachments) {
    const trimmed = text.trim();
    const { activeSessionId } = get();
    const files = attachments ?? [];
    // 只有图没有字也算一句话；两者都没有才不发
    if ((!trimmed && files.length === 0) || !activeSessionId || get().sending) return;

    // 群聊要带上「我是谁」，否则后端记成 local-user，
    // 群聊总结的参与者列表就永远只有一个人
    const session = get().sessions.find((s) => s.id === activeSessionId);
    const isGroup = session?.type === "group";
    const identity = currentIdentity(useIdentityStore.getState().identityId);

    const userMessage: Message = {
      id: `local-${Date.now()}`,
      sessionId: activeSessionId,
      senderType: "user",
      senderId: isGroup ? identity.id : LOCAL_USER_ID,
      senderLabel: isGroup ? identity.name : undefined,
      content: trimmed || "（图片）",
      contentType: files.some((f) => f.kind === "image") ? "image" : "text",
      attachments: files,
      createdAt: new Date().toISOString(),
    };

    const streamingMessage: Message = {
      id: STREAMING_ID,
      sessionId: activeSessionId,
      senderType: "ai",
      senderId: "companion",
      content: "",
      contentType: "text",
      createdAt: new Date().toISOString(),
      streaming: true,
    };

    set((state) => ({
      sending: true,
      error: null,
      recalledMemories: [],
      learnedMemories: [],
      groupSummary: null,
      groupSummaryOpen: false,
      lastAction: action ?? "chat",
      waitingForMention: false,
      messages: {
        ...state.messages,
        [activeSessionId]: [...(state.messages[activeSessionId] ?? []), userMessage, streamingMessage],
      },
    }));

    const appendToken = (chunk: string) => {
      set((state) => {
        const list = state.messages[activeSessionId] ?? [];
        const next = list.map((m) =>
          m.id === STREAMING_ID ? { ...m, content: m.content + chunk } : m,
        );
        return { messages: { ...state.messages, [activeSessionId]: next } };
      });
    };

    const patch = (partial: Partial<Message>) => {
      set((state) => {
        const list = state.messages[activeSessionId] ?? [];
        return {
          messages: {
            ...state.messages,
            [activeSessionId]: list.map((m) => (m.id === STREAMING_ID ? { ...m, ...partial } : m)),
          },
        };
      });
    };

    try {
      await streamPost(
        absoluteUrl(chatApi.streamUrl),
        {
          session_id: activeSessionId,
          messages: [
            {
              role: "user",
              content: trimmed,
              attachments: files,
              ...(isGroup ? { sender_id: identity.id, sender_name: identity.name } : {}),
            },
          ],
          ...(action ? { action } : {}),
        },
        {
          onEvent(event, raw) {
            switch (event) {
              case "meta": {
                const meta = raw as StreamMetaPayload;
                set({ model: meta.model, mocked: meta.mocked });
                break;
              }
              case "action": {
                const payload = raw as StreamActionPayload;
                set({ lastAction: payload.action, waitingForMention: payload.waiting_for_mention });
                break;
              }
              case "emotion": {
                const payload = raw as StreamEmotionPayload;
                set({ emotion: payload.tag, emotionConfidence: payload.confidence });
                patch({ emotion: payload.tag });
                break;
              }
              case "memory": {
                const payload = raw as { items: RecalledMemory[] };
                set({ recalledMemories: payload.items ?? [] });
                break;
              }
              case "learned": {
                // 「记住了」与「想起了」是两件事：前者是后台抽取的结果
                const payload = raw as { items: LearnedMemory[]; attempted: boolean };
                set({ learnedMemories: payload.items ?? [] });
                break;
              }
              case "token":
                appendToken((raw as StreamTokenPayload).text);
                break;
              case "error":
                set({ error: (raw as StreamErrorPayload).message });
                patch({ streaming: false });
                break;
              case "done": {
                const payload = raw as StreamDonePayload;
                patch({ id: `ai-${Date.now()}`, streaming: false });
                void payload;
                break;
              }
              default:
                break;
            }
          },
          onError: (error) => set({ error: `连接中断：${error.message}` }),
        },
        undefined,
        readByokHeaders(),
      );
    } catch (error) {
      set({ error: `发送失败：${describe(error)}` });
      patch({ streaming: false });
    } finally {
      patch({ streaming: false });
      set({ sending: false });
      // 群聊未被 @ 时后端不会生成回复，把占位气泡清掉，别留一个空壳
      if (get().waitingForMention) {
        set((state) => ({
          messages: {
            ...state.messages,
            [activeSessionId]: (state.messages[activeSessionId] ?? []).filter(
              (m) => m.id !== STREAMING_ID,
            ),
          },
        }));
      }
      // 后端已落库，回读一次拿正式 id 与完整历史
      void get().selectSession(activeSessionId);
    }
  },

  clearError() {
    set({ error: null });
  },

  async removeMessage(messageId) {
    const sessionId = get().activeSessionId;
    if (!sessionId) return;
    // 先本地移除：接口往返几百毫秒，UI 里留着会让人觉得没点动
    const cached = (get().messages[sessionId] ?? []).find((m) => m.id === messageId);
    set((state) => ({
      messages: {
        ...state.messages,
        [sessionId]: (state.messages[sessionId] ?? []).filter((m) => m.id !== messageId),
      },
    }));
    try {
      await chatApi.deleteMessage(sessionId, messageId);
    } catch (error) {
      // 失败要回滚 —— 界面删了但服务端没删，等于两边不一致
      if (cached) {
        set((state) => ({
          messages: {
            ...state.messages,
            [sessionId]: [...(state.messages[sessionId] ?? []), cached],
          },
        }));
      }
      set({ error: describe(error) });
    }
  },

  async regenerate() {
    const sessionId = get().activeSessionId;
    if (!sessionId || get().sending) return;
    const list = get().messages[sessionId] ?? [];

    // 找到最后一条 AI 回复与它上面的用户消息
    const lastAi = [...list].reverse().find((m) => m.senderType === "ai");
    if (!lastAi) return;
    const before = list.slice(0, list.indexOf(lastAi)).reverse();
    const lastUser = before.find((m) => m.senderType === "user");
    if (!lastUser) return;

    // 两条都要删：旧回复留着，模型会在上下文里看到自己说过两次
    await get().removeMessage(lastAi.id);
    if (lastUser.id.startsWith("local-")) {
      set((state) => ({
        messages: {
          ...state.messages,
          [sessionId]: (state.messages[sessionId] ?? []).filter((m) => m.id !== lastUser.id),
        },
      }));
    } else {
      await get().removeMessage(lastUser.id);
    }
    await get().sendMessage(lastUser.content);
  },

  async runSummary() {
    const sessionId = get().activeSessionId;
    if (!sessionId) return;
    const session = get().sessions.find((s) => s.id === sessionId);
    if (session?.type !== "group") return;

    set({ summarizeLoading: true, groupSummaryOpen: true });
    try {
      set({ groupSummary: await chatApi.summarize(sessionId) });
    } catch (err) {
      // 摘要失败不该清掉已有结果 —— 用户可能只是想再看一遍
      set({ error: describe(err) });
    } finally {
      set({ summarizeLoading: false });
    }
  },

  closeSummary() {
    set({ groupSummaryOpen: false });
  },
}));

function describe(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function defaultTitle(type: Session["type"]): string {
  return { ai: "新的 AI 会话", direct: "新的好友", group: "新的群聊" }[type];
}
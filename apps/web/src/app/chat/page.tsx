import type { Metadata } from "next";

import { ChatWindow } from "@/features/chat/components/ChatWindow";

export const metadata: Metadata = {
  title: "对话中枢",
};

export default function ChatPage() {
  return <ChatWindow />;
}
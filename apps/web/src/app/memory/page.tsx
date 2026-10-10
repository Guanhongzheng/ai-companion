import type { Metadata } from "next";

import { MemoryPanel } from "@/features/memory/components/MemoryPanel";

export const metadata: Metadata = {
  title: "长期记忆",
};

export default function MemoryPage() {
  return (
    <main className="min-h-screen bg-background px-4">
      <MemoryPanel />
    </main>
  );
}
import type { Metadata } from "next";

import { SettingsPanel } from "@/features/settings/components/SettingsPanel";

export const metadata: Metadata = {
  title: "设置",
};

export default function SettingsPage() {
  return (
    <main className="min-h-screen bg-background px-3 pb-[env(safe-area-inset-bottom)] sm:px-4">
      <SettingsPanel />
    </main>
  );
}
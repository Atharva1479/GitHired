"use client";

import { AppShell } from "@/components/layout/AppShell";
import { StudyShell } from "@/components/study/StudyShell";

export default function StudyPage() {
  return (
    <AppShell>
      <main className="flex-1 flex flex-col">
        <StudyShell />
      </main>
    </AppShell>
  );
}

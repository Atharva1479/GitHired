"use client";

import { useEffect, useState } from "react";

import { useStudyPlan } from "@/hooks/useStudy";

import { SectionRail } from "./SectionRail";
import { SectionWorkspace } from "./SectionWorkspace";
import { StudyHome } from "./StudyHome";

export function StudyShell() {
  const { data, isLoading, error } = useStudyPlan();
  // null = Home view; a number = section workspace
  const [activeSectionId, setActiveSectionId] = useState<number | null>(null);

  // When plan loads and user is on Home with sections available, keep Home.
  // If the active section is deleted, fall back to Home.
  useEffect(() => {
    if (!data) return;
    if (activeSectionId != null) {
      const stillExists = data.sections.some((s) => s.id === activeSectionId);
      if (!stillExists) setActiveSectionId(null);
    }
  }, [data, activeSectionId]);

  if (isLoading) return <Skeleton />;
  if (error) {
    return (
      <div className="max-w-2xl w-full mx-auto px-6 pt-12">
        <div className="rounded-xl ring-1 ring-rose-200 bg-rose-50 px-4 py-3 text-[13.5px] text-rose-700">
          {error instanceof Error
            ? error.message
            : "Couldn't load your study plan."}
        </div>
      </div>
    );
  }

  const sections = data?.sections ?? [];
  const activeSection = sections.find((s) => s.id === activeSectionId);

  // Home view — shown when no section is selected (or plan is empty)
  if (!activeSection) {
    return (
      <div className="flex-1 flex max-w-7xl w-full mx-auto px-6 pt-6 pb-12 gap-6">
        {sections.length > 0 && (
          <SectionRail
            sections={sections}
            activeSectionId={null}
            onSelect={setActiveSectionId}
            onHome={() => setActiveSectionId(null)}
          />
        )}
        <div className="flex-1 min-w-0">
          <StudyHome onNavigateToSection={setActiveSectionId} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex max-w-7xl w-full mx-auto px-6 pt-6 pb-12 gap-6">
      <SectionRail
        sections={sections}
        activeSectionId={activeSection.id}
        onSelect={setActiveSectionId}
        onHome={() => setActiveSectionId(null)}
      />
      <div className="flex-1 min-w-0">
        <SectionWorkspace section={activeSection} />
      </div>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="flex-1 flex max-w-7xl w-full mx-auto px-6 pt-6 pb-12 gap-6">
      <aside className="w-[240px] shrink-0 space-y-2">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-9 rounded-lg bg-[var(--color-surface-2)] animate-pulse"
          />
        ))}
      </aside>
      <div className="flex-1 space-y-4">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-32 rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] animate-pulse"
          />
        ))}
      </div>
    </div>
  );
}

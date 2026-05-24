"use client";

import { Plus, Sparkles } from "lucide-react";
import { useState } from "react";

import { useCreateSubsection } from "@/hooks/useStudy";
import type { StudyPlanSection } from "@/lib/types";

import { AIGeneratePlanModal } from "./AIGenerateModal";
import { StudyProgressBar } from "./StudyProgressBar";
import { SubsectionCard } from "./SubsectionCard";

export function SectionWorkspace({ section }: { section: StudyPlanSection }) {
  const create = useCreateSubsection();
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState("");
  const [showGenModal, setShowGenModal] = useState(false);

  const totalTopics = section.subsections.reduce(
    (n, s) => n + s.topics.length,
    0,
  );
  const doneTopics = section.subsections.reduce(
    (n, s) =>
      n + s.topics.filter((t) => t.status === "done" || t.status === "mastered").length,
    0,
  );

  const submit = async () => {
    const name = draft.trim();
    if (!name) {
      setAdding(false);
      setDraft("");
      return;
    }
    try {
      await create.mutateAsync({ sectionId: section.id, data: { name } });
    } finally {
      setAdding(false);
      setDraft("");
    }
  };

  return (
    <>
    {showGenModal && (
      <AIGeneratePlanModal onClose={() => setShowGenModal(false)} />
    )}
    <div>
      <header className="mb-6">
        <div className="flex items-baseline justify-between gap-4 flex-wrap">
          <div className="min-w-0">
            <h1 className="text-[26px] font-bold tracking-tight text-[var(--color-text)]">
              {section.name}
            </h1>
            <p className="text-[13px] text-[var(--color-text-3)] mt-1">
              {section.subsections.length}{" "}
              {section.subsections.length === 1 ? "subsection" : "subsections"}
              {" · "}
              {totalTopics} {totalTopics === 1 ? "topic" : "topics"}
              {totalTopics > 0 ? (
                <>
                  {" · "}
                  <span className="text-emerald-600 font-medium">
                    {doneTopics} done
                  </span>
                </>
              ) : null}
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowGenModal(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg ring-1 ring-indigo-500/30 bg-indigo-500/10 text-[12.5px] text-indigo-400 hover:bg-indigo-500/20 transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Generate plan
          </button>
        </div>
        {totalTopics > 0 ? (
          <div className="mt-4 max-w-xs">
            <StudyProgressBar done={doneTopics} total={totalTopics} />
          </div>
        ) : null}
      </header>

      <div className="space-y-4">
        {section.subsections.map((sub) => (
          <SubsectionCard
            key={sub.id}
            subsection={sub}
            sectionName={section.name}
          />
        ))}
        {adding ? (
          <div className="rounded-2xl bg-[var(--color-surface)] ring-2 ring-indigo-500 px-4 py-3">
            <input
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onBlur={submit}
              onKeyDown={(e) => {
                if (e.key === "Enter") submit();
                if (e.key === "Escape") {
                  setAdding(false);
                  setDraft("");
                }
              }}
              placeholder="Subsection name…"
              className="w-full bg-transparent text-[15px] font-semibold text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-3)]"
            />
            <p className="mt-1 text-[11.5px] text-[var(--color-text-3)]">
              Enter to save · Esc to cancel
            </p>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setAdding(true)}
            className="w-full rounded-2xl border-2 border-dashed border-[var(--color-border)] hover:border-indigo-500/50 hover:bg-indigo-500/5 text-[var(--color-text-3)] hover:text-indigo-400 transition-colors px-4 py-3.5 flex items-center justify-center gap-2 text-[13.5px]"
          >
            <Plus className="w-4 h-4" />
            Add subsection
          </button>
        )}
      </div>
    </div>
    </>
  );
}

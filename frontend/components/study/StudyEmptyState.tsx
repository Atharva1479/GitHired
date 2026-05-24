"use client";

import { BookOpenCheck, Plus, Sparkles } from "lucide-react";
import { useState } from "react";

import { useCreateSection } from "@/hooks/useStudy";
import { AIGeneratePlanModal } from "./AIGenerateModal";

const _STARTER_SUGGESTIONS = [
  "Backend",
  "Frontend",
  "Language",
  "DB",
  "System Design",
];

export function StudyEmptyState() {
  const create = useCreateSection();
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [busyName, setBusyName] = useState<string | null>(null);
  const [showGenModal, setShowGenModal] = useState(false);

  const submitFreeform = async () => {
    const trimmed = name.trim();
    if (!trimmed) {
      setAdding(false);
      setName("");
      return;
    }
    try {
      await create.mutateAsync({ name: trimmed });
    } finally {
      setAdding(false);
      setName("");
    }
  };

  const submitSuggestion = async (label: string) => {
    setBusyName(label);
    try {
      await create.mutateAsync({ name: label });
    } finally {
      setBusyName(null);
    }
  };

  return (
    <>
    {showGenModal && (
      <AIGeneratePlanModal onClose={() => setShowGenModal(false)} />
    )}
    <div className="flex-1 grid place-items-center px-6 py-16">
      <div className="max-w-xl w-full text-center">
        <div className="mx-auto w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500 text-white grid place-items-center shadow-lg shadow-indigo-200">
          <BookOpenCheck className="w-7 h-7" />
        </div>
        <h1 className="mt-5 text-[24px] font-bold tracking-tight text-[var(--color-text)]">
          Build your interview prep tree
        </h1>
        <p className="mt-2 text-[14px] text-[var(--color-text-3)] leading-relaxed max-w-md mx-auto">
          Organise topics by section, mark them as you revise.
          Mix things you&apos;re learning fresh with things you&apos;re brushing up.
        </p>

        <button
          type="button"
          onClick={() => setShowGenModal(true)}
          className="mt-6 inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 text-white text-[13.5px] font-medium hover:bg-indigo-700 transition-colors shadow-sm shadow-indigo-200"
        >
          <Sparkles className="w-4 h-4" />
          Generate my study plan
        </button>

        <div className="mt-8 flex items-center gap-3 text-[11px] uppercase tracking-[0.18em] text-[var(--color-text-3)]">
          <span className="flex-1 h-px bg-[var(--color-border)]" />
          Or start manually
          <span className="flex-1 h-px bg-[var(--color-border)]" />
        </div>

        <div className="mt-5 flex flex-wrap justify-center gap-2">
          {_STARTER_SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => submitSuggestion(s)}
              disabled={busyName === s}
              className="px-3 py-1.5 rounded-full text-[12.5px] bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] text-[var(--color-text-2)] hover:ring-indigo-500/50 hover:text-indigo-400 transition-colors disabled:opacity-60"
            >
              + {s}
            </button>
          ))}
        </div>

        {adding ? (
          <div className="mt-5 mx-auto max-w-sm">
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              onBlur={submitFreeform}
              onKeyDown={(e) => {
                if (e.key === "Enter") submitFreeform();
                if (e.key === "Escape") {
                  setAdding(false);
                  setName("");
                }
              }}
              placeholder="Section name…"
              className="w-full bg-[var(--color-surface)] text-[var(--color-text)] ring-2 ring-indigo-500 rounded-lg px-3 py-2 text-[14px] outline-none placeholder:text-[var(--color-text-3)]"
            />
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setAdding(true)}
            className="mt-3 inline-flex items-center gap-1.5 text-[12.5px] text-indigo-600 hover:text-indigo-800 font-medium"
          >
            <Plus className="w-3.5 h-3.5" />
            Custom name
          </button>
        )}
      </div>
    </div>
    </>
  );
}

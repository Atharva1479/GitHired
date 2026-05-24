"use client";

import {
  BookOpen,
  CheckCircle2,
  Plus,
  RefreshCw,
  Sparkles,
  Star,
  TrendingUp,
} from "lucide-react";
import { useRef, useState } from "react";

import { useCreateSection, useStudyPlan, useStudyProgress } from "@/hooks/useStudy";
import type { StudyPlanSection } from "@/lib/types";

import { AIGeneratePlanModal } from "./AIGenerateModal";
import { StudyProgressBar } from "./StudyProgressBar";

type Props = {
  onNavigateToSection: (id: number) => void;
};

export function StudyHome({ onNavigateToSection }: Props) {
  const { data: plan, isLoading: planLoading } = useStudyPlan();
  const { data: progress, isLoading: progLoading } = useStudyProgress();
  const createSection = useCreateSection();
  const [showGenModal, setShowGenModal] = useState(false);
  const [addingSection, setAddingSection] = useState(false);
  const [newSectionName, setNewSectionName] = useState("");
  const addInputRef = useRef<HTMLInputElement>(null);

  const submitSection = async () => {
    const name = newSectionName.trim();
    if (!name) {
      setAddingSection(false);
      setNewSectionName("");
      return;
    }
    try {
      await createSection.mutateAsync({ name });
    } finally {
      setAddingSection(false);
      setNewSectionName("");
    }
  };

  const isLoading = planLoading || progLoading;

  if (isLoading) return <HomeSkeleton />;

  const hasPlan = plan && plan.sections.length > 0;
  const p = progress ?? {
    total_topics: 0,
    todo: 0,
    in_progress: 0,
    done: 0,
    mastered: 0,
    revisions_this_week: 0,
    due_for_review: 0,
  };

  const completedTopics = p.done + p.mastered;
  const pct =
    p.total_topics > 0
      ? Math.round((completedTopics / p.total_topics) * 100)
      : 0;

  return (
    <>
      {showGenModal && (
        <AIGeneratePlanModal onClose={() => setShowGenModal(false)} />
      )}
      <div className="max-w-3xl w-full mx-auto px-2 pt-2 pb-12 space-y-8">
        {/* Header */}
        <header>
          <h1 className="text-[26px] font-bold tracking-tight text-[var(--color-text)]">
            Study Dashboard
          </h1>
          <p className="text-[13.5px] text-[var(--color-text-3)] mt-1">
            Track your prep progress across all sections.
          </p>
        </header>

        {/* Stats row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard
            icon={<BookOpen className="w-4 h-4" />}
            label="Total topics"
            value={p.total_topics}
            color="text-indigo-400"
            bg="bg-indigo-500/10"
          />
          <StatCard
            icon={<CheckCircle2 className="w-4 h-4" />}
            label="Completed"
            value={completedTopics}
            color="text-emerald-400"
            bg="bg-emerald-500/10"
          />
          <StatCard
            icon={<Star className="w-4 h-4" />}
            label="Mastered"
            value={p.mastered}
            color="text-amber-400"
            bg="bg-amber-500/10"
          />
          <StatCard
            icon={<TrendingUp className="w-4 h-4" />}
            label="This week"
            value={p.revisions_this_week}
            suffix="revisions"
            color="text-violet-400"
            bg="bg-violet-500/10"
          />
        </div>

        {/* Overall progress bar */}
        {p.total_topics > 0 && (
          <div className="rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] px-5 py-4 shadow-sm">
            <div className="flex items-baseline justify-between mb-2">
              <span className="text-[13.5px] font-semibold text-[var(--color-text)]">
                Overall progress
              </span>
              <span className="text-[13px] font-semibold text-indigo-400 tabular-nums">
                {pct}%
              </span>
            </div>
            <StudyProgressBar done={completedTopics} total={p.total_topics} />
            <p className="mt-2 text-[12px] text-[var(--color-text-3)]">
              {completedTopics} of {p.total_topics} topics done or mastered
              {p.due_for_review > 0 && (
                <>
                  {" · "}
                  <span className="text-amber-600 font-medium">
                    {p.due_for_review} due for review
                  </span>
                </>
              )}
            </p>
          </div>
        )}

        {/* Due for review banner */}
        {p.due_for_review > 0 && (
          <div className="rounded-xl bg-amber-500/10 ring-1 ring-amber-500/20 px-4 py-3 flex items-center gap-3">
            <RefreshCw className="w-4 h-4 text-amber-500 shrink-0" />
            <p className="text-[13px] text-amber-300">
              <span className="font-semibold">{p.due_for_review}</span>{" "}
              {p.due_for_review === 1 ? "topic is" : "topics are"} due for
              review. Open a section to revise them.
            </p>
          </div>
        )}

        {/* Section overview */}
        {hasPlan ? (
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-[11px] uppercase tracking-[0.16em] text-[var(--color-text-3)] font-semibold">
                Sections
              </h2>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowGenModal(true)}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[12px] text-violet-400 hover:bg-violet-500/10 ring-1 ring-violet-500/30 transition-colors"
                >
                  <Sparkles className="w-3 h-3" />
                  Generate with AI
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAddingSection(true);
                    setTimeout(() => addInputRef.current?.focus(), 0);
                  }}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[12px] text-indigo-400 hover:bg-indigo-500/10 ring-1 ring-indigo-500/30 transition-colors"
                >
                  <Plus className="w-3 h-3" />
                  Add section
                </button>
              </div>
            </div>
            <div className="space-y-2">
              {plan.sections.map((s) => (
                <SectionCard
                  key={s.id}
                  section={s}
                  onClick={() => onNavigateToSection(s.id)}
                />
              ))}
              {addingSection ? (
                <div className="rounded-xl bg-[var(--color-surface)] ring-2 ring-indigo-500 px-4 py-3">
                  <input
                    ref={addInputRef}
                    autoFocus
                    value={newSectionName}
                    onChange={(e) => setNewSectionName(e.target.value)}
                    onBlur={submitSection}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") submitSection();
                      if (e.key === "Escape") {
                        setAddingSection(false);
                        setNewSectionName("");
                      }
                    }}
                    placeholder="Section name…"
                    className="w-full bg-transparent text-[14px] font-semibold text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-3)]"
                  />
                  <p className="mt-1 text-[11px] text-[var(--color-text-3)]">
                    Enter to save · Esc to cancel
                  </p>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    setAddingSection(true);
                    setTimeout(() => addInputRef.current?.focus(), 0);
                  }}
                  className="w-full rounded-xl border-2 border-dashed border-[var(--color-border)] hover:border-indigo-500/50 hover:bg-indigo-500/5 text-[var(--color-text-3)] hover:text-indigo-400 transition-colors px-4 py-3 flex items-center justify-center gap-2 text-[13px]"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add section
                </button>
              )}
            </div>
          </section>
        ) : (
          <EmptyPlanCTA onGenerate={() => setShowGenModal(true)} />
        )}
      </div>
    </>
  );
}

function StatCard({
  icon,
  label,
  value,
  suffix,
  color,
  bg,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  suffix?: string;
  color: string;
  bg: string;
}) {
  return (
    <div className="rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] px-4 py-3 shadow-sm flex items-start gap-3">
      <div className={`mt-0.5 p-1.5 rounded-lg ${bg} ${color} shrink-0`}>
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-[11px] text-[var(--color-text-3)] leading-tight">{label}</p>
        <p className="text-[22px] font-bold tabular-nums text-[var(--color-text)] leading-tight">
          {value}
        </p>
        {suffix && (
          <p className="text-[11px] text-[var(--color-text-3)] leading-tight">{suffix}</p>
        )}
      </div>
    </div>
  );
}

function SectionCard({
  section,
  onClick,
}: {
  section: StudyPlanSection;
  onClick: () => void;
}) {
  const total = section.subsections.reduce(
    (n, s) => n + s.topics.length,
    0,
  );
  const done = section.subsections.reduce(
    (n, s) =>
      n +
      s.topics.filter((t) => t.status === "done" || t.status === "mastered")
        .length,
    0,
  );

  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] hover:ring-indigo-500/50 hover:shadow-sm transition-all px-4 py-3 flex items-center gap-4 group"
    >
      <div className="flex-1 min-w-0">
        <p className="text-[14px] font-semibold text-[var(--color-text)] truncate group-hover:text-indigo-400 transition-colors">
          {section.name}
        </p>
        <p className="text-[11.5px] text-[var(--color-text-3)] mt-0.5">
          {section.subsections.length}{" "}
          {section.subsections.length === 1 ? "subsection" : "subsections"} ·{" "}
          {total} {total === 1 ? "topic" : "topics"}
        </p>
      </div>
      {total > 0 ? (
        <div className="w-32 shrink-0 space-y-1">
          <StudyProgressBar done={done} total={total} />
          <p className="text-[10.5px] text-[var(--color-text-3)] tabular-nums text-right">
            {done}/{total}
          </p>
        </div>
      ) : (
        <span className="text-[11.5px] text-[var(--color-text-3)] shrink-0">empty</span>
      )}
    </button>
  );
}

function EmptyPlanCTA({ onGenerate }: { onGenerate: () => void }) {
  return (
    <div className="rounded-2xl bg-gradient-to-br from-indigo-500/10 to-violet-500/10 ring-1 ring-indigo-500/20 px-6 py-10 text-center space-y-4">
      <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-indigo-100">
        <Sparkles className="w-6 h-6 text-indigo-600" />
      </div>
      <div>
        <p className="text-[15px] font-semibold text-[var(--color-text)]">
          No study plan yet
        </p>
        <p className="text-[13px] text-[var(--color-text-3)] mt-1 max-w-xs mx-auto">
          Let AI build your personalised syllabus, or add sections manually
          from the sidebar.
        </p>
      </div>
      <button
        type="button"
        onClick={onGenerate}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-[13.5px] font-medium hover:bg-indigo-700 transition-colors shadow-sm"
      >
        <Sparkles className="w-4 h-4" />
        Generate my study plan
      </button>
    </div>
  );
}

function HomeSkeleton() {
  return (
    <div className="max-w-3xl w-full mx-auto px-2 pt-2 pb-12 space-y-8">
      <div className="h-8 w-48 rounded-lg bg-[var(--color-surface-2)] animate-pulse" />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-20 rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] animate-pulse" />
        ))}
      </div>
      <div className="h-20 rounded-2xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] animate-pulse" />
      <div className="space-y-2">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-14 rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] animate-pulse" />
        ))}
      </div>
    </div>
  );
}

"use client";

import { ChevronDown, ChevronRight, Loader2, Sparkles, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import {
  useApplyGeneratedPlan,
  useApplyGeneratedTopics,
  useGeneratePlan,
  useGenerateTopics,
} from "@/hooks/useStudy";
import type {
  StudyAISectionPreview,
  StudyAISubsectionPreview,
  StudyAITopicPreview,
  StudyGenerateResponse,
  StudyGenerateTopicsResponse,
} from "@/lib/types";

// ── Plan-level modal ──────────────────────────────────────────────────

type PlanModalProps = {
  onClose: () => void;
  existingSectionNames?: string[];
};

export function AIGeneratePlanModal({
  onClose,
  existingSectionNames = [],
}: PlanModalProps) {
  const [role, setRole] = useState("");
  const [companies, setCompanies] = useState("");
  const [preview, setPreview] = useState<StudyGenerateResponse | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<number>>(
    new Set([0]),
  );
  const [error, setError] = useState<string | null>(null);

  const generate = useGeneratePlan();
  const apply = useApplyGeneratedPlan();

  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => { inputRef.current?.focus(); }, []);

  const handleGenerate = async () => {
    if (!role.trim()) return;
    setError(null);
    try {
      const result = await generate.mutateAsync({
        role: role.trim(),
        target_companies: companies
          ? companies.split(",").map((c) => c.trim()).filter(Boolean)
          : null,
        existing_sections:
          existingSectionNames.length > 0 ? existingSectionNames : null,
      });
      setPreview(result);
      setExpandedSections(new Set(result.sections.map((_, i) => i)));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Generation failed — try again.");
    }
  };

  const handleApply = async () => {
    if (!preview) return;
    try {
      await apply.mutateAsync(preview);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save — try again.");
    }
  };

  const toggleSection = (i: number) =>
    setExpandedSections((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });

  const removeTopic = (si: number, subi: number, ti: number) => {
    if (!preview) return;
    setPreview({
      sections: preview.sections.map((s, sIdx) =>
        sIdx !== si
          ? s
          : {
              ...s,
              subsections: s.subsections.map((sub, subIdx) =>
                subIdx !== subi
                  ? sub
                  : {
                      ...sub,
                      topics: sub.topics.filter((_, tIdx) => tIdx !== ti),
                    },
              ),
            },
      ),
    });
  };

  const totalTopics = preview?.sections.reduce(
    (n, s) =>
      n + s.subsections.reduce((m, sub) => m + sub.topics.length, 0),
    0,
  ) ?? 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative z-10 w-full max-w-2xl max-h-[90vh] flex flex-col rounded-2xl bg-[var(--color-surface)] shadow-2xl ring-1 ring-[var(--color-border)] overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-[var(--color-border)]">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 grid place-items-center shrink-0">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-[15px] font-semibold text-[var(--color-text)]">
              {preview ? "Review your plan" : "Generate study plan"}
            </h2>
            {preview ? (
              <p className="text-[12px] text-[var(--color-text-3)]">
                {preview.sections.length} sections · {totalTopics} topics —
                remove anything you don&apos;t need, then apply.
              </p>
            ) : (
              <p className="text-[12px] text-[var(--color-text-3)]">
                AI builds a personalised revision tree based on your role.
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-[var(--color-text-3)] hover:text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {/* Input form — shown until preview arrives */}
          {!preview && (
            <div className="space-y-3">
              <div>
                <label className="block text-[12px] font-medium text-[var(--color-text-2)] mb-1">
                  Your role *
                </label>
                <input
                  ref={inputRef}
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
                  placeholder="e.g. Full Stack Java Developer"
                  className="w-full rounded-lg bg-[var(--color-surface)] text-[var(--color-text)] px-3 py-2 text-[14px] ring-1 ring-[var(--color-border)] focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-[12px] font-medium text-[var(--color-text-2)] mb-1">
                  Target companies{" "}
                  <span className="text-[var(--color-text-3)] font-normal">
                    (optional, comma-separated)
                  </span>
                </label>
                <input
                  value={companies}
                  onChange={(e) => setCompanies(e.target.value)}
                  placeholder="e.g. Stripe, Anthropic, Zepto"
                  className="w-full rounded-lg bg-[var(--color-surface)] text-[var(--color-text)] px-3 py-2 text-[14px] ring-1 ring-[var(--color-border)] focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
            </div>
          )}

          {/* Preview tree */}
          {preview && (
            <div className="space-y-2">
              {preview.sections.map((section, si) => (
                <PreviewSection
                  key={si}
                  section={section}
                  expanded={expandedSections.has(si)}
                  onToggle={() => toggleSection(si)}
                  onRemoveTopic={(subi, ti) => removeTopic(si, subi, ti)}
                />
              ))}
            </div>
          )}

          {error && (
            <p className="text-[12.5px] text-rose-400 bg-rose-500/10 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-3 px-5 py-3 border-t border-[var(--color-border)] bg-[var(--color-surface-2)]">
          {preview ? (
            <>
              <button
                type="button"
                onClick={() => { setPreview(null); setError(null); }}
                className="text-[13px] text-[var(--color-text-3)] hover:text-[var(--color-text)]"
              >
                ← Edit role
              </button>
              <button
                type="button"
                onClick={handleApply}
                disabled={apply.isPending || totalTopics === 0}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-[13.5px] font-medium hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
              >
                {apply.isPending ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5" />
                )}
                Apply {totalTopics} topics
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={onClose}
                className="text-[13px] text-[var(--color-text-3)] hover:text-[var(--color-text)]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleGenerate}
                disabled={!role.trim() || generate.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-[13.5px] font-medium hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
              >
                {generate.isPending ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5" />
                )}
                {generate.isPending ? "Generating…" : "Generate plan"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Subsection-level modal ────────────────────────────────────────────

type TopicsModalProps = {
  subsectionId: number;
  subsectionName: string;
  sectionName: string;
  onClose: () => void;
};

export function AIGenerateTopicsModal({
  subsectionId,
  subsectionName,
  sectionName,
  onClose,
}: TopicsModalProps) {
  const [count, setCount] = useState(10);
  const [hint, setHint] = useState("");
  const [preview, setPreview] = useState<StudyGenerateTopicsResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  const generate = useGenerateTopics();
  const apply = useApplyGeneratedTopics();

  const handleGenerate = async () => {
    setError(null);
    try {
      const result = await generate.mutateAsync({
        subsectionId,
        data: { count, hint: hint.trim() || null },
      });
      setPreview(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Generation failed — try again.");
    }
  };

  const handleApply = async () => {
    if (!preview) return;
    try {
      await apply.mutateAsync({ subsectionId, data: preview });
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save — try again.");
    }
  };

  const removeTopic = (i: number) =>
    preview &&
    setPreview({ topics: preview.topics.filter((_, idx) => idx !== i) });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative z-10 w-full max-w-lg max-h-[85vh] flex flex-col rounded-2xl bg-[var(--color-surface)] shadow-2xl ring-1 ring-[var(--color-border)] overflow-hidden">
        <div className="flex items-center gap-3 px-5 py-4 border-b border-[var(--color-border)]">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 grid place-items-center shrink-0">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-[15px] font-semibold text-gray-900 truncate">
              AI topics for {subsectionName}
            </h2>
            <p className="text-[12px] text-gray-500">{sectionName}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-[var(--color-text-3)] hover:text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {!preview && (
            <div className="space-y-3">
              <div>
                <label className="block text-[12px] font-medium text-[var(--color-text-2)] mb-1">
                  Number of topics
                </label>
                <input
                  type="number"
                  min={1}
                  max={30}
                  value={count}
                  onChange={(e) =>
                    setCount(Math.max(1, Math.min(30, Number(e.target.value))))
                  }
                  className="w-28 rounded-lg bg-[var(--color-surface)] text-[var(--color-text)] px-3 py-2 text-[14px] ring-1 ring-[var(--color-border)] focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-[12px] font-medium text-[var(--color-text-2)] mb-1">
                  Focus hint{" "}
                  <span className="text-[var(--color-text-3)] font-normal">(optional)</span>
                </label>
                <input
                  value={hint}
                  onChange={(e) => setHint(e.target.value)}
                  placeholder="e.g. focus on interview gotchas"
                  className="w-full rounded-lg bg-[var(--color-surface)] text-[var(--color-text)] px-3 py-2 text-[14px] ring-1 ring-[var(--color-border)] focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
            </div>
          )}

          {preview && (
            <ul className="space-y-1">
              {preview.topics.map((t, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 rounded-lg px-3 py-2 hover:bg-[var(--color-surface-2)] group"
                >
                  <span className="flex-1 text-[13.5px] text-[var(--color-text)]">
                    {t.title}
                    {t.notes && (
                      <span className="ml-2 text-[11px] text-[var(--color-text-3)]">
                        {t.notes}
                      </span>
                    )}
                  </span>
                  <button
                    type="button"
                    onClick={() => removeTopic(i)}
                    className="opacity-0 group-hover:opacity-100 text-[var(--color-text-3)] hover:text-rose-500 text-[11px] shrink-0 transition-opacity"
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}

          {error && (
            <p className="text-[12.5px] text-rose-400 bg-rose-500/10 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
        </div>

        <div className="flex items-center justify-between gap-3 px-5 py-3 border-t border-[var(--color-border)] bg-[var(--color-surface-2)]">
          {preview ? (
            <>
              <button
                type="button"
                onClick={() => { setPreview(null); setError(null); }}
                className="text-[13px] text-[var(--color-text-3)] hover:text-[var(--color-text)]"
              >
                ← Re-generate
              </button>
              <button
                type="button"
                onClick={handleApply}
                disabled={apply.isPending || preview.topics.length === 0}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-[13.5px] font-medium hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
              >
                {apply.isPending && (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                )}
                Add {preview.topics.length} topics
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={onClose}
                className="text-[13px] text-[var(--color-text-3)] hover:text-[var(--color-text)]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleGenerate}
                disabled={generate.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-[13.5px] font-medium hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
              >
                {generate.isPending ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5" />
                )}
                {generate.isPending ? "Generating…" : "Generate"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Preview sub-components ────────────────────────────────────────────

function PreviewSection({
  section,
  expanded,
  onToggle,
  onRemoveTopic,
}: {
  section: StudyAISectionPreview;
  expanded: boolean;
  onToggle: () => void;
  onRemoveTopic: (subi: number, ti: number) => void;
}) {
  const topicCount = section.subsections.reduce(
    (n, s) => n + s.topics.length,
    0,
  );
  return (
    <div className="rounded-xl ring-1 ring-[var(--color-border)] overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-4 py-3 bg-[var(--color-surface-2)] hover:bg-[var(--color-surface-2)]/80 transition-colors text-left"
      >
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-[var(--color-text-3)] shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-[var(--color-text-3)] shrink-0" />
        )}
        <span className="flex-1 text-[14px] font-semibold text-[var(--color-text)]">
          {section.name}
        </span>
        <span className="text-[11px] text-[var(--color-text-3)]">
          {section.subsections.length} subsections · {topicCount} topics
        </span>
      </button>
      {expanded && (
        <div className="px-4 py-3 space-y-3">
          {section.subsections.map((sub, subi) => (
            <PreviewSubsection
              key={subi}
              subsection={sub}
              onRemoveTopic={(ti) => onRemoveTopic(subi, ti)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function PreviewSubsection({
  subsection,
  onRemoveTopic,
}: {
  subsection: StudyAISubsectionPreview;
  onRemoveTopic: (ti: number) => void;
}) {
  return (
    <div>
      <p className="text-[12.5px] font-medium text-[var(--color-text-2)] mb-1.5">
        {subsection.name}
      </p>
      <ul className="space-y-1">
        {subsection.topics.map((t, ti) => (
          <PreviewTopicRow
            key={ti}
            topic={t}
            onRemove={() => onRemoveTopic(ti)}
          />
        ))}
      </ul>
    </div>
  );
}

function PreviewTopicRow({
  topic,
  onRemove,
}: {
  topic: StudyAITopicPreview;
  onRemove: () => void;
}) {
  return (
    <li className="flex items-start gap-2 rounded-md px-2 py-1 hover:bg-[var(--color-surface-2)] group">
      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-[6px] shrink-0" />
      <span className="flex-1 text-[13px] text-[var(--color-text)]">
        {topic.title}
        {topic.notes && (
          <span className="ml-2 text-[11px] text-[var(--color-text-3)]">{topic.notes}</span>
        )}
      </span>
      <button
        type="button"
        onClick={onRemove}
        className="opacity-0 group-hover:opacity-100 text-[var(--color-text-3)] hover:text-rose-500 text-[11px] shrink-0 transition-opacity"
      >
        ✕
      </button>
    </li>
  );
}

"use client";

import { ExternalLink, Trash2, X } from "lucide-react";
import { useState } from "react";

import { useDeleteDsaProblem, useDsaProblem, useUpdateDsaProblem } from "@/hooks/useDsa";
import type { DsaProblemOut } from "@/lib/types";

import { AnalysisPanel } from "./AnalysisPanel";

const DIFF_STYLES: Record<string, string> = {
  easy: "text-emerald-700 dark:text-emerald-400",
  medium: "text-amber-700 dark:text-amber-400",
  hard: "text-rose-700 dark:text-rose-400",
};

interface ProblemDetailProps {
  problem: DsaProblemOut;
  onClose: () => void;
  autoAnalyze?: boolean;
}

export function ProblemDetail({ problem, onClose, autoAnalyze = false }: ProblemDetailProps) {
  // Subscribe to live cache so analysis shows immediately after mutation
  const { data: liveProblem } = useDsaProblem(problem.id);
  const p = liveProblem ?? problem;

  const [editingSolution, setEditingSolution] = useState(false);
  const [solutionDraft, setSolutionDraft] = useState(p.user_solution ?? "");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const update = useUpdateDsaProblem();
  const deleteProblem = useDeleteDsaProblem();

  const saveSolution = async () => {
    await update.mutateAsync({ id: problem.id, patch: { user_solution: solutionDraft } });
    setEditingSolution(false);
  };

  const handleDelete = async () => {
    await deleteProblem.mutateAsync(problem.id);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-end bg-black/40 backdrop-blur-sm">
      <div className="relative bg-[var(--color-surface)] border-l border-[var(--color-border)] w-full sm:w-[520px] h-full overflow-y-auto shadow-2xl">
        <div className="sticky top-0 bg-[var(--color-surface)] border-b border-[var(--color-border)] px-6 py-4 flex items-start gap-3 z-10">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-[11px] font-semibold uppercase ${DIFF_STYLES[p.difficulty]}`}>
                {p.difficulty}
              </span>
              <span className="text-[11px] text-[var(--color-text-3)]">· {p.topic}</span>
            </div>
            <h2 className="text-[15px] font-semibold text-[var(--color-text)] leading-snug">
              {p.title}
            </h2>
            {p.source_url ? (
              <a
                href={p.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[12px] text-indigo-500 hover:text-indigo-400 mt-1 transition-colors"
              >
                Open problem <ExternalLink className="w-3 h-3" />
              </a>
            ) : null}
          </div>

          <div className="flex items-center gap-1">
            {confirmDelete ? (
              <div className="flex items-center gap-2">
                <span className="text-[12px] text-[var(--color-text-3)]">Delete?</span>
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={deleteProblem.isPending}
                  className="px-2.5 py-1 text-[12px] rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-medium transition-colors disabled:opacity-60"
                >
                  Yes
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmDelete(false)}
                  className="px-2.5 py-1 text-[12px] rounded-lg hover:bg-[var(--color-surface-2)] text-[var(--color-text-2)] transition-colors"
                >
                  No
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setConfirmDelete(true)}
                className="p-1.5 rounded-lg hover:bg-rose-500/10 text-[var(--color-text-3)] hover:text-rose-500 transition-colors"
                title="Delete problem"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-[var(--color-surface-2)] text-[var(--color-text-3)] hover:text-[var(--color-text)] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="px-6 py-5 space-y-6">
          {p.description ? (
            <DetailSection title="Problem Statement">
              <p className="text-[14px] text-[var(--color-text)] leading-relaxed whitespace-pre-wrap">
                {p.description}
              </p>
            </DetailSection>
          ) : null}

          <DetailSection
            title="Your Solution"
            action={
              !editingSolution ? (
                <button
                  type="button"
                  onClick={() => {
                    setSolutionDraft(p.user_solution ?? "");
                    setEditingSolution(true);
                  }}
                  className="text-[12px] text-indigo-500 hover:text-indigo-400 transition-colors"
                >
                  {p.user_solution ? "Edit" : "Add solution"}
                </button>
              ) : null
            }
          >
            {editingSolution ? (
              <div className="space-y-2">
                <textarea
                  rows={10}
                  value={solutionDraft}
                  onChange={(e) => setSolutionDraft(e.target.value)}
                  className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-2 text-[12px] font-mono text-[var(--color-text)] focus:outline-none focus:ring-2 focus:ring-indigo-500/60 resize-y"
                />
                <div className="flex gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => setEditingSolution(false)}
                    className="px-3 py-1.5 text-[12px] rounded-lg text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={saveSolution}
                    disabled={update.isPending}
                    className="px-4 py-1.5 text-[12px] rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-60 transition-colors"
                  >
                    {update.isPending ? "Saving…" : "Save"}
                  </button>
                </div>
              </div>
            ) : p.user_solution ? (
              <pre className="text-[12px] font-mono bg-[var(--color-surface-2)] rounded-lg p-4 overflow-x-auto ring-1 ring-[var(--color-border)] text-[var(--color-text)] leading-relaxed whitespace-pre-wrap">
                {p.user_solution}
              </pre>
            ) : (
              <p className="text-[13px] text-[var(--color-text-3)] italic">No solution added yet.</p>
            )}
          </DetailSection>

          <div className="border-t border-[var(--color-border)] pt-5">
            <AnalysisPanel
              problemId={problem.id}
              hasSolution={!!p.user_solution}
              analysis={p.analysis}
              autoAnalyze={autoAnalyze}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function DetailSection({
  title,
  children,
  action,
}: {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-3)]">
          {title}
        </h3>
        {action}
      </div>
      {children}
    </div>
  );
}

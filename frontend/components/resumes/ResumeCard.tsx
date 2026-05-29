"use client";
import { useState } from "react";
import { FileText, Trash2, BarChart2, ExternalLink, Check, X } from "lucide-react";
import { useDeleteResume } from "@/hooks/useResumes";
import type { ResumeOut } from "@/lib/resumes-api";

interface Props {
  resume: ResumeOut;
  isSelected: boolean;
  onSelect: () => void;
}

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export function ResumeCard({ resume, isSelected, onSelect }: Props) {
  const { mutate: del, isPending } = useDeleteResume();
  const [confirming, setConfirming] = useState(false);

  return (
    <div
      className={`rounded-xl border bg-[var(--color-surface)] p-4 transition-all ${
        isSelected
          ? "border-indigo-400 ring-2 ring-indigo-400/20"
          : "border-[var(--color-border)] hover:border-indigo-400/60"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="shrink-0 w-9 h-9 rounded-lg bg-indigo-500/10 flex items-center justify-center">
            <FileText className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="min-w-0">
            <p className="text-[13px] font-semibold truncate">{resume.name}</p>
            <span className="inline-block mt-0.5 text-[10px] font-medium bg-indigo-500/10 text-indigo-400 ring-1 ring-indigo-400/20 rounded-full px-2 py-0.5">
              {resume.role_tag}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {!confirming && (
            <>
              <a
                href={`${BASE}/resumes/${resume.id}/file`}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1.5 rounded-lg text-[var(--color-text-3)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-2)] transition-colors"
                title="View PDF"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
              <button
                onClick={() => setConfirming(true)}
                className="p-1.5 rounded-lg text-[var(--color-text-3)] hover:text-red-400 hover:bg-red-500/10 transition-colors"
                title="Delete"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </>
          )}

          {confirming && (
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-[var(--color-text-3)] mr-1">Delete?</span>
              <button
                onClick={() => del(resume.id, { onSuccess: () => setConfirming(false) })}
                disabled={isPending}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-red-500 text-white text-[11px] font-semibold hover:bg-red-600 disabled:opacity-50 transition-colors"
              >
                <Check className="w-3 h-3" /> Yes
              </button>
              <button
                onClick={() => setConfirming(false)}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg border border-[var(--color-border)] text-[11px] font-semibold hover:border-[var(--color-text-3)] transition-colors"
              >
                <X className="w-3 h-3" /> No
              </button>
            </div>
          )}
        </div>
      </div>

      {!confirming && (
        <button
          onClick={onSelect}
          className={`mt-3 w-full flex items-center justify-center gap-1.5 py-2 rounded-lg text-[12px] font-medium transition-colors ${
            isSelected
              ? "bg-indigo-600 text-white"
              : "bg-[var(--color-surface-2)] text-[var(--color-text-3)] hover:bg-indigo-500/10 hover:text-indigo-400"
          }`}
        >
          <BarChart2 className="w-3.5 h-3.5" />
          {isSelected ? "Showing Gap Analysis" : "Analyze Skill Gaps"}
        </button>
      )}
    </div>
  );
}

"use client";

import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import type { AnalysisResult } from "@/types/ats";

interface Props {
  sections: AnalysisResult["sections"];
}

export function SectionStatus({ sections }: Props) {
  return (
    <div className="rounded-xl bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] p-5 shadow-sm">
      <h2 className="text-[15px] font-semibold text-[var(--color-text)] mb-4">
        Resume Sections
      </h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        {sections.found.length > 0 && (
          <div>
            <p className="text-[11px] font-medium text-[var(--color-text-3)] uppercase tracking-wider mb-2">
              Found ({sections.found.length})
            </p>
            <ul className="space-y-1.5">
              {sections.found.map((s) => (
                <li key={s} className="flex items-center gap-2 text-[13px] text-[var(--color-text)]">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                  {s}
                </li>
              ))}
            </ul>
          </div>
        )}

        {sections.missing.length > 0 && (
          <div>
            <p className="text-[11px] font-medium text-[var(--color-text-3)] uppercase tracking-wider mb-2">
              Missing ({sections.missing.length})
            </p>
            <ul className="space-y-1.5">
              {sections.missing.map((s) => (
                <li key={s} className="flex items-center gap-2 text-[13px] text-[var(--color-text-2)]">
                  <XCircle className="w-4 h-4 text-red-500 shrink-0" />
                  {s}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {sections.ats_risks.length > 0 && (
        <div>
          <p className="text-[11px] font-medium text-red-500 uppercase tracking-wider mb-2">
            ATS Risks ({sections.ats_risks.length})
          </p>
          <ul className="space-y-2">
            {sections.ats_risks.map((risk, i) => (
              <li
                key={i}
                className="flex items-start gap-2.5 rounded-lg bg-red-500/5 ring-1 ring-red-300/30 px-3 py-2.5"
              >
                <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                <span className="text-[12px] text-[var(--color-text)]">{risk}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

"use client";

import { Check, ChevronDown, ChevronUp, Copy, FileText, Info, Loader2, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import type { TailorSuggestion } from "@/types/ats";

interface TailorPanelProps {
  suggestions: TailorSuggestion[];
  loading: boolean;
  error: string | null;
  resumeText: string;
  onRetry: () => void;
}

/** Apply all rewrites to the original resume text (exact string replacement). */
function applyRewrites(resumeText: string, suggestions: TailorSuggestion[]): string {
  let updated = resumeText;
  for (const s of suggestions) {
    if (s.original && s.rewritten && s.original !== s.rewritten) {
      updated = updated.replace(s.original, s.rewritten);
    }
  }
  return updated;
}

/** Highlights each keyword occurrence in the rewritten bullet. */
function HighlightedText({ text, keywords }: { text: string; keywords: string[] }) {
  if (!keywords.length) return <>{text}</>;
  const escaped = keywords.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`(${escaped.join("|")})`, "gi");
  const parts = text.split(pattern);
  return (
    <>
      {parts.map((part, i) =>
        pattern.test(part) ? (
          <mark key={i} className="bg-emerald-100 text-emerald-800 rounded px-0.5 font-semibold not-italic">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

function CopyBtn({ text, label = "Copy", className = "" }: { text: string; label?: string; className?: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try { await navigator.clipboard.writeText(text); } catch { /* blocked */ }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }
  return (
    <button
      onClick={copy}
      className={`inline-flex items-center gap-1 font-medium transition-colors ${className}`}
    >
      {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? "Copied!" : label}
    </button>
  );
}

function SuggestionCard({ s, index }: { s: TailorSuggestion; index: number }) {
  const [showRationale, setShowRationale] = useState(false);
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-[var(--color-border)] bg-[var(--color-surface-2)]">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[11px] font-bold uppercase tracking-wide text-[var(--color-text-3)]">
            {s.section} · #{index + 1}
          </span>
          {s.keywords_added.map((kw) => (
            <span key={kw} className="text-[10.5px] font-semibold bg-emerald-100 text-emerald-700 ring-1 ring-emerald-200/80 rounded-full px-2 py-0.5">
              +{kw}
            </span>
          ))}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {s.rationale && (
            <button
              onClick={() => setShowRationale((v) => !v)}
              className="p-1 rounded-md text-[var(--color-text-3)] hover:text-indigo-500 hover:bg-indigo-50 transition-colors"
              title="Why this bullet?"
            >
              <Info className="w-3.5 h-3.5" />
            </button>
          )}
          <CopyBtn text={s.rewritten} className="text-[11px] text-[var(--color-text-3)] hover:text-indigo-500 px-2 py-1 rounded-md hover:bg-indigo-50" />
        </div>
      </div>

      {showRationale && s.rationale && (
        <div className="px-4 py-2 bg-indigo-50 border-b border-indigo-100">
          <p className="text-[11.5px] text-indigo-700 leading-relaxed">{s.rationale}</p>
        </div>
      )}

      {/* Before */}
      <div className="px-4 py-3 border-b border-[var(--color-border)]">
        <p className="text-[10px] font-bold uppercase tracking-widest text-red-400 mb-1.5">Before</p>
        <p className="text-[13px] text-[var(--color-text-3)] leading-relaxed line-through decoration-red-300/70 decoration-1">
          {s.original}
        </p>
      </div>

      {/* After */}
      <div className="px-4 py-3 bg-emerald-500/[0.04]">
        <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-600 mb-1.5">After</p>
        <p className="text-[13px] text-[var(--color-text)] leading-relaxed font-[450]">
          <HighlightedText text={s.rewritten} keywords={s.keywords_added} />
        </p>
      </div>
    </div>
  );
}

function UpdatedResumePanel({ resumeText, suggestions }: { resumeText: string; suggestions: TailorSuggestion[] }) {
  const [open, setOpen] = useState(false);
  const updatedText = useMemo(() => applyRewrites(resumeText, suggestions), [resumeText, suggestions]);
  const changeCount = suggestions.filter(
    (s) => updatedText !== resumeText && updatedText.includes(s.rewritten)
  ).length;

  return (
    <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 overflow-hidden">
      {/* Header — always visible */}
      <div className="flex items-center justify-between gap-3 px-4 py-3">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-indigo-500 shrink-0" />
          <div>
            <p className="text-[13px] font-semibold text-indigo-800">Updated resume text</p>
            <p className="text-[11.5px] text-indigo-500">
              All {changeCount} rewrite{changeCount !== 1 ? "s" : ""} applied — paste into your Google Doc or Word file
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <CopyBtn
            text={updatedText}
            label="Copy full resume"
            className="text-[12px] text-indigo-600 hover:text-indigo-700 px-3 py-1.5 rounded-lg bg-indigo-100 hover:bg-indigo-200"
          />
          <button
            onClick={() => setOpen((v) => !v)}
            className="p-1.5 rounded-lg text-indigo-500 hover:bg-indigo-100 transition-colors"
            title={open ? "Collapse" : "Preview"}
          >
            {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expandable preview */}
      {open && (
        <div className="border-t border-indigo-200 px-4 pb-4 pt-3">
          <textarea
            readOnly
            value={updatedText}
            rows={Math.min(20, updatedText.split("\n").length + 2)}
            className="w-full rounded-lg border border-indigo-200 bg-white px-3 py-2.5 text-[12.5px] text-[var(--color-text)] font-mono leading-relaxed resize-y focus:outline-none focus:ring-2 focus:ring-indigo-400 shadow-sm"
          />
          <p className="text-[10.5px] text-indigo-400 mt-2">
            Tip: Select all (Ctrl+A) inside the box then copy, or use the "Copy full resume" button above.
          </p>
        </div>
      )}
    </div>
  );
}

export function TailorPanel({ suggestions, loading, error, resumeText, onRetry }: TailorPanelProps) {
  const [allCopied, setAllCopied] = useState(false);

  async function copyAllBullets() {
    const text = suggestions
      .map((s, i) => `[${s.section} #${i + 1}]\nBefore: ${s.original}\nAfter:  ${s.rewritten}`)
      .join("\n\n");
    try { await navigator.clipboard.writeText(text); } catch { /* blocked */ }
    setAllCopied(true);
    setTimeout(() => setAllCopied(false), 2500);
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-14">
        <div className="relative">
          <Loader2 className="w-7 h-7 animate-spin text-indigo-500" />
          <Sparkles className="w-3.5 h-3.5 text-indigo-300 absolute -top-1 -right-1" />
        </div>
        <div className="text-center space-y-1">
          <p className="text-[13.5px] font-medium text-[var(--color-text)]">AI is rewriting your bullets…</p>
          <p className="text-[11.5px] text-[var(--color-text-3)]">
            Reading your resume · matching keywords · crafting rewrites · usually 15–30 s
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-center space-y-2">
        <p className="text-[13px] text-red-700">{error}</p>
        <button onClick={onRetry} className="text-[12px] font-semibold text-red-600 hover:underline">Try again</button>
      </div>
    );
  }

  if (!suggestions.length) {
    return (
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)] px-5 py-10 text-center space-y-2">
        <Sparkles className="w-6 h-6 mx-auto text-[var(--color-text-3)]" />
        <p className="text-[13px] text-[var(--color-text-3)] max-w-sm mx-auto">
          No specific bullets found to improve. Your resume may already cover the missing keywords contextually, or the text could not be parsed into individual bullets.
        </p>
        <button onClick={onRetry} className="text-[12px] font-medium text-indigo-500 hover:underline">Try again</button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <p className="text-[12px] text-[var(--color-text-3)]">
          <span className="font-semibold text-[var(--color-text)]">{suggestions.length}</span>
          {" "}bullet{suggestions.length !== 1 ? "s" : ""} identified for improvement
        </p>
        <button
          onClick={copyAllBullets}
          className="inline-flex items-center gap-1.5 text-[12px] font-semibold text-indigo-500 hover:text-indigo-600 transition-colors"
        >
          {allCopied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          {allCopied ? "Copied all" : "Copy bullet diffs"}
        </button>
      </div>

      {/* Individual before/after cards */}
      {suggestions.map((s, i) => (
        <SuggestionCard key={i} s={s} index={i} />
      ))}

      {/* ── Updated full resume ──────────────────────────────────── */}
      {resumeText && (
        <UpdatedResumePanel resumeText={resumeText} suggestions={suggestions} />
      )}

      <p className="text-[11px] text-[var(--color-text-3)] pt-1 leading-relaxed">
        Verify each rewrite matches your actual experience before submitting. AI preserves your metrics — double-check all numbers.
      </p>
    </div>
  );
}

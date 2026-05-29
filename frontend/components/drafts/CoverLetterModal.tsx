"use client";

import { Check, Copy, FileText, RefreshCw, Sparkles, Upload, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useToast } from "@/app/providers";
import { api } from "@/lib/api";
import type { Draft } from "@/lib/drafts";

type Tone = "professional" | "concise" | "enthusiastic";

const TONE_OPTIONS: { value: Tone; label: string; desc: string }[] = [
  { value: "professional", label: "Professional", desc: "Confident peer-to-peer" },
  { value: "concise",      label: "Concise",      desc: "200–230 words, punchy" },
  { value: "enthusiastic", label: "Enthusiastic", desc: "Warm, grounded interest" },
];

interface CoverLetterModalProps {
  open: boolean;
  onClose: () => void;
  appId: number | null;
  company: string;
  role: string;
  hasJd: boolean;
  hasResume: boolean;
}

export function CoverLetterModal({
  open,
  onClose,
  appId,
  company,
  role,
  hasJd,
  hasResume,
}: CoverLetterModalProps) {
  const toast = useToast();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [draft, setDraft]       = useState<Draft | null>(null);
  const [content, setContent]   = useState("");
  const [loading, setLoading]   = useState(false);
  const [copied, setCopied]     = useState(false);
  const [tone, setTone]         = useState<Tone>("professional");
  const [generated, setGenerated] = useState(false);

  useEffect(() => {
    if (open) {
      setDraft(null);
      setContent("");
      setCopied(false);
      setGenerated(false);
    }
  }, [open, appId]);

  async function generate(regenerate = false) {
    if (!appId) return;
    setLoading(true);
    try {
      const d = await api.drafts.applicationCoverLetter(appId, { regenerate, tone });
      setDraft(d);
      setContent(d.content);
      setGenerated(true);
    } catch (err) {
      toast.push("error", err instanceof Error ? err.message : "Couldn't generate cover letter");
    } finally {
      setLoading(false);
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      toast.push("success", "Cover letter copied to clipboard");
      setTimeout(() => setCopied(false), 2500);
    } catch {
      toast.push("error", "Clipboard blocked — select & copy manually");
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-2xl max-h-[90vh] flex flex-col rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="flex items-start justify-between px-5 py-4 border-b border-[var(--color-border)] shrink-0">
          <div className="flex items-center gap-2.5">
            <span className="w-8 h-8 rounded-lg bg-indigo-500/10 grid place-items-center shrink-0">
              <FileText className="w-4 h-4 text-indigo-500" />
            </span>
            <div>
              <h2 className="text-[15px] font-semibold text-[var(--color-text)]">Cover Letter</h2>
              <p className="text-[12px] text-[var(--color-text-3)]">{company} — {role}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[var(--color-text-3)] hover:bg-[var(--color-surface-2)] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="overflow-y-auto flex-1 px-5 py-4 space-y-4">

          {/* Source info row */}
          <div className="flex gap-2">
            {/* Resume status */}
            {hasResume ? (
              <div className="flex items-center gap-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 text-[12px] text-emerald-500 flex-1">
                <FileText className="w-3.5 h-3.5 shrink-0" />
                Resume uploaded — AI will read it automatically
              </div>
            ) : (
              <div className="flex items-center gap-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 px-3 py-2 text-[12px] text-amber-500 flex-1">
                <Upload className="w-3.5 h-3.5 shrink-0" />
                No resume uploaded — upload one for a personalised letter
              </div>
            )}
            {/* JD status */}
            {!hasJd && (
              <div className="flex items-center gap-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 px-3 py-2 text-[12px] text-amber-500 flex-1">
                No JD saved — letter will be role-based only
              </div>
            )}
          </div>

          {/* Tone selector */}
          <div>
            <label className="block text-[11.5px] font-semibold uppercase tracking-wide text-[var(--color-text-3)] mb-2">
              Tone
            </label>
            <div className="flex gap-2">
              {TONE_OPTIONS.map((t) => (
                <button
                  key={t.value}
                  onClick={() => setTone(t.value)}
                  className={`flex-1 rounded-lg border px-3 py-2 text-left transition-colors ${
                    tone === t.value
                      ? "border-indigo-500 bg-indigo-500/10 ring-1 ring-indigo-400/30"
                      : "border-[var(--color-border)] hover:border-indigo-400 bg-[var(--color-surface-2)]"
                  }`}
                >
                  <p className={`text-[12px] font-semibold ${tone === t.value ? "text-indigo-400" : "text-[var(--color-text)]"}`}>
                    {t.label}
                  </p>
                  <p className="text-[10.5px] text-[var(--color-text-3)] mt-0.5">{t.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Generate button (pre-generation) */}
          {!generated && (
            <button
              onClick={() => generate(false)}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-indigo-600 text-white text-[13.5px] font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors shadow-sm"
            >
              {loading
                ? <><RefreshCw className="w-4 h-4 animate-spin" /> Generating…</>
                : <><Sparkles className="w-4 h-4" /> Generate cover letter</>}
            </button>
          )}

          {/* Draft output */}
          {generated && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-[11.5px]">
                {loading ? (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-500/10 text-indigo-500 ring-1 ring-indigo-300/40 px-2.5 py-0.5">
                    <Sparkles className="w-3 h-3 animate-pulse" /> Regenerating…
                  </span>
                ) : draft?.cached ? (
                  <span className="rounded-full bg-[var(--color-surface-2)] text-[var(--color-text-3)] ring-1 ring-[var(--color-border)] px-2.5 py-0.5">
                    cached
                  </span>
                ) : (
                  <span className="rounded-full bg-emerald-500/10 text-emerald-600 ring-1 ring-emerald-300/40 px-2.5 py-0.5">
                    fresh
                  </span>
                )}
                {draft?.fallback && (
                  <span className="rounded-full bg-amber-500/10 text-amber-600 ring-1 ring-amber-300/40 px-2.5 py-0.5">
                    AI offline — template used
                  </span>
                )}
                {draft && !draft.fallback && (
                  <span className="text-[var(--color-text-3)]">{draft.model}</span>
                )}
              </div>

              <textarea
                ref={textareaRef}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={Math.max(14, content.split("\n").length + 2)}
                className="w-full rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] px-4 py-3 text-[13px] text-[var(--color-text)] leading-relaxed ring-0 focus:outline-none focus:ring-2 focus:ring-indigo-400 shadow-sm resize-y font-mono"
              />
              <p className="text-[10.5px] text-[var(--color-text-3)]">
                Editable — make it yours before sending.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-3 px-5 py-3.5 border-t border-[var(--color-border)] bg-[var(--color-surface-2)] shrink-0">
          <div className="flex items-center gap-2">
            {generated && (
              <button
                onClick={() => generate(true)}
                disabled={loading}
                className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[var(--color-text-3)] hover:text-[var(--color-text)] disabled:opacity-50 transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                Regenerate
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg text-[12.5px] font-medium text-[var(--color-text-3)] hover:bg-[var(--color-surface)] border border-[var(--color-border)] transition-colors"
            >
              Close
            </button>
            <button
              onClick={copy}
              disabled={!content}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-indigo-600 text-white text-[12.5px] font-semibold hover:bg-indigo-700 disabled:opacity-40 transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? "Copied!" : "Copy letter"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

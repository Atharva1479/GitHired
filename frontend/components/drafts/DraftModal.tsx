"use client";

import { Check, Copy, RefreshCw, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

import { useToast } from "@/app/providers";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import {
  DRAFT_SUBTITLE,
  DRAFT_TITLE,
  type Draft,
  type DraftType,
} from "@/lib/drafts";

type DraftRequest =
  | { kind: "application_followup"; appId: number }
  | { kind: "referral_ask"; refId: number }
  | { kind: "referral_followup"; refId: number };

export function DraftModal({
  open,
  onClose,
  request,
}: {
  open: boolean;
  onClose: () => void;
  request: DraftRequest | null;
}) {
  const toast = useToast();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  async function fetchDraft(regenerate: boolean) {
    if (!request) return;
    setLoading(true);
    try {
      const fn =
        request.kind === "application_followup"
          ? () => api.drafts.applicationFollowup(request.appId, regenerate)
          : request.kind === "referral_ask"
            ? () => api.drafts.referralAsk(request.refId, regenerate)
            : () => api.drafts.referralFollowup(request.refId, regenerate);
      const d = await fn();
      setDraft(d);
      setContent(d.content);
    } catch (err) {
      toast.push(
        "error",
        err instanceof Error ? err.message : "Couldn't generate draft",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!open || !request) return;
    setDraft(null);
    setContent("");
    setCopied(false);
    fetchDraft(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, request?.kind, (request as { appId?: number; refId?: number })?.appId, (request as { refId?: number })?.refId]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      toast.push("success", "Copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.push("error", "Clipboard blocked — select & copy manually");
    }
  }

  const draftType: DraftType | null = request
    ? request.kind === "application_followup"
      ? "followup_email"
      : request.kind === "referral_ask"
        ? "referral_ask"
        : "referral_followup"
    : null;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={draftType ? DRAFT_TITLE[draftType] : "Draft"}
      subtitle={draftType ? DRAFT_SUBTITLE[draftType] : undefined}
    >
      <div className="space-y-4">
        {/* status row */}
        <div className="flex items-center gap-2 flex-wrap text-[12px]">
          {loading ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-500/10 text-indigo-400 ring-1 ring-indigo-500/20 px-2 py-0.5">
              <Sparkles className="w-3 h-3 animate-pulse" />
              Generating…
            </span>
          ) : draft?.cached ? (
            <span className="rounded-full bg-[var(--color-surface-2)] text-[var(--color-text-3)] ring-1 ring-[var(--color-border)] px-2 py-0.5">
              cached
            </span>
          ) : draft ? (
            <span className="rounded-full bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20 px-2 py-0.5">
              fresh
            </span>
          ) : null}
          {draft?.fallback ? (
            <span className="rounded-full bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20 px-2 py-0.5">
              AI offline — using template
            </span>
          ) : null}
          {draft && !draft.fallback ? (
            <span className="text-[var(--color-text-3)]">{draft.model}</span>
          ) : null}
        </div>

        {/* content */}
        {loading && !draft ? (
          <div className="space-y-2">
            <div className="h-3 rounded bg-[var(--color-surface-2)] animate-pulse" />
            <div className="h-3 rounded bg-gray-100 animate-pulse w-11/12" />
            <div className="h-3 rounded bg-gray-100 animate-pulse w-9/12" />
            <div className="h-3 rounded bg-gray-100 animate-pulse w-10/12" />
          </div>
        ) : (
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={Math.max(8, content.split("\n").length + 1)}
            className="w-full rounded-lg bg-[var(--color-surface)] px-3 py-2 text-[13.5px] text-[var(--color-text)] leading-relaxed ring-1 ring-inset ring-[var(--color-border)] focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm resize-y font-mono"
          />
        )}

        <div className="flex items-center justify-between pt-3 border-t border-[var(--color-border)]">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => fetchDraft(true)}
            disabled={loading}
            className="gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Regenerate
          </Button>
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={onClose}>
              Close
            </Button>
            <Button onClick={copy} disabled={!content} className="gap-1.5">
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? "Copied" : "Copy"}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}

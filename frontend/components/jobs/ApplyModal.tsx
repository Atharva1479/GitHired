"use client";
import { useState } from "react";
import { CheckCircle2, ChevronRight, ExternalLink, X, Zap } from "lucide-react";

import { useToast } from "@/app/providers";
import { useApplyAndTrack, useSimilarJobs } from "@/hooks/useJobs";
import type { JobResult } from "@/types/jobs";
import { safeUrl } from "@/lib/url-utils";

interface ApplyModalProps {
  job: JobResult;
  onClose: () => void;
  onSuccess: (applicationId: number) => void;
  onViewJob?: (job: JobResult) => void;  // open a similar job in preview
}

function SimilarJobRow({ job, onView }: { job: JobResult; onView: () => void }) {
  const color =
    job.freshness_color === "emerald" ? "text-emerald-600" :
    job.freshness_color === "green"   ? "text-green-600" :
    job.freshness_color === "amber"   ? "text-amber-600" : "text-red-500";

  return (
    <button
      onClick={onView}
      className="w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-xl border border-[var(--color-border)] hover:border-indigo-400/60 hover:bg-[var(--color-surface)] transition-colors text-left"
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[var(--color-text)] truncate">{job.title}</p>
        <p className="text-xs text-[var(--color-text-3)]">{job.company} · <span className={color}>{job.freshness_label}</span></p>
      </div>
      <ChevronRight className="w-4 h-4 text-[var(--color-text-3)] shrink-0" />
    </button>
  );
}

export default function ApplyModal({ job, onClose, onSuccess, onViewJob }: ApplyModalProps) {
  const { mutateAsync, isPending } = useApplyAndTrack();
  const toast = useToast();
  const [applied, setApplied] = useState(false);
  const [appliedId, setAppliedId] = useState<number | null>(null);

  // Fetch similar jobs only after success
  const { data: similarJobs } = useSimilarJobs(applied ? job.id : null);

  async function handleApply() {
    window.open(safeUrl(job.apply_url), "_blank", "noopener,noreferrer");
    try {
      const res = await mutateAsync({
        job_cache_id: job.id,
        title: job.title,
        company: job.company,
        apply_url: job.apply_url,
        posted_at: job.posted_at,
        source: job.source,
        external_id: job.external_id,
        description: job.description,
      });
      setApplied(true);
      setAppliedId(res.application_id);
      onSuccess(res.application_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "";
      if (msg.startsWith("already_applied:")) {
        toast.push("error", "You've already applied to this job");
        onClose();
      } else {
        toast.push("error", "Failed to track application. Please try again.");
      }
    }
  }

  function handleViewSimilar(similar: JobResult) {
    onClose();
    onViewJob?.(similar);
  }

  /* ── Success state ──────────────────────────────────────────── */
  if (applied) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm px-4">
        <div className="w-full max-w-md rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-2xl">
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              <div>
                <p className="text-sm font-bold text-emerald-600">Added to tracker!</p>
                <p className="text-xs text-[var(--color-text-3)]">{job.title} · {job.company}</p>
              </div>
            </div>
            <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-[var(--color-border)]">
              <X className="w-4 h-4 text-[var(--color-text-3)]" />
            </button>
          </div>

          {/* Similar jobs */}
          {similarJobs && similarJobs.length > 0 && (
            <div className="mb-4">
              <p className="text-xs font-semibold text-[var(--color-text-3)] uppercase tracking-wide mb-2">
                Similar fresh roles
              </p>
              <div className="space-y-2">
                {similarJobs.map((s) => (
                  <SimilarJobRow
                    key={`${s.source}-${s.external_id}`}
                    job={s}
                    onView={() => handleViewSimilar(s)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 mt-2">
            <a
              href="/applications"
              className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl border border-[var(--color-border)] text-sm font-medium hover:border-indigo-400 transition-colors"
            >
              View in Tracker
            </a>
            <button
              onClick={onClose}
              className="flex-1 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 transition-colors"
            >
              Continue Browsing
            </button>
          </div>
        </div>
      </div>
    );
  }

  /* ── Confirm state ──────────────────────────────────────────── */
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm px-4">
      <div className="w-full max-w-md rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Zap className="w-4 h-4 text-indigo-500" />
              <span className="text-sm font-semibold text-indigo-500">Apply & Auto-Track</span>
            </div>
            <h3 className="font-bold text-base text-[var(--color-text)]">{job.title}</h3>
            <p className="text-sm text-[var(--color-text-2)]">{job.company}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-[var(--color-border)]">
            <X className="w-4 h-4 text-[var(--color-text-3)]" />
          </button>
        </div>

        <div className="rounded-xl bg-indigo-500/5 ring-1 ring-indigo-500/20 p-4 mb-5 space-y-1.5 text-sm">
          <p className="text-[var(--color-text-2)]">✓ Job posting opens in a new tab</p>
          <p className="text-[var(--color-text-2)]">✓ Application entry created automatically in your tracker</p>
          <p className="text-[var(--color-text-2)]">✓ Job description saved · Status set to <strong>Applied</strong></p>
        </div>

        <div className="rounded-xl px-4 py-3 mb-5 text-sm font-medium bg-emerald-500/10 text-emerald-600">
          {job.freshness_label} · Est. {job.est_applicants} applicants — apply now for best chances!
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 rounded-xl border border-[var(--color-border)] text-sm font-medium hover:border-[var(--color-text-3)] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleApply}
            disabled={isPending}
            className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            {isPending ? "Tracking…" : "Apply & Track"}
          </button>
        </div>
      </div>
    </div>
  );
}

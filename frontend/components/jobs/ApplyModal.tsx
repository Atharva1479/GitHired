"use client";
import { ExternalLink, X, Zap } from "lucide-react";

import { useApplyAndTrack } from "@/hooks/useJobs";
import type { JobResult } from "@/types/jobs";

interface ApplyModalProps {
  job: JobResult;
  onClose: () => void;
  onSuccess: (applicationId: number) => void;
}

export default function ApplyModal({ job, onClose, onSuccess }: ApplyModalProps) {
  const { mutateAsync, isPending } = useApplyAndTrack();

  async function handleApply() {
    window.open(job.apply_url, "_blank", "noopener,noreferrer");
    const res = await mutateAsync({
      job_cache_id: job.id,
      title: job.title,
      company: job.company,
      apply_url: job.apply_url,
      posted_at: job.posted_at,
      source: job.source,
      external_id: job.external_id,
    });
    onSuccess(res.application_id);
    onClose();
  }

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
          <p className="text-[var(--color-text-2)]">✓ Status set to <strong>Applied</strong> with today's date</p>
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

"use client";

import { Pencil, ExternalLink, Sparkles, Trash2, UserCircle2, Mail, FileText } from "lucide-react";
import { formatDistanceToNowStrict, parseISO } from "date-fns";
import { useEffect, useState } from "react";

import { useToast } from "@/app/providers";
import { CoverLetterModal } from "@/components/drafts/CoverLetterModal";
import { DraftModal } from "@/components/drafts/DraftModal";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  useApplication,
  useDeleteApplication,
} from "@/hooks/useApplications";
import { companyAvatarClass } from "@/lib/types";

import { AttachmentRow } from "./AttachmentRow";
import { EditApplicationForm } from "./EditApplicationForm";

export function ApplicationDetail({
  appId,
  onClose,
}: {
  appId: number | null;
  onClose: () => void;
}) {
  const { data: app, isLoading } = useApplication(appId);
  const del = useDeleteApplication();
  const toast = useToast();
  const [confirming, setConfirming] = useState(false);
  const [draftOpen, setDraftOpen] = useState(false);
  const [coverLetterOpen, setCoverLetterOpen] = useState(false);
  const [editing, setEditing] = useState(false);

  // Reset edit mode when switching applications.
  useEffect(() => {
    setEditing(false);
    setConfirming(false);
  }, [appId]);

  async function handleDelete() {
    if (!app) return;
    try {
      await del.mutateAsync(app.id);
      toast.push("success", `${app.company} deleted`);
      onClose();
    } catch (err) {
      toast.push(
        "error",
        err instanceof Error ? err.message : "Couldn't delete",
      );
    }
  }

  return (
    <Modal
      open={appId != null}
      onClose={() => {
        setConfirming(false);
        setEditing(false);
        onClose();
      }}
      title={app ? app.company : "Loading…"}
      subtitle={app ? app.role : undefined}
    >
      {isLoading || !app ? (
        <div className="space-y-3">
          <div className="h-4 bg-[var(--color-surface-2)] rounded animate-pulse" />
          <div className="h-4 bg-[var(--color-surface-2)] rounded animate-pulse w-2/3" />
        </div>
      ) : editing ? (
        <EditApplicationForm
          app={app}
          onDone={() => setEditing(false)}
          onCancel={() => setEditing(false)}
        />
      ) : (
        <div className="space-y-5">
          {/* meta row */}
          <div className="flex items-center gap-3 flex-wrap">
            <span
              className={`w-10 h-10 rounded-lg grid place-items-center text-sm font-semibold shrink-0 ${companyAvatarClass(app.company)}`}
              aria-hidden
            >
              {app.company.charAt(0).toUpperCase()}
            </span>
            <StatusBadge status={app.status} />
            <span className="text-[12.5px] text-[var(--color-text-3)]">
              Applied{" "}
              {formatDistanceToNowStrict(parseISO(app.applied_date), {
                addSuffix: true,
              })}
            </span>
            <span className="text-[var(--color-border)]">·</span>
            <span className="text-[12.5px] text-[var(--color-text-3)]">
              via {app.source}
            </span>
            <div className="ml-auto flex items-center gap-3">
              {app.jd_url ? (
                <a
                  href={app.jd_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-[12.5px] font-medium text-indigo-400 hover:text-indigo-300"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  Job post
                </a>
              ) : null}
              <button
                type="button"
                onClick={() => setEditing(true)}
                className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[12.5px] font-medium text-[var(--color-text-2)] ring-1 ring-[var(--color-border)] hover:bg-[var(--color-surface-2)] hover:text-[var(--color-text)] transition-colors"
              >
                <Pencil className="w-3.5 h-3.5" />
                Edit
              </button>
            </div>
          </div>

          {app.contact_name ? (
            <div className="inline-flex items-center gap-1.5 text-[12.5px] text-[var(--color-text-2)] bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)] rounded-md px-2.5 py-1.5 w-fit">
              <UserCircle2 className="w-3.5 h-3.5 text-[var(--color-text-3)]" />
              <span className="text-[var(--color-text-3)]">Referred by</span>
              <span className="font-medium text-[var(--color-text)]">
                {app.contact_name}
              </span>
            </div>
          ) : null}

          {/* AI drafts */}
          <section>
            <div className="flex items-center gap-1.5 mb-2">
              <Sparkles className="w-3 h-3 text-indigo-400" />
              <span className="text-[11.5px] font-semibold uppercase tracking-wide text-[var(--color-text-3)]">
                AI Drafts
              </span>
            </div>
            <div className="grid grid-cols-1 gap-1.5">
              <button
                onClick={() => setDraftOpen(true)}
                className="group flex items-center gap-2.5 rounded-lg bg-indigo-500/5 ring-1 ring-indigo-500/15 px-3 py-2.5 text-left transition-colors hover:bg-indigo-500/10 hover:ring-indigo-500/25"
              >
                <span className="w-7 h-7 rounded-md bg-[var(--color-surface-2)] ring-1 ring-indigo-500/20 grid place-items-center shrink-0">
                  <Mail className="w-3.5 h-3.5 text-indigo-400" />
                </span>
                <span className="flex-1 min-w-0">
                  <span className="block text-[13px] font-medium text-[var(--color-text)]">Follow-up email</span>
                  <span className="block text-[11.5px] text-[var(--color-text-3)]">Nudge after applying — no reply yet</span>
                </span>
                <span className="text-[11.5px] font-medium text-indigo-400 group-hover:text-indigo-300 shrink-0">Draft →</span>
              </button>
              <button
                onClick={() => setCoverLetterOpen(true)}
                className="group flex items-center gap-2.5 rounded-lg bg-indigo-500/5 ring-1 ring-indigo-500/15 px-3 py-2.5 text-left transition-colors hover:bg-indigo-500/10 hover:ring-indigo-500/25"
              >
                <span className="w-7 h-7 rounded-md bg-[var(--color-surface-2)] ring-1 ring-indigo-500/20 grid place-items-center shrink-0">
                  <FileText className="w-3.5 h-3.5 text-indigo-400" />
                </span>
                <span className="flex-1 min-w-0">
                  <span className="block text-[13px] font-medium text-[var(--color-text)]">Cover letter</span>
                  <span className="block text-[11.5px] text-[var(--color-text-3)]">Reads your resume + JD — specific, no clichés</span>
                </span>
                <span className="text-[11.5px] font-medium text-indigo-400 group-hover:text-indigo-300 shrink-0">Draft →</span>
              </button>
            </div>
          </section>

          {/* job description text */}
          {app.jd_text ? (
            <section>
              <h3 className="text-[12px] font-semibold uppercase tracking-wide text-[var(--color-text-3)] mb-2">
                Job description
              </h3>
              <div className="rounded-lg bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)] p-3 text-[13px] text-[var(--color-text-2)] whitespace-pre-wrap leading-relaxed">
                {app.jd_text}
              </div>
            </section>
          ) : null}

          {/* attachments */}
          <section className="space-y-2">
            <h3 className="text-[12px] font-semibold uppercase tracking-wide text-[var(--color-text-3)]">
              Attachments
            </h3>
            <AttachmentRow
              appId={app.id}
              kind="resume"
              fileName={app.resume_file_name}
            />
            <AttachmentRow
              appId={app.id}
              kind="cover_letter"
              fileName={app.cover_letter_file_name}
            />
          </section>

          {/* notes (read-only for now) */}
          {app.notes ? (
            <section>
              <h3 className="text-[12px] font-semibold uppercase tracking-wide text-[var(--color-text-3)] mb-2">
                Notes
              </h3>
              <p className="text-[13.5px] text-[var(--color-text-2)] whitespace-pre-wrap leading-relaxed">
                {app.notes}
              </p>
            </section>
          ) : null}

          {/* danger zone */}
          <section className="flex items-center justify-between pt-4 border-t border-[var(--color-border)]">
            <span className="text-[12px] text-[var(--color-text-3)]">
              Created {formatDistanceToNowStrict(parseISO(app.created_at))} ago
            </span>
            {confirming ? (
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setConfirming(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={handleDelete}
                  disabled={del.isPending}
                >
                  {del.isPending ? "Deleting…" : "Confirm delete"}
                </Button>
              </div>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setConfirming(true)}
                className="text-red-600 hover:bg-red-50 gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Delete application
              </Button>
            )}
          </section>

          <DraftModal
            open={draftOpen}
            onClose={() => setDraftOpen(false)}
            request={
              draftOpen ? { kind: "application_followup", appId: app.id } : null
            }
          />
          <CoverLetterModal
            open={coverLetterOpen}
            onClose={() => setCoverLetterOpen(false)}
            appId={app.id}
            company={app.company}
            role={app.role}
            hasJd={!!app.jd_text}
            hasResume={!!app.resume_file_name}
          />
        </div>
      )}
    </Modal>
  );
}

"use client";

import { formatDistanceToNowStrict, parseISO } from "date-fns";
import { ExternalLink, Pencil, Plus, Sparkles, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";

import { useToast } from "@/app/providers";
import { DraftModal } from "@/components/drafts/DraftModal";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { useApplications } from "@/hooks/useApplications";
import {
  useDeleteReferral,
  useLinkApplication,
  useLinkedApplications,
  useMarkAccepted,
  useMarkReplied,
  useMarkSent,
  useReferral,
  useUnlinkApplication,
} from "@/hooks/useReferrals";
import { CONN_STATUS_META } from "@/lib/referrals";
import { companyAvatarClass } from "@/lib/types";

import { EditReferralForm } from "./EditReferralForm";

export function ReferralDetail({
  refId,
  onClose,
}: {
  refId: number | null;
  onClose: () => void;
}) {
  const { data: ref, isLoading } = useReferral(refId);
  const linked = useLinkedApplications(refId);
  const allApps = useApplications();
  const link = useLinkApplication();
  const unlink = useUnlinkApplication();
  const accepted = useMarkAccepted();
  const sent = useMarkSent();
  const replied = useMarkReplied();
  const del = useDeleteReferral();
  const toast = useToast();
  const [confirming, setConfirming] = useState(false);
  const [picking, setPicking] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draftKind, setDraftKind] = useState<
    "referral_ask" | "referral_followup" | null
  >(null);

  useEffect(() => {
    setEditing(false);
    setConfirming(false);
    setPicking(false);
  }, [refId]);

  async function quick(
    fn: ReturnType<typeof useMarkAccepted>,
    okMsg: string,
  ) {
    if (!ref) return;
    try {
      await fn.mutateAsync(ref.id);
      toast.push("success", okMsg);
    } catch (err) {
      toast.push("error", err instanceof Error ? err.message : "Action failed");
    }
  }

  async function handleDelete() {
    if (!ref) return;
    try {
      await del.mutateAsync(ref.id);
      toast.push("success", `${ref.name} deleted`);
      onClose();
    } catch (err) {
      toast.push("error", err instanceof Error ? err.message : "Couldn't delete");
    }
  }

  async function doLink(appId: number) {
    if (!ref) return;
    try {
      await link.mutateAsync({ refId: ref.id, appId });
      toast.push("success", "Linked");
      setPicking(false);
    } catch (err) {
      toast.push("error", err instanceof Error ? err.message : "Couldn't link");
    }
  }

  async function doUnlink(appId: number) {
    if (!ref) return;
    try {
      await unlink.mutateAsync({ refId: ref.id, appId });
      toast.push("success", "Unlinked");
    } catch (err) {
      toast.push("error", err instanceof Error ? err.message : "Couldn't unlink");
    }
  }

  const linkedApps = linked.data ?? [];
  const linkedIds = new Set(linkedApps.map((a) => a.id));
  const candidates = (allApps.data ?? []).filter((a) => !linkedIds.has(a.id));

  return (
    <Modal
      open={refId != null}
      onClose={() => {
        setConfirming(false);
        setPicking(false);
        setEditing(false);
        onClose();
      }}
      title={ref ? ref.name : "Loading…"}
      subtitle={
        ref
          ? `${ref.role_at_company ? ref.role_at_company + " · " : ""}${ref.company} · seeking ${ref.target_role}`
          : undefined
      }
    >
      {isLoading || !ref ? (
        <div className="space-y-3">
          <div className="h-4 bg-[var(--color-surface-2)] rounded animate-pulse" />
          <div className="h-4 bg-gray-100 rounded animate-pulse w-2/3" />
        </div>
      ) : editing ? (
        <EditReferralForm
          referral={ref}
          onDone={() => setEditing(false)}
          onCancel={() => setEditing(false)}
        />
      ) : (
        <div className="space-y-5">
          {/* meta */}
          <div className="flex items-center gap-3 flex-wrap">
            <span
              className={`w-10 h-10 rounded-lg grid place-items-center text-sm font-semibold shrink-0 ${companyAvatarClass(ref.name)}`}
              aria-hidden
            >
              {ref.name.charAt(0).toUpperCase()}
            </span>
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ${CONN_STATUS_META[ref.connection_status].chip}`}
            >
              <span
                aria-hidden
                className={`w-1.5 h-1.5 rounded-full ${CONN_STATUS_META[ref.connection_status].dot}`}
              />
              {CONN_STATUS_META[ref.connection_status].label}
            </span>
            <span className="text-[12.5px] text-[var(--color-text-3)]">
              Invited{" "}
              {formatDistanceToNowStrict(parseISO(ref.connection_sent_date), {
                addSuffix: true,
              })}
            </span>
            <div className="ml-auto flex items-center gap-3">
              {ref.linkedin_url ? (
                <a
                  href={ref.linkedin_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-[12.5px] font-medium text-indigo-400 hover:text-indigo-300"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  LinkedIn
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

          {/* quick actions */}
          <section>
            <h3 className="text-[12px] font-semibold uppercase tracking-wide text-[var(--color-text-3)] mb-2">
              Quick actions
            </h3>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="secondary"
                disabled={ref.connection_status !== "Request Sent" || accepted.isPending}
                onClick={() => quick(accepted, "Marked accepted")}
              >
                Mark accepted
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={
                  !["Request Sent", "Accepted"].includes(ref.connection_status) ||
                  sent.isPending
                }
                onClick={() => quick(sent, "Marked message sent")}
              >
                Mark message sent
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={ref.connection_status !== "Msg Sent" || replied.isPending}
                onClick={() => quick(replied, "Marked replied")}
              >
                Mark replied
              </Button>
            </div>
          </section>

          {/* AI drafts */}
          <section>
            <h3 className="text-[12px] font-semibold uppercase tracking-wide text-[var(--color-text-3)] mb-2">
              AI drafts
            </h3>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setDraftKind("referral_ask")}
                className="gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                Draft referral ask
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setDraftKind("referral_followup")}
                className="gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                Draft gentle follow-up
              </Button>
            </div>
          </section>

          {/* mutual context */}
          {ref.mutual_context ? (
            <section>
              <h3 className="text-[12px] font-semibold uppercase tracking-wide text-[var(--color-text-3)] mb-2">
                Mutual context
              </h3>
              <p className="text-[13.5px] text-[var(--color-text-2)] whitespace-pre-wrap leading-relaxed">
                {ref.mutual_context}
              </p>
            </section>
          ) : null}

          {/* linked applications */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-[12px] font-semibold uppercase tracking-wide text-[var(--color-text-3)]">
                Linked applications
              </h3>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setPicking((p) => !p)}
                className="gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" />
                Link app
              </Button>
            </div>

            {picking ? (
              <div className="rounded-lg ring-1 ring-[var(--color-border)] bg-[var(--color-surface-2)] p-2 mb-2 max-h-40 overflow-y-auto">
                {candidates.length === 0 ? (
                  <div className="text-[12.5px] text-[var(--color-text-3)] px-2 py-1">
                    No applications available to link.
                  </div>
                ) : (
                  <ul className="space-y-1">
                    {candidates.map((a) => (
                      <li key={a.id}>
                        <button
                          type="button"
                          onClick={() => doLink(a.id)}
                          className="w-full flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left hover:bg-[var(--color-surface)] transition-colors"
                        >
                          <span className="text-[13px] text-[var(--color-text)] truncate">
                            <span className="font-medium">{a.company}</span> ·{" "}
                            <span className="text-[var(--color-text-3)]">{a.role}</span>
                          </span>
                          <span className="text-[11px] text-[var(--color-text-3)]">{a.status}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : null}

            {linkedApps.length === 0 ? (
              <div className="text-[12.5px] text-[var(--color-text-3)]">
                None yet — link an application this referral pointed you to.
              </div>
            ) : (
              <ul className="space-y-1.5">
                {linkedApps.map((a) => (
                  <li
                    key={a.id}
                    className="flex items-center justify-between gap-2 rounded-lg bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] px-3 py-2"
                  >
                    <span className="text-[13px] text-[var(--color-text)] truncate">
                      <span className="font-medium">{a.company}</span> ·{" "}
                      <span className="text-[var(--color-text-3)]">{a.role}</span>
                    </span>
                    <button
                      onClick={() => doUnlink(a.id)}
                      aria-label="Unlink"
                      className="rounded-md p-1 text-[var(--color-text-3)] hover:text-red-500 hover:bg-red-500/10 transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {ref.notes ? (
            <section>
              <h3 className="text-[12px] font-semibold uppercase tracking-wide text-[var(--color-text-3)] mb-2">
                Notes
              </h3>
              <p className="text-[13.5px] text-[var(--color-text-2)] whitespace-pre-wrap leading-relaxed">
                {ref.notes}
              </p>
            </section>
          ) : null}

          <section className="flex items-center justify-between pt-4 border-t border-[var(--color-border)]">
            <span className="text-[12px] text-[var(--color-text-3)]">
              Created {formatDistanceToNowStrict(parseISO(ref.created_at))} ago
            </span>
            {confirming ? (
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={() => setConfirming(false)}>
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
                Delete referral
              </Button>
            )}
          </section>

          <DraftModal
            open={draftKind != null}
            onClose={() => setDraftKind(null)}
            request={
              draftKind === "referral_ask"
                ? { kind: "referral_ask", refId: ref.id }
                : draftKind === "referral_followup"
                  ? { kind: "referral_followup", refId: ref.id }
                  : null
            }
          />
        </div>
      )}
    </Modal>
  );
}

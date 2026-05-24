"use client";

import { formatDistanceToNowStrict, parseISO } from "date-fns";
import {
  AlertCircle,
  Calendar,
  Check,
  Clock,
  ExternalLink,
  MessageSquare,
  Sparkles,
  Target,
  UserCheck,
  UserPlus,
  Users,
  UserX,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { useToast } from "@/app/providers";
import { DraftModal } from "@/components/drafts/DraftModal";
import { useMarkActed, useSnooze } from "@/hooks/useNudges";
import { SEVERITY_META, type Nudge, type NudgeType } from "@/lib/nudges";

type DraftRequest =
  | { kind: "application_followup"; appId: number }
  | { kind: "referral_ask"; refId: number }
  | { kind: "referral_followup"; refId: number };

const TYPE_META: Record<
  NudgeType,
  { icon: React.ComponentType<{ className?: string }>; label: string }
> = {
  application_followup:        { icon: MessageSquare, label: "Follow-up"    },
  application_stale:           { icon: AlertCircle,   label: "Stale"         },
  application_interview_stale: { icon: Calendar,      label: "Interview"     },
  apply_more:                  { icon: Target,        label: "Apply more"    },
  referral_check:              { icon: UserCheck,     label: "Check in"      },
  referral_unaccepted:         { icon: UserX,         label: "Not accepted"  },
  referral_ask:                { icon: UserPlus,      label: "Ask referral"  },
  referral_followup:           { icon: Users,         label: "Follow-up"     },
};

function draftFor(nudge: Nudge): DraftRequest | null {
  const t: NudgeType = nudge.type;
  if (nudge.reference_id == null) return null;
  if (t === "application_followup")
    return { kind: "application_followup", appId: nudge.reference_id };
  if (t === "referral_check" || t === "referral_ask")
    return { kind: "referral_ask", refId: nudge.reference_id };
  if (t === "referral_followup")
    return { kind: "referral_followup", refId: nudge.reference_id };
  return null;
}

function renderInline(message: string): React.ReactNode[] {
  const parts = message.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**") ? (
      <strong key={i} className="font-semibold text-[var(--color-text)]">
        {p.slice(2, -2)}
      </strong>
    ) : (
      <span key={i}>{p}</span>
    ),
  );
}

const SNOOZE_OPTIONS = [1, 3, 7];

export function NudgeCard({ nudge, dimmed = false }: { nudge: Nudge; dimmed?: boolean }) {
  const acted = useMarkActed();
  const snooze = useSnooze();
  const toast = useToast();
  const [menuOpen, setMenuOpen] = useState(false);
  const [draftOpen, setDraftOpen] = useState(false);

  const draftReq  = draftFor(nudge);
  const meta      = SEVERITY_META[nudge.severity];
  const typeMeta  = TYPE_META[nudge.type];
  const TypeIcon  = typeMeta.icon;
  const ago       = formatDistanceToNowStrict(parseISO(nudge.created_at), { addSuffix: true });

  const openHref =
    nudge.reference_type === "application"
      ? "/applications"
      : nudge.reference_type === "referral"
      ? "/referrals"
      : null;

  async function doActed() {
    try {
      await acted.mutateAsync(nudge.id);
    } catch (err) {
      toast.push("error", err instanceof Error ? err.message : "Couldn't mark done");
    }
  }

  async function doSnooze(days: number) {
    setMenuOpen(false);
    try {
      await snooze.mutateAsync({ id: nudge.id, days });
      toast.push("success", `Snoozed for ${days}d`);
    } catch (err) {
      toast.push("error", err instanceof Error ? err.message : "Couldn't snooze");
    }
  }

  return (
    <div
      className={`relative bg-[var(--color-surface)] rounded-xl ring-1 ${meta.ring} shadow-sm overflow-hidden ${dimmed ? "opacity-55" : ""}`}
    >
      {/* Severity colour bar */}
      <span aria-hidden className={`absolute left-0 top-0 bottom-0 w-1 ${meta.bar}`} />

      <div className="pl-4 pr-3 py-3.5">
        {/* Header row */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap mb-1.5">
              {/* Severity chip */}
              <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10.5px] font-medium uppercase tracking-wide ${meta.chip}`}>
                {meta.label}
              </span>
              {/* Type icon + label */}
              <span className="inline-flex items-center gap-1 text-[11px] text-[var(--color-text-3)]">
                <TypeIcon className="w-3 h-3" />
                {typeMeta.label}
              </span>
              <span className="text-[11.5px] text-[var(--color-text-3)] ml-auto">{ago}</span>
            </div>
            <p className="text-[14px] text-[var(--color-text-2)] leading-relaxed">
              {renderInline(nudge.message)}
            </p>
          </div>
        </div>

        {/* Action row */}
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-[var(--color-border)]">
          <div className="flex items-center gap-1.5">
            {draftReq ? (
              <button
                type="button"
                onClick={() => setDraftOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-md px-2.5 h-8 text-[12.5px] font-medium text-indigo-600 hover:bg-indigo-500/10 transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5" />
                Draft
              </button>
            ) : null}
            {openHref ? (
              <Link
                href={openHref}
                className="inline-flex items-center gap-1.5 rounded-md px-2.5 h-8 text-[12.5px] font-medium text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Open
              </Link>
            ) : null}
            <div className="relative">
              <button
                type="button"
                onClick={() => setMenuOpen((o) => !o)}
                className="inline-flex items-center gap-1.5 rounded-md px-2.5 h-8 text-[12.5px] font-medium text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)] transition-colors"
              >
                <Clock className="w-3.5 h-3.5" />
                Snooze
              </button>
              {menuOpen ? (
                <div
                  className="absolute z-10 mt-1 left-0 min-w-[120px] rounded-lg bg-[var(--color-surface)] ring-1 ring-[var(--color-border)] shadow-lg py-1"
                  onMouseLeave={() => setMenuOpen(false)}
                >
                  {SNOOZE_OPTIONS.map((d) => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => doSnooze(d)}
                      className="w-full text-left px-3 py-1.5 text-[13px] text-[var(--color-text-2)] hover:bg-[var(--color-surface-2)]"
                    >
                      {d} day{d > 1 ? "s" : ""}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          </div>

          {!dimmed && (
            <button
              type="button"
              onClick={doActed}
              disabled={acted.isPending}
              className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 hover:bg-indigo-700 text-white px-3 h-8 text-[12.5px] font-medium shadow-sm transition-colors disabled:opacity-50"
            >
              <Check className="w-3.5 h-3.5" />
              {acted.isPending ? "Saving…" : "Mark done"}
            </button>
          )}
        </div>
      </div>

      <DraftModal
        open={draftOpen}
        onClose={() => setDraftOpen(false)}
        request={draftOpen ? draftReq : null}
      />
    </div>
  );
}

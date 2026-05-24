"use client";

import { useDraggable } from "@dnd-kit/core";
import { formatDistanceToNowStrict, parseISO } from "date-fns";
import { ExternalLink } from "lucide-react";

import { CONN_STATUS_META, type Referral } from "@/lib/referrals";
import { companyAvatarClass } from "@/lib/types";

export function ReferralCard({
  ref: refContact,
  draggable = false,
  overlay = false,
  onOpen,
}: {
  ref: Referral;
  draggable?: boolean;
  overlay?: boolean;
  onOpen?: (id: number) => void;
}) {
  const drag = useDraggable({ id: refContact.id, disabled: !draggable });
  const meta = CONN_STATUS_META[refContact.connection_status];
  const sentAgo = formatDistanceToNowStrict(
    parseISO(refContact.connection_sent_date),
    { addSuffix: true },
  );
  const initial = refContact.name.trim().charAt(0).toUpperCase() || "?";

  const style = drag.transform
    ? {
        transform: `translate3d(${drag.transform.x}px, ${drag.transform.y}px, 0)`,
        opacity: drag.isDragging ? 0.4 : 1,
      }
    : undefined;

  return (
    <div
      ref={draggable ? drag.setNodeRef : undefined}
      style={style}
      {...(draggable ? drag.listeners : {})}
      {...(draggable ? drag.attributes : {})}
      onClick={onOpen && !drag.isDragging ? () => onOpen(refContact.id) : undefined}
      className={`group relative bg-[var(--color-surface)] rounded-xl ring-1 ring-[var(--color-border)] hover:ring-indigo-400 hover:shadow-md transition-all p-3.5 cursor-pointer select-none ${
        overlay ? "shadow-xl rotate-[1.5deg]" : "shadow-sm"
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`shrink-0 w-9 h-9 rounded-lg grid place-items-center text-sm font-semibold ${companyAvatarClass(refContact.name)}`}
          aria-hidden
        >
          {initial}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="text-[14px] font-semibold text-[var(--color-text)] truncate leading-tight">
                {refContact.name}
              </div>
              <div className="text-[12.5px] text-[var(--color-text-2)] truncate mt-0.5">
                {refContact.role_at_company
                  ? `${refContact.role_at_company} · ${refContact.company}`
                  : refContact.company}
              </div>
            </div>
            {refContact.linkedin_url ? (
              <a
                href={refContact.linkedin_url}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
                onPointerDown={(e) => e.stopPropagation()}
                className="shrink-0 text-[var(--color-text-3)] hover:text-indigo-400 transition-colors"
                aria-label="Open LinkedIn"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            ) : null}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-[var(--color-border)]">
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ${meta.chip}`}
        >
          <span aria-hidden className={`w-1.5 h-1.5 rounded-full ${meta.dot}`} />
          {meta.label}
        </span>
        <span className="text-[11.5px] text-[var(--color-text-3)]">{sentAgo}</span>
      </div>

      <div className="mt-2 text-[10.5px] uppercase tracking-wide text-[var(--color-text-3)] truncate">
        for {refContact.target_role}
        {refContact.mutual_context ? (
          <span className="ml-1 text-[var(--color-border)]">·</span>
        ) : null}
        {refContact.mutual_context ? (
          <span className="ml-1 normal-case text-[var(--color-text-2)] truncate">
            {refContact.mutual_context}
          </span>
        ) : null}
      </div>

      {refContact.outcome === "Referred" ? (
        <span className="absolute top-2 right-2 inline-flex items-center gap-1 rounded-full bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20 text-[10px] px-1.5 py-0.5">
          <ExternalLink className="w-3 h-3" />
          referred
        </span>
      ) : null}
    </div>
  );
}

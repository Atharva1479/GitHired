"use client";

import { useDraggable } from "@dnd-kit/core";
import { formatDistanceToNowStrict, parseISO } from "date-fns";
import { Calendar, ExternalLink, MessageCircle } from "lucide-react";

import { StatusBadge } from "@/components/ui/StatusBadge";
import { companyAvatarClass, type Application } from "@/lib/types";

export function Card({
  app,
  draggable = false,
  overlay = false,
  onOpen,
}: {
  app: Application;
  draggable?: boolean;
  overlay?: boolean;
  onOpen?: (id: number) => void;
}) {
  const drag = useDraggable({ id: app.id, disabled: !draggable });
  const appliedAgo = formatDistanceToNowStrict(parseISO(app.applied_date), {
    addSuffix: true,
  });
  const initial = app.company.trim().charAt(0).toUpperCase() || "?";

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
      onClick={onOpen && !drag.isDragging ? () => onOpen(app.id) : undefined}
      className={`group relative bg-[var(--color-surface)] rounded-xl ring-1 ring-[var(--color-border)] hover:ring-indigo-400 hover:shadow-md transition-all p-3.5 cursor-pointer select-none ${
        overlay ? "shadow-xl rotate-[1.5deg]" : "shadow-sm"
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`shrink-0 w-9 h-9 rounded-lg grid place-items-center text-sm font-semibold ${companyAvatarClass(app.company)}`}
          aria-hidden
        >
          {initial}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="text-[14px] font-semibold text-[var(--color-text)] truncate leading-tight">
                {app.company}
              </div>
              <div className="text-[12.5px] text-[var(--color-text-2)] truncate mt-0.5">
                {app.role}
              </div>
            </div>
            {app.jd_url ? (
              <a
                href={app.jd_url}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
                onPointerDown={(e) => e.stopPropagation()}
                className="shrink-0 text-[var(--color-text-3)] hover:text-indigo-500 transition-colors"
                aria-label="Open job description"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            ) : null}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-[var(--color-border)]">
        <StatusBadge status={app.status} />
        <div className="flex items-center gap-3 text-[11.5px] text-[var(--color-text-3)]">
          {app.follow_up_count > 0 ? (
            <span className="inline-flex items-center gap-1 text-amber-700">
              <MessageCircle className="w-3 h-3" />
              {app.follow_up_count}
            </span>
          ) : null}
          <span className="inline-flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            {appliedAgo}
          </span>
        </div>
      </div>

      <div className="mt-2 text-[10.5px] uppercase tracking-wide text-[var(--color-text-3)]">
        via {app.source}
      </div>
    </div>
  );
}

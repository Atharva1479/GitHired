"use client";

import { Calendar, Star } from "lucide-react";

import { type Application, companyAvatarClass } from "@/lib/types";

interface CardProps {
  app: Application;
  dragging: boolean;
  onOpen: () => void;
  onDragStart: () => void;
  onDragEnd: () => void;
}

export function Card({ app, dragging, onOpen, onDragStart, onDragEnd }: CardProps) {
  const avatarClass = companyAvatarClass(app.company);
  const initials = app.company.slice(0, 2).toUpperCase();
  const date = new Date(app.applied_date).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });

  return (
    <div
      draggable
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = "move";
        onDragStart();
      }}
      onDragEnd={onDragEnd}
      onClick={onOpen}
      className="group rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3.5 shadow-sm cursor-grab select-none transition-all duration-150 hover:border-indigo-300 hover:shadow-md active:scale-[0.98] active:cursor-grabbing"
      style={{ opacity: dragging ? 0.4 : 1 }}
    >
      <div className="flex items-center gap-2.5 mb-2.5">
        <span className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-[11px] font-bold ${avatarClass}`}>
          {initials}
        </span>
        <div className="min-w-0">
          <p className="text-[13px] font-semibold text-[var(--color-text)] truncate leading-tight">
            {app.company}
          </p>
          <p className="text-[11.5px] text-[var(--color-text-3)] truncate leading-tight mt-0.5">
            {app.role}
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1 text-[11px] text-[var(--color-text-3)]">
          <Calendar className="w-3 h-3 shrink-0" />
          {date}
        </span>
        <div className="flex items-center gap-1.5">
          {app.fit_score != null && (
            <span className="flex items-center gap-0.5 text-[11px] font-medium text-amber-600 bg-amber-50 ring-1 ring-amber-200 rounded-full px-1.5 py-0.5">
              <Star className="w-2.5 h-2.5 fill-amber-500 text-amber-500" />
              {app.fit_score}%
            </span>
          )}
          <span className="text-[10px] font-medium text-[var(--color-text-3)] bg-[var(--color-surface-2)] ring-1 ring-[var(--color-border)] rounded-full px-1.5 py-0.5">
            {app.source}
          </span>
        </div>
      </div>
    </div>
  );
}

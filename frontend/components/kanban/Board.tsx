"use client";

import { useState } from "react";

import { STATUSES, type Status } from "@/lib/types";
import { useApplications } from "@/hooks/useApplications";
import { useUpdateApplication } from "@/hooks/useApplications";
import { Column } from "./Column";

interface BoardProps {
  onOpenCard: (id: number) => void;
}

export function Board({ onOpenCard }: BoardProps) {
  const { data: apps = [] } = useApplications();
  const { mutate: update } = useUpdateApplication();

  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [dragOverStatus, setDragOverStatus] = useState<Status | null>(null);

  function handleDrop(status: Status) {
    if (draggingId == null) return;
    const app = apps.find((a) => a.id === draggingId);
    if (app && app.status !== status) {
      update({ id: draggingId, patch: { status } });
    }
    setDraggingId(null);
    setDragOverStatus(null);
  }

  return (
    <div className="flex gap-3 overflow-x-auto pb-4 px-6 min-h-[calc(100vh-220px)]">
      {STATUSES.map((status) => (
        <Column
          key={status}
          status={status}
          apps={apps.filter((a) => a.status === status)}
          draggingId={draggingId}
          isOver={dragOverStatus === status}
          onOpenCard={onOpenCard}
          onDragStart={(id) => { setDraggingId(id); setDragOverStatus(null); }}
          onDragEnd={() => { setDraggingId(null); setDragOverStatus(null); }}
          onDragOver={() => setDragOverStatus(status)}
          onDragLeave={() => setDragOverStatus((prev) => (prev === status ? null : prev))}
          onDrop={() => handleDrop(status)}
        />
      ))}
    </div>
  );
}

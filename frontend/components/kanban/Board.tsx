"use client";

import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { AlertCircle } from "lucide-react";
import { useState } from "react";

import { useToast } from "@/app/providers";
import {
  useApplications,
  useUpdateApplication,
} from "@/hooks/useApplications";
import { STATUSES, type Application, type Status } from "@/lib/types";

import { Card } from "./Card";
import { Column } from "./Column";

export function Board({
  onOpenCard,
}: {
  onOpenCard?: (id: number) => void;
}) {
  const { data, isLoading, error } = useApplications();
  const update = useUpdateApplication();
  const toast = useToast();
  const [dragged, setDragged] = useState<Application | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor),
  );

  if (isLoading) {
    return (
      <div className="flex-1 flex gap-4 px-6 py-6 overflow-hidden items-stretch">
        {STATUSES.map((s) => (
          <div
            key={s}
            className="w-[300px] flex-1 rounded-2xl bg-[var(--color-surface-2)] animate-pulse shrink-0"
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-6 my-6 max-w-2xl rounded-xl bg-red-50 ring-1 ring-red-200 p-5 flex gap-3">
        <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
        <div className="text-[14px] text-red-800">
          <div className="font-semibold mb-1">Can&apos;t reach the API</div>
          <div className="text-red-700">
            Make sure{" "}
            <code className="bg-white px-1.5 py-0.5 rounded ring-1 ring-red-200">
              uvicorn backend.main:app --reload
            </code>{" "}
            is running on :8000.
          </div>
        </div>
      </div>
    );
  }

  const apps = data ?? [];
  const byStatus = new Map<Status, Application[]>(
    STATUSES.map((s) => [s, []]),
  );
  for (const app of apps) byStatus.get(app.status)?.push(app);

  function handleStart(e: DragStartEvent) {
    const app = apps.find((a) => a.id === Number(e.active.id));
    if (app) setDragged(app);
  }

  function handleEnd(e: DragEndEvent) {
    setDragged(null);
    if (!e.over) return;
    const newStatus = e.over.id as Status;
    const id = Number(e.active.id);
    const app = apps.find((a) => a.id === id);
    if (!app || app.status === newStatus) return;
    update.mutate(
      { id, patch: { status: newStatus } },
      {
        onError: (err) =>
          toast.push(
            "error",
            err instanceof Error ? err.message : "Couldn't update status",
          ),
      },
    );
  }

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleStart}
      onDragEnd={handleEnd}
    >
      <div className="flex-1 flex gap-4 overflow-x-auto items-stretch px-6 pb-8 pt-2">
        {STATUSES.map((s) => (
          <Column
            key={s}
            status={s}
            apps={byStatus.get(s) ?? []}
            onOpenCard={onOpenCard}
          />
        ))}
      </div>
      <DragOverlay dropAnimation={null}>
        {dragged ? <Card app={dragged} overlay /> : null}
      </DragOverlay>
    </DndContext>
  );
}

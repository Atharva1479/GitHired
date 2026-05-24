"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Nudge } from "@/lib/nudges";

const LIST_KEY = ["nudges"] as const;
const TODAY_KEY = ["nudges", "today"] as const;

export function useTodayNudges() {
  return useQuery({
    queryKey: TODAY_KEY,
    queryFn: () => api.nudges.today(),
    refetchOnWindowFocus: true,
  });
}

export function useAllNudges() {
  return useQuery({
    queryKey: LIST_KEY,
    queryFn: () => api.nudges.list(),
  });
}

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: LIST_KEY });
  qc.invalidateQueries({ queryKey: TODAY_KEY });
}

function optimisticRemoveFromToday(
  qc: ReturnType<typeof useQueryClient>,
  id: number,
) {
  const prev = qc.getQueryData<Nudge[]>(TODAY_KEY);
  qc.setQueryData<Nudge[]>(
    TODAY_KEY,
    (prev ?? []).filter((n) => n.id !== id),
  );
  return prev;
}

export function useMarkActed() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.nudges.markActed(id),
    onMutate: (id) => ({ prev: optimisticRemoveFromToday(qc, id) }),
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(TODAY_KEY, ctx.prev);
    },
    onSettled: () => invalidateAll(qc),
  });
}

export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.nudges.markRead(id),
    onMutate: (id) => ({ prev: optimisticRemoveFromToday(qc, id) }),
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(TODAY_KEY, ctx.prev);
    },
    onSettled: () => invalidateAll(qc),
  });
}

type SnoozeArgs = { id: number; days: number };

export function useSnooze() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, days }: SnoozeArgs) => api.nudges.snooze(id, days),
    onMutate: ({ id }) => ({ prev: optimisticRemoveFromToday(qc, id) }),
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(TODAY_KEY, ctx.prev);
    },
    onSettled: () => invalidateAll(qc),
  });
}

export function useRunNudges() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.nudges.run(),
    onSuccess: () => invalidateAll(qc),
  });
}

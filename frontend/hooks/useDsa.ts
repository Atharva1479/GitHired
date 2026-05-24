"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { DsaProblemCreate, DsaProblemOut, DsaProblemUpdate, DsaStatsOut } from "@/lib/types";

const PROBLEMS_KEY = ["dsa", "problems"] as const;
const STATS_KEY = ["dsa", "stats"] as const;

export function useDsaStats() {
  return useQuery({
    queryKey: STATS_KEY,
    queryFn: () => api.dsa.stats(),
  });
}

export function useDsaProblems(topic?: string) {
  return useQuery({
    queryKey: [...PROBLEMS_KEY, topic ?? "all"],
    queryFn: () => api.dsa.list(topic),
  });
}

export function useDsaProblem(id: number) {
  return useQuery({
    queryKey: [...PROBLEMS_KEY, id],
    queryFn: () => api.dsa.get(id),
    enabled: id > 0,
  });
}

export function useCreateDsaProblem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: DsaProblemCreate) => api.dsa.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PROBLEMS_KEY });
      qc.invalidateQueries({ queryKey: STATS_KEY });
    },
  });
}

export function useUpdateDsaProblem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }: { id: number; patch: DsaProblemUpdate }) =>
      api.dsa.update(id, patch),
    onMutate: async ({ id, patch }) => {
      await qc.cancelQueries({ queryKey: PROBLEMS_KEY });
      const snapshot = qc.getQueryData<DsaProblemOut[]>(PROBLEMS_KEY);
      if (snapshot) {
        qc.setQueryData<DsaProblemOut[]>(PROBLEMS_KEY, (old) =>
          old?.map((p) => (p.id === id ? { ...p, ...patch } : p)) ?? [],
        );
      }
      return { snapshot };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.snapshot) qc.setQueryData(PROBLEMS_KEY, ctx.snapshot);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: PROBLEMS_KEY });
    },
  });
}

export function useDeleteDsaProblem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.dsa.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PROBLEMS_KEY });
      qc.invalidateQueries({ queryKey: STATS_KEY });
    },
  });
}

export function useAnalyzeDsaProblem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.dsa.analyze(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: [...PROBLEMS_KEY, id] });
      qc.invalidateQueries({ queryKey: PROBLEMS_KEY });
      qc.invalidateQueries({ queryKey: STATS_KEY });
    },
  });
}

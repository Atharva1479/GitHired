"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { ApiError, type GamifyEnvelope, api } from "@/lib/api";

export const GAMIFY_KEY = ["gamify", "state"] as const;

export function useGamifyState() {
  return useQuery({
    queryKey: GAMIFY_KEY,
    queryFn: () => api.gamify.state(),
    retry: (count, err) =>
      err instanceof ApiError && err.status === 401 ? false : count < 2,
    staleTime: 30_000,
  });
}

export function useAchievements() {
  return useQuery({
    queryKey: ["gamify", "achievements"],
    queryFn: () => api.gamify.achievements(),
    staleTime: 5 * 60_000,
  });
}

export function useGamifyAcknowledge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.gamify.acknowledge(),
    onSuccess: () => qc.invalidateQueries({ queryKey: GAMIFY_KEY }),
  });
}

export function useGamifyListener(
  cb: (envelope: GamifyEnvelope) => void,
): void {
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<GamifyEnvelope>).detail;
      if (detail && !detail.duplicate) cb(detail);
    };
    window.addEventListener("jp:gamify", handler);
    return () => window.removeEventListener("jp:gamify", handler);
  }, [cb]);
}

export function useGamifyAutoRefresh(): void {
  const qc = useQueryClient();
  useGamifyListener(() => {
    qc.invalidateQueries({ queryKey: GAMIFY_KEY });
  });
}

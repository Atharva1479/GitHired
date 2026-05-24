"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, api } from "@/lib/api";
import type { SettingsPatch } from "@/lib/settings";

export const SETTINGS_KEY = ["settings"] as const;

export function useSettings() {
  return useQuery({
    queryKey: SETTINGS_KEY,
    queryFn: () => api.settings.get(),
    retry: (count, err) =>
      err instanceof ApiError && err.status === 401 ? false : count < 2,
    staleTime: 5 * 60_000,
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: SettingsPatch) => api.settings.patch(patch),
    onSuccess: (updated) => {
      qc.setQueryData(SETTINGS_KEY, updated);
    },
  });
}

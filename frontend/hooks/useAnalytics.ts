// frontend/hooks/useAnalytics.ts
"use client";

import { useQuery } from "@tanstack/react-query";

import { ApiError, api } from "@/lib/api";

export const ANALYTICS_KEY = ["analytics", "stats"] as const;

export function useAnalyticsStats() {
  return useQuery({
    queryKey: ANALYTICS_KEY,
    queryFn: () => api.analytics.stats(),
    retry: (count, err) =>
      err instanceof ApiError && err.status === 401 ? false : count < 2,
    staleTime: 2 * 60_000,  // 2 minutes — analytics doesn't need live refresh
  });
}

"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: () => api.dashboard.stats(),
    refetchOnWindowFocus: true,
  });
}

export function useDashboardActivity(limit = 15) {
  return useQuery({
    queryKey: ["dashboard", "activity", limit],
    queryFn: () => api.dashboard.activity(limit),
  });
}

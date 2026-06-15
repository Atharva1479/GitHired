"use client";
import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  applyAndTrack,
  atsJobScan,
  bookmarkJob,
  createSavedSearch,
  deleteSavedSearch,
  getSimilarJobs,
  listSavedSearches,
  matchResume,
  searchJobs,
} from "@/lib/jobs-api";
import type { JobSearchCreate, SearchParams } from "@/types/jobs";

export const JOB_KEYS = {
  search: (params: SearchParams) => ["jobs", "search", params] as const,
  searches: () => ["jobs", "searches"] as const,
};

export function useJobSearch(params: SearchParams | null, freshnessHours = 72) {
  const query = useQuery({
    queryKey: JOB_KEYS.search(params ?? { q: "" }),
    queryFn: () => searchJobs(params!),
    enabled: !!params && params.q.trim().length > 0,
    staleTime: 1000 * 60 * 15,
  });

  const filteredData = useMemo(
    () =>
      query.data?.filter(
        (j) => j.hours_old === null || j.hours_old <= freshnessHours,
      ) ?? [],
    [query.data, freshnessHours],
  );

  return { ...query, filteredData };
}

export function useSavedSearches() {
  return useQuery({
    queryKey: JOB_KEYS.searches(),
    queryFn: listSavedSearches,
  });
}

export function useCreateSavedSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: JobSearchCreate) => createSavedSearch(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: JOB_KEYS.searches() }),
  });
}

export function useDeleteSavedSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteSavedSearch(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: JOB_KEYS.searches() }),
  });
}

export function useBookmarkJob() {
  return useMutation({
    mutationFn: (jobCacheId: number) => bookmarkJob(jobCacheId),
  });
}

export function useApplyAndTrack() {
  return useMutation({ mutationFn: applyAndTrack });
}

export function useMatchResume(jobCacheId: number | null) {
  return useQuery({
    queryKey: ["jobs", "match", jobCacheId],
    queryFn: () => matchResume(jobCacheId!),
    enabled: jobCacheId !== null,
    staleTime: 1000 * 60 * 30,
    retry: false,
  });
}

export function useAtsJobScan() {
  return useMutation({ mutationFn: (jobCacheId: number) => atsJobScan(jobCacheId) });
}

export function useSimilarJobs(jobCacheId: number | null) {
  return useQuery({
    queryKey: ["jobs", "similar", jobCacheId],
    queryFn: () => getSimilarJobs(jobCacheId!),
    enabled: jobCacheId !== null,
    staleTime: 1000 * 60 * 15,
    retry: false,
  });
}

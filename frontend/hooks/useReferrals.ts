"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  ConnectionStatus,
  Referral,
  ReferralCreate,
  ReferralUpdate,
} from "@/lib/referrals";

const LIST_KEY = ["referrals"] as const;
const oneKey = (id: number) => ["referral", id] as const;
const linkedKey = (id: number) => ["referral", id, "applications"] as const;

export function useReferrals(connection_status?: ConnectionStatus) {
  return useQuery({
    queryKey: [...LIST_KEY, connection_status ?? "all"],
    queryFn: () => api.referrals.list({ connection_status }),
  });
}

export function useReferral(id: number | null) {
  return useQuery({
    queryKey: id != null ? oneKey(id) : ["referral", "none"],
    queryFn: () => api.referrals.get(id as number),
    enabled: id != null,
  });
}

export function useLinkedApplications(refId: number | null) {
  return useQuery({
    queryKey: refId != null ? linkedKey(refId) : ["referral", "none", "applications"],
    queryFn: () => api.referrals.linkedApplications(refId as number),
    enabled: refId != null,
  });
}

export function useCreateReferral() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ReferralCreate) => api.referrals.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: LIST_KEY }),
  });
}

type UpdateArgs = { id: number; patch: ReferralUpdate };

export function useUpdateReferral() {
  const qc = useQueryClient();
  return useMutation<
    Referral,
    Error,
    UpdateArgs,
    { snapshots: [readonly unknown[], Referral[] | undefined][] }
  >({
    mutationFn: ({ id, patch }) => api.referrals.update(id, patch),
    onMutate: async ({ id, patch }) => {
      await qc.cancelQueries({ queryKey: LIST_KEY });
      const snapshots = qc.getQueriesData<Referral[]>({ queryKey: LIST_KEY });
      for (const [key, data] of snapshots) {
        if (!Array.isArray(data)) continue;
        qc.setQueryData<Referral[]>(
          key,
          data.map((r) => (r.id === id ? ({ ...r, ...patch } as Referral) : r)),
        );
      }
      return { snapshots };
    },
    onError: (_e, _v, ctx) => {
      ctx?.snapshots.forEach(([key, data]) => qc.setQueryData(key, data));
    },
    onSettled: (_d, _e, { id }) => {
      qc.invalidateQueries({ queryKey: LIST_KEY });
      qc.invalidateQueries({ queryKey: oneKey(id) });
    },
  });
}

export function useDeleteReferral() {
  const qc = useQueryClient();
  return useMutation<
    null,
    Error,
    number,
    { snapshots: [readonly unknown[], Referral[] | undefined][] }
  >({
    mutationFn: (id) => api.referrals.remove(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: LIST_KEY });
      const snapshots = qc.getQueriesData<Referral[]>({ queryKey: LIST_KEY });
      for (const [key, data] of snapshots) {
        if (!Array.isArray(data)) continue;
        qc.setQueryData<Referral[]>(key, data.filter((r) => r.id !== id));
      }
      return { snapshots };
    },
    onError: (_e, _v, ctx) => {
      ctx?.snapshots.forEach(([key, data]) => qc.setQueryData(key, data));
    },
    onSettled: (_d, _e, id) => {
      qc.invalidateQueries({ queryKey: LIST_KEY });
      qc.removeQueries({ queryKey: oneKey(id) });
    },
  });
}

function makeQuickAction(fn: (id: number) => Promise<Referral>) {
  return function () {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: (id: number) => fn(id),
      onSuccess: (_d, id) => {
        qc.invalidateQueries({ queryKey: LIST_KEY });
        qc.invalidateQueries({ queryKey: oneKey(id) });
      },
    });
  };
}

export const useMarkAccepted = makeQuickAction(api.referrals.markAccepted);
export const useMarkSent = makeQuickAction(api.referrals.markSent);
export const useMarkReplied = makeQuickAction(api.referrals.markReplied);

type LinkArgs = { refId: number; appId: number };

export function useLinkApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ refId, appId }: LinkArgs) =>
      api.referrals.linkApplication(refId, appId),
    onSuccess: (_d, { refId }) =>
      qc.invalidateQueries({ queryKey: linkedKey(refId) }),
  });
}

export function useUnlinkApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ refId, appId }: LinkArgs) =>
      api.referrals.unlinkApplication(refId, appId),
    onSuccess: (_d, { refId }) =>
      qc.invalidateQueries({ queryKey: linkedKey(refId) }),
  });
}

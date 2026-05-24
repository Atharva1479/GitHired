"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  Application,
  ApplicationCreate,
  ApplicationUpdate,
  FileKind,
  Status,
} from "@/lib/types";

const LIST_KEY = ["applications"] as const;
const oneKey = (id: number) => ["application", id] as const;

export function useApplications(status?: Status) {
  return useQuery({
    queryKey: [...LIST_KEY, status ?? "all"],
    queryFn: () => api.applications.list({ status }),
  });
}

export function useApplication(id: number | null) {
  return useQuery({
    queryKey: id != null ? oneKey(id) : ["application", "none"],
    queryFn: () => api.applications.get(id as number),
    enabled: id != null,
  });
}

export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ApplicationCreate) => api.applications.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: LIST_KEY }),
  });
}

type UpdateArgs = { id: number; patch: ApplicationUpdate };

export function useUpdateApplication() {
  const qc = useQueryClient();
  return useMutation<
    Application,
    Error,
    UpdateArgs,
    { snapshots: [readonly unknown[], Application[] | undefined][] }
  >({
    mutationFn: ({ id, patch }) => api.applications.update(id, patch),
    onMutate: async ({ id, patch }) => {
      await qc.cancelQueries({ queryKey: LIST_KEY });
      const snapshots = qc.getQueriesData<Application[]>({ queryKey: LIST_KEY });
      for (const [key, data] of snapshots) {
        if (!Array.isArray(data)) continue;
        qc.setQueryData<Application[]>(
          key,
          data.map((a) => (a.id === id ? ({ ...a, ...patch } as Application) : a)),
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

export function useDeleteApplication() {
  const qc = useQueryClient();
  return useMutation<
    null,
    Error,
    number,
    { snapshots: [readonly unknown[], Application[] | undefined][] }
  >({
    mutationFn: (id) => api.applications.remove(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: LIST_KEY });
      const snapshots = qc.getQueriesData<Application[]>({ queryKey: LIST_KEY });
      for (const [key, data] of snapshots) {
        if (!Array.isArray(data)) continue;
        qc.setQueryData<Application[]>(
          key,
          data.filter((a) => a.id !== id),
        );
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

export function useFollowupApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.applications.followup(id),
    onSuccess: (_d, id) => {
      qc.invalidateQueries({ queryKey: LIST_KEY });
      qc.invalidateQueries({ queryKey: oneKey(id) });
    },
  });
}

type UploadArgs = { id: number; kind: FileKind; file: File };

export function useUploadApplicationFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, kind, file }: UploadArgs) =>
      api.applications.uploadFile(id, kind, file),
    onSuccess: (_d, { id }) => {
      qc.invalidateQueries({ queryKey: LIST_KEY });
      qc.invalidateQueries({ queryKey: oneKey(id) });
    },
  });
}

type DeleteFileArgs = { id: number; kind: FileKind };

export function useDeleteApplicationFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, kind }: DeleteFileArgs) =>
      api.applications.deleteFile(id, kind),
    onSuccess: (_d, { id }) => {
      qc.invalidateQueries({ queryKey: LIST_KEY });
      qc.invalidateQueries({ queryKey: oneKey(id) });
    },
  });
}

"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listResumes,
  uploadResume,
  deleteResume,
  getSkillGap,
} from "@/lib/resumes-api";

const KEYS = {
  list: ["resumes"] as const,
  gap: (id: number) => ["resumes", "gap", id] as const,
};

export function useResumes() {
  return useQuery({ queryKey: KEYS.list, queryFn: listResumes });
}

export function useUploadResume() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      name,
      roleTag,
      file,
    }: {
      name: string;
      roleTag: string;
      file: File;
    }) => uploadResume(name, roleTag, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.list }),
  });
}

export function useDeleteResume() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteResume(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.list }),
  });
}

export function useSkillGap(resumeId: number | null) {
  return useQuery({
    queryKey: KEYS.gap(resumeId ?? 0),
    queryFn: () => getSkillGap(resumeId!),
    enabled: resumeId !== null,
  });
}

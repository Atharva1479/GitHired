"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  StudyGenerateRequest,
  StudyGenerateResponse,
  StudyGenerateTopicsRequest,
  StudyGenerateTopicsResponse,
  StudyPlan,
  StudyPlanSection,
  StudyPlanSubsection,
  StudyReviseResponse,
  StudySection,
  StudySectionCreate,
  StudySectionUpdate,
  StudySubsection,
  StudySubsectionCreate,
  StudySubsectionUpdate,
  StudyTopic,
  StudyTopicCreate,
  StudyTopicUpdate,
} from "@/lib/types";

const PLAN_KEY = ["study", "plan"] as const;
const PROGRESS_KEY = ["study", "progress"] as const;


// ── reads ────────────────────────────────────────────────────────────


export function useStudyPlan() {
  return useQuery({
    queryKey: PLAN_KEY,
    queryFn: () => api.study.plan(),
    staleTime: 10_000,
  });
}

export function useStudyProgress() {
  return useQuery({
    queryKey: PROGRESS_KEY,
    queryFn: () => api.study.progress(),
    staleTime: 15_000,
  });
}


// ── sections ─────────────────────────────────────────────────────────


export function useCreateSection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: StudySectionCreate) => api.study.createSection(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PLAN_KEY });
      qc.invalidateQueries({ queryKey: PROGRESS_KEY });
    },
  });
}

export function useUpdateSection() {
  const qc = useQueryClient();
  return useMutation<
    StudySection,
    Error,
    { id: number; patch: StudySectionUpdate },
    { snapshot: StudyPlan | undefined }
  >({
    mutationFn: ({ id, patch }) => api.study.updateSection(id, patch),
    // Optimistic: rename the section in the cached plan instantly so the
    // user doesn't see a "freeze + repaint" while the request flies.
    onMutate: async ({ id, patch }) => {
      await qc.cancelQueries({ queryKey: PLAN_KEY });
      const snapshot = qc.getQueryData<StudyPlan>(PLAN_KEY);
      if (snapshot) {
        qc.setQueryData<StudyPlan>(PLAN_KEY, {
          sections: snapshot.sections.map((s) =>
            s.id === id ? { ...s, ...patch } : s,
          ),
        });
      }
      return { snapshot };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.snapshot) qc.setQueryData(PLAN_KEY, ctx.snapshot);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: PLAN_KEY }),
  });
}

export function useDeleteSection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.study.deleteSection(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PLAN_KEY });
      qc.invalidateQueries({ queryKey: PROGRESS_KEY });
    },
  });
}


// ── subsections ──────────────────────────────────────────────────────


export function useCreateSubsection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      sectionId,
      data,
    }: {
      sectionId: number;
      data: StudySubsectionCreate;
    }) => api.study.createSubsection(sectionId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: PLAN_KEY }),
  });
}

export function useUpdateSubsection() {
  const qc = useQueryClient();
  return useMutation<
    StudySubsection,
    Error,
    { id: number; patch: StudySubsectionUpdate },
    { snapshot: StudyPlan | undefined }
  >({
    mutationFn: ({ id, patch }) => api.study.updateSubsection(id, patch),
    onMutate: async ({ id, patch }) => {
      await qc.cancelQueries({ queryKey: PLAN_KEY });
      const snapshot = qc.getQueryData<StudyPlan>(PLAN_KEY);
      if (snapshot) {
        qc.setQueryData<StudyPlan>(PLAN_KEY, {
          sections: snapshot.sections.map((s) => ({
            ...s,
            subsections: s.subsections.map((sub) =>
              sub.id === id ? { ...sub, ...patch } : sub,
            ),
          })),
        });
      }
      return { snapshot };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.snapshot) qc.setQueryData(PLAN_KEY, ctx.snapshot);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: PLAN_KEY }),
  });
}

export function useDeleteSubsection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.study.deleteSubsection(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PLAN_KEY });
      qc.invalidateQueries({ queryKey: PROGRESS_KEY });
    },
  });
}


// ── topics ──────────────────────────────────────────────────────────


export function useCreateTopic() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      subsectionId,
      data,
    }: {
      subsectionId: number;
      data: StudyTopicCreate;
    }) => api.study.createTopic(subsectionId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PLAN_KEY });
      qc.invalidateQueries({ queryKey: PROGRESS_KEY });
    },
  });
}

export function useUpdateTopic() {
  const qc = useQueryClient();
  return useMutation<
    StudyTopic,
    Error,
    { id: number; patch: StudyTopicUpdate },
    { snapshot: StudyPlan | undefined }
  >({
    mutationFn: ({ id, patch }) => api.study.updateTopic(id, patch),
    onMutate: async ({ id, patch }) => {
      await qc.cancelQueries({ queryKey: PLAN_KEY });
      const snapshot = qc.getQueryData<StudyPlan>(PLAN_KEY);
      if (snapshot) {
        qc.setQueryData<StudyPlan>(PLAN_KEY, _updateTopicInPlan(snapshot, id, patch));
      }
      return { snapshot };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.snapshot) qc.setQueryData(PLAN_KEY, ctx.snapshot);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: PLAN_KEY });
      qc.invalidateQueries({ queryKey: PROGRESS_KEY });
    },
  });
}

export function useDeleteTopic() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.study.deleteTopic(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PLAN_KEY });
      qc.invalidateQueries({ queryKey: PROGRESS_KEY });
    },
  });
}

/**
 * Revise hook. Optimistically flips the topic to status=done +
 * increments revision_count so the checkbox visibly checks immediately.
 * The server's authoritative response (which may bump to 'mastered')
 * replaces the optimistic state on settle.
 */
export function useReviseTopic() {
  const qc = useQueryClient();
  return useMutation<
    StudyReviseResponse,
    Error,
    { id: number },
    { snapshot: StudyPlan | undefined }
  >({
    mutationFn: ({ id }) => api.study.reviseTopic(id),
    onMutate: async ({ id }) => {
      await qc.cancelQueries({ queryKey: PLAN_KEY });
      const snapshot = qc.getQueryData<StudyPlan>(PLAN_KEY);
      if (snapshot) {
        qc.setQueryData<StudyPlan>(
          PLAN_KEY,
          _updateTopicInPlan(snapshot, id, (prev) => ({
            status: "done",
            revision_count: prev.revision_count + 1,
            last_revised_at: new Date().toISOString(),
          })),
        );
      }
      return { snapshot };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.snapshot) qc.setQueryData(PLAN_KEY, ctx.snapshot);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: PLAN_KEY });
      qc.invalidateQueries({ queryKey: PROGRESS_KEY });
    },
  });
}

export function useUnmarkTopic() {
  const qc = useQueryClient();
  return useMutation<
    StudyTopic,
    Error,
    { id: number },
    { snapshot: StudyPlan | undefined }
  >({
    mutationFn: ({ id }) => api.study.unmarkTopic(id),
    onMutate: async ({ id }) => {
      await qc.cancelQueries({ queryKey: PLAN_KEY });
      const snapshot = qc.getQueryData<StudyPlan>(PLAN_KEY);
      if (snapshot) {
        qc.setQueryData<StudyPlan>(
          PLAN_KEY,
          _updateTopicInPlan(snapshot, id, { status: "todo" }),
        );
      }
      return { snapshot };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.snapshot) qc.setQueryData(PLAN_KEY, ctx.snapshot);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: PLAN_KEY });
      qc.invalidateQueries({ queryKey: PROGRESS_KEY });
    },
  });
}


// ── AI generation ────────────────────────────────────────────────────

export function useGeneratePlan() {
  return useMutation<StudyGenerateResponse, Error, StudyGenerateRequest>({
    mutationFn: (data) => api.study.generatePlan(data),
  });
}

export function useApplyGeneratedPlan() {
  const qc = useQueryClient();
  return useMutation<StudyPlan, Error, StudyGenerateResponse>({
    mutationFn: (data) => api.study.applyGeneratedPlan(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PLAN_KEY });
      qc.invalidateQueries({ queryKey: PROGRESS_KEY });
    },
  });
}

export function useGenerateTopics() {
  return useMutation<
    StudyGenerateTopicsResponse,
    Error,
    { subsectionId: number; data: StudyGenerateTopicsRequest }
  >({
    mutationFn: ({ subsectionId, data }) =>
      api.study.generateTopics(subsectionId, data),
  });
}

export function useApplyGeneratedTopics() {
  const qc = useQueryClient();
  return useMutation<
    StudyTopic[],
    Error,
    { subsectionId: number; data: StudyGenerateTopicsResponse }
  >({
    mutationFn: ({ subsectionId, data }) =>
      api.study.applyGeneratedTopics(subsectionId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PLAN_KEY });
      qc.invalidateQueries({ queryKey: PROGRESS_KEY });
    },
  });
}

// ── helpers ──────────────────────────────────────────────────────────


type TopicPatchFn = (prev: StudyTopic) => Partial<StudyTopic>;
type TopicPatch = Partial<StudyTopic> | TopicPatchFn;

/**
 * Walk the plan tree, applying ``patch`` to the matching topic. Used by
 * every optimistic-update path so the tree shape is preserved exactly.
 */
function _updateTopicInPlan(
  plan: StudyPlan,
  topicId: number,
  patch: TopicPatch,
): StudyPlan {
  return {
    sections: plan.sections.map((s: StudyPlanSection) => ({
      ...s,
      subsections: s.subsections.map((sub: StudyPlanSubsection) => ({
        ...sub,
        topics: sub.topics.map((t: StudyTopic) =>
          t.id === topicId
            ? { ...t, ...(typeof patch === "function" ? patch(t) : patch) }
            : t,
        ),
      })),
    })),
  };
}

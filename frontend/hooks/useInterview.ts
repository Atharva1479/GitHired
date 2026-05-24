"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  deleteSession,
  endSession,
  getHistory,
  getReport,
  startSession,
  submitTurn,
} from "@/lib/interview-api";

export const INTERVIEW_KEYS = {
  report: (id: number) => ["interview", "report", id] as const,
  history: () => ["interview", "history"] as const,
};

export function useStartSession() {
  return useMutation({ mutationFn: startSession });
}

export function useSubmitTurn() {
  return useMutation({
    mutationFn: ({
      sessionId,
      ...payload
    }: {
      sessionId: number;
      question_index: number;
      question: string;
      user_answer: string;
    }) => submitTurn(sessionId, payload),
  });
}

export function useEndSession() {
  return useMutation({ mutationFn: endSession });
}

export function useReport(sessionId: number | null) {
  return useQuery({
    queryKey: INTERVIEW_KEYS.report(sessionId ?? 0),
    queryFn: () => getReport(sessionId!),
    enabled: sessionId !== null,
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.status === "ready" ? false : 3000;
    },
  });
}

export function useHistory() {
  return useQuery({
    queryKey: INTERVIEW_KEYS.history(),
    queryFn: getHistory,
  });
}

export function useDeleteSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: INTERVIEW_KEYS.history() });
    },
  });
}

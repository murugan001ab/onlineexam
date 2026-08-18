import { apiClient } from "@/api/client";
import type {
  QuizClassTargetAssign,
  QuizClassTargetOut,
  QuizCreate,
  QuizOut,
  QuizQuestionAdd,
  QuizQuestionOut,
  QuizQuestionReorder,
  QuizUpdate,
} from "@/types/quiz";

export const quizzesApi = {
  list: async (params?: { quiz_type?: string; status_?: string }) =>
    (await apiClient.get<QuizOut[]>("/admin/quizzes", { params })).data,
  get: async (id: number) => (await apiClient.get<QuizOut>(`/admin/quizzes/${id}`)).data,
  create: async (payload: QuizCreate) => (await apiClient.post<QuizOut>("/admin/quizzes", payload)).data,
  update: async (id: number, payload: QuizUpdate) =>
    (await apiClient.patch<QuizOut>(`/admin/quizzes/${id}`, payload)).data,
  remove: async (id: number) => {
    await apiClient.delete(`/admin/quizzes/${id}`);
  },

  listQuestions: async (quizId: number) =>
    (await apiClient.get<QuizQuestionOut[]>(`/admin/quizzes/${quizId}/questions`)).data,
  addQuestion: async (quizId: number, payload: QuizQuestionAdd) =>
    (await apiClient.post<QuizQuestionOut>(`/admin/quizzes/${quizId}/questions`, payload)).data,
  updateQuestion: async (quizId: number, quizQuestionId: number, payload: QuizQuestionReorder) =>
    (
      await apiClient.patch<QuizQuestionOut>(
        `/admin/quizzes/${quizId}/questions/${quizQuestionId}`,
        payload,
      )
    ).data,
  removeQuestion: async (quizId: number, quizQuestionId: number) => {
    await apiClient.delete(`/admin/quizzes/${quizId}/questions/${quizQuestionId}`);
  },

  listClassTargets: async (quizId: number) =>
    (await apiClient.get<QuizClassTargetOut[]>(`/admin/quizzes/${quizId}/class-targets`)).data,
  assignClassTarget: async (quizId: number, payload: QuizClassTargetAssign) =>
    (await apiClient.post<QuizClassTargetOut>(`/admin/quizzes/${quizId}/class-targets`, payload)).data,
  unassignClassTarget: async (quizId: number, targetId: number) => {
    await apiClient.delete(`/admin/quizzes/${quizId}/class-targets/${targetId}`);
  },
};

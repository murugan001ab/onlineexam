import { apiClient } from "@/api/client";
import type {
  AnswerSubmitRequest,
  AttemptAnswerReview,
  AttemptOut,
  AttemptQuestionOut,
  AvailableClassQuiz,
} from "@/types/attempt";

// Student-facing: browse & take quizzes assigned to the classes I'm enrolled in.
export const classQuizAttemptsApi = {
  listAvailable: async () => (await apiClient.get<AvailableClassQuiz[]>("/class-quizzes")).data,
  start: async (quizId: number) => (await apiClient.post<AttemptOut>(`/class-quizzes/${quizId}/start`)).data,
  getAttempt: async (attemptId: number) =>
    (await apiClient.get<AttemptOut>(`/class-quizzes/attempts/${attemptId}`)).data,
  getQuestions: async (attemptId: number) =>
    (await apiClient.get<AttemptQuestionOut[]>(`/class-quizzes/attempts/${attemptId}/questions`)).data,
  answer: async (attemptId: number, payload: AnswerSubmitRequest) =>
    (await apiClient.post(`/class-quizzes/attempts/${attemptId}/answers`, payload)).data,
  submit: async (attemptId: number) =>
    (await apiClient.post<AttemptOut>(`/class-quizzes/attempts/${attemptId}/submit`)).data,
};

// Staff/admin-facing: review attempts made against a quiz you own or manage.
export const quizAttemptsAdminApi = {
  list: async (quizId: number) =>
    (await apiClient.get<AttemptOut[]>(`/admin/quizzes/${quizId}/attempts`)).data,
  reviewAnswers: async (quizId: number, attemptId: number) =>
    (await apiClient.get<AttemptAnswerReview[]>(`/admin/quizzes/${quizId}/attempts/${attemptId}/answers`)).data,
};

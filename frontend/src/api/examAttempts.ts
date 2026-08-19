import { apiClient } from "@/api/client";
import type {
  ExamAnswerReview,
  ExamAnswerSubmit,
  ExamAttemptOut,
  ExamQuestionOut,
} from "@/types/examAttempt";

// Student-facing: take an entrance exam once invited & registration is confirmed.
// Backend: routers/attempt.py (student_router, prefix /exam-attempts).
export const examAttemptsApi = {
  start: async (examId: number) =>
    (await apiClient.post<ExamAttemptOut>(`/exam-attempts/${examId}/start`)).data,
  getAttempt: async (attemptId: number) =>
    (await apiClient.get<ExamAttemptOut>(`/exam-attempts/${attemptId}`)).data,
  getQuestions: async (attemptId: number) =>
    (await apiClient.get<ExamQuestionOut[]>(`/exam-attempts/${attemptId}/questions`)).data,
  answer: async (attemptId: number, payload: ExamAnswerSubmit) =>
    (await apiClient.post(`/exam-attempts/${attemptId}/answers`, payload)).data,
  submit: async (attemptId: number) =>
    (await apiClient.post<ExamAttemptOut>(`/exam-attempts/${attemptId}/submit`)).data,
};

// Admin-facing: review attempts made against an entrance exam.
// Backend: routers/attempt.py (admin_router, prefix /admin).
export const examAttemptsAdminApi = {
  list: async (examId: number) =>
    (await apiClient.get<ExamAttemptOut[]>(`/admin/exams/${examId}/attempts`)).data,
  reviewAnswers: async (examId: number, attemptId: number) =>
    (await apiClient.get<ExamAnswerReview[]>(`/admin/exams/${examId}/attempts/${attemptId}/answers`)).data,
};

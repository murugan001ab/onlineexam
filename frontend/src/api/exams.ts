import { apiClient } from "@/api/client";
import type {
  ExamCreate,
  ExamOut,
  ExamProblemAssign,
  ExamProblemOut,
  ExamProblemUpdate,
  ExamQuizAssign,
  ExamQuizOut,
  ExamQuizUpdate,
  ExamSlotCreate,
  ExamSlotOut,
  ExamSlotUpdate,
  ExamTopicWeightCreate,
  ExamTopicWeightOut,
  ExamTopicWeightUpdate,
  ExamTypeCreate,
  ExamTypeOut,
  ExamTypeUpdate,
  ExamUpdate,
} from "@/types/exam";

export const examTypesApi = {
  list: async () => (await apiClient.get<ExamTypeOut[]>("/admin/exam-types")).data,
  create: async (payload: ExamTypeCreate) =>
    (await apiClient.post<ExamTypeOut>("/admin/exam-types", payload)).data,
  update: async (id: number, payload: ExamTypeUpdate) =>
    (await apiClient.patch<ExamTypeOut>(`/admin/exam-types/${id}`, payload)).data,
  remove: async (id: number) => {
    await apiClient.delete(`/admin/exam-types/${id}`);
  },
};

export const examsApi = {
  list: async (params?: { exam_type_id?: number; status_?: string }) =>
    (await apiClient.get<ExamOut[]>("/admin/exams", { params })).data,
  get: async (id: number) => (await apiClient.get<ExamOut>(`/admin/exams/${id}`)).data,
  create: async (payload: ExamCreate) => (await apiClient.post<ExamOut>("/admin/exams", payload)).data,
  update: async (id: number, payload: ExamUpdate) =>
    (await apiClient.patch<ExamOut>(`/admin/exams/${id}`, payload)).data,
  remove: async (id: number) => {
    await apiClient.delete(`/admin/exams/${id}`);
  },

  listQuizzes: async (examId: number) =>
    (await apiClient.get<ExamQuizOut[]>(`/admin/exams/${examId}/quizzes`)).data,
  assignQuiz: async (examId: number, payload: ExamQuizAssign) =>
    (await apiClient.post<ExamQuizOut>(`/admin/exams/${examId}/quizzes`, payload)).data,
  updateQuizLink: async (examId: number, examQuizId: number, payload: ExamQuizUpdate) =>
    (await apiClient.patch<ExamQuizOut>(`/admin/exams/${examId}/quizzes/${examQuizId}`, payload)).data,
  unassignQuiz: async (examId: number, examQuizId: number) => {
    await apiClient.delete(`/admin/exams/${examId}/quizzes/${examQuizId}`);
  },

  listProblems: async (examId: number) =>
    (await apiClient.get<ExamProblemOut[]>(`/admin/exams/${examId}/problems`)).data,
  assignProblem: async (examId: number, payload: ExamProblemAssign) =>
    (await apiClient.post<ExamProblemOut>(`/admin/exams/${examId}/problems`, payload)).data,
  updateProblemLink: async (examId: number, examProblemId: number, payload: ExamProblemUpdate) =>
    (await apiClient.patch<ExamProblemOut>(`/admin/exams/${examId}/problems/${examProblemId}`, payload)).data,
  unassignProblem: async (examId: number, examProblemId: number) => {
    await apiClient.delete(`/admin/exams/${examId}/problems/${examProblemId}`);
  },

  listTopicWeights: async (examId: number) =>
    (await apiClient.get<ExamTopicWeightOut[]>(`/admin/exams/${examId}/topic-weights`)).data,
  addTopicWeight: async (examId: number, payload: ExamTopicWeightCreate) =>
    (await apiClient.post<ExamTopicWeightOut>(`/admin/exams/${examId}/topic-weights`, payload)).data,
  updateTopicWeight: async (examId: number, weightId: number, payload: ExamTopicWeightUpdate) =>
    (await apiClient.patch<ExamTopicWeightOut>(`/admin/exams/${examId}/topic-weights/${weightId}`, payload))
      .data,
  removeTopicWeight: async (examId: number, weightId: number) => {
    await apiClient.delete(`/admin/exams/${examId}/topic-weights/${weightId}`);
  },
};

export const examSlotsApi = {
  list: async (params?: { exam_id?: number; status_?: string }) =>
    (await apiClient.get<ExamSlotOut[]>("/admin/exam-slots", { params })).data,
  create: async (payload: ExamSlotCreate) =>
    (await apiClient.post<ExamSlotOut>("/admin/exam-slots", payload)).data,
  update: async (id: number, payload: ExamSlotUpdate) =>
    (await apiClient.patch<ExamSlotOut>(`/admin/exam-slots/${id}`, payload)).data,
  cancel: async (id: number) => {
    await apiClient.delete(`/admin/exam-slots/${id}`);
  },
};

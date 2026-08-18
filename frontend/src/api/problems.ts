import { apiClient } from "@/api/client";
import type {
  ProblemCreate,
  ProblemListItem,
  ProblemOut,
  ProblemUpdate,
  TestCaseCreate,
  TestCaseOut,
  TestCaseUpdate,
} from "@/types/problem";

export const problemsApi = {
  list: async (params?: { topic_id?: number; difficulty?: string; is_active?: boolean }) =>
    (await apiClient.get<ProblemListItem[]>("/problems", { params })).data,
  get: async (id: number) => (await apiClient.get<ProblemOut>(`/problems/${id}`)).data,
  create: async (payload: ProblemCreate) => (await apiClient.post<ProblemOut>("/problems", payload)).data,
  update: async (id: number, payload: ProblemUpdate) =>
    (await apiClient.patch<ProblemOut>(`/problems/${id}`, payload)).data,
  deactivate: async (id: number) => {
    await apiClient.delete(`/problems/${id}`);
  },

  listTestCases: async (problemId: number) =>
    (await apiClient.get<TestCaseOut[]>(`/problems/${problemId}/test-cases`)).data,
  createTestCase: async (problemId: number, payload: TestCaseCreate) =>
    (await apiClient.post<TestCaseOut>(`/problems/${problemId}/test-cases`, payload)).data,
  updateTestCase: async (problemId: number, testCaseId: number, payload: TestCaseUpdate) =>
    (await apiClient.patch<TestCaseOut>(`/problems/${problemId}/test-cases/${testCaseId}`, payload)).data,
  removeTestCase: async (problemId: number, testCaseId: number) => {
    await apiClient.delete(`/problems/${problemId}/test-cases/${testCaseId}`);
  },
};

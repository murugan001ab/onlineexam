import { apiClient } from "@/api/client";
import type { SubmissionCreate, SubmissionOut } from "@/types/submission";

export const submissionsApi = {
  create: async (payload: SubmissionCreate) => (await apiClient.post<SubmissionOut>("/submissions", payload)).data,
  listMine: async (params?: { problem_id?: number }) =>
    (await apiClient.get<SubmissionOut[]>("/submissions", { params })).data,
  get: async (id: number) => (await apiClient.get<SubmissionOut>(`/submissions/${id}`)).data,
};

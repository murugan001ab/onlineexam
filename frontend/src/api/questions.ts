import { apiClient } from "@/api/client";
import type { QuestionCreate, QuestionOut, QuestionUpdate } from "@/types/question";

export const questionsApi = {
  list: async (params?: { topic_id?: number; difficulty?: string; question_type?: string; is_active?: boolean }) =>
    (await apiClient.get<QuestionOut[]>("/admin/questions", { params })).data,
  get: async (id: number) => (await apiClient.get<QuestionOut>(`/admin/questions/${id}`)).data,
  create: async (payload: QuestionCreate) => (await apiClient.post<QuestionOut>("/admin/questions", payload)).data,
  update: async (id: number, payload: QuestionUpdate) =>
    (await apiClient.patch<QuestionOut>(`/admin/questions/${id}`, payload)).data,
  deactivate: async (id: number) => { await apiClient.delete(`/admin/questions/${id}`); },
  uploadImage: async (file: File) => {
    // Content-Type deliberately omitted: the browser must set
    // multipart/form-data itself (with the correct boundary) — hardcoding
    // it here would send a boundary-less header and break parsing.
    const form = new FormData();
    form.append("file", file);
    return (
      await apiClient.post<{ image_url: string }>("/admin/questions/upload-image", form, {
        headers: { "Content-Type": undefined },
      })
    ).data;
  },
};

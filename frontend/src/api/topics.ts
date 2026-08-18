import { apiClient } from "@/api/client";
import type { TopicCreate, TopicOut, TopicUpdate } from "@/types/topic";

export const topicsApi = {
  list: async () => (await apiClient.get<TopicOut[]>("/topics")).data,
  get: async (id: number) => (await apiClient.get<TopicOut>(`/topics/${id}`)).data,
  create: async (payload: TopicCreate) => (await apiClient.post<TopicOut>("/topics", payload)).data,
  update: async (id: number, payload: TopicUpdate) =>
    (await apiClient.patch<TopicOut>(`/topics/${id}`, payload)).data,
  remove: async (id: number) => {
    await apiClient.delete(`/topics/${id}`);
  },
};

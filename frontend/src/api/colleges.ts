import { apiClient } from "@/api/client";
import type { CollegeCreate, CollegeOut, CollegeUpdate } from "@/types/college";

export const collegesApi = {
  list: async (params?: { is_active?: boolean }) => {
    const { data } = await apiClient.get<CollegeOut[]>("/admin/colleges", { params });
    return data;
  },
  get: async (id: number) => {
    const { data } = await apiClient.get<CollegeOut>(`/admin/colleges/${id}`);
    return data;
  },
  create: async (payload: CollegeCreate) => {
    const { data } = await apiClient.post<CollegeOut>("/admin/colleges", payload);
    return data;
  },
  update: async (id: number, payload: CollegeUpdate) => {
    const { data } = await apiClient.patch<CollegeOut>(`/admin/colleges/${id}`, payload);
    return data;
  },
  deactivate: async (id: number) => {
    await apiClient.delete(`/admin/colleges/${id}`);
  },
};

import { apiClient } from "@/api/client";
import type { UserCreate, UserOut, UserUpdate } from "@/types/user";

export const usersApi = {
  list: async (params?: { role?: "admin" | "staff"; college_id?: number; is_active?: boolean }) => {
    const { data } = await apiClient.get<UserOut[]>("/admin/users", { params });
    return data;
  },
  get: async (id: number) => {
    const { data } = await apiClient.get<UserOut>(`/admin/users/${id}`);
    return data;
  },
  create: async (payload: UserCreate) => {
    const { data } = await apiClient.post<UserOut>("/admin/users", payload);
    return data;
  },
  update: async (id: number, payload: UserUpdate) => {
    const { data } = await apiClient.patch<UserOut>(`/admin/users/${id}`, payload);
    return data;
  },
  deactivate: async (id: number) => {
    await apiClient.delete(`/admin/users/${id}`);
  },
};

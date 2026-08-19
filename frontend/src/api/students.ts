import { apiClient } from "@/api/client";
import type { StudentClassOut, StudentCreate, StudentLoginOut, StudentOut, StudentUpdate } from "@/types/student";
export const studentsApi = {
  list: async (params?: { stage?: string; q?: string }) => (await apiClient.get<StudentOut[]>("/admin/students", { params })).data,
  create: async (payload: StudentCreate) => (await apiClient.post<StudentOut>("/admin/students", payload)).data,
  update: async (id: number, payload: StudentUpdate) => (await apiClient.patch<StudentOut>(`/admin/students/${id}`, payload)).data,
  remove: async (id: number) => { await apiClient.delete(`/admin/students/${id}`); },
  classes: async (id: number) => (await apiClient.get<StudentClassOut[]>(`/admin/students/${id}/classes`)).data,
  enroll: async (id: number, class_id: number) => (await apiClient.post<StudentClassOut>(`/admin/students/${id}/classes`, { class_id })).data,
  leaveClass: async (id: number, classId: number) => { await apiClient.delete(`/admin/students/${id}/classes/${classId}`); },
  createLogin: async (id: number, username?: string) => (await apiClient.post<StudentLoginOut>(`/admin/students/${id}/login`, { username: username || null })).data,
  updateLogin: async (id: number, payload: { is_active?: boolean; reset_password?: boolean }) => (await apiClient.patch<StudentLoginOut>(`/admin/students/${id}/login`, payload)).data,
};

import { apiClient } from "@/api/client";
import type {
  ClassCreate,
  ClassOut,
  ClassUpdate,
  DepartmentCreate,
  DepartmentOut,
  DepartmentUpdate,
  StaffClassAssign,
  StaffClassOut,
  StaffClassUpdate,
  StaffDepartmentAssign,
  StaffDepartmentOut,
} from "@/types/organization";

export const departmentsApi = {
  list: async (params?: { college_id?: number }) => {
    const { data } = await apiClient.get<DepartmentOut[]>("/admin/departments", { params });
    return data;
  },
  create: async (payload: DepartmentCreate) => {
    const { data } = await apiClient.post<DepartmentOut>("/admin/departments", payload);
    return data;
  },
  update: async (id: number, payload: DepartmentUpdate) => {
    const { data } = await apiClient.patch<DepartmentOut>(`/admin/departments/${id}`, payload);
    return data;
  },
  remove: async (id: number) => {
    await apiClient.delete(`/admin/departments/${id}`);
  },
};

export const classesApi = {
  list: async (params?: { department_id?: number; college_id?: number }) => {
    const { data } = await apiClient.get<ClassOut[]>("/admin/classes", { params });
    return data;
  },
  create: async (payload: ClassCreate) => {
    const { data } = await apiClient.post<ClassOut>("/admin/classes", payload);
    return data;
  },
  update: async (id: number, payload: ClassUpdate) => {
    const { data } = await apiClient.patch<ClassOut>(`/admin/classes/${id}`, payload);
    return data;
  },
  remove: async (id: number) => {
    await apiClient.delete(`/admin/classes/${id}`);
  },
};

export const staffAssignmentsApi = {
  listDepartments: async (staffId: number, includeInactive = false) => {
    const { data } = await apiClient.get<StaffDepartmentOut[]>(
      `/admin/staff/${staffId}/departments`,
      { params: { include_inactive: includeInactive } },
    );
    return data;
  },
  assignDepartment: async (staffId: number, payload: StaffDepartmentAssign) => {
    const { data } = await apiClient.post<StaffDepartmentOut>(
      `/admin/staff/${staffId}/departments`,
      payload,
    );
    return data;
  },
  unassignDepartment: async (staffId: number, departmentId: number) => {
    await apiClient.delete(`/admin/staff/${staffId}/departments/${departmentId}`);
  },

  listClasses: async (staffId: number) => {
    const { data } = await apiClient.get<StaffClassOut[]>(`/admin/staff/${staffId}/classes`);
    return data;
  },
  assignClass: async (staffId: number, payload: StaffClassAssign) => {
    const { data } = await apiClient.post<StaffClassOut>(`/admin/staff/${staffId}/classes`, payload);
    return data;
  },
  updateClass: async (staffId: number, classId: number, payload: StaffClassUpdate) => {
    const { data } = await apiClient.patch<StaffClassOut>(
      `/admin/staff/${staffId}/classes/${classId}`,
      payload,
    );
    return data;
  },
  unassignClass: async (staffId: number, classId: number) => {
    await apiClient.delete(`/admin/staff/${staffId}/classes/${classId}`);
  },
};

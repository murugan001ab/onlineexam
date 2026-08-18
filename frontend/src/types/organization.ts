export interface DepartmentCreate {
  name: string;
  code?: string | null;
  college_id?: number | null;
}
export type DepartmentUpdate = Partial<Pick<DepartmentCreate, "name" | "code">>;
export interface DepartmentOut {
  id: number;
  college_id: number;
  name: string;
  code: string | null;
}

export interface ClassCreate {
  department_id: number;
  name: string;
  academic_year?: string | null;
  section?: string | null;
}
export type ClassUpdate = Partial<Pick<ClassCreate, "name" | "academic_year" | "section">>;
export interface ClassOut {
  id: number;
  college_id: number;
  department_id: number;
  name: string;
  academic_year: string | null;
  section: string | null;
}

export interface StaffDepartmentAssign {
  department_id: number;
}
export interface StaffDepartmentOut {
  id: number;
  department_id: number;
  department_name: string;
  is_active: boolean;
  assigned_at: string | null;
}

export interface StaffClassAssign {
  class_id: number;
  is_incharge?: boolean;
}
export interface StaffClassUpdate {
  is_incharge: boolean;
}
export interface StaffClassOut {
  id: number;
  class_id: number;
  class_name: string;
  is_incharge: boolean;
  assigned_at: string | null;
}

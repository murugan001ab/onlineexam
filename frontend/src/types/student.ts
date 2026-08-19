import type { ProfileIn, ProfileOut, ProfileUpdate } from "./user";
export interface StudentCreate { email?: string | null; register_number?: string | null; application_number?: string | null; stage: "applicant" | "enrolled"; tenth_mark?: number | null; twelfth_mark?: number | null; diploma_mark?: number | null; is_diploma: boolean; profile: ProfileIn; }
export type StudentUpdate = Partial<Omit<StudentCreate, "profile">> & { profile?: ProfileUpdate };
export interface StudentOut { id: number; college_id: number; email: string | null; register_number: string | null; application_number: string | null; stage: string; tenth_mark: number | null; twelfth_mark: number | null; diploma_mark: number | null; is_diploma: boolean; admitted_at: string | null; has_login: boolean; profile: ProfileOut | null; }
export interface StudentClassOut { id: number; class_id: number; class_name: string; academic_year: string | null; joined_at: string | null; left_at: string | null; }
export interface StudentLoginOut { user_id: number; username: string; is_active: boolean; temporary_password: string | null; }

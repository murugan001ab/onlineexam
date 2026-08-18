export type ManagedRole = "admin" | "staff";

export interface ProfileIn {
  name: string;
  phone?: string | null;
  dob?: string | null;
  gender?: string | null;
  address?: string | null;
}

export type ProfileUpdate = Partial<ProfileIn>;

export interface ProfileOut {
  name: string;
  phone: string | null;
  dob: string | null;
  gender: string | null;
  address: string | null;
}

export interface UserCreate {
  username: string;
  email?: string | null;
  password: string;
  role: ManagedRole;
  college_id?: number | null;
  profile: ProfileIn;
}

export interface UserUpdate {
  email?: string | null;
  password?: string | null;
  is_active?: boolean | null;
  college_id?: number | null;
  profile?: ProfileUpdate | null;
}

export interface UserOut {
  id: number;
  username: string;
  email: string | null;
  role: string;
  college_id: number | null;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  profile: ProfileOut | null;
}

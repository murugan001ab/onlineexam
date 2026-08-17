export type RoleName = "super_admin" | "admin" | "staff" | "student";

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
}

export interface MeResponse {
  id: number;
  username: string;
  email: string | null;
  role: RoleName;
  college_id: number | null;
  is_active: boolean;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

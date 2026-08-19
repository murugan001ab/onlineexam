export type ContactType = "email" | "phone";

export interface PublicCollegeOut {
  id: number;
  name: string;
  city: string | null;
  state: string | null;
}

export interface SendOtpRequest {
  contact_type: ContactType;
  contact: string;
}

export interface SendOtpResponse {
  contact_type: ContactType;
  contact: string;
  expires_in_seconds: number;
  // Only populated when SMTP/SMS isn't configured on the backend (dev mode) —
  // lets the form auto-fill the code so signup can still be tested end to end.
  debug_code: string | null;
}

export interface VerifyOtpRequest {
  contact_type: ContactType;
  contact: string;
  code: string;
}

export interface VerifyOtpResponse {
  contact_type: ContactType;
  contact: string;
  verified: boolean;
}

export interface ApplicantSignupRequest {
  college_id: number;
  name: string;
  email: string;
  phone: string;
  password: string;
  dob?: string | null;
  gender?: string | null;
  tenth_mark?: number | null;
  twelfth_mark?: number | null;
}

export interface ApplicantSignupResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  username: string;
  student_id: number;
}

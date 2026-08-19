import { apiClient } from "@/api/client";
import type {
  ApplicantSignupRequest,
  ApplicantSignupResponse,
  PublicCollegeOut,
  SendOtpRequest,
  SendOtpResponse,
  VerifyOtpRequest,
  VerifyOtpResponse,
} from "@/types/publicSignup";
import type { ExamPublicOut } from "@/types/exam";

// Unauthenticated endpoints — used before a login exists.
export const publicSignupApi = {
  listColleges: async () => (await apiClient.get<PublicCollegeOut[]>("/public/colleges")).data,
  sendOtp: async (payload: SendOtpRequest) => (await apiClient.post<SendOtpResponse>("/public/signup/send-otp", payload)).data,
  verifyOtp: async (payload: VerifyOtpRequest) => (await apiClient.post<VerifyOtpResponse>("/public/signup/verify-otp", payload)).data,
  register: async (payload: ApplicantSignupRequest) => (await apiClient.post<ApplicantSignupResponse>("/public/signup/register", payload)).data,
  // Landing page for the shareable exam link (FRONTEND_URL/e/{slug}).
  getExamBySlug: async (slug: string) => (await apiClient.get<ExamPublicOut>(`/public/exams/${slug}`)).data,
};

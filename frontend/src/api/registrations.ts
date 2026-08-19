import { apiClient } from "@/api/client";
import type { ExamInvitationOut, ExamInvitationWithToken, ExamRegistrationOut } from "@/types/registration";
export const registrationsApi = {
  list: async (examId: number, status?: string) => (await apiClient.get<ExamRegistrationOut[]>(`/admin/exams/${examId}/registrations`, { params: status ? { status_ : status } : undefined })).data,
  invitations: async (examId: number) => (await apiClient.get<ExamInvitationOut[]>(`/admin/exams/${examId}/invitations`)).data,
  generateInvitations: async (examId: number, registration_ids?: number[]) => (await apiClient.post<ExamInvitationWithToken[]>(`/admin/exams/${examId}/invitations/generate`, { registration_ids: registration_ids?.length ? registration_ids : null, expires_in_hours: 72 })).data,
  resendInvitation: async (id: number) => (await apiClient.post<ExamInvitationWithToken>(`/admin/invitations/${id}/resend`)).data,
};

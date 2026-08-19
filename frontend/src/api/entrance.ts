import { apiClient } from "@/api/client";
import type { PaymentOrderOut, PaymentVerifyRequest, RegistrationCreate, SlotHoldOut } from "@/types/entranceApply";
import type { ExamRegistrationOut } from "@/types/registration";
import type { ExamOut, ExamSlotOut } from "@/types/exam";

// Applicant-facing entrance-exam application flow.
export const entranceApi = {
  // Exams open for application (student-accessible; college-scoped, published only).
  listOpenExams: async () => (await apiClient.get<ExamOut[]>("/entrance/exams")).data,
  // Open slots for a specific exam only (exam_id is required by the backend).
  listSlots: async (examId: number) =>
    (await apiClient.get<ExamSlotOut[]>("/entrance/slots", { params: { exam_id: examId } })).data,

  holdSlot: async (slotId: number) => (await apiClient.post<SlotHoldOut>(`/entrance/slots/${slotId}/hold`)).data,
  releaseHold: async (slotId: number) => {
    await apiClient.delete(`/entrance/slots/${slotId}/hold`);
  },

  myRegistrations: async () => (await apiClient.get<ExamRegistrationOut[]>("/entrance/registrations")).data,
  register: async (payload: RegistrationCreate) =>
    (await apiClient.post<ExamRegistrationOut>("/entrance/registrations", payload)).data,
  getRegistration: async (id: number) =>
    (await apiClient.get<ExamRegistrationOut>(`/entrance/registrations/${id}`)).data,
  cancelRegistration: async (id: number) => {
    await apiClient.delete(`/entrance/registrations/${id}`);
  },

  createPaymentOrder: async (registrationId: number) =>
    (await apiClient.post<PaymentOrderOut>(`/entrance/registrations/${registrationId}/payment-order`)).data,
  verifyPayment: async (payload: PaymentVerifyRequest) =>
    (await apiClient.post<ExamRegistrationOut>("/entrance/payments/verify", payload)).data,
  // Dev/local stand-in used when payment-order came back with key_id: null
  // (Razorpay isn't configured) — see backend routers/registration.py.
  mockConfirmPayment: async (registrationId: number) =>
    (await apiClient.post<ExamRegistrationOut>(`/entrance/registrations/${registrationId}/payments/mock-confirm`)).data,
};

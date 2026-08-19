import { apiClient } from "@/api/client";
import type { ExamRegistrationOut } from "@/types/registration";
export const registrationsApi = { myRegistrations: async () => (await apiClient.get<ExamRegistrationOut[]>("/entrance/registrations")).data };

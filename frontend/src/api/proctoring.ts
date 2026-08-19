import { apiClient } from "@/api/client";
import type { ProctoringEventBatchOut, ProctoringEventIn, ProctoringSnapshotOut } from "@/types/proctoring";

// Student-facing: called from TakeExamPage while an attempt is in progress.
// Backend: routers/proctoring.py (student_router, prefix /exam-attempts).
export const proctoringApi = {
  sendEvents: async (attemptId: number, events: ProctoringEventIn[]) =>
    (
      await apiClient.post<ProctoringEventBatchOut>(`/exam-attempts/${attemptId}/proctoring/events`, {
        events,
      })
    ).data,
  sendSnapshot: async (attemptId: number, imageBase64: string) =>
    (
      await apiClient.post<ProctoringSnapshotOut>(`/exam-attempts/${attemptId}/proctoring/snapshot`, {
        image_base64: imageBase64,
      })
    ).data,
};

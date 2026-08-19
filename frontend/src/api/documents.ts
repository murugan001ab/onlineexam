import { apiClient } from "@/api/client";
import type { DocType, StudentDocumentOut, StudentDocumentReview } from "@/types/document";

export const documentsApi = {
  // ---- student-facing (POST /entrance/documents, GET /entrance/documents)
  myDocuments: async () => (await apiClient.get<StudentDocumentOut[]>("/entrance/documents")).data,

  upload: async (params: {
    doc_type: DocType;
    file: File;
    issued_place?: string;
    issuing_board?: string;
  }) => {
    const form = new FormData();
    form.append("doc_type", params.doc_type);
    if (params.issued_place) form.append("issued_place", params.issued_place);
    if (params.issuing_board) form.append("issuing_board", params.issuing_board);
    form.append("file", params.file);
    // Content-Type deliberately omitted so the browser sets the multipart
    // boundary itself — see api/questions.ts::uploadImage for the same
    // pattern.
    return (
      await apiClient.post<StudentDocumentOut>("/entrance/documents", form, {
        headers: { "Content-Type": undefined },
      })
    ).data;
  },

  // ---- admin/staff review (GET/PATCH /admin/students/{id}/documents)
  listForStudent: async (studentId: number) =>
    (await apiClient.get<StudentDocumentOut[]>(`/admin/students/${studentId}/documents`)).data,

  review: async (studentId: number, documentId: number, payload: StudentDocumentReview) =>
    (
      await apiClient.patch<StudentDocumentOut>(
        `/admin/students/${studentId}/documents/${documentId}`,
        payload,
      )
    ).data,
};

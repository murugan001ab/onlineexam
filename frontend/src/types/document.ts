export type DocType = "tenth_marksheet" | "twelfth_marksheet" | "diploma_marksheet" | "age_proof" | "photo";
export type DocStatus = "pending" | "verified" | "rejected";

export interface StudentDocumentOut {
  id: number;
  student_id: number;
  doc_type: DocType;
  issued_place: string | null;
  issuing_board: string | null;
  file_url: string;
  original_filename: string | null;
  status: DocStatus;
  remarks: string | null;
  reviewed_by: number | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface StudentDocumentReview {
  status: "verified" | "rejected";
  remarks?: string | null;
}

/** Docs every applicant must upload before they can register for an exam —
 * kept in one place so ApplyEntrancePage and DocumentUploadSection agree on
 * what "ready" means. Diploma marksheet and photo are optional extras, not
 * part of the base gate. */
export const REQUIRED_DOC_TYPES: DocType[] = ["tenth_marksheet", "twelfth_marksheet", "age_proof"];

export const DOC_TYPE_LABELS: Record<DocType, string> = {
  tenth_marksheet: "10th marksheet",
  twelfth_marksheet: "12th marksheet",
  diploma_marksheet: "Diploma marksheet",
  age_proof: "Age proof",
  photo: "Photo",
};

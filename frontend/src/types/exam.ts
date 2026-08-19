export type ExamStatus = "draft" | "published" | "running" | "completed" | "cancelled";
export type SlotStatus = "open" | "closed" | "cancelled";

export interface ExamTypeCreate {
  name: string;
  description?: string | null;
}
export type ExamTypeUpdate = Partial<ExamTypeCreate>;
export interface ExamTypeOut {
  id: number;
  name: string;
  description: string | null;
}

export interface ExamCreate {
  name: string;
  description?: string | null;
  exam_type_id: number;
  starts_at?: string | null;
  ends_at?: string | null;
  duration_minutes?: number | null;
  fee?: number | null;
  fee_currency?: string;
  status?: ExamStatus;
  proctoring_enabled?: boolean;
  fullscreen_required?: boolean;
  camera_required?: boolean;
  max_tab_switch_warnings?: number;
}
export type ExamUpdate = Partial<ExamCreate>;
export interface ExamOut {
  id: number;
  college_id: number;
  name: string;
  description: string | null;
  exam_type_id: number;
  exam_type_name: string | null;
  starts_at: string | null;
  ends_at: string | null;
  duration_minutes: number | null;
  fee: number | null;
  fee_currency: string;
  status: string | null;
  public_slug: string | null;
  public_url: string | null;
  proctoring_enabled: boolean;
  fullscreen_required: boolean;
  camera_required: boolean;
  max_tab_switch_warnings: number;
  registration_count: number;
  slot_count: number;
  created_by: number;
  created_at: string;
}

export interface ExamQuizAssign {
  quiz_id: number;
  order_index?: number | null;
  weight?: number | null;
}
export interface ExamQuizUpdate {
  order_index?: number | null;
  weight?: number | null;
}
export interface ExamQuizOut {
  id: number;
  quiz_id: number;
  quiz_name: string;
  order_index: number | null;
  weight: number | null;
}

export interface ExamProblemAssign {
  problem_id: number;
  order_index?: number | null;
  marks?: number | null;
}
export interface ExamProblemUpdate {
  order_index?: number | null;
  marks?: number | null;
}
export interface ExamProblemOut {
  id: number;
  problem_id: number;
  problem_title: string;
  order_index: number | null;
  marks: number | null;
}

export interface ExamTopicWeightCreate {
  topic_id: number;
  question_count: number;
  weight?: number | null;
}
export interface ExamTopicWeightUpdate {
  question_count?: number;
  weight?: number | null;
}
export interface ExamTopicWeightOut {
  id: number;
  topic_id: number;
  topic_name: string;
  question_count: number;
  weight: number | null;
}

export interface ExamSlotCreate {
  exam_id: number;
  name?: string | null;
  starts_at: string;
  ends_at: string;
  max_capacity: number;
  status?: SlotStatus;
}
export type ExamSlotUpdate = Partial<Omit<ExamSlotCreate, "exam_id">>;
export interface ExamSlotOut {
  id: number;
  college_id: number;
  exam_id: number | null;
  name: string | null;
  starts_at: string;
  ends_at: string;
  max_capacity: number;
  status: string | null;
  booked_count: number;
  available: number;
}

// Unauthenticated landing page served from the public share link
// (FRONTEND_URL/e/{slug}) — WhatsApp/poster/QR/college-portal.
export interface ExamPublicOut {
  name: string;
  description: string | null;
  exam_type_name: string | null;
  college_name: string;
  starts_at: string | null;
  ends_at: string | null;
  duration_minutes: number | null;
  fee: number | null;
  fee_currency: string;
  status: string | null;
  open_slot_count: number;
}

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
  name?: string | null;
  starts_at: string;
  ends_at: string;
  max_capacity: number;
  status?: SlotStatus;
}
export type ExamSlotUpdate = Partial<ExamSlotCreate>;
export interface ExamSlotOut {
  id: number;
  college_id: number;
  name: string | null;
  starts_at: string;
  ends_at: string;
  max_capacity: number;
  status: string | null;
  booked_count: number;
  available: number;
}

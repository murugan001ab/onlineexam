export type QuizType = "entrance" | "class" | "placement";
export type QuizStatus = "draft" | "published" | "archived";

export interface QuizCreate {
  name: string;
  description?: string | null;
  quiz_type: QuizType;
  subject?: string | null;
  schedule_start?: string | null;
  schedule_end?: string | null;
  duration_minutes?: number | null;
  status?: QuizStatus;
}
export type QuizUpdate = Partial<Omit<QuizCreate, "quiz_type">>;

export interface QuizOut {
  id: number;
  college_id: number;
  name: string;
  description: string | null;
  quiz_type: string | null;
  subject: string | null;
  schedule_start: string | null;
  schedule_end: string | null;
  duration_minutes: number | null;
  status: string | null;
  created_by: number;
  created_at: string;
  question_count: number;
}

export interface QuizQuestionAdd {
  question_id: number;
  order_index?: number | null;
  marks?: number | null;
}
export interface QuizQuestionReorder {
  order_index?: number | null;
  marks?: number | null;
}
export interface QuizQuestionOut {
  id: number;
  question_id: number;
  order_index: number | null;
  marks: number | null;
  text: string;
  question_type: string | null;
  difficulty: string | null;
}

export interface QuizClassTargetAssign {
  class_id: number;
}
export interface QuizClassTargetOut {
  id: number;
  quiz_id: number;
  class_id: number;
  class_name: string;
  assigned_by: number;
  assigned_at: string | null;
}

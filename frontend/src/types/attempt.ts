// Shared shapes for both class-quiz attempts (/class-quizzes/attempts/*) and
// entrance-exam attempts (/exam-attempts/*) — the two backends are structurally
// the same, so one set of types covers both.

export type AttemptStatus = "in_progress" | "submitted" | "expired" | "graded";

export interface AttemptOut {
  id: number;
  quiz_id?: number;
  exam_id?: number;
  student_id: number;
  status: AttemptStatus | string;
  started_at: string | null;
  submitted_at: string | null;
  expires_at?: string | null;
  duration_minutes?: number | null;
  score: number | null;
  total_marks: number | null;
}

export interface AttemptQuestionOut {
  id: number;
  question_id: number;
  text: string;
  question_type: "single_choice" | "multiple_choice" | "true_false" | string;
  options: Record<string, string> | string[] | null;
  marks: number | null;
  order_index: number | null;
  selected_answer?: unknown;
}

export interface AnswerSubmitRequest {
  question_id: number;
  answer: unknown;
}

export interface AttemptAnswerReview {
  question_id: number;
  text: string;
  question_type: string;
  options: Record<string, string> | string[] | null;
  correct_answer?: unknown;
  selected_answer: unknown;
  is_correct: boolean | null;
  marks_awarded: number | null;
  marks: number | null;
}

export interface AvailableClassQuiz {
  id: number;
  name: string;
  description: string | null;
  subject: string | null;
  class_name: string;
  duration_minutes: number | null;
  schedule_start?: string | null;
  schedule_end?: string | null;
  attempt_id: number | null;
  attempt_status: string | null;
}

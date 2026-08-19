// Entrance-exam attempt types — mirrors backend schemas/attempt.py exactly.
// Kept separate from types/attempt.ts (which backs the *class-quiz* attempt
// flow against a differently-shaped backend) to avoid coupling two unrelated
// features to one guessed-at shared shape.

export type ExamAttemptStatus = "not_started" | "in_progress" | "submitted" | "expired" | "disqualified";

export interface ExamAttemptOut {
  id: number;
  exam_id: number;
  exam_name: string | null;
  student_id: number;
  status: ExamAttemptStatus;
  started_at: string | null;
  submitted_at: string | null;
  duration_minutes: number | null;
  score: number | string | null;
  max_score: number | string | null;
}

export type ExamQuestionType = "single_choice" | "multiple_choice" | "true_false";

export interface ExamQuestionOut {
  id: number;
  topic_id: number | null;
  text: string;
  question_type: ExamQuestionType | string | null;
  options: Record<string, string> | string[] | null;
  image_url: string | null;
  difficulty: string | null;
  marks: number;
}

export interface ExamAnswerSubmit {
  question_id: number;
  answer: unknown;
}

export interface ExamAnswerOut {
  id: number;
  question_id: number;
  answer: unknown;
  is_correct: boolean | null;
  marks: number | string | null;
  answered_at: string | null;
}

export interface ExamAnswerReview extends ExamAnswerOut {
  question_text: string;
  correct_answer: unknown;
}

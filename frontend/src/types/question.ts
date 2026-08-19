export type QuestionType = "single_choice" | "multiple_choice" | "true_false";
export type QuestionDifficulty = "easy" | "medium" | "hard";

export interface QuestionCreate {
  topic_id?: number | null;
  text: string;
  question_type: QuestionType;
  options?: unknown;
  correct_answer?: unknown;
  explanation?: string | null;
  image_url?: string | null;
  difficulty?: QuestionDifficulty | null;
  marks: number;
  is_active: boolean;
}

export type QuestionUpdate = Partial<QuestionCreate>;

export interface QuestionOut extends QuestionCreate {
  id: number;
  college_id: number;
  created_by: number;
  created_at: string;
}

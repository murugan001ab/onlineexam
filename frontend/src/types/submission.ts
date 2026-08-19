export interface SubmissionCreate {
  problem_id: number;
  language: string;
  code: string;
}

export interface TestCaseResult {
  test_case_id: number;
  passed: boolean | null;
  is_hidden?: boolean;
  input?: string | null;
  expected_output?: string | null;
  actual_output?: string | null;
  runtime_ms?: number | null;
  error?: string | null;
}

export type SubmissionStatus = "pending" | "running" | "accepted" | "wrong_answer" | "error" | "compile_error" | string;

export interface SubmissionOut {
  id: number;
  problem_id: number;
  problem_title?: string | null;
  student_id?: number;
  language: string;
  code: string;
  status: SubmissionStatus;
  score: number | null;
  passed_count?: number | null;
  total_count?: number | null;
  results?: TestCaseResult[] | null;
  created_at: string;
}

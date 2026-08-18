export type Difficulty = "easy" | "medium" | "hard";

export interface TopicBrief {
  id: number;
  name: string;
  slug: string;
}

export interface TestCaseOut {
  id: number;
  input: string | null;
  expected_output: string | null;
  is_hidden: boolean;
  order_index: number | null;
  points: number | null;
}

export interface TestCaseCreate {
  input?: string | null;
  expected_output?: string | null;
  is_hidden?: boolean;
  order_index?: number | null;
  points?: number | null;
}

export type TestCaseUpdate = Partial<TestCaseCreate>;

export interface ProblemBase {
  title: string;
  slug: string;
  description?: string | null;
  constraints?: string | null;
  starter_code?: string | null;
  difficulty?: Difficulty | null;
  time_limit_ms?: number | null;
  memory_limit_kb?: number | null;
  allowed_languages?: string[] | null;
  default_language?: string | null;
  is_active: boolean;
}

export interface ProblemCreate extends ProblemBase {
  topic_ids: number[];
}

export type ProblemUpdate = Partial<ProblemBase> & { topic_ids?: number[] };

export interface ProblemListItem {
  id: number;
  uuid: string;
  title: string;
  slug: string;
  difficulty: string | null;
  is_active: boolean;
}

export interface ProblemOut {
  id: number;
  uuid: string;
  college_id: number;
  title: string;
  slug: string;
  description: string | null;
  constraints: string | null;
  starter_code: string | null;
  difficulty: string | null;
  time_limit_ms: number | null;
  memory_limit_kb: number | null;
  allowed_languages: string[] | null;
  default_language: string | null;
  is_active: boolean;
  created_by: number;
  created_at: string;
  updated_at: string;
  topics: TopicBrief[];
  test_cases: TestCaseOut[];
}

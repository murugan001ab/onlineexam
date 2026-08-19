// Mirrors backend schemas/proctoring.py.

export type ProctoringEventType =
  | "tab_switch"
  | "window_blur"
  | "fullscreen_exit"
  | "copy"
  | "paste"
  | "right_click"
  | "devtools"
  | "face_missing"
  | "multiple_faces";

export interface ProctoringEventIn {
  event_type: ProctoringEventType;
  metadata?: unknown;
  occurred_at?: string;
}

export interface ProctoringEventBatchOut {
  accepted: number;
  warning_count: number;
  max_warnings: number;
  disqualified: boolean;
}

export interface ProctoringSnapshotOut {
  id: number;
  file_url: string;
  face_count: number | null;
  flagged: boolean;
  captured_at: string | null;
}

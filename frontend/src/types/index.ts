export type BrowserMode = "headful" | "headless";

export type RunStatus =
  | "pending"
  | "running"
  | "awaiting_challenge"
  | "success"
  | "failed"
  | "blocked"
  | "cancelled";

export interface Bot {
  bot_id: string;
  name: string;
}

export interface RunMetadata {
  challenge_id?: string | null;
  captcha_status?: string | null;
  [key: string]: unknown;
}

export interface Run {
  id: string;
  bot_id: string;
  browser_mode: BrowserMode;
  status: RunStatus;
  bot_metadata: RunMetadata;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
}

export interface RunEvent {
  id: string;
  run_id: string;
  event_type: string;
  message: string;
  created_at: string;
}

export interface RunListResponse {
  items: Run[];
  total: number;
  limit: number;
  offset: number;
}

export interface RunCreatePayload {
  bot_id: string;
  browser_mode: BrowserMode;
}

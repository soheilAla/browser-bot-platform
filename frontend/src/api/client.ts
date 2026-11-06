import type { Bot, Run, RunCreatePayload, RunEvent, RunListResponse, RunStatus } from "@/types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let errorMessage = `Request failed with status ${response.status}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorMessage = errorData.detail;
      }
    } catch {}
    throw new Error(errorMessage);
  }

  return response.json() as Promise<T>;
}

export const api = {
  getBots: () => request<Bot[]>("/bots"),
  getBot: (botId: string) => request<Bot>(`/bots/${botId}`),
  createRun: (payload: RunCreatePayload) =>
    request<Run>("/runs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getRuns: (limit = 20, offset = 0, status?: RunStatus) => {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    if (status) {
      params.append("run_status", status);
    }
    return request<RunListResponse>(`/runs?${params.toString()}`);
  },
  getRun: (runId: string) => request<Run>(`/runs/${runId}`),
  getRunEvents: (runId: string) => request<RunEvent[]>(`/runs/${runId}/events`),
  checkHealth: () => request<{ status: string; timestamp: string }>("/health"),
};

import type { RunStatus } from "@/types";

export function statusBadgeClass(status: RunStatus | string): string {
  switch (status) {
    case "success":
      return "bg-emerald-50 text-emerald-700 border-emerald-200";
    case "running":
      return "bg-sky-50 text-sky-700 border-sky-200 animate-pulse";
    case "pending":
      return "bg-slate-100 text-slate-700 border-slate-200";
    case "blocked":
      return "bg-amber-50 text-amber-700 border-amber-200";
    case "failed":
      return "bg-rose-50 text-rose-700 border-rose-200";
    default:
      return "bg-slate-100 text-slate-600 border-slate-200";
  }
}

export function getVncUrl(): string {
  const host =
    typeof window !== "undefined" && window.location.hostname
      ? window.location.hostname
      : "localhost";
  return `http://${host}:7900/?autoconnect=1`;
}

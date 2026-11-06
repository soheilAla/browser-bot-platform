<script setup lang="ts">
import type { Run, RunStatus } from "@/types";
import { statusBadgeClass } from "@/utils";

const props = defineProps<{
  runs: Run[];
  total: number;
  loading: boolean;
  selectedStatus: RunStatus | "all";
  currentPage: number;
  pageSize: number;
}>();

const emit = defineEmits<{
  (e: "select-run", run: Run): void;
  (e: "filter-status", status: RunStatus | "all"): void;
  (e: "page-change", page: number): void;
  (e: "refresh"): void;
}>();

const statuses: { label: string; value: RunStatus | "all" }[] = [
  { label: "All Runs", value: "all" },
  { label: "Pending", value: "pending" },
  { label: "Running", value: "running" },
  { label: "Success", value: "success" },
  { label: "Blocked", value: "blocked" },
  { label: "Failed", value: "failed" },
];

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return dateStr;
  }
}

function truncateId(id: string): string {
  return `${id.slice(0, 8)}…`;
}
</script>

<template>
  <div class="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden flex flex-col">
    <div class="p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h2 class="text-base font-semibold text-slate-900 tracking-tight">Execution History</h2>
        <p class="text-xs text-slate-500 mt-0.5">
          Showing {{ runs.length }} of {{ total }} recorded bot execution runs.
        </p>
      </div>

      <div class="flex items-center gap-2">
        <button
          @click="emit('refresh')"
          :disabled="loading"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-md transition disabled:opacity-50"
          title="Refresh run history"
        >
          <svg
            :class="['w-3.5 h-3.5 text-slate-500', loading ? 'animate-spin' : '']"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>Refresh</span>
        </button>
      </div>
    </div>

    <div class="px-5 py-2.5 bg-slate-50/70 border-b border-slate-100 flex items-center gap-1 overflow-x-auto text-xs">
      <span class="text-slate-400 mr-2 font-medium">Filter:</span>
      <button
        v-for="s in statuses"
        :key="s.value"
        @click="emit('filter-status', s.value)"
        :class="[
          'px-2.5 py-1 rounded font-medium transition-colors whitespace-nowrap',
          selectedStatus === s.value
            ? 'bg-slate-900 text-white'
            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
        ]"
      >
        {{ s.label }}
      </button>
    </div>

    <div class="overflow-x-auto">
      <table class="w-full text-left text-xs border-collapse">
        <thead>
          <tr class="border-b border-slate-200 text-slate-400 uppercase tracking-wider font-semibold bg-slate-50/30">
            <th class="py-3 px-4">Run ID</th>
            <th class="py-3 px-4">Bot</th>
            <th class="py-3 px-4">Mode</th>
            <th class="py-3 px-4">Status</th>
            <th class="py-3 px-4">Challenge ID</th>
            <th class="py-3 px-4">Created</th>
            <th class="py-3 px-4 text-right">Details</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100 text-slate-700">
          <tr
            v-for="r in runs"
            :key="r.id"
            @click="emit('select-run', r)"
            class="hover:bg-slate-50/80 cursor-pointer transition-colors"
          >
            <td class="py-3.5 px-4 font-mono font-medium text-slate-900">
              <span :title="r.id">{{ truncateId(r.id) }}</span>
            </td>

            <td class="py-3.5 px-4 font-medium text-slate-800">
              {{ r.bot_id }}
            </td>

            <td class="py-3.5 px-4">
              <span
                :class="[
                  'inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium border capitalize',
                  r.browser_mode === 'headful'
                    ? 'bg-sky-50 text-sky-700 border-sky-200'
                    : 'bg-slate-100 text-slate-600 border-slate-200'
                ]"
              >
                {{ r.browser_mode }}
              </span>
            </td>

            <td class="py-3.5 px-4">
              <span
                :class="[
                  'inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border uppercase tracking-wide',
                  statusBadgeClass(r.status)
                ]"
              >
                {{ r.status }}
              </span>
            </td>

            <td class="py-3.5 px-4 font-mono text-[11px]">
              <span
                v-if="r.bot_metadata?.challenge_id"
                class="text-slate-800 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200"
                :title="String(r.bot_metadata.challenge_id)"
              >
                {{ String(r.bot_metadata.challenge_id).slice(0, 12) }}…
              </span>
              <span v-else class="text-slate-400">—</span>
            </td>

            <td class="py-3.5 px-4 text-slate-500 whitespace-nowrap">
              {{ formatDate(r.created_at) }}
            </td>

            <td class="py-3.5 px-4 text-right">
              <span class="text-brand-600 hover:text-brand-700 font-medium text-xs">
                View &rarr;
              </span>
            </td>
          </tr>

          <tr v-if="runs.length === 0 && !loading">
            <td colspan="7" class="py-12 text-center text-slate-400 text-xs">
              No execution runs found. Launch a bot to start tracking.
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      v-if="total > pageSize"
      class="px-5 py-3 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500"
    >
      <span>
        Page {{ currentPage }} of {{ Math.ceil(total / pageSize) }}
      </span>
      <div class="flex items-center gap-2">
        <button
          @click="emit('page-change', currentPage - 1)"
          :disabled="currentPage <= 1 || loading"
          class="px-2.5 py-1 bg-white border border-slate-200 rounded text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Previous
        </button>
        <button
          @click="emit('page-change', currentPage + 1)"
          :disabled="currentPage >= Math.ceil(total / pageSize) || loading"
          class="px-2.5 py-1 bg-white border border-slate-200 rounded text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>

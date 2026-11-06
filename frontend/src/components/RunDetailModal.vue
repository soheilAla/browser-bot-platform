<script setup lang="ts">
import type { Run, RunEvent } from "@/types";
import { getVncUrl, statusBadgeClass } from "@/utils";
import { computed, onMounted, onUnmounted } from "vue";

const props = defineProps<{
  run: Run | null;
  events: RunEvent[];
  open: boolean;
  loadingEvents: boolean;
}>();

const emit = defineEmits<(e: "close") => void>();

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === "Escape" && props.open) {
    emit("close");
  }
}

onMounted(() => window.addEventListener("keydown", handleKeyDown));
onUnmounted(() => window.removeEventListener("keydown", handleKeyDown));

function formatTimestamp(ts: string | null): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

function calculateDuration(start: string | null, finish: string | null): string {
  if (!start) return "—";
  const s = new Date(start).getTime();
  const f = finish ? new Date(finish).getTime() : Date.now();
  const sec = Math.max(0, (f - s) / 1000);
  return `${sec.toFixed(1)}s`;
}

const challengeId = computed(() => props.run?.bot_metadata?.challenge_id || null);
const captchaStatus = computed(() => props.run?.bot_metadata?.captcha_status || null);
</script>

<template>
  <div
    v-if="open && run"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm transition-opacity"
    @click.self="emit('close')"
  >
    <div class="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-in fade-in duration-150">
      <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
        <div class="flex items-center gap-3">
          <span
            :class="[
              'px-2 py-0.5 rounded text-[11px] font-semibold border uppercase tracking-wider',
              statusBadgeClass(run.status)
            ]"
          >
            {{ run.status }}
          </span>
          <span class="font-mono text-xs text-slate-500 truncate max-w-xs" :title="run.id">
            {{ run.id }}
          </span>
        </div>

        <button
          @click="emit('close')"
          class="text-slate-400 hover:text-slate-600 p-1 rounded-md hover:bg-slate-100 transition-colors"
          title="Close modal"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="p-6 overflow-y-auto space-y-6 text-xs text-slate-700">
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-slate-50 border border-slate-100 rounded-lg">
          <div>
            <span class="block text-slate-400 font-medium text-[11px] uppercase tracking-wider mb-1">Bot</span>
            <span class="font-semibold text-slate-900 text-sm">{{ run.bot_id }}</span>
          </div>

          <div>
            <span class="block text-slate-400 font-medium text-[11px] uppercase tracking-wider mb-1">Browser Mode</span>
            <span class="font-semibold text-slate-900 text-sm capitalize">{{ run.browser_mode }}</span>
          </div>

          <div>
            <span class="block text-slate-400 font-medium text-[11px] uppercase tracking-wider mb-1">Duration</span>
            <span class="font-mono font-semibold text-slate-900 text-sm">
              {{ calculateDuration(run.started_at, run.finished_at) }}
            </span>
          </div>

          <div>
            <span class="block text-slate-400 font-medium text-[11px] uppercase tracking-wider mb-1">Started</span>
            <span class="text-slate-700">{{ formatTimestamp(run.started_at) }}</span>
          </div>
        </div>

        <div
          v-if="run.browser_mode === 'headful' && run.status === 'running'"
          class="p-3 bg-sky-50 border border-sky-200 rounded-md flex items-center justify-between"
        >
          <div class="text-sky-900">
            <span class="font-semibold">Run in Progress:</span> Watch the browser live inside the container.
          </div>
          <a
            :href="getVncUrl()"
            target="_blank"
            rel="noopener noreferrer"
            class="px-3 py-1 bg-sky-600 hover:bg-sky-700 text-white rounded font-medium text-xs shadow-sm transition"
          >
            Open Viewer (Port 7900) &rarr;
          </a>
        </div>

        <div class="border border-slate-200 rounded-lg p-4 space-y-2">
          <h4 class="font-semibold text-slate-900 text-xs uppercase tracking-wider">Bot Execution Metadata</h4>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
            <div>
              <span class="text-slate-400 block text-[11px]">Extracted Challenge ID</span>
              <span v-if="challengeId" class="font-mono text-slate-800 break-all select-all font-medium">
                {{ challengeId }}
              </span>
              <span v-else class="text-slate-400 italic">None extracted</span>
            </div>

            <div>
              <span class="text-slate-400 block text-[11px]">CAPTCHA Status</span>
              <span v-if="captchaStatus" class="font-medium text-slate-800 uppercase tracking-wide">
                {{ captchaStatus }}
              </span>
              <span v-else class="text-slate-400 italic">None</span>
            </div>
          </div>
        </div>

        <div v-if="run.error_message" class="p-3 bg-rose-50 border border-rose-200 rounded-md text-rose-800">
          <span class="font-semibold block mb-0.5 text-[11px] uppercase tracking-wider">Diagnostic Result</span>
          <p class="font-mono text-xs break-words">{{ run.error_message }}</p>
        </div>

        <div>
          <h4 class="font-semibold text-slate-900 text-xs uppercase tracking-wider mb-3">Event Timeline</h4>

          <div v-if="loadingEvents" class="py-6 text-center text-slate-400 italic">
            Loading timeline events...
          </div>

          <div v-else-if="events.length === 0" class="py-6 text-center text-slate-400 italic bg-slate-50 border border-dashed border-slate-200 rounded-md">
            No events recorded for this run.
          </div>

          <div v-else class="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
            <div
              v-for="ev in events"
              :key="ev.id"
              class="relative flex items-start justify-between gap-4"
            >
              <span class="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-slate-400 ring-4 ring-white" />

              <div class="space-y-0.5">
                <span class="font-mono font-semibold text-slate-900 uppercase text-[11px]">
                  {{ ev.event_type }}
                </span>
                <p class="text-slate-600 text-xs">{{ ev.message }}</p>
              </div>

              <time class="text-[11px] text-slate-400 font-mono whitespace-nowrap">
                {{ formatTimestamp(ev.created_at) }}
              </time>
            </div>
          </div>
        </div>
      </div>

      <div class="px-6 py-3 border-t border-slate-100 bg-slate-50 flex justify-end">
        <button
          @click="emit('close')"
          class="px-4 py-1.5 text-xs font-medium text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 rounded-md shadow-sm transition"
        >
          Close
        </button>
      </div>
    </div>
  </div>
</template>

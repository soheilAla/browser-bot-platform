<script setup lang="ts">
import { api } from "@/api/client";
import BotLauncher from "@/components/BotLauncher.vue";
import RunDetailModal from "@/components/RunDetailModal.vue";
import RunHistoryTable from "@/components/RunHistoryTable.vue";
import type { Bot, BrowserMode, Run, RunEvent, RunStatus } from "@/types";
import { getVncUrl } from "@/utils";
import { computed, onMounted, onUnmounted, ref } from "vue";

const bots = ref<Bot[]>([]);
const runs = ref<Run[]>([]);
const totalRuns = ref(0);
const loading = ref(false);
const launching = ref(false);
const selectedStatus = ref<RunStatus | "all">("all");
const currentPage = ref(1);
const pageSize = 15;

const selectedRun = ref<Run | null>(null);
const runEvents = ref<RunEvent[]>([]);
const loadingEvents = ref(false);
const modalOpen = ref(false);

const apiError = ref<string | null>(null);
let pollTimer: ReturnType<typeof setInterval> | null = null;

const hasActiveRuns = computed(() =>
  runs.value.some((r) => r.status === "pending" || r.status === "running"),
);

async function fetchBots() {
  try {
    bots.value = await api.getBots();
  } catch (err: any) {
    apiError.value = `Unable to connect to backend API: ${err.message}`;
  }
}

async function fetchRuns(quiet = false) {
  if (!quiet) loading.value = true;
  apiError.value = null;

  try {
    const offset = (currentPage.value - 1) * pageSize;
    const filter = selectedStatus.value === "all" ? undefined : selectedStatus.value;
    const res = await api.getRuns(pageSize, offset, filter);
    runs.value = res.items;
    totalRuns.value = res.total;

    if (selectedRun.value && modalOpen.value) {
      const updated = res.items.find((r) => r.id === selectedRun.value?.id);
      if (updated) {
        selectedRun.value = updated;
        if (updated.status === "running" || updated.status === "pending") {
          fetchEvents(updated.id);
        }
      }
    }
  } catch (err: any) {
    if (!quiet) {
      apiError.value = `Failed to fetch runs: ${err.message}`;
    }
  } finally {
    if (!quiet) loading.value = false;
  }
}

async function fetchEvents(runId: string) {
  loadingEvents.value = true;
  try {
    runEvents.value = await api.getRunEvents(runId);
  } catch (err: any) {
    console.error("Failed to fetch events", err);
  } finally {
    loadingEvents.value = false;
  }
}

async function handleLaunch(payload: { bot_id: string; browser_mode: BrowserMode }) {
  launching.value = true;
  apiError.value = null;
  try {
    const newRun = await api.createRun(payload);
    currentPage.value = 1;
    selectedStatus.value = "all";
    await fetchRuns();
    handleSelectRun(newRun);
  } catch (err: any) {
    apiError.value = `Launch failed: ${err.message}`;
  } finally {
    launching.value = false;
  }
}

function handleSelectRun(run: Run) {
  selectedRun.value = run;
  runEvents.value = [];
  modalOpen.value = true;
  fetchEvents(run.id);
}

function handleFilterStatus(status: RunStatus | "all") {
  selectedStatus.value = status;
  currentPage.value = 1;
  fetchRuns();
}

function handlePageChange(newPage: number) {
  currentPage.value = newPage;
  fetchRuns();
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(() => {
    fetchRuns(true);
  }, 2500);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

onMounted(async () => {
  await fetchBots();
  await fetchRuns();
  startPolling();
});

onUnmounted(() => {
  stopPolling();
});
</script>

<template>
  <div class="min-h-screen bg-slate-50 text-slate-800 flex flex-col">
    <header class="bg-white border-b border-slate-200 sticky top-0 z-40">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded bg-slate-900 flex items-center justify-center text-white font-bold text-sm">
            B
          </div>
          <div>
            <h1 class="text-sm font-bold text-slate-900 tracking-tight">Browser Bot Platform</h1>
            <p class="text-[11px] text-slate-500">Extensible Automation & Inspection Engine</p>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <a
            :href="getVncUrl()"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-slate-100 hover:bg-slate-200/80 text-slate-800 border border-slate-200 transition"
            title="Open container virtual desktop"
          >
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span>noVNC Screen (Port 7900)</span>
            <svg class="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>

          <div
            v-if="hasActiveRuns"
            class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-sky-50 text-sky-700 border border-sky-200"
          >
            <span class="w-2 h-2 rounded-full bg-sky-500 animate-ping"></span>
            <span>Worker Active</span>
          </div>
        </div>
      </div>
    </header>

    <div
      v-if="apiError"
      class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6 w-full"
    >
      <div class="p-3.5 bg-rose-50 border border-rose-200 rounded-md text-xs text-rose-800 flex items-center justify-between">
        <span>{{ apiError }}</span>
        <button @click="apiError = null" class="text-rose-500 hover:text-rose-700 font-bold ml-4">
          &times;
        </button>
      </div>
    </div>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full flex-1">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        <section class="lg:col-span-1">
          <BotLauncher
            :bots="bots"
            :loading="launching"
            @launch="handleLaunch"
          />
        </section>

        <section class="lg:col-span-2">
          <RunHistoryTable
            :runs="runs"
            :total="totalRuns"
            :loading="loading"
            :selected-status="selectedStatus"
            :current-page="currentPage"
            :page-size="pageSize"
            @select-run="handleSelectRun"
            @filter-status="handleFilterStatus"
            @page-change="handlePageChange"
            @refresh="() => fetchRuns()"
          />
        </section>
      </div>
    </main>

    <RunDetailModal
      :run="selectedRun"
      :events="runEvents"
      :open="modalOpen"
      :loading-events="loadingEvents"
      @close="modalOpen = false"
    />
  </div>
</template>

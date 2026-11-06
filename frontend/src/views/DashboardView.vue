<script setup lang="ts">
import { api } from "@/api/client";
import BotLauncher from "@/components/BotLauncher.vue";
import RunDetailModal from "@/components/RunDetailModal.vue";
import RunHistoryTable from "@/components/RunHistoryTable.vue";
import type { Bot, Run } from "@/types";
import { onMounted, ref } from "vue";

const bots = ref<Bot[]>([]);
const runs = ref<Run[]>([]);
const totalRuns = ref(0);
const loading = ref(false);
const selectedRun = ref<Run | null>(null);
const modalOpen = ref(false);

onMounted(async () => {
  try {
    bots.value = await api.getBots();
    const res = await api.getRuns(10, 0);
    runs.value = res.items;
    totalRuns.value = res.total;
  } catch (err) {
    console.error("Failed to load initial data", err);
  }
});
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
    <header class="flex items-center justify-between pb-6 border-b border-slate-200">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Browser Bot Platform</h1>
        <p class="text-sm text-slate-500 mt-1">
          Automate, monitor, and inspect browser runs in real time.
        </p>
      </div>
      <a
        href="http://localhost:7900/?autoconnect=1"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-flex items-center px-4 py-2 text-sm font-medium rounded-md text-brand-700 bg-brand-50 hover:bg-brand-100 border border-brand-200 transition-colors"
      >
        View noVNC Screen (Port 7900)
      </a>
    </header>

    <main class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <section class="lg:col-span-1">
        <BotLauncher :bots="bots" :loading="loading" />
      </section>
      <section class="lg:col-span-2">
        <RunHistoryTable
          :runs="runs"
          :total="totalRuns"
          :loading="loading"
          @select-run="(r) => { selectedRun = r; modalOpen = true; }"
        />
      </section>
    </main>

    <RunDetailModal
      :run="selectedRun"
      :events="[]"
      :open="modalOpen"
      @close="modalOpen = false"
    />
  </div>
</template>

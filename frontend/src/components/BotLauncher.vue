<script setup lang="ts">
import type { Bot, BrowserMode } from "@/types";
import { ref, watch } from "vue";

const props = defineProps<{
  bots: Bot[];
  loading: boolean;
}>();

const emit =
  defineEmits<(e: "launch", payload: { bot_id: string; browser_mode: BrowserMode }) => void>();

const selectedBot = ref<string>("");
const browserMode = ref<BrowserMode>("headful");
const launchError = ref<string | null>(null);

watch(
  () => props.bots,
  (newBots) => {
    if (newBots.length > 0 && !selectedBot.value) {
      selectedBot.value = newBots[0].bot_id;
    }
  },
  { immediate: true },
);

function handleSubmit() {
  launchError.value = null;
  if (!selectedBot.value) {
    launchError.value = "Please select a bot to execute.";
    return;
  }
  emit("launch", {
    bot_id: selectedBot.value,
    browser_mode: browserMode.value,
  });
}
</script>

<template>
  <div class="bg-white rounded-lg border border-slate-200 p-6 shadow-sm">
    <div class="flex items-center justify-between pb-4 mb-5 border-b border-slate-100">
      <h2 class="text-base font-semibold text-slate-900 tracking-tight">Launch Bot</h2>
      <span class="text-xs font-medium text-slate-500 uppercase tracking-wider">Configure Run</span>
    </div>

    <form @submit.prevent="handleSubmit" class="space-y-5">
      <div>
        <label for="bot-select" class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-2">
          Select Bot
        </label>
        <div v-if="bots.length === 0" class="text-xs text-slate-400 py-2">
          Loading available bots...
        </div>
        <select
          v-else
          id="bot-select"
          v-model="selectedBot"
          :disabled="loading"
          class="w-full px-3.5 py-2.5 text-sm bg-white border border-slate-300 rounded-md text-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-900/10 focus:border-slate-800 disabled:bg-slate-50 disabled:text-slate-400 transition"
        >
          <option v-for="b in bots" :key="b.bot_id" :value="b.bot_id">
            {{ b.name }} ({{ b.bot_id }})
          </option>
        </select>
      </div>

      <div>
        <span class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-2">
          Browser Mode
        </span>
        <div class="grid grid-cols-2 gap-3">
          <label
            :class="[
              'cursor-pointer border rounded-md p-3 flex flex-col justify-between transition-all select-none',
              browserMode === 'headful'
                ? 'border-slate-800 bg-slate-900/5 text-slate-900 shadow-sm'
                : 'border-slate-200 hover:border-slate-300 text-slate-600 bg-white'
            ]"
          >
            <input
              type="radio"
              v-model="browserMode"
              value="headful"
              class="sr-only"
            />
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm font-medium">Headful</span>
              <span
                :class="[
                  'w-2 h-2 rounded-full',
                  browserMode === 'headful' ? 'bg-emerald-500' : 'bg-slate-300'
                ]"
              />
            </div>
            <span class="text-xs text-slate-500 leading-snug">
              Live virtual display via noVNC (Port 7900)
            </span>
          </label>

          <label
            :class="[
              'cursor-pointer border rounded-md p-3 flex flex-col justify-between transition-all select-none',
              browserMode === 'headless'
                ? 'border-slate-800 bg-slate-900/5 text-slate-900 shadow-sm'
                : 'border-slate-200 hover:border-slate-300 text-slate-600 bg-white'
            ]"
          >
            <input
              type="radio"
              v-model="browserMode"
              value="headless"
              class="sr-only"
            />
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm font-medium">Headless</span>
              <span
                :class="[
                  'w-2 h-2 rounded-full',
                  browserMode === 'headless' ? 'bg-emerald-500' : 'bg-slate-300'
                ]"
              />
            </div>
            <span class="text-xs text-slate-500 leading-snug">
              Silent background container automation
            </span>
          </label>
        </div>
      </div>

      <div v-if="launchError" class="p-3 bg-rose-50 border border-rose-200 rounded text-xs text-rose-700">
        {{ launchError }}
      </div>

      <button
        type="submit"
        :disabled="loading || bots.length === 0"
        class="w-full inline-flex items-center justify-center px-4 py-2.5 bg-slate-900 hover:bg-slate-800 active:bg-black text-white text-sm font-medium rounded-md shadow-sm transition disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-900"
      >
        <svg
          v-if="loading"
          class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        <span>{{ loading ? "Queueing Run..." : "Trigger Run" }}</span>
      </button>
    </form>
  </div>
</template>

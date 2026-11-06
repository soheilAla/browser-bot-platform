<script setup lang="ts">
import type { Bot, BrowserMode } from "@/types";

defineProps<{
  bots: Bot[];
  loading: boolean;
}>();

defineEmits<(e: "launch", payload: { bot_id: string; browser_mode: BrowserMode }) => void>();
</script>

<template>
  <div class="bg-white rounded-lg border border-slate-200 p-6 shadow-sm">
    <h2 class="text-lg font-semibold text-slate-800 mb-4">Launch Bot</h2>
    <!-- Form implementation will follow in UI milestone -->
    <div class="text-sm text-slate-500">
      Bot selector and browser mode controls placeholder.
    </div>
  </div>
</template>

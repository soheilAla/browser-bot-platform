<script setup lang="ts">
import type { Run } from "@/types";

defineProps<{
  runs: Run[];
  total: number;
  loading: boolean;
}>();

defineEmits<(e: "select-run", run: Run) => void>();
</script>

<template>
  <div class="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm">
    <div class="px-6 py-4 border-b border-slate-200">
      <h2 class="text-lg font-semibold text-slate-800">Run History</h2>
    </div>
    <!-- Run history table implementation will follow in UI milestone -->
    <div class="p-6 text-sm text-slate-500">
      Run history table placeholder.
    </div>
  </div>
</template>

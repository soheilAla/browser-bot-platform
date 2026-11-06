<script setup lang="ts">
import type { Run, RunEvent } from "@/types";

defineProps<{
  run: Run | null;
  events: RunEvent[];
  open: boolean;
}>();

defineEmits<(e: "close") => void>();
</script>

<template>
  <div v-if="open && run" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40">
    <div class="bg-white rounded-lg max-w-2xl w-full p-6 shadow-xl border border-slate-200">
      <h3 class="text-lg font-semibold text-slate-800">Run Details</h3>
      <div class="mt-4 text-sm text-slate-500">
        Run metadata and timeline events placeholder.
      </div>
    </div>
  </div>
</template>

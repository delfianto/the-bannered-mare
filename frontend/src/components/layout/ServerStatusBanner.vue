<script setup lang="ts">
import { watch, onBeforeUnmount } from "vue";
import { useServerStatus } from "@/composables/useServerStatus";

const { reachable, checking, checkNow } = useServerStatus();

// While the backend is unreachable, poll so the banner clears itself once it's
// back — no manual retry needed if the server comes up on its own.
let pollTimer: ReturnType<typeof setInterval> | null = null;
watch(reachable, (ok) => {
  if (!ok && pollTimer === null) {
    pollTimer = setInterval(() => void checkNow(), 5000);
  } else if (ok && pollTimer !== null) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
});

onBeforeUnmount(() => {
  if (pollTimer !== null) clearInterval(pollTimer);
});
</script>

<template>
  <div
    v-if="!reachable"
    role="alert"
    class="flex shrink-0 items-center justify-center gap-3 bg-error px-4 py-2 text-sm font-medium text-error-content"
  >
    <AppIcon name="i-lucide-server" class="size-4 shrink-0" />
    <span>{{ $t("common.serverUnreachable") }}</span>
    <button
      class="inline-flex items-center gap-1.5 rounded-md border border-error-content/30 px-2 py-0.5 text-xs transition-colors hover:bg-error-content/10 disabled:opacity-50"
      :disabled="checking"
      @click="checkNow"
    >
      <AppIcon name="i-lucide-refresh-cw" class="size-3.5" :class="{ 'animate-spin': checking }" />
      {{ $t("common.retry") }}
    </button>
  </div>
</template>

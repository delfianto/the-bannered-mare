<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  page: number;
  totalPages: number;
}>();

const emit = defineEmits<{
  "update:page": [page: number];
}>();

// Windowed page list: first + last + neighbours of the current page, with
// "…" markers standing in for the collapsed gaps. e.g. 1 … 3 4 5 … 9
const pages = computed<(number | "…")[]>(() => {
  const total = props.totalPages;
  const current = props.page;
  const delta = 1;

  const range: number[] = [];
  for (let i = Math.max(1, current - delta); i <= Math.min(total, current + delta); i++) {
    range.push(i);
  }

  const result: (number | "…")[] = [];
  if (range[0] > 1) {
    result.push(1);
    if (range[0] > 2) result.push("…");
  }
  result.push(...range);
  const last = range[range.length - 1];
  if (last < total) {
    if (last < total - 1) result.push("…");
    result.push(total);
  }
  return result;
});

function go(p: number) {
  if (p < 1 || p > props.totalPages || p === props.page) return;
  emit("update:page", p);
}
</script>

<template>
  <div class="flex items-center justify-between gap-2">
    <span class="text-xs text-muted-foreground">Page {{ page }} of {{ totalPages }}</span>

    <div class="flex items-center gap-1">
      <button
        class="flex size-8 items-center justify-center rounded-lg border text-muted-foreground transition-colors hover:bg-accent disabled:pointer-events-none disabled:opacity-40"
        :disabled="page <= 1"
        aria-label="Previous page"
        @click="go(page - 1)"
      >
        <UIcon name="i-lucide-chevron-left" class="size-4" />
      </button>

      <template v-for="(p, i) in pages" :key="i">
        <span v-if="p === '…'" class="px-1 text-xs text-muted-foreground/60">…</span>
        <button
          v-else
          class="flex h-8 min-w-8 items-center justify-center rounded-lg border px-2 text-xs font-medium transition-colors"
          :class="
            p === page
              ? 'border-primary/40 bg-primary/10 text-primary'
              : 'text-muted-foreground hover:bg-accent'
          "
          :aria-current="p === page ? 'page' : undefined"
          @click="go(p as number)"
        >
          {{ p }}
        </button>
      </template>

      <button
        class="flex size-8 items-center justify-center rounded-lg border text-muted-foreground transition-colors hover:bg-accent disabled:pointer-events-none disabled:opacity-40"
        :disabled="page >= totalPages"
        aria-label="Next page"
        @click="go(page + 1)"
      >
        <UIcon name="i-lucide-chevron-right" class="size-4" />
      </button>
    </div>
  </div>
</template>

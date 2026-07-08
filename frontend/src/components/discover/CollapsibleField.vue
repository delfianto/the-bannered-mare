<script setup lang="ts">
import { ref, computed } from "vue";

const props = withDefaults(
  defineProps<{
    label: string;
    content: string;
    // System prompt override reads better in a monospaced face.
    mono?: boolean;
    defaultOpen?: boolean;
  }>(),
  { mono: false, defaultOpen: false },
);

const open = ref(props.defaultOpen);

// Imported cards routinely dump a whole character sheet into one field
// (the stepsister card's description is ~19k chars), so surface the size and a
// one-line teaser while collapsed and keep the expanded body scrollable.
const charCount = computed(() => {
  const n = props.content.length;
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
});

const teaser = computed(() => props.content.replace(/\s+/g, " ").trim().slice(0, 100));
</script>

<template>
  <div class="overflow-hidden rounded-lg border border-border/50 bg-base-100/40">
    <button
      class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-base-300/40"
      @click="open = !open"
    >
      <div class="flex min-w-0 items-center gap-2.5">
        <h3
          class="shrink-0 font-cinzel text-xs font-semibold tracking-widest text-muted-foreground uppercase"
        >
          {{ label }}
        </h3>
        <span v-if="!open" class="truncate text-xs text-muted-foreground/50">{{ teaser }}</span>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        <span class="text-[10px] tabular-nums text-muted-foreground/40">{{ charCount }}</span>
        <AppIcon
          name="i-lucide-chevron-down"
          class="size-4 text-muted-foreground transition-transform"
          :class="{ 'rotate-180': open }"
        />
      </div>
    </button>

    <div v-if="open" class="border-t border-border/40 px-4 py-3">
      <div class="max-h-80 overflow-y-auto pr-1">
        <p
          class="text-sm leading-relaxed whitespace-pre-wrap text-foreground"
          :class="mono ? 'font-mono text-[13px]' : ''"
        >
          {{ content }}
        </p>
      </div>
    </div>
  </div>
</template>

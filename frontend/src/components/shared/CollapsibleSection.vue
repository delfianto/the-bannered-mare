<script setup lang="ts">
import { ref } from "vue";

const props = withDefaults(
  defineProps<{
    title: string;
    defaultOpen?: boolean;
    icon?: string;
  }>(),
  { defaultOpen: false },
);

const emit = defineEmits<{
  toggle: [open: boolean];
}>();

const open = ref(props.defaultOpen);

function toggle() {
  open.value = !open.value;
  emit("toggle", open.value);
}
</script>

<template>
  <div class="overflow-hidden rounded-lg border border-border/50 bg-base-100/40">
    <button
      class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-base-300/40"
      @click="toggle"
    >
      <div class="flex min-w-0 items-center gap-2.5">
        <AppIcon v-if="icon" :name="icon" class="size-4 shrink-0 text-muted-foreground" />
        <h3
          class="truncate font-cinzel text-xs font-semibold tracking-widest text-muted-foreground uppercase"
        >
          {{ title }}
        </h3>
        <slot name="badge" />
      </div>
      <AppIcon
        name="i-lucide-chevron-down"
        class="size-4 shrink-0 text-muted-foreground transition-transform"
        :class="{ 'rotate-180': open }"
      />
    </button>

    <div v-if="open" class="border-t border-border/40 px-4 py-3">
      <slot />
    </div>
  </div>
</template>

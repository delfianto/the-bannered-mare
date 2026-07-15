<script setup lang="ts">
import type { LoreEntryResponse } from "@/composables/useLorebooks";

defineProps<{
  entry: LoreEntryResponse;
  pendingDelete?: boolean;
}>();

defineEmits<{
  edit: [];
  delete: [];
  toggleEnabled: [];
}>();

const positionLabels: Record<string, string> = {
  before_character: "Before character",
  after_character: "After character",
  at_depth: "At depth",
  before_examples: "Before examples",
};
</script>

<template>
  <div
    class="group relative flex flex-col app-card transition-all hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
    :class="{ 'opacity-60': !entry.enabled }"
  >
    <!-- Header: name + enabled toggle -->
    <div class="mb-2 flex items-start justify-between gap-2">
      <h4 class="font-cinzel text-sm font-semibold tracking-wide text-foreground">
        {{ entry.name }}
      </h4>
      <AppToggle
        class="shrink-0"
        :model-value="entry.enabled"
        :title="entry.enabled ? $t('lorebooks.enabled') : $t('lorebooks.disabled')"
        :aria-label="entry.enabled ? $t('lorebooks.enabled') : $t('lorebooks.disabled')"
        @change="$emit('toggleEnabled')"
      />
    </div>

    <!-- Trigger keywords -->
    <div v-if="entry.keys?.length" class="mb-2 flex flex-wrap gap-1">
      <span
        v-for="k in entry.keys ?? []"
        :key="k"
        class="rounded-full bg-base-300 px-2 py-0.5 text-3xs font-medium text-muted-foreground"
      >
        {{ k }}
      </span>
    </div>

    <!-- Content preview -->
    <p class="mb-3 line-clamp-3 text-xs leading-relaxed text-muted-foreground">
      {{ entry.content }}
    </p>

    <div class="flex-1" />

    <!-- Footer: meta + hover actions -->
    <div class="flex items-center justify-between border-t border-border/30 pt-2.5">
      <div class="flex items-center gap-3 text-3xs text-muted-foreground">
        <span class="flex items-center gap-1">
          <AppIcon name="i-lucide-map-pin" class="size-3" />
          {{ positionLabels[entry.position] ?? entry.position }}
        </span>
        <span class="flex items-center gap-1">
          <AppIcon name="i-lucide-arrow-up-down" class="size-3" />
          {{ $t("lorebooks.order") }} {{ entry.order }}
        </span>
        <span v-if="entry.constant" class="flex items-center gap-1 text-primary">
          <AppIcon name="i-lucide-pin" class="size-3" />
          {{ $t("lorebooks.constant") }}
        </span>
      </div>
      <div
        class="flex items-center gap-2 text-3xs text-muted-foreground/0 transition-colors group-hover:text-muted-foreground/60"
      >
        <button class="flex items-center gap-1 hover:text-foreground" @click="$emit('edit')">
          <AppIcon name="i-lucide-pencil" class="size-3" />
          {{ $t("common.edit") }}
        </button>
        <button
          class="flex items-center gap-1"
          :class="pendingDelete ? 'text-error!' : 'hover:text-error'"
          @click="$emit('delete')"
        >
          <AppIcon name="i-lucide-trash-2" class="size-3" />
          {{ pendingDelete ? $t("lorebooks.confirmDelete") : $t("common.delete") }}
        </button>
      </div>
    </div>
  </div>
</template>

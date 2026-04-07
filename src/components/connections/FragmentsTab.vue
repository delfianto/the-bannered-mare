<script setup lang="ts">
import { usePromptFragments } from "@/composables/usePromptFragments";
import type { PromptFragment } from "@/composables/usePromptFragments";

const { fragments, loading, error, refresh } = usePromptFragments();

function onCardClick(fragment: PromptFragment) {
  console.log("Fragment clicked:", fragment.id, fragment.name);
}

function typeBadgeClass(type: string): string {
  switch (type) {
    case "nsfw":
      return "bg-red-500/15 text-red-400";
    case "instruction":
      return "bg-blue-500/15 text-blue-400";
    case "system":
      return "bg-purple-500/15 text-purple-400";
    default:
      return "bg-accent text-foreground";
  }
}
</script>

<template>
  <div>
    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <UIcon name="i-lucide-loader-2" class="h-6 w-6 animate-spin text-primary" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-20">
      <UIcon name="i-lucide-alert-circle" class="h-8 w-8 text-destructive" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border border-border px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent"
        @click="refresh"
      >
        Retry
      </button>
    </div>

    <!-- Grid -->
    <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="(fragment, index) in fragments"
        :key="fragment.id"
        class="group relative flex animate-fade-in-up cursor-pointer flex-col rounded-xl border border-[var(--border)] bg-card/50 p-4 pb-8 transition-all hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
        :style="{ animationDelay: `${index * 30}ms` }"
        @click="onCardClick(fragment)"
      >
        <!-- Header -->
        <div class="mb-2 flex items-start justify-between gap-2">
          <div class="min-w-0">
            <h3 class="font-cinzel text-sm font-semibold tracking-wide text-foreground">
              {{ fragment.name }}
            </h3>
          </div>
          <span
            class="shrink-0 rounded-full px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide"
            :class="typeBadgeClass(fragment.fragment_type)"
          >
            {{ fragment.fragment_type }}
          </span>
        </div>

        <!-- Description -->
        <p
          v-if="fragment.description"
          class="mb-3 line-clamp-2 text-xs leading-relaxed text-muted-foreground"
        >
          {{ fragment.description }}
        </p>

        <!-- Spacer -->
        <div class="flex-1" />

        <!-- Details -->
        <div class="space-y-1.5 border-t border-border/30 pt-3 text-[11px] text-muted-foreground">
          <div class="flex items-center gap-1.5">
            <UIcon name="i-lucide-globe" class="h-3 w-3 shrink-0" />
            <span v-if="fragment.is_global" class="text-emerald-500">Global</span>
            <span v-else class="text-muted-foreground">Local</span>
          </div>
          <div class="flex items-center gap-1.5">
            <UIcon name="i-lucide-clock" class="h-3 w-3 shrink-0" />
            <span>{{ new Date(fragment.updated_at).toLocaleDateString() }}</span>
          </div>
        </div>

        <!-- Edit hint -->
        <div class="absolute bottom-3 right-3 flex items-center gap-1 text-[10px] text-muted-foreground/0 transition-colors group-hover:text-muted-foreground/60">
          <UIcon name="i-lucide-pencil" class="h-3 w-3" />
          Edit
        </div>
      </div>
    </div>
  </div>
</template>

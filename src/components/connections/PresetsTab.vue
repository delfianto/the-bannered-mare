<script setup lang="ts">
import { ref } from "vue";
import { usePresets } from "@/composables/usePresets";
import type { Preset } from "@/composables/usePresets";
import ImportPresetModal from "./ImportPresetModal.vue";

const { presets, loading, error, refresh } = usePresets();
const showImport = ref(false);

function parameterCount(preset: Preset): number {
  return preset.parameters ? Object.keys(preset.parameters).length : 0;
}

function onImported() {
  refresh();
}
</script>

<template>
  <div>
    <div class="mb-4 flex justify-end">
      <button
        class="flex items-center gap-2 rounded-lg border bg-card px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
        @click="showImport = true"
      >
        <UIcon name="i-lucide-upload" class="h-4 w-4" />
        {{ $t('presetImport.button') }}
      </button>
    </div>

    <ImportPresetModal v-if="showImport" @close="showImport = false" @imported="onImported" />

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <UIcon name="i-lucide-loader-2" class="h-6 w-6 animate-spin text-primary" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-20">
      <UIcon name="i-lucide-alert-circle" class="h-8 w-8 text-destructive" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent"
        @click="refresh"
      >
        {{ $t('common.retry') }}
      </button>
    </div>

    <!-- Grid -->
    <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <RouterLink
        v-for="(preset, index) in presets"
        :key="preset.id"
        :to="`/settings/presets/${preset.id}`"
        class="group relative flex animate-fade-in-up cursor-pointer flex-col rounded-xl border bg-card/50 p-4 pb-8 transition-all hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
        :style="{ animationDelay: `${index * 30}ms` }"
      >
        <!-- Header -->
        <div class="mb-2 flex items-start justify-between gap-2">
          <div class="min-w-0">
            <h3 class="font-cinzel text-sm font-semibold tracking-wide text-foreground">
              {{ preset.name }}
            </h3>
          </div>
          <span
            v-if="preset.is_default"
            class="shrink-0 rounded-full bg-accent px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide text-foreground"
          >
            Default
          </span>
        </div>

        <!-- Description -->
        <p
          v-if="preset.description"
          class="mb-3 line-clamp-2 text-xs leading-relaxed text-muted-foreground"
        >
          {{ preset.description }}
        </p>

        <!-- Spacer -->
        <div class="flex-1" />

        <!-- Details -->
        <div class="space-y-1.5 border-t border-border/30 pt-3 text-[11px] text-muted-foreground">
          <div class="flex items-center gap-1.5">
            <UIcon name="i-lucide-sliders-horizontal" class="h-3 w-3 shrink-0" />
            <span>{{ parameterCount(preset) }} parameter{{ parameterCount(preset) !== 1 ? "s" : "" }}</span>
          </div>
          <div class="flex items-center gap-1.5">
            <UIcon name="i-lucide-clock" class="h-3 w-3 shrink-0" />
            <span>{{ new Date(preset.updated_at).toLocaleDateString() }}</span>
          </div>
        </div>

        <!-- Edit hint -->
        <div class="absolute bottom-3 right-3 flex items-center gap-1 text-[10px] text-muted-foreground/0 transition-colors group-hover:text-muted-foreground/60">
          <UIcon name="i-lucide-pencil" class="h-3 w-3" />
          {{ $t('common.edit') }}
        </div>
      </RouterLink>
    </div>
  </div>
</template>

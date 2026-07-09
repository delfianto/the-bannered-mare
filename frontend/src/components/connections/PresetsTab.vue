<script setup lang="ts">
import { ref } from "vue";
import { usePresets } from "@/composables/usePresets";
import type { Preset } from "@/composables/usePresets";
import ImportPresetModal from "./ImportPresetModal.vue";
import EmptyState from "@/components/shared/EmptyState.vue";

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
    <!-- Primary action lives on the tab bar (see ProfilesTabs) -->
    <Teleport defer to="#loadout-tab-action">
      <button
        v-if="!loading && presets.length > 0"
        class="inline-flex items-center gap-1.5 rounded-lg border bg-base-200 px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-base-300"
        @click="showImport = true"
      >
        <AppIcon name="i-lucide-upload" class="size-4" />
        {{ $t("presetImport.button") }}
      </button>
    </Teleport>

    <ImportPresetModal v-if="showImport" @close="showImport = false" @imported="onImported" />

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <AppIcon name="i-lucide-loader-2" class="size-6 animate-spin text-primary" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-20">
      <AppIcon name="i-lucide-alert-circle" class="size-8 text-error" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border px-4 py-2 text-sm text-foreground transition-colors hover:bg-base-300"
        @click="refresh"
      >
        {{ $t("common.retry") }}
      </button>
    </div>

    <!-- Empty State -->
    <EmptyState
      v-else-if="presets.length === 0"
      icon="i-lucide-sliders-horizontal"
      title="No Presets Found"
      description="Import a parameter preset to easily configure generation settings."
      action-label="Import Preset"
      @action="showImport = true"
    />

    <!-- Grid -->
    <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <RouterLink
        v-for="(preset, index) in presets"
        :key="preset.id"
        :to="`/settings/presets/${preset.id}`"
        class="group relative flex animate-fade-in-up cursor-pointer flex-col rounded-xl border bg-base-200/50 p-4 pb-8 transition-all hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
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
            class="shrink-0 rounded-full bg-base-300 px-2 py-0.5 text-[0.5625rem] font-medium tracking-wide text-foreground uppercase"
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
        <div
          class="space-y-1.5 border-t border-border/30 pt-3 text-[0.6875rem] text-muted-foreground"
        >
          <div class="flex items-center gap-1.5">
            <AppIcon name="i-lucide-sliders-horizontal" class="size-3 shrink-0" />
            <span
              >{{ parameterCount(preset) }} parameter{{
                parameterCount(preset) !== 1 ? "s" : ""
              }}</span
            >
          </div>
          <div class="flex items-center gap-1.5">
            <AppIcon name="i-lucide-clock" class="size-3 shrink-0" />
            <span>{{ new Date(preset.updated_at).toLocaleDateString() }}</span>
          </div>
        </div>

        <!-- Edit hint -->
        <div
          class="absolute right-3 bottom-3 flex items-center gap-1 text-[0.625rem] text-muted-foreground/0 transition-colors group-hover:text-muted-foreground/60"
        >
          <AppIcon name="i-lucide-pencil" class="size-3" />
          {{ $t("common.edit") }}
        </div>
      </RouterLink>
    </div>
  </div>
</template>

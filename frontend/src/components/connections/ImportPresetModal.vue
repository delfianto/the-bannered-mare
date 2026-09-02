<script setup lang="ts">
import { ref } from "vue";
import { usePresetImport } from "@/composables/usePresetImport";
import type { STImportResult } from "@/composables/usePresetImport";

const emit = defineEmits<{
  close: [];
  imported: [result: STImportResult];
}>();

const { importing, result, error, importPreset, reset } = usePresetImport();

const fileInputRef = ref<HTMLInputElement | null>(null);
const dragging = ref(false);

function browse() {
  fileInputRef.value?.click();
}

async function handleFile(file: File) {
  const res = await importPreset(file);
  if (res) emit("imported", res);
}

function onFileSelected(e: Event) {
  const target = e.target as HTMLInputElement;
  const file = target.files?.[0];
  if (file) handleFile(file);
  if (target) target.value = "";
}

function onDrop(e: DragEvent) {
  dragging.value = false;
  const file = e.dataTransfer?.files?.[0];
  if (file) handleFile(file);
}

function importAnother() {
  reset();
}
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="emit('close')" />

    <div
      class="relative z-10 w-full max-w-lg animate-fade-in-up rounded-xl border bg-base-200 p-6 shadow-xl"
    >
      <div class="mb-4 flex items-center justify-between">
        <h2 class="font-story text-lg font-bold tracking-wide text-foreground">
          {{ $t("presetImport.title") }}
        </h2>
        <button
          class="flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
          :aria-label="$t('common.cancel')"
          @click="emit('close')"
        >
          <AppIcon name="i-lucide-x" class="size-5" />
        </button>
      </div>

      <input
        ref="fileInputRef"
        type="file"
        accept=".json"
        class="hidden"
        @change="onFileSelected"
      />

      <!-- Result -->
      <div v-if="result" class="space-y-4">
        <div class="rounded-lg border border-success/30 bg-success/10 p-4">
          <div class="mb-3 flex items-center gap-2 text-success">
            <AppIcon name="i-lucide-circle-check" class="size-5" />
            <span class="font-medium">{{ $t("presetImport.complete") }}</span>
          </div>
          <div class="space-y-2 text-sm">
            <div class="flex items-center gap-2">
              <AppIcon name="i-lucide-scroll-text" class="size-4 shrink-0 text-muted-foreground" />
              <span class="text-muted-foreground">{{ $t("presetImport.template") }}:</span>
              <span class="truncate text-foreground">{{ result.template_name }}</span>
            </div>
            <div v-if="result.fragment_ids?.length" class="flex items-center gap-2">
              <AppIcon name="i-lucide-puzzle" class="size-4 shrink-0 text-muted-foreground" />
              <span class="text-foreground">{{
                $t("presetImport.fragments", { count: result.fragment_ids.length })
              }}</span>
            </div>
            <div v-if="result.preset_name" class="flex items-center gap-2">
              <AppIcon
                name="i-lucide-sliders-horizontal"
                class="size-4 shrink-0 text-muted-foreground"
              />
              <span class="text-muted-foreground">{{ $t("presetImport.preset") }}:</span>
              <span class="truncate text-foreground">{{ result.preset_name }}</span>
            </div>
            <div v-if="result.profile_name" class="flex items-center gap-2">
              <AppIcon name="i-lucide-layers" class="size-4 shrink-0 text-muted-foreground" />
              <span class="text-muted-foreground">{{ $t("presetImport.profile") }}:</span>
              <span class="truncate text-foreground">{{ result.profile_name }}</span>
            </div>
          </div>
        </div>

        <div
          v-if="result.warnings?.length"
          class="rounded-lg border border-warning/30 bg-warning/10 p-3"
        >
          <div class="mb-1 flex items-center gap-2 text-sm font-medium text-warning">
            <AppIcon name="i-lucide-triangle-alert" class="size-4" />
            {{ $t("presetImport.warnings") }}
          </div>
          <ul class="ml-6 list-disc text-xs text-muted-foreground">
            <li v-for="(w, i) in result.warnings" :key="i">{{ w }}</li>
          </ul>
        </div>

        <div class="flex items-center gap-3">
          <button
            class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-content transition-colors hover:bg-primary/90"
            @click="emit('close')"
          >
            {{ $t("presetImport.done") }}
          </button>
          <button
            class="rounded-lg border px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
            @click="importAnother"
          >
            {{ $t("presetImport.importAnother") }}
          </button>
        </div>
      </div>

      <!-- Upload -->
      <div v-else>
        <button
          type="button"
          class="flex w-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors"
          :class="
            dragging
              ? 'border-primary bg-primary/5'
              : 'border-border hover:border-primary/40 hover:bg-base-300/30'
          "
          :disabled="importing"
          @click="browse"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="onDrop"
        >
          <AppIcon
            v-if="importing"
            name="i-lucide-loader-2"
            class="size-8 animate-spin text-primary"
          />
          <AppIcon v-else name="i-lucide-upload" class="size-8 text-muted-foreground" />
          <div>
            <p class="text-sm font-medium text-foreground">
              {{ importing ? $t("presetImport.importing") : $t("presetImport.dropzone") }}
            </p>
            <p class="mt-1 text-xs text-muted-foreground">{{ $t("presetImport.dropzoneHint") }}</p>
          </div>
        </button>
        <p v-if="error" class="mt-3 text-sm text-error">{{ $t("presetImport.failed") }}</p>
      </div>
    </div>
  </div>
</template>

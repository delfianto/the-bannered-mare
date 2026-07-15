<script setup lang="ts">
import { computed, ref } from "vue";
import type { CharacterData } from "@/types/creator";
import NarrativeText from "@/components/chat/NarrativeText.vue";
import Modal from "@/components/shared/Modal.vue";

const props = defineProps<{
  data: CharacterData;
  completeness: { filled: number; total: number };
}>();

// The preview card doubles as the portrait uploader on wide screens (the
// standalone form uploader only appears when this panel is hidden), so the
// image you see is the image you drop onto.
const emit = defineEmits<{
  change: [file: File];
}>();

const dragOver = ref(false);
const inputRef = ref<HTMLInputElement | null>(null);

function handleFile(file: File) {
  if (!file.type.startsWith("image/")) return;
  emit("change", file);
}

function onDrop(e: DragEvent) {
  e.preventDefault();
  dragOver.value = false;
  const file = e.dataTransfer?.files[0];
  if (file) handleFile(file);
}

function onChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (file) handleFile(file);
}

const pct = computed(() =>
  props.completeness.total > 0 ? (props.completeness.filled / props.completeness.total) * 100 : 0,
);

const circumference = 2 * Math.PI * 18;
const offset = computed(() => circumference - (pct.value / 100) * circumference);

const greetingExpanded = ref(false);
// Roughly the number of characters that fills the capped preview height; beyond
// this we fade the bottom to hint there's more (and the expand button opens it).
const greetingOverflows = computed(() => (props.data.greeting?.length || 0) > 260);
</script>

<template>
  <div class="space-y-4">
    <!-- Character portrait — a clean contained thumbnail matching the detail
         view (no scrim / text overlay), that also doubles as the portrait
         dropzone (click or drag an image). -->
    <div
      class="group relative aspect-3/4 max-w-90 cursor-pointer overflow-hidden rounded-xl border bg-base-200/50 transition-all"
      :class="dragOver ? 'ring-2 ring-primary' : ''"
      @click="inputRef?.click()"
      @dragover.prevent="dragOver = true"
      @dragleave="dragOver = false"
      @drop="onDrop"
    >
      <img
        v-if="data.avatarUrl"
        :src="data.avatarUrl"
        :alt="data.name"
        class="absolute inset-0 size-full object-cover object-top"
      />

      <!-- Empty state -->
      <div
        v-else
        class="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-base-300"
        :class="dragOver ? 'text-primary' : 'text-muted-foreground/50'"
      >
        <AppIcon name="i-lucide-image-plus" class="size-8" />
        <span class="text-2xs font-medium">Drop image or click</span>
      </div>

      <!-- Hover affordance when a portrait exists -->
      <div
        v-if="data.avatarUrl"
        class="absolute inset-0 flex items-center justify-center bg-black/0 transition-colors group-hover:bg-black/40"
      >
        <div
          class="flex flex-col items-center gap-1.5 opacity-0 transition-opacity group-hover:opacity-100"
        >
          <AppIcon name="i-lucide-camera" class="size-6 text-white" />
          <span class="text-xs font-medium text-white">Change portrait</span>
        </div>
      </div>

      <input ref="inputRef" type="file" accept="image/*" class="hidden" @change="onChange" />
    </div>

    <!-- Greeting Preview — height-capped so the panel never needs to scroll;
         the expand button opens the full greeting in a modal. -->
    <div class="space-y-2 rounded-xl border bg-base-200 p-4">
      <div class="flex items-center justify-between">
        <div
          class="flex items-center gap-1.5 text-3xs font-semibold tracking-widest text-muted-foreground uppercase"
        >
          <AppIcon name="i-lucide-message-circle" class="size-3" />
          {{ $t("characters.form.greeting") }}
        </div>
        <button
          v-if="data.greeting"
          type="button"
          class="flex size-6 items-center justify-center rounded-md text-muted-foreground/60 transition-colors hover:bg-base-300 hover:text-foreground"
          :aria-label="$t('characters.form.greeting')"
          @click="greetingExpanded = true"
        >
          <AppIcon name="i-lucide-maximize-2" class="size-3" />
        </button>
      </div>
      <div v-if="data.greeting" class="relative max-h-40 overflow-hidden">
        <NarrativeText :content="data.greeting" />
        <div
          v-if="greetingOverflows"
          class="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-linear-to-t from-base-200 to-transparent"
        />
      </div>
      <span v-else class="text-xs text-muted-foreground italic">No greeting set yet...</span>
    </div>

    <!-- Completeness -->
    <div class="rounded-xl border bg-base-200 p-4">
      <p class="mb-2 text-3xs font-semibold tracking-widest text-muted-foreground uppercase">
        {{ $t("characters.form.completeness") }}
      </p>
      <div class="flex items-center gap-3">
        <svg width="44" height="44" class="shrink-0 -rotate-90">
          <circle cx="22" cy="22" r="18" fill="none" stroke="var(--border)" stroke-width="3" />
          <circle
            cx="22"
            cy="22"
            r="18"
            fill="none"
            stroke="var(--primary)"
            stroke-width="3"
            stroke-linecap="round"
            :stroke-dasharray="circumference"
            :stroke-dashoffset="offset"
            class="transition-all duration-500 ease-out"
          />
        </svg>
        <div>
          <p class="text-sm font-medium text-foreground">
            {{ completeness.filled }} / {{ completeness.total }}
          </p>
          <p class="text-2xs text-muted-foreground">
            <span v-if="pct >= 100" class="flex items-center gap-1 text-primary">
              <AppIcon name="i-lucide-check" class="size-3" /> Character complete
            </span>
            <span v-else-if="pct >= 50">Looking good — keep going!</span>
            <span v-else>Fill in more details</span>
          </p>
        </div>
      </div>
    </div>

    <!-- Full greeting preview — greetings are short, so a modest modal is plenty. -->
    <Modal
      :show="greetingExpanded"
      :title="$t('characters.form.greeting')"
      max-width="xl"
      @close="greetingExpanded = false"
    >
      <div class="max-h-[60vh] overflow-y-auto text-foreground">
        <NarrativeText :content="data.greeting" />
      </div>
    </Modal>
  </div>
</template>

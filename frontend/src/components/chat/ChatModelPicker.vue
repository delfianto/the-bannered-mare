<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";

interface PickerModel {
  id: string;
  display_name: string;
}

const props = defineProps<{
  models: PickerModel[];
  currentModelId?: string | null;
  currentModelName?: string | null;
}>();

const emit = defineEmits<{
  change: [modelId: string];
}>();

const open = ref(false);
const rootRef = ref<HTMLElement | null>(null);

function toggle() {
  open.value = !open.value;
}

function choose(m: PickerModel) {
  open.value = false;
  // Overrides this chat's snapshot only; re-selecting the current model is a no-op.
  if (m.id !== props.currentModelId) emit("change", m.id);
}

function onClickOutside(e: MouseEvent) {
  if (rootRef.value && !rootRef.value.contains(e.target as Node)) open.value = false;
}

onMounted(() => document.addEventListener("click", onClickOutside, true));
onUnmounted(() => document.removeEventListener("click", onClickOutside, true));
</script>

<template>
  <div ref="rootRef" class="relative">
    <button
      class="flex h-9 items-center gap-1.5 rounded-lg border bg-base-300/40 px-3 text-xs text-muted-foreground transition-colors hover:text-foreground"
      :title="$t('chat.model.change')"
      @click="toggle"
    >
      <AppIcon name="i-lucide-cpu" class="size-3.5 shrink-0" />
      <span class="max-w-30 truncate">{{ currentModelName || $t("chat.model.none") }}</span>
      <AppIcon name="i-lucide-chevron-down" class="size-3.5 shrink-0" />
    </button>

    <div
      v-if="open"
      class="absolute top-full right-0 z-20 mt-1 w-64 rounded-lg border bg-base-200 py-1 shadow-lg"
    >
      <div
        class="px-3 py-1.5 text-[0.625rem] font-semibold tracking-wider text-muted-foreground uppercase"
      >
        {{ $t("chat.model.title") }}
      </div>

      <div class="max-h-64 overflow-y-auto">
        <button
          v-for="m in models"
          :key="m.id"
          class="flex w-full items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-base-300/50"
          @click="choose(m)"
        >
          <AppIcon
            name="i-lucide-check"
            class="size-3.5 shrink-0"
            :class="m.id === currentModelId ? 'text-primary' : 'text-transparent'"
          />
          <span class="block min-w-0 truncate font-cinzel text-sm text-foreground">
            {{ m.display_name }}
          </span>
        </button>
      </div>

      <div v-if="models.length === 0" class="p-3 text-center text-xs text-muted-foreground">
        {{ $t("chat.model.empty") }}
      </div>

      <div class="my-1 h-px bg-border" />

      <p class="px-3 py-1.5 text-[0.625rem] leading-snug text-muted-foreground/70">
        {{ $t("chat.model.overrideHint") }}
      </p>
    </div>
  </div>
</template>

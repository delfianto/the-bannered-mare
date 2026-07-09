<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from "vue";
import Modal from "@/components/shared/Modal.vue";

const props = withDefaults(
  defineProps<{
    modelValue: string;
    placeholder?: string;
    /** Collapsed height, in rows. */
    minRows?: number;
    /** Inline max-height (in vh) before the field starts scrolling. */
    maxVh?: number;
    /** Title for the expand-to-focus editor. */
    label?: string;
    /** Show the expand-to-fullscreen button. */
    expandable?: boolean;
  }>(),
  {
    minRows: 3,
    maxVh: 45,
    expandable: true,
  },
);

const emit = defineEmits<{ "update:modelValue": [value: string] }>();

const taRef = ref<HTMLTextAreaElement | null>(null);
const expanded = ref(false);

// Grow with content so short notes stay compact and long ones get a real
// editing viewport (no fighting a tiny fixed scrollbar); cap at maxVh, then
// scroll. The expand button opens a focused editor for very long fields.
function autosize() {
  const el = taRef.value;
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${el.scrollHeight}px`;
}

function onInput(e: Event) {
  emit("update:modelValue", (e.target as HTMLTextAreaElement).value);
  autosize();
}

watch(
  () => props.modelValue,
  () => nextTick(autosize),
);
onMounted(() => nextTick(autosize));
</script>

<template>
  <div class="relative">
    <textarea
      ref="taRef"
      :value="modelValue"
      :placeholder="placeholder"
      :rows="minRows"
      class="w-full resize-none overflow-y-auto rounded-lg border bg-base-300/40 px-4 py-3 pr-10 text-sm leading-relaxed text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
      :style="{ maxHeight: `${maxVh}vh` }"
      @input="onInput"
    />
    <button
      v-if="expandable"
      type="button"
      class="absolute top-2 right-2 flex size-7 items-center justify-center rounded-md text-muted-foreground/60 transition-colors hover:bg-base-300 hover:text-foreground"
      :aria-label="`Expand ${label || 'editor'}`"
      @click="expanded = true"
    >
      <AppIcon name="i-lucide-maximize-2" class="size-3.5" />
    </button>

    <Modal :show="expanded" :title="label" max-width="3xl" @close="expanded = false">
      <textarea
        :value="modelValue"
        :placeholder="placeholder"
        class="h-[70vh] w-full resize-none rounded-lg border bg-base-300/40 px-4 py-3 text-sm leading-relaxed text-foreground outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
        @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
      ></textarea>
      <template #footer>
        <button
          type="button"
          class="flex h-9 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-content transition-colors hover:bg-primary/90"
          @click="expanded = false"
        >
          {{ $t("common.done") }}
        </button>
      </template>
    </Modal>
  </div>
</template>

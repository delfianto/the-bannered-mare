<script setup lang="ts">
import { ref, computed } from "vue";

const props = defineProps<{
  modelValue: string;
  options: string[];
  placeholder?: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

const open = ref(false);
const filter = ref("");
const containerRef = ref<HTMLElement | null>(null);

// Filter by what the user has actually typed. (Falling back to modelValue here
// collapsed the list to the current selection, so you couldn't pick anything else.)
const filtered = computed(() =>
  props.options.filter((o) => o.toLowerCase().includes(filter.value.toLowerCase())),
);

function select(opt: string) {
  emit("update:modelValue", opt);
  filter.value = "";
  open.value = false;
}

function handleBlur(e: FocusEvent) {
  if (!containerRef.value?.contains(e.relatedTarget as Node)) {
    open.value = false;
    if (filter.value) {
      emit("update:modelValue", filter.value);
      filter.value = "";
    }
  }
}
</script>

<template>
  <div ref="containerRef" class="relative" @blur.capture="handleBlur">
    <div class="relative">
      <input
        :value="open ? filter : modelValue"
        :placeholder="placeholder"
        class="input-field pr-10"
        @input="
          filter = ($event.target as HTMLInputElement).value;
          open = true;
        "
        @focus="open = true"
      />
      <button
        type="button"
        tabindex="-1"
        class="absolute top-0 right-0 flex h-full w-10 items-center justify-center text-muted-foreground"
        @click="open = !open"
      >
        <AppIcon
          name="i-lucide-chevron-down"
          class="size-4 transition-transform"
          :class="open ? 'rotate-180' : ''"
        />
      </button>
    </div>
    <div
      v-if="open && filtered.length > 0"
      class="absolute inset-x-0 top-full z-30 mt-1 max-h-48 overflow-y-auto rounded-lg border bg-base-200 shadow-lg"
    >
      <button
        v-for="opt in filtered"
        :key="opt"
        type="button"
        class="w-full px-4 py-2.5 text-left text-sm transition-colors"
        :class="
          opt === modelValue
            ? 'bg-base-300 font-medium text-foreground'
            : 'text-foreground hover:bg-base-300/50'
        "
        @mousedown.prevent
        @click="select(opt)"
      >
        {{ opt }}
      </button>
    </div>
  </div>
</template>

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

const filtered = computed(() =>
  props.options.filter((o) =>
    o.toLowerCase().includes((filter.value || props.modelValue).toLowerCase()),
  ),
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
        class="h-11 w-full rounded-lg border border-border bg-muted/40 px-4 pr-10 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
        @input="filter = ($event.target as HTMLInputElement).value; open = true"
        @focus="open = true"
      />
      <button
        type="button"
        tabindex="-1"
        class="absolute right-0 top-0 flex h-full w-10 items-center justify-center text-muted-foreground"
        @click="open = !open"
      >
        <UIcon
          name="i-lucide-chevron-down"
          class="h-4 w-4 transition-transform"
          :class="open ? 'rotate-180' : ''"
        />
      </button>
    </div>
    <div
      v-if="open && filtered.length > 0"
      class="absolute z-30 top-full left-0 right-0 mt-1 max-h-48 overflow-y-auto rounded-lg border border-border bg-card shadow-lg"
    >
      <button
        v-for="opt in filtered"
        :key="opt"
        type="button"
        class="w-full px-4 py-2.5 text-left text-sm transition-colors"
        :class="opt === modelValue ? 'bg-accent font-medium text-foreground' : 'text-foreground hover:bg-accent/50'"
        @mousedown.prevent
        @click="select(opt)"
      >
        {{ opt }}
      </button>
    </div>
  </div>
</template>

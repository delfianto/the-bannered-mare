<script setup lang="ts">
import { ref, computed } from "vue";

const props = defineProps<{
  tags: string[];
  suggestions: string[];
  max?: number;
}>();

const emit = defineEmits<{
  add: [tag: string];
  remove: [tag: string];
}>();

const input = ref("");
const maxTags = computed(() => props.max ?? 10);

const availableSuggestions = computed(() =>
  props.suggestions.filter((s) => !props.tags.includes(s)).slice(0, 8),
);

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === "Enter" && input.value.trim()) {
    e.preventDefault();
    emit("add", input.value.trim());
    input.value = "";
  }
}
</script>

<template>
  <div class="space-y-3">
    <div
      class="flex min-h-[44px] flex-wrap items-center gap-2 rounded-lg border bg-muted/40 p-3 transition-all focus-within:border-primary/40 focus-within:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
    >
      <span
        v-for="tag in tags"
        :key="tag"
        class="inline-flex items-center gap-1 rounded-full border border-primary/20 bg-primary/15 px-2.5 py-1 text-xs font-medium text-primary"
      >
        {{ tag }}
        <button
          type="button"
          class="flex h-3.5 w-3.5 items-center justify-center rounded-full transition-colors hover:bg-primary/20"
          :aria-label="'Remove tag ' + tag"
          @click="emit('remove', tag)"
        >
          <UIcon name="i-lucide-x" class="h-2.5 w-2.5" />
        </button>
      </span>
      <input
        v-if="tags.length < maxTags"
        v-model="input"
        :placeholder="tags.length === 0 ? $t('characters.form.addTagsPlaceholder') : '+'"
        class="min-w-[80px] flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
        @keydown="handleKeyDown"
      />
    </div>

    <div v-if="availableSuggestions.length > 0" class="flex flex-wrap gap-1.5">
      <button
        v-for="s in availableSuggestions"
        :key="s"
        type="button"
        class="inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-medium text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground"
        @click="emit('add', s)"
      >
        <UIcon name="i-lucide-plus" class="h-3 w-3" />
        {{ s }}
      </button>
    </div>
  </div>
</template>

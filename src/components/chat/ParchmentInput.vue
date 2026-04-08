<script setup lang="ts">
import { ref, computed } from "vue";

defineProps<{
  disabled?: boolean;
}>();

const emit = defineEmits<{
  send: [message: string];
}>();

const value = ref("");
const focused = ref(false);
const textareaRef = ref<HTMLTextAreaElement | null>(null);

const canSend = computed(() => value.value.trim().length > 0);

function handleInput(e: Event) {
  const el = e.target as HTMLTextAreaElement;
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 140) + "px";
}

function handleSend() {
  const trimmed = value.value.trim();
  if (!trimmed) return;
  emit("send", trimmed);
  value.value = "";
  if (textareaRef.value) {
    textareaRef.value.style.height = "auto";
  }
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
}
</script>

<template>
  <div class="px-4 pb-4 pt-2">
    <div
      class="relative flex items-center gap-3 rounded-xl border bg-card px-4 py-3 transition-all duration-300"
      :class="
        focused
          ? 'border-primary/40 shadow-[0_0_0_3px_var(--color-primary)/0.1,0_2px_16px_var(--color-primary)/0.08]'
          : 'border-border shadow-[0_1px_4px_var(--color-foreground)/0.04]'
      "
    >
      <!-- Quill icon -->
      <div class="flex-shrink-0">
        <UIcon
          name="i-lucide-pen-tool"
          class="h-[18px] w-[18px] transition-colors duration-300"
          :class="focused ? 'text-primary' : 'text-muted-foreground'"
        />
      </div>

      <!-- Textarea -->
      <textarea
        ref="textareaRef"
        v-model="value"
        placeholder="Continue the tale..."
        rows="1"
        class="max-h-[140px] flex-1 resize-none bg-transparent text-sm leading-relaxed text-foreground outline-none placeholder:text-muted-foreground"
        :disabled="disabled"
        @input="handleInput"
        @focus="focused = true"
        @blur="focused = false"
        @keydown="handleKeyDown"
      />

      <!-- Send button -->
      <button
        :disabled="!canSend || disabled"
        class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full transition-all duration-200 active:scale-[0.92]"
        :class="
          canSend && !disabled
            ? 'bg-primary text-primary-foreground shadow-sm hover:shadow-[0_2px_12px_var(--color-primary)/0.3]'
            : 'cursor-not-allowed bg-muted text-muted-foreground'
        "
        @click="handleSend"
      >
        <UIcon name="i-lucide-arrow-up" class="h-4 w-4" />
      </button>
    </div>

    <p class="mt-2 text-center text-[10px] text-muted-foreground opacity-60">
      Shift + Enter for new line · Your words shape the story
    </p>
  </div>
</template>

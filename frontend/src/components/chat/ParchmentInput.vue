<script setup lang="ts">
import { ref, computed, nextTick } from "vue";

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

// Prefill the composer (e.g. with an impersonated draft) and focus it so the
// user can edit before sending.
function setDraft(text: string) {
  value.value = text;
  void nextTick(() => {
    const el = textareaRef.value;
    if (!el) return;
    el.focus();
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 140) + "px";
  });
}

defineExpose({ setDraft });

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
  <div class="px-4 pt-2 pb-4">
    <div
      class="relative flex items-center gap-3 rounded-xl border bg-base-200 px-4 py-3 transition-all duration-300"
      :class="
        focused
          ? 'border-primary/40 shadow-[0_0_0_3px_var(--color-primary)/0.1,0_2px_16px_var(--color-primary)/0.08]'
          : 'border-border shadow-[0_1px_4px_var(--color-foreground)/0.04]'
      "
    >
      <!-- Quill icon -->
      <div class="shrink-0">
        <AppIcon
          name="i-lucide-pen-tool"
          class="size-5 transition-colors duration-300"
          :class="focused ? 'text-primary' : 'text-muted-foreground'"
        />
      </div>

      <!-- Textarea -->
      <textarea
        ref="textareaRef"
        v-model="value"
        :placeholder="$t('chat.inputPlaceholder')"
        rows="1"
        class="max-h-35 flex-1 resize-none bg-transparent text-sm leading-relaxed text-foreground outline-none placeholder:text-muted-foreground"
        :disabled="disabled"
        @input="handleInput"
        @focus="focused = true"
        @blur="focused = false"
        @keydown="handleKeyDown"
      />

      <!-- Send button -->
      <button
        :aria-label="$t('chat.sendMessage')"
        :disabled="!canSend || disabled"
        class="flex size-8 shrink-0 items-center justify-center rounded-full transition-all duration-200 active:scale-[0.92]"
        :class="
          canSend && !disabled
            ? 'bg-primary text-primary-content shadow-sm hover:shadow-[0_2px_12px_var(--color-primary)/0.3]'
            : 'cursor-not-allowed bg-base-300 text-muted-foreground'
        "
        @click="handleSend"
      >
        <AppIcon name="i-lucide-arrow-up" class="size-4" />
      </button>
    </div>

    <p class="mt-2 text-center text-[0.625rem] text-muted-foreground opacity-60">
      {{ $t("chat.inputHint") }}
    </p>
  </div>
</template>

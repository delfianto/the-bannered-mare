<script setup lang="ts">
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import type { Message } from "@/types/chat";
import NarrativeText from "./NarrativeText.vue";
import QuillTypingIndicator from "./QuillTypingIndicator.vue";

const { t } = useI18n();

const props = defineProps<{
  message: Message;
  index: number;
  characterName?: string;
  characterAvatar?: string;
  alternativeCount?: number;
  currentAltIndex?: number;
  streaming?: boolean;
}>();

const emit = defineEmits<{
  edit: [messageId: string, content: string];
  swipe: [messageId: string, direction: "left" | "right"];
  action: [messageId: string, action: string];
}>();

const hovered = ref(false);
const isUser = computed(() => props.message.role === "user");

// The response bubble is created empty before the first token arrives; while it
// is still empty and streaming, show the composing (quill) animation in its place.
const isPending = computed(() => props.streaming === true && !props.message.content);

// Inline edit state
const isEditing = ref(false);
const editContent = ref("");

// Whether to show swipe arrows (assistant messages only, on hover)
const showSwipeArrows = computed(() => !isUser.value && hovered.value && !isEditing.value);

// Alternative counter display
const hasAlternatives = computed(
  () => props.alternativeCount != null && props.alternativeCount > 0,
);

const formattedTime = computed(() => {
  try {
    return new Date(props.message.created_at).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
});

function handleAction(action: string) {
  if (action === "edit") {
    isEditing.value = true;
    editContent.value = props.message.content;
  } else {
    emit("action", props.message.id, action);
  }
}

function saveEdit() {
  const trimmed = editContent.value.trim();
  if (trimmed && trimmed !== props.message.content) {
    emit("edit", props.message.id, trimmed);
  }
  isEditing.value = false;
}

function cancelEdit() {
  isEditing.value = false;
}

function handleEditKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    cancelEdit();
  }
}

const characterActions = [
  { icon: "i-lucide-rotate-ccw", label: t("chat.actions.regenerate"), key: "regen" },
  { icon: "i-lucide-copy", label: t("chat.actions.copy"), key: "copy" },
  { icon: "i-lucide-bookmark", label: t("chat.actions.bookmark"), key: "bookmark" },
];

const userActions = [
  { icon: "i-lucide-pencil", label: t("chat.actions.edit"), key: "edit" },
  { icon: "i-lucide-trash-2", label: t("chat.actions.delete"), key: "delete" },
];
</script>

<template>
  <div
    class="flex animate-fade-in-up gap-3"
    :class="isUser ? 'flex-row-reverse' : 'flex-row'"
    :style="{ animationDelay: `${index * 60}ms` }"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <!-- Avatar — assistant only -->
    <div v-if="!isUser && characterAvatar" class="mt-1 shrink-0">
      <img
        :src="characterAvatar"
        :alt="characterName"
        class="size-9 rounded-full object-cover ring-1 ring-border"
      />
    </div>

    <!-- Message Card -->
    <div class="relative max-w-[75%]">
      <!-- Swipe Left Arrow (assistant only) -->
      <button
        v-if="!isUser && (showSwipeArrows || hasAlternatives)"
        :aria-label="$t('chat.swipe.previous')"
        class="absolute top-1/2 -left-10 flex size-7 -translate-y-1/2 items-center justify-center rounded-full bg-base-300/80 text-foreground transition-all hover:bg-base-300"
        @click="emit('swipe', message.id, 'left')"
      >
        <AppIcon name="i-lucide-chevron-left" class="size-4" />
      </button>

      <!-- Swipe Right Arrow (assistant only) -->
      <button
        v-if="!isUser && (showSwipeArrows || hasAlternatives)"
        :aria-label="$t('chat.swipe.next')"
        class="absolute top-1/2 -right-10 flex size-7 -translate-y-1/2 items-center justify-center rounded-full bg-base-300/80 text-foreground transition-all hover:bg-base-300"
        @click="emit('swipe', message.id, 'right')"
      >
        <AppIcon name="i-lucide-chevron-right" class="size-4" />
      </button>

      <!-- Sender name — assistant only -->
      <p
        v-if="!isUser && characterName"
        class="mb-1 ml-1 font-cinzel text-xs font-medium text-muted-foreground"
        style="letter-spacing: 0.02em"
      >
        {{ characterName }}
      </p>

      <!-- Card -->
      <div
        class="relative rounded-2xl px-5 py-4 transition-shadow duration-300"
        :class="[
          isUser
            ? 'rounded-tr-md border border-primary/20 bg-primary/10'
            : 'rounded-tl-md border bg-base-300',
          hovered
            ? isUser
              ? 'shadow-[0_4px_20px_var(--color-primary)/0.12]'
              : 'shadow-[0_4px_20px_var(--color-foreground)/0.06]'
            : '',
        ]"
      >
        <!-- Edit mode -->
        <template v-if="isEditing">
          <textarea
            v-model="editContent"
            class="w-full resize-none rounded-lg border bg-base-300/40 px-3 py-2 text-sm leading-relaxed text-foreground outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/30"
            rows="4"
            autofocus
            @keydown="handleEditKeydown"
          />
          <div class="mt-2 flex items-center justify-end gap-2">
            <button
              class="rounded-md px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
              @click="cancelEdit"
            >
              {{ $t("common.cancel") }}
            </button>
            <button
              class="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-content transition-colors hover:bg-primary/90"
              @click="saveEdit"
            >
              {{ $t("common.save") }}
            </button>
          </div>
        </template>

        <!-- Composing animation — empty assistant bubble awaiting first token -->
        <QuillTypingIndicator v-else-if="isPending" :character-name="characterName" />

        <!-- Normal display -->
        <NarrativeText v-else :content="message.content" />
      </div>

      <!-- Bottom row: actions + alt counter + timestamp -->
      <div
        v-if="!isPending"
        class="mt-1.5 flex items-center gap-1"
        :class="isUser ? 'mr-1 flex-row-reverse' : 'ml-1'"
      >
        <!-- Inline action icons (always visible) -->
        <div v-if="!isEditing" class="flex items-center gap-0.5">
          <button
            v-for="act in isUser ? userActions : characterActions"
            :key="act.key"
            :title="act.label"
            class="flex size-6 items-center justify-center rounded text-muted-foreground/40 transition-colors hover:text-muted-foreground"
            @click="handleAction(act.key)"
          >
            <AppIcon :name="act.icon" class="size-3" />
          </button>
        </div>

        <!-- Alternative counter badge (assistant only) -->
        <span
          v-if="hasAlternatives && !isUser"
          class="rounded-full bg-base-300/60 px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
        >
          {{ (currentAltIndex ?? 0) + 1 }} / {{ alternativeCount }}
        </span>

        <!-- Timestamp -->
        <p class="text-[10px] text-muted-foreground">
          {{ formattedTime }}
        </p>
      </div>
    </div>
  </div>
</template>

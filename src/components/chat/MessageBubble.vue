<script setup lang="ts">
import { ref, computed } from "vue";
import type { Message } from "@/types/chat";
import NarrativeText from "./NarrativeText.vue";
import MessageActions from "./MessageActions.vue";

const props = defineProps<{
  message: Message;
  index: number;
  characterName?: string;
  characterAvatar?: string;
  alternativeCount?: number;
  currentAltIndex?: number;
}>();

const emit = defineEmits<{
  edit: [messageId: string, content: string];
  swipe: [messageId: string, direction: "left" | "right"];
}>();

const hovered = ref(false);
const isUser = computed(() => props.message.role === "user");

// Inline edit state
const isEditing = ref(false);
const editContent = ref("");

// Whether to show swipe arrows (assistant messages only, on hover)
const showSwipeArrows = computed(
  () => !isUser.value && hovered.value && !isEditing.value,
);

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
  }
  // other actions (copy, regen, delete, bookmark) can be handled later
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

function swipeLeft() {
  emit("swipe", props.message.id, "left");
}

function swipeRight() {
  emit("swipe", props.message.id, "right");
}
</script>

<template>
  <div
    class="flex gap-3 animate-fade-in-up"
    :class="isUser ? 'flex-row-reverse' : 'flex-row'"
    :style="{ animationDelay: `${index * 60}ms` }"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <!-- Avatar — assistant only -->
    <div v-if="!isUser && characterAvatar" class="mt-1 flex-shrink-0">
      <img
        :src="characterAvatar"
        :alt="characterName"
        class="h-9 w-9 rounded-full object-cover ring-1 ring-border"
      />
    </div>

    <!-- Message Card -->
    <div class="relative max-w-[75%]">
      <MessageActions
        :type="message.role === 'user' ? 'user' : 'character'"
        :visible="hovered && !isEditing"
        @action="handleAction"
      />

      <!-- Swipe Left Arrow (assistant only) -->
      <button
        v-if="!isUser && (showSwipeArrows || hasAlternatives)"
        class="absolute -left-10 top-1/2 -translate-y-1/2 flex h-7 w-7 items-center justify-center rounded-full bg-accent/80 text-foreground transition-all hover:bg-accent"
        :class="showSwipeArrows || hasAlternatives ? 'opacity-100' : 'opacity-0 pointer-events-none'"
        @click="swipeLeft"
      >
        <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
      </button>

      <!-- Swipe Right Arrow (assistant only) -->
      <button
        v-if="!isUser && (showSwipeArrows || hasAlternatives)"
        class="absolute -right-10 top-1/2 -translate-y-1/2 flex h-7 w-7 items-center justify-center rounded-full bg-accent/80 text-foreground transition-all hover:bg-accent"
        :class="showSwipeArrows || hasAlternatives ? 'opacity-100' : 'opacity-0 pointer-events-none'"
        @click="swipeRight"
      >
        <UIcon name="i-lucide-chevron-right" class="h-4 w-4" />
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
            : 'rounded-tl-md border border-border bg-muted',
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
            class="w-full resize-none rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm leading-relaxed text-foreground outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/30"
            rows="4"
            autofocus
            @keydown="handleEditKeydown"
          />
          <div class="mt-2 flex items-center justify-end gap-2">
            <button
              class="rounded-md px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              @click="cancelEdit"
            >
              Cancel
            </button>
            <button
              class="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground transition-colors hover:bg-primary/90"
              @click="saveEdit"
            >
              Save
            </button>
          </div>
        </template>

        <!-- Normal display -->
        <NarrativeText v-else :content="message.content" />
      </div>

      <!-- Alternative Counter + Timestamp -->
      <div
        class="mt-1.5 flex items-center gap-2"
        :class="isUser ? 'mr-1 justify-end' : 'ml-1 justify-start'"
      >
        <!-- Alternative counter badge (assistant only) -->
        <span
          v-if="hasAlternatives && !isUser"
          class="rounded-full bg-accent/60 px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
        >
          {{ (currentAltIndex ?? 0) + 1 }} / {{ alternativeCount }}
        </span>

        <p class="text-[10px] text-muted-foreground">
          {{ formattedTime }}
        </p>
      </div>
    </div>
  </div>
</template>

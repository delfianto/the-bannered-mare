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
}>();

const hovered = ref(false);
const isUser = computed(() => props.message.role === "user");

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
      <MessageActions :type="message.role === 'user' ? 'user' : 'character'" :visible="hovered" />

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
        <NarrativeText :content="message.content" />
      </div>

      <!-- Timestamp -->
      <p
        class="mt-1.5 text-[10px] text-muted-foreground"
        :class="isUser ? 'mr-1 text-right' : 'ml-1'"
      >
        {{ formattedTime }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import type { ChatMessage } from "@/types/chat";
import NarrativeText from "./NarrativeText.vue";
import MessageActions from "./MessageActions.vue";

const props = defineProps<{
  message: ChatMessage;
  index: number;
}>();

const hovered = ref(false);
</script>

<template>
  <div
    class="flex gap-3 animate-fade-in-up"
    :class="message.sender === 'user' ? 'flex-row-reverse' : 'flex-row'"
    :style="{ animationDelay: `${index * 60}ms` }"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <!-- Avatar — character only -->
    <div v-if="message.sender === 'character'" class="mt-1 flex-shrink-0">
      <img
        :src="message.characterAvatar"
        :alt="message.characterName"
        class="h-9 w-9 rounded-full object-cover ring-1 ring-border"
      />
    </div>

    <!-- Message Card -->
    <div class="relative max-w-[75%]">
      <MessageActions :type="message.sender" :visible="hovered" />

      <!-- Sender name — character only -->
      <p
        v-if="message.sender === 'character' && message.characterName"
        class="mb-1 ml-1 font-cinzel text-xs font-medium text-muted-foreground"
        style="letter-spacing: 0.02em"
      >
        {{ message.characterName }}
      </p>

      <!-- Card -->
      <div
        class="relative rounded-2xl px-5 py-4 transition-shadow duration-300"
        :class="[
          message.sender === 'user'
            ? 'rounded-tr-md border border-primary/20 bg-primary/10'
            : 'rounded-tl-md border border-border bg-muted',
          hovered
            ? message.sender === 'user'
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
        :class="message.sender === 'user' ? 'mr-1 text-right' : 'ml-1'"
      >
        {{ message.timestamp }}
      </p>
    </div>
  </div>
</template>

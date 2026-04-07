<script setup lang="ts">
import { ref, computed, nextTick, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import ChatSessionList from "@/components/chat/ChatSessionList.vue";
import ChatHeader from "@/components/chat/ChatHeader.vue";
import MessageBubble from "@/components/chat/MessageBubble.vue";
import QuillTypingIndicator from "@/components/chat/QuillTypingIndicator.vue";
import MoodChips from "@/components/chat/MoodChips.vue";
import ParchmentInput from "@/components/chat/ParchmentInput.vue";
import {
  CHAT_SESSIONS,
  MOCK_MESSAGES,
  MOOD_CHIPS,
  ACTIVE_CHARACTER,
} from "@/constants/chatData";
import type { ChatMessage, MoodChip } from "@/types/chat";

const router = useRouter();
const route = useRoute();

const activeSessionId = ref((route.params.chatId as string) || "session-1");
const messages = ref<ChatMessage[]>([...MOCK_MESSAGES]);
const isTyping = ref(false);
const messageListRef = ref<HTMLElement | null>(null);

const activeSession = computed(
  () => CHAT_SESSIONS.find((s) => s.id === activeSessionId.value) || CHAT_SESSIONS[0],
);

const showMoodChips = computed(() => {
  const last = messages.value[messages.value.length - 1];
  return last?.sender === "character" && !isTyping.value;
});

function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight;
    }
  });
}

function handleSend(text: string) {
  const userMsg: ChatMessage = {
    id: `msg-user-${Date.now()}`,
    sender: "user",
    content: text,
    timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  };
  messages.value.push(userMsg);
  scrollToBottom();

  isTyping.value = true;
  scrollToBottom();

  setTimeout(() => {
    const aiMsg: ChatMessage = {
      id: `msg-ai-${Date.now()}`,
      sender: "character",
      content:
        "*Elara\u2019s eyes widen as she watches the luminescent ink swirl in response to your words. The ancient library seems to breathe around you \u2014 a low, resonant hum vibrating through the stone floors and towering shelves.* \"Remarkable. The wards recognize your sincerity.\" *She moves deeper into the chamber, her fingertips trailing along the spines of books that have waited centuries for this moment.* \"But be cautious. Knowledge preserved this long was guarded for a reason. Not everything within these pages was meant to be read aloud.\"",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      characterName: ACTIVE_CHARACTER.name,
      characterAvatar: ACTIVE_CHARACTER.avatar,
    };
    messages.value.push(aiMsg);
    isTyping.value = false;
    scrollToBottom();
  }, 2800);
}

function handleMoodSelect(chip: MoodChip) {
  handleSend(`*${chip.label}* "I understand the risks. Show me what lies within."`);
}

function selectSession(id: string) {
  activeSessionId.value = id;
  router.replace({ name: "chat", params: { chatId: id } });
}

watch(
  () => route.params.chatId,
  (id) => {
    if (id && typeof id === "string") activeSessionId.value = id;
  },
);
</script>

<template>
  <div class="flex h-full overflow-hidden">
    <!-- Session List -->
    <ChatSessionList
      :sessions="CHAT_SESSIONS"
      :active-session-id="activeSessionId"
      @select="selectSession"
    />

    <!-- Main Chat Area -->
    <div class="flex flex-1 flex-col overflow-hidden">
      <ChatHeader
        :character="activeSession.character"
        :session-title="activeSession.sessionTitle"
        @back="router.push({ name: 'chats' })"
      />

      <!-- Message List -->
      <div ref="messageListRef" class="flex-1 overflow-y-auto px-5 py-6" style="scroll-behavior: smooth">
        <div class="mx-auto max-w-[720px] space-y-5">
          <!-- Session Start Marker -->
          <div class="flex items-center justify-center py-4">
            <div class="flex items-center gap-3">
              <div class="h-px w-12 bg-border" />
              <div class="text-center">
                <p class="font-cinzel text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {{ activeSession.sessionTitle }}
                </p>
                <p class="mt-0.5 text-[10px] text-muted-foreground/60">
                  Session began · Today at 10:40 AM
                </p>
              </div>
              <div class="h-px w-12 bg-border" />
            </div>
          </div>

          <!-- Messages -->
          <MessageBubble
            v-for="(msg, i) in messages"
            :key="msg.id"
            :message="msg"
            :index="i"
          />

          <!-- Mood Chips -->
          <MoodChips
            v-if="showMoodChips"
            :chips="MOOD_CHIPS"
            @select="handleMoodSelect"
          />

          <!-- Typing Indicator -->
          <QuillTypingIndicator
            v-if="isTyping"
            :character-name="activeSession.character.name"
            :character-avatar="activeSession.character.avatar"
          />
        </div>
      </div>

      <!-- Input -->
      <ParchmentInput :disabled="isTyping" @send="handleSend" />
    </div>
  </div>
</template>

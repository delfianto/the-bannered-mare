<script setup lang="ts">
import { ref, computed, nextTick, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useChatSessions } from "@/composables/useChatSessions";
import { useChatMessages } from "@/composables/useChatMessages";
import { getAvatarUrl } from "@/api/client";
import ChatSessionList from "@/components/chat/ChatSessionList.vue";
import ChatHeader from "@/components/chat/ChatHeader.vue";
import MessageBubble from "@/components/chat/MessageBubble.vue";
import QuillTypingIndicator from "@/components/chat/QuillTypingIndicator.vue";
import MoodChips from "@/components/chat/MoodChips.vue";
import ParchmentInput from "@/components/chat/ParchmentInput.vue";
import type { MoodChip } from "@/types/chat";

const router = useRouter();
const route = useRoute();

const activeSessionId = ref((route.params.chatId as string) || "");

// Wire to API via composables
const {
  chatSessions,
  loading: sessionsLoading,
} = useChatSessions({ pageSize: 30 });

const {
  messages,
  loading: messagesLoading,
  isGenerating,
  hasMore,
  sendMessage,
  loadMore,
} = useChatMessages(
  () => activeSessionId.value || null,
  { pageSize: 30 },
);

// Auto-select first session if none specified
watch(chatSessions, (sessions) => {
  if (!activeSessionId.value && sessions.length > 0) {
    activeSessionId.value = sessions[0].id;
    router.replace({ name: "chat", params: { chatId: sessions[0].id } });
  }
}, { immediate: true });

const activeSession = computed(
  () => chatSessions.value.find((s) => s.id === activeSessionId.value),
);

const characterAvatar = computed(() => {
  const char = activeSession.value?.character;
  if (!char) return "";
  if (char.avatar_thumbnail) return getAvatarUrl(char.id);
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(char.name)}&background=C9922E&color=fff&size=80`;
});

const showMoodChips = computed(() => {
  const last = messages.value[messages.value.length - 1];
  return last?.role === "assistant" && !isGenerating.value;
});

const messageListRef = ref<HTMLElement | null>(null);

function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight;
    }
  });
}

// Scroll on new messages
watch(() => messages.value.length, () => scrollToBottom());

const MOOD_CHIPS: MoodChip[] = [
  { id: "mood-1", label: "Boldly" },
  { id: "mood-2", label: "With caution" },
  { id: "mood-3", label: "Whisper" },
  { id: "mood-4", label: "Defiantly" },
  { id: "mood-5", label: "Tenderly" },
];

function handleSend(text: string) {
  sendMessage(text);
  scrollToBottom();
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
    <!-- Session List (from API) -->
    <ChatSessionList
      :sessions="chatSessions"
      :active-session-id="activeSessionId"
      :loading="sessionsLoading"
      @select="selectSession"
    />

    <!-- Main Chat Area -->
    <div v-if="activeSession" class="flex flex-1 flex-col overflow-hidden">
      <ChatHeader
        :character="activeSession.character"
        :session-title="activeSession.title || 'Untitled Tale'"
        @back="router.push({ name: 'chats' })"
      />

      <!-- Message List -->
      <div ref="messageListRef" class="flex-1 overflow-y-auto px-5 py-6" style="scroll-behavior: smooth">
        <div class="mx-auto max-w-[720px] space-y-5">
          <!-- Load More -->
          <div v-if="hasMore" class="flex justify-center py-2">
            <button
              class="text-xs text-muted-foreground hover:text-primary transition-colors"
              @click="loadMore"
            >
              Load earlier messages...
            </button>
          </div>

          <!-- Session Start Marker -->
          <div class="flex items-center justify-center py-4">
            <div class="flex items-center gap-3">
              <div class="h-px w-12 bg-border" />
              <div class="text-center">
                <p class="font-cinzel text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {{ activeSession.title || "Untitled Tale" }}
                </p>
                <p class="mt-0.5 text-[10px] text-muted-foreground/60">
                  Session began · {{ new Date(activeSession.created_at).toLocaleDateString() }}
                </p>
              </div>
              <div class="h-px w-12 bg-border" />
            </div>
          </div>

          <!-- Loading messages -->
          <div v-if="messagesLoading && messages.length === 0" class="flex justify-center py-8">
            <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin text-muted-foreground" />
          </div>

          <!-- Messages -->
          <MessageBubble
            v-for="(msg, i) in messages"
            :key="msg.id"
            :message="msg"
            :index="i"
            :character-name="msg.role === 'assistant' ? activeSession.character.name : undefined"
            :character-avatar="msg.role === 'assistant' ? characterAvatar : undefined"
          />

          <!-- Mood Chips -->
          <MoodChips
            v-if="showMoodChips"
            :chips="MOOD_CHIPS"
            @select="handleMoodSelect"
          />

          <!-- Typing Indicator -->
          <QuillTypingIndicator
            v-if="isGenerating"
            :character-name="activeSession.character.name"
            :character-avatar="characterAvatar"
          />
        </div>
      </div>

      <!-- Input -->
      <ParchmentInput :disabled="isGenerating" @send="handleSend" />
    </div>

    <!-- No session selected -->
    <div v-else class="flex flex-1 items-center justify-center">
      <p class="text-muted-foreground">Select a tale to continue...</p>
    </div>
  </div>
</template>

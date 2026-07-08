<script setup lang="ts">
import { ref, computed, nextTick, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { useChatSessions } from "@/composables/useChatSessions";
import { useChatMessages } from "@/composables/useChatMessages";
import { useProfiles } from "@/composables/useProfiles";
import { useAppToast } from "@/composables/useToast";
import ChatSessionList from "@/components/chat/ChatSessionList.vue";
import ChatHeader from "@/components/chat/ChatHeader.vue";
import MessageBubble from "@/components/chat/MessageBubble.vue";
import MoodChips from "@/components/chat/MoodChips.vue";
import ParchmentInput from "@/components/chat/ParchmentInput.vue";
import type { MoodChip } from "@/types/chat";
import EmptyState from "@/components/shared/EmptyState.vue";

const { t } = useI18n();
const router = useRouter();
const route = useRoute();

const activeSessionId = ref((route.params.chatId as string) || "");

// Wire to API via composables
const {
  chatSessions,
  loading: sessionsLoading,
  updateChat,
  deleteChat,
  applyProfile,
  generateTitle,
} = useChatSessions({ pageSize: 30 });

const { profiles } = useProfiles();

const {
  messages,
  loading: messagesLoading,
  isGenerating,
  suggesting,
  fetchSuggestions,
  hasMore,
  sendMessage,
  loadMore,
  editMessage,
  fetchAlternatives,
  activateAlternative,
} = useChatMessages(() => activeSessionId.value || null, { pageSize: 30 });

// Auto-select first session if none specified
watch(
  chatSessions,
  (sessions) => {
    if (!activeSessionId.value && sessions.length > 0) {
      activeSessionId.value = sessions[0].id;
      router.replace({ name: "chat", params: { chatId: sessions[0].id } });
    }
  },
  { immediate: true },
);

const activeSession = computed(() =>
  chatSessions.value.find((s) => s.id === activeSessionId.value),
);

const characterAvatar = computed(() => {
  const char = activeSession.value?.character;
  if (!char) return "";
  return (
    char.avatar_thumbnail ||
    char.avatar ||
    `https://ui-avatars.com/api/?name=${encodeURIComponent(char.name)}&background=C9922E&color=fff&size=80`
  );
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
watch(
  () => messages.value.length,
  () => scrollToBottom(),
);

// Auto-title (once) after the first exchange, when the chat has no title yet.
async function maybeGenerateTitle() {
  const session = activeSession.value;
  if (!session || (session.title || "").trim()) return;
  if (messages.value.length < 2) return;
  await generateTitle(session.id);
}

watch(isGenerating, (now, was) => {
  if (was && !now) void maybeGenerateTitle();
});

// Tone options for #2 (impersonation): clicking drafts the user's next line in
// their voice, steered by this tone, into the composer for editing.
const MOOD_CHIPS: MoodChip[] = [
  { id: "mood-1", label: t("chat.moods.boldly") },
  { id: "mood-2", label: t("chat.moods.caution") },
  { id: "mood-3", label: t("chat.moods.whisper") },
  { id: "mood-4", label: t("chat.moods.defiantly") },
  { id: "mood-5", label: t("chat.moods.tenderly") },
];

const inputRef = ref<InstanceType<typeof ParchmentInput> | null>(null);
const toast = useAppToast();

// #1: dynamically generated reply candidates (clicking one sends it).
const replySuggestions = ref<string[]>([]);
const replyChips = computed<MoodChip[]>(() =>
  replySuggestions.value.map((text, i) => ({ id: `sg-${i}`, label: text })),
);

function handleSend(text: string) {
  replySuggestions.value = [];
  sendMessage(text);
  scrollToBottom();
}

// #1 — fetch contextual reply candidates and show them as chips.
async function loadSuggestions() {
  const items = await fetchSuggestions({ mode: "reply", count: 3 });
  if (items.length) replySuggestions.value = items;
  else toast.error(t("chat.suggest.error"));
}

function handleReplySelect(chip: MoodChip) {
  handleSend(chip.label);
}

// #2 — draft the user's next line in the chosen tone into the composer.
async function handleToneSelect(chip: MoodChip) {
  const [draft] = await fetchSuggestions({ mode: "impersonate", tone: chip.label });
  if (draft) inputRef.value?.setDraft(draft);
  else toast.error(t("chat.suggest.error"));
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

// --- Chat Rename & Delete ---

async function handleRename(newTitle: string) {
  if (!activeSessionId.value) return;
  await updateChat(activeSessionId.value, newTitle);
}

async function handleApplyProfile(profileId: string) {
  if (!activeSessionId.value) return;
  await applyProfile(activeSessionId.value, profileId);
}

async function handleDeleteChat() {
  if (!activeSessionId.value) return;
  const deletedId = activeSessionId.value;
  await deleteChat(deletedId);
  // Navigate to first remaining session or empty state
  const remaining = chatSessions.value;
  if (remaining.length > 0) {
    activeSessionId.value = remaining[0].id;
    router.replace({ name: "chat", params: { chatId: remaining[0].id } });
  } else {
    activeSessionId.value = "";
    router.replace({ name: "chats" });
  }
}

// --- Message Editing ---

async function handleEditMessage(messageId: string, content: string) {
  await editMessage(messageId, content);
}

// --- Alternatives / Swipes ---

const alternativesCache = ref(new Map<string, any[]>());

function getAlternativeCount(messageId: string): number | undefined {
  const alts = alternativesCache.value.get(messageId);
  return alts ? alts.length : undefined;
}

function getCurrentAltIndex(messageId: string): number | undefined {
  const msg = messages.value.find((m) => m.id === messageId);
  if (!msg) return undefined;
  return msg.active_index ?? 0;
}

async function handleSwipe(messageId: string, direction: "left" | "right") {
  // Lazy-load alternatives if not cached
  if (!alternativesCache.value.has(messageId)) {
    const alts = await fetchAlternatives(messageId);
    if (alts.length === 0) return;
    alternativesCache.value.set(messageId, alts);
    // Force reactivity by reassigning
    alternativesCache.value = new Map(alternativesCache.value);
  }

  const alts = alternativesCache.value.get(messageId);
  if (!alts || alts.length === 0) return;

  const msg = messages.value.find((m) => m.id === messageId);
  if (!msg) return;

  const currentIdx = msg.active_index ?? 0;
  let newIdx: number;

  if (direction === "left") {
    newIdx = currentIdx > 0 ? currentIdx - 1 : alts.length - 1;
  } else {
    newIdx = currentIdx < alts.length - 1 ? currentIdx + 1 : 0;
  }

  if (newIdx !== currentIdx && alts[newIdx]) {
    await activateAlternative(messageId, alts[newIdx].id);
  }
}
</script>

<template>
  <!-- Loading state -->
  <div
    v-if="sessionsLoading && chatSessions.length === 0"
    class="flex h-full flex-1 items-center justify-center"
  >
    <UIcon name="i-lucide-loader-circle" class="size-6 animate-spin text-muted-foreground" />
  </div>

  <!-- Empty state -->
  <div
    v-else-if="chatSessions.length === 0"
    class="flex h-full flex-1 flex-col overflow-hidden p-8 lg:px-12"
  >
    <!-- Header -->
    <header class="shrink-0 animate-fade-in-up pb-4">
      <div>
        <h1 class="font-cinzel text-2xl font-bold tracking-wide text-foreground">
          {{ $t("chat.activeTales") || "Active Tales" }}
        </h1>
        <p class="mt-1 text-sm text-muted-foreground">Your active roleplay chat sessions.</p>
      </div>
    </header>

    <!-- Empty Content -->
    <EmptyState
      icon="i-lucide-scroll-text"
      title="No Tales Begun"
      description="You haven't started any chat sessions yet. Head over to the Character Library, pick a companion, and begin your journey."
      action-label="Browse Characters"
      @action="router.push('/characters')"
    />
  </div>

  <!-- Normal chat view -->
  <div v-else class="flex h-full overflow-hidden">
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
        :session-title="activeSession.title || $t('chat.untitled')"
        :profiles="profiles"
        :current-profile-name="activeSession.last_profile_name"
        @back="router.push({ name: 'chats' })"
        @rename="handleRename"
        @delete="handleDeleteChat"
        @apply-profile="handleApplyProfile"
      />

      <!-- Message List -->
      <div
        ref="messageListRef"
        class="flex-1 overflow-y-auto px-5 py-6"
        style="scroll-behavior: smooth"
      >
        <div class="mx-auto max-w-[720px] space-y-5">
          <!-- Load More -->
          <div v-if="hasMore" class="flex justify-center py-2">
            <button
              class="text-xs text-muted-foreground transition-colors hover:text-primary"
              @click="loadMore"
            >
              {{ $t("chat.loadEarlier") }}
            </button>
          </div>

          <!-- Session Start Marker -->
          <div class="flex items-center justify-center py-4">
            <div class="flex items-center gap-3">
              <div class="h-px w-12 bg-border" />
              <div class="text-center">
                <p
                  class="font-cinzel text-xs font-semibold tracking-wider text-muted-foreground uppercase"
                >
                  {{ activeSession.title || $t("chat.untitled") }}
                </p>
                <p class="mt-0.5 text-[10px] text-muted-foreground/60">
                  {{ $t("chat.sessionBegan") }} ·
                  {{ new Date(activeSession.created_at).toLocaleDateString() }}
                </p>
              </div>
              <div class="h-px w-12 bg-border" />
            </div>
          </div>

          <!-- Loading messages -->
          <div v-if="messagesLoading && messages.length === 0" class="flex justify-center py-8">
            <UIcon
              name="i-lucide-loader-circle"
              class="size-6 animate-spin text-muted-foreground"
            />
          </div>

          <!-- Messages -->
          <MessageBubble
            v-for="(msg, i) in messages"
            :key="msg.id"
            :message="msg"
            :index="i"
            :character-name="msg.role === 'assistant' ? activeSession.character.name : undefined"
            :character-avatar="msg.role === 'assistant' ? characterAvatar : undefined"
            :alternative-count="getAlternativeCount(msg.id)"
            :current-alt-index="getCurrentAltIndex(msg.id)"
            :streaming="isGenerating && i === messages.length - 1 && msg.role === 'assistant'"
            @edit="handleEditMessage"
            @swipe="handleSwipe"
          />

          <!-- Suggestions bar (after the latest assistant reply) -->
          <div v-if="showMoodChips" class="flex flex-col items-center gap-1.5 py-2">
            <!-- #1: dynamic reply candidates — click to send -->
            <template v-if="replyChips.length">
              <MoodChips :chips="replyChips" @select="handleReplySelect" />
              <button
                class="text-[10px] text-muted-foreground transition-colors hover:text-primary"
                @click="replySuggestions = []"
              >
                {{ $t("chat.suggest.back") }}
              </button>
            </template>

            <!-- #2: tone chips (draft into composer) + trigger for #1 -->
            <template v-else>
              <MoodChips :chips="MOOD_CHIPS" :disabled="suggesting" @select="handleToneSelect" />
              <button
                :disabled="suggesting"
                class="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground transition-colors hover:text-primary disabled:opacity-50"
                @click="loadSuggestions"
              >
                <UIcon
                  :name="suggesting ? 'i-lucide-loader-circle' : 'i-lucide-sparkles'"
                  class="size-3.5"
                  :class="{ 'animate-spin': suggesting }"
                />
                {{ suggesting ? $t("chat.suggest.loading") : $t("chat.suggest.button") }}
              </button>
            </template>
          </div>
        </div>
      </div>

      <!-- Input -->
      <ParchmentInput ref="inputRef" :disabled="isGenerating" @send="handleSend" />
    </div>

    <!-- No session selected -->
    <div v-else class="flex flex-1 items-center justify-center">
      <p class="text-muted-foreground">{{ $t("chat.selectTale") }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import type { ChatCharacterInfo } from "@/types/chat";
import { useOverlayTransition } from "@/composables/useOverlayTransition";
import Tabs from "@/components/shared/Tabs.vue";
import ChatDrawerCharacterTab from "@/components/chat/ChatDrawerCharacterTab.vue";
import ChatDrawerSettingsTab from "@/components/chat/ChatDrawerSettingsTab.vue";
import ChatDrawerSessionTab from "@/components/chat/ChatDrawerSessionTab.vue";
import ChatDrawerLogsTab from "@/components/chat/ChatDrawerLogsTab.vue";

const props = defineProps<{
  show: boolean;
  character: ChatCharacterInfo;
  chatId?: string;
  sessionTitle: string;
  currentModelId?: string | null;
  currentModelName?: string | null;
  currentTaskModelId?: string | null;
  currentProfileName?: string | null;
  currentPersonaId?: string | null;
}>();

const emit = defineEmits<{
  close: [];
  changeModel: [modelId: string];
  changeTaskModel: [modelId: string | null];
  applyProfile: [profileId: string];
  changePersona: [personaId: string | null];
  rename: [title: string];
  delete: [];
}>();

const { t } = useI18n();

// Timer-driven open/close + scroll-lock + Escape-to-close (shared composable).
const { visible, entered } = useOverlayTransition(() => props.show, {
  onEscape: () => emit("close"),
});

const tabs = [
  { key: "character", label: t("chat.drawer.tabs.character") },
  { key: "settings", label: t("chat.drawer.tabs.settings") },
  { key: "session", label: t("chat.drawer.tabs.session") },
  { key: "logs", label: t("chat.drawer.tabs.logs") },
];
const activeTab = ref("character");
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="fixed inset-0 z-50" role="dialog" aria-modal="true">
      <!-- Backdrop -->
      <div
        class="fixed inset-0 bg-black/50 backdrop-blur-[2px] transition-opacity duration-200"
        :class="entered ? 'opacity-100' : 'opacity-0'"
        @click="emit('close')"
      />

      <!-- Panel (slides in from the right) -->
      <div
        class="fixed inset-y-0 right-0 flex w-96 max-w-full flex-col border-l bg-base-200 shadow-2xl transition-transform duration-200 ease-out"
        :class="entered ? 'translate-x-0' : 'translate-x-full'"
      >
        <!-- Header -->
        <div class="flex h-15.5 shrink-0 items-center justify-between border-b px-4">
          <h2
            class="min-w-0 truncate font-story text-sm font-semibold tracking-wide text-foreground"
          >
            {{ character.name }}
          </h2>
          <button
            :aria-label="$t('common.close')"
            class="flex size-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
            @click="emit('close')"
          >
            <AppIcon name="i-lucide-x" class="size-4" />
          </button>
        </div>

        <!-- Tabs -->
        <Tabs v-model="activeTab" :tabs="tabs" class="shrink-0" />

        <!-- Body: each tab is a child that owns its composables and lazy-fetches
             when it becomes active. -->
        <div class="flex-1 overflow-y-auto">
          <ChatDrawerCharacterTab v-if="activeTab === 'character'" :character-id="character.id" />

          <ChatDrawerSettingsTab
            v-else-if="activeTab === 'settings'"
            :chat-id="chatId"
            :character-id="character.id"
            :session-title="sessionTitle"
            :current-model-id="currentModelId"
            :current-model-name="currentModelName"
            :current-task-model-id="currentTaskModelId"
            :current-profile-name="currentProfileName"
            :current-persona-id="currentPersonaId"
            @change-model="emit('changeModel', $event)"
            @change-task-model="emit('changeTaskModel', $event)"
            @apply-profile="emit('applyProfile', $event)"
            @change-persona="emit('changePersona', $event)"
            @rename="emit('rename', $event)"
            @delete="emit('delete')"
            @close="emit('close')"
          />

          <ChatDrawerSessionTab v-else-if="activeTab === 'session'" :chat-id="chatId" />

          <ChatDrawerLogsTab v-else-if="activeTab === 'logs'" :chat-id="chatId" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

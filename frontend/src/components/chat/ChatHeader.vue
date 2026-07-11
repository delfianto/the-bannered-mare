<script setup lang="ts">
import { ref } from "vue";
import type { ChatCharacterInfo } from "@/types/chat";
import type { Profile } from "@/composables/useProfiles";
import ChatDrawer from "@/components/chat/ChatDrawer.vue";

interface PickerModel {
  id: string;
  display_name: string;
}

const props = defineProps<{
  character: ChatCharacterInfo;
  chatId?: string;
  sessionTitle: string;
  profiles?: Profile[];
  currentProfileName?: string | null;
  models?: PickerModel[];
  currentModelId?: string | null;
  currentModelName?: string | null;
  currentTaskModelId?: string | null;
  currentPersonaId?: string | null;
}>();

const emit = defineEmits<{
  back: [];
  rename: [title: string];
  delete: [];
  applyProfile: [profileId: string];
  changeModel: [modelId: string];
  changeTaskModel: [modelId: string | null];
  changePersona: [personaId: string | null];
}>();

const drawerOpen = ref(false);

function avatarSrc(): string {
  return (
    props.character.avatar_thumbnail ||
    props.character.avatar ||
    `https://ui-avatars.com/api/?name=${encodeURIComponent(props.character.name)}&background=C9922E&color=fff&size=80`
  );
}
</script>

<template>
  <header
    class="z-10 grid h-15.5 shrink-0 grid-cols-3 items-center border-b bg-base-100/80 px-5 backdrop-blur-sm"
  >
    <button
      :aria-label="$t('common.goBack')"
      class="flex size-9 items-center justify-center justify-self-start rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
      @click="emit('back')"
    >
      <AppIcon name="i-lucide-arrow-left" class="size-5" />
    </button>

    <!-- Center third stays dead-centered regardless of the side zones' widths,
         so changing the side controls never shifts the heading. -->
    <div class="flex min-w-0 items-center justify-center gap-3 justify-self-center">
      <div class="relative shrink-0">
        <img
          :src="avatarSrc()"
          :alt="character.name"
          class="size-9 rounded-full object-cover ring-2 ring-primary/30"
        />
        <div
          class="absolute right-0 bottom-0 size-2.5 rounded-full border-2 border-base-100 bg-emerald-500"
        />
      </div>
      <div class="min-w-0 text-center">
        <h2
          class="truncate font-cinzel text-sm leading-tight font-semibold text-foreground"
          style="letter-spacing: 0.03em"
        >
          {{ character.name }}
        </h2>
        <p class="mt-0.5 truncate text-[0.6875rem] leading-tight text-muted-foreground">
          {{ sessionTitle }}
        </p>
      </div>
    </div>

    <div class="flex items-center justify-self-end">
      <button
        :aria-label="$t('chat.sessionMenu')"
        class="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
        @click="drawerOpen = true"
      >
        <AppIcon name="i-lucide-more-horizontal" class="size-5" />
      </button>

      <ChatDrawer
        :show="drawerOpen"
        :character="character"
        :chat-id="chatId"
        :session-title="sessionTitle"
        :models="models ?? []"
        :current-model-id="currentModelId"
        :current-model-name="currentModelName"
        :current-task-model-id="currentTaskModelId"
        :profiles="profiles ?? []"
        :current-profile-name="currentProfileName"
        :current-persona-id="currentPersonaId"
        @close="drawerOpen = false"
        @rename="emit('rename', $event)"
        @delete="emit('delete')"
        @change-model="emit('changeModel', $event)"
        @change-task-model="emit('changeTaskModel', $event)"
        @apply-profile="emit('applyProfile', $event)"
        @change-persona="emit('changePersona', $event)"
      />
    </div>
  </header>
</template>

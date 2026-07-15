<script setup lang="ts">
import { fallbackAvatarUrl } from "@/utils/avatar";
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import type { Chat } from "@/types/chat";
import { timeAgo as timeAgoUtil } from "@/utils/date";

const { t } = useI18n();

const props = defineProps<{
  sessions: Chat[];
  activeSessionId: string;
  loading?: boolean;
}>();

const emit = defineEmits<{
  select: [id: string];
}>();

const search = ref("");

const filtered = computed(() => {
  if (!search.value) return props.sessions;
  const q = search.value.toLowerCase();
  return props.sessions.filter(
    (s) => s.character.name.toLowerCase().includes(q) || (s.title ?? "").toLowerCase().includes(q),
  );
});

function timeAgo(dateStr: string): string {
  return timeAgoUtil(dateStr, t);
}

function avatarSrc(chat: Chat): string {
  return (
    chat.character.avatar_thumbnail ||
    chat.character.avatar ||
    fallbackAvatarUrl(chat.character.name, 80)
  );
}
</script>

<template>
  <div class="flex h-full w-75 min-w-75 flex-col border-r bg-base-200">
    <!-- Search -->
    <div class="px-3 pt-4 pb-3">
      <div class="flex items-center gap-2 rounded-lg border bg-base-100/60 px-3 py-2">
        <AppIcon name="i-lucide-search" class="size-3.5 shrink-0 text-muted-foreground" />
        <input
          v-model="search"
          type="text"
          :placeholder="$t('chat.searchPlaceholder')"
          :aria-label="$t('chat.searchPlaceholder')"
          autocomplete="off"
          class="flex-1 bg-transparent text-xs text-foreground outline-none placeholder:text-muted-foreground"
        />
      </div>
    </div>

    <!-- Label -->
    <p class="mb-1.5 px-5 text-3xs font-semibold tracking-widest text-muted-foreground uppercase">
      {{ $t("chat.activeTales") }}
    </p>

    <!-- Loading -->
    <div v-if="loading" class="flex flex-1 items-center justify-center">
      <AppIcon name="i-lucide-loader-circle" class="size-5 animate-spin text-muted-foreground" />
    </div>

    <!-- Session List -->
    <div v-else class="flex-1 space-y-0.5 overflow-y-auto px-2">
      <button
        v-for="session in filtered"
        :key="session.id"
        class="group relative flex w-full items-start gap-3 rounded-xl p-3 text-left transition-all duration-200"
        :class="session.id === activeSessionId ? 'bg-base-300' : 'hover:bg-base-300/50'"
        @click="emit('select', session.id)"
      >
        <!-- Active bar -->
        <span
          v-if="session.id === activeSessionId"
          class="absolute top-1/2 left-0 h-6 w-0.75 -translate-y-1/2 rounded-full bg-primary"
        />

        <!-- Avatar -->
        <div class="relative shrink-0">
          <img
            :src="avatarSrc(session)"
            :alt="session.character.name"
            class="size-10 rounded-full object-cover ring-1 ring-border"
          />
        </div>

        <!-- Info -->
        <div class="min-w-0 flex-1">
          <div class="flex items-center justify-between gap-1">
            <p class="truncate text-sm font-medium text-foreground">
              {{ session.character.name }}
            </p>
            <span class="shrink-0 text-3xs text-muted-foreground">
              {{ timeAgo(session.updated_at) }}
            </span>
          </div>
          <p class="mt-0.5 truncate font-cinzel text-2xs text-primary/80">
            {{ session.title || $t("chat.untitled") }}
          </p>
          <p
            v-if="session.preview"
            class="mt-0.5 line-clamp-1 text-2xs leading-relaxed text-muted-foreground italic"
          >
            {{ session.preview }}
          </p>
        </div>
      </button>
    </div>
  </div>
</template>

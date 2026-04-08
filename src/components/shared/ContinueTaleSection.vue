<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import type { components } from "@/api/schema";

type Chat = components["schemas"]["ChatResponse"];

const { t } = useI18n();

defineProps<{
  sessions: Chat[];
  loading?: boolean;
}>();

const scrollContainer = ref<HTMLElement | null>(null);

function scroll(direction: "left" | "right") {
  if (!scrollContainer.value) return;
  scrollContainer.value.scrollBy({
    left: direction === "left" ? -320 : 320,
    behavior: "smooth",
  });
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return t('time.justNow');
  if (mins < 60) return t('time.minutesAgo', { count: mins });
  const hours = Math.floor(mins / 60);
  if (hours < 24) return t('time.hoursAgo', { count: hours });
  const days = Math.floor(hours / 24);
  return t('time.daysAgo', { count: days });
}

function avatarSrc(chat: Chat): string {
  return chat.character.avatar_thumbnail
    || chat.character.avatar
    || `https://ui-avatars.com/api/?name=${encodeURIComponent(chat.character.name)}&background=C9922E&color=fff&size=600`;
}
</script>

<template>
  <section>
    <div class="mb-4 flex items-center justify-between">
      <h2 class="font-cinzel text-lg font-semibold tracking-wide text-foreground">
        {{ $t('home.continueTale') }}
      </h2>
      <div class="flex items-center gap-1.5">
        <button
          :aria-label="$t('bookmarks.scrollLeft')"
          class="flex h-8 w-8 items-center justify-center rounded-lg border text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          @click="scroll('left')"
        >
          <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
        </button>
        <button
          :aria-label="$t('bookmarks.scrollRight')"
          class="flex h-8 w-8 items-center justify-center rounded-lg border text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          @click="scroll('right')"
        >
          <UIcon name="i-lucide-chevron-right" class="h-4 w-4" />
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-8">
      <UIcon name="i-lucide-loader-circle" class="h-5 w-5 animate-spin text-muted-foreground" />
    </div>

    <div v-else ref="scrollContainer" class="scrollbar-hide flex gap-4 overflow-x-auto pb-2">
      <RouterLink
        v-for="(session, i) in sessions"
        :key="session.id"
        :to="{ name: 'chat', params: { chatId: session.id } }"
        class="group relative h-[160px] w-[280px] flex-shrink-0 cursor-pointer overflow-hidden rounded-xl animate-fade-in-up"
        :style="{ animationDelay: `${i * 80}ms` }"
      >
        <!-- Background image -->
        <img
          :src="avatarSrc(session)"
          :alt="session.title ?? $t('chat.untitled')"
          class="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        />

        <!-- Gradient overlay -->
        <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent" />

        <!-- Content -->
        <div class="absolute bottom-0 left-0 right-0 p-4">
          <h3 class="mb-1 text-sm font-semibold text-white drop-shadow-md">
            {{ session.title || $t('chat.untitled') }}
          </h3>
          <p class="mb-2 text-xs text-white/70">with {{ session.character.name }}</p>
          <div class="flex items-center gap-3 text-[11px] text-white/60">
            <span class="flex items-center gap-1">
              <UIcon name="i-lucide-clock" class="h-3 w-3" />
              {{ timeAgo(session.updated_at) }}
            </span>
          </div>
        </div>

        <!-- Hover glow ring -->
        <div
          class="absolute inset-0 rounded-xl ring-2 ring-inset ring-primary/40 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        />
      </RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { fallbackAvatarUrl } from "@/utils/avatar";
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import type { components } from "@/api/schema";
import { timeAgo as timeAgoUtil } from "@/utils/date";

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
  return timeAgoUtil(dateStr, t);
}

function avatarSrc(chat: Chat): string {
  // Large tier: this is a full-bleed banner, so the head-crop thumbnail would be
  // too tightly cropped — use the large full portrait.
  return (
    chat.character.avatar_large ||
    chat.character.avatar ||
    fallbackAvatarUrl(chat.character.name, 600)
  );
}
</script>

<template>
  <section>
    <div class="mb-4 flex items-center justify-between">
      <h2 class="font-cinzel text-lg font-semibold tracking-wide text-foreground">
        {{ $t("home.continueTale") }}
      </h2>
      <div class="flex items-center gap-1.5">
        <button
          :aria-label="$t('bookmarks.scrollLeft')"
          class="flex size-8 items-center justify-center rounded-lg border text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
          @click="scroll('left')"
        >
          <AppIcon name="i-lucide-chevron-left" class="size-4" />
        </button>
        <button
          :aria-label="$t('bookmarks.scrollRight')"
          class="flex size-8 items-center justify-center rounded-lg border text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
          @click="scroll('right')"
        >
          <AppIcon name="i-lucide-chevron-right" class="size-4" />
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-8">
      <AppIcon name="i-lucide-loader-circle" class="size-5 animate-spin text-muted-foreground" />
    </div>

    <div v-else ref="scrollContainer" class="scrollbar-hide flex gap-4 overflow-x-auto pb-2">
      <RouterLink
        v-for="(session, i) in sessions"
        :key="session.id"
        :to="{ name: 'chat', params: { chatId: session.id } }"
        class="group relative h-40 w-70 shrink-0 animate-fade-in-up cursor-pointer overflow-hidden rounded-xl"
        :style="{ animationDelay: `${i * 80}ms` }"
      >
        <!-- Background image -->
        <img
          :src="avatarSrc(session)"
          :alt="session.title ?? $t('chat.untitled')"
          class="absolute inset-0 size-full object-cover transition-transform duration-500 group-hover:scale-105"
        />

        <!-- Gradient overlay -->
        <div class="absolute inset-0 bg-linear-to-t from-black/80 via-black/30 to-transparent" />

        <!-- Content -->
        <div class="absolute inset-x-0 bottom-0 p-4">
          <h3 class="mb-1 text-sm font-semibold text-white drop-shadow-md">
            {{ session.title || $t("chat.untitled") }}
          </h3>
          <p class="mb-2 text-xs text-white/70">with {{ session.character.name }}</p>
          <div class="flex items-center gap-3 text-2xs text-white/60">
            <span class="flex items-center gap-1">
              <AppIcon name="i-lucide-clock" class="size-3" />
              {{ timeAgo(session.updated_at) }}
            </span>
          </div>
        </div>

        <!-- Hover glow ring -->
        <div
          class="absolute inset-0 rounded-xl opacity-0 ring-2 ring-primary/40 transition-opacity duration-300 ring-inset group-hover:opacity-100"
        />
      </RouterLink>
    </div>
  </section>
</template>

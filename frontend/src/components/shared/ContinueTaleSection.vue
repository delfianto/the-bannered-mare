<script setup lang="ts">
import { fallbackAvatarUrl } from "@/utils/avatar";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { components } from "@/api/schema";
import { timeAgo as timeAgoUtil } from "@/utils/date";

type Chat = components["schemas"]["ChatResponse"];

const { t } = useI18n();

const props = defineProps<{
  sessions: Chat[];
  loading?: boolean;
}>();

const featured = computed(() => props.sessions[0]);
const recent = computed(() => props.sessions.slice(1, 5));

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
    <div class="mb-6 flex items-center gap-4">
      <h2
        class="shrink-0 font-story text-xs font-semibold tracking-[0.18em] text-muted-foreground uppercase"
      >
        {{ $t("home.continueTale") }}
      </h2>
      <div class="h-px flex-1 bg-border" />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-8">
      <AppIcon name="i-lucide-loader-circle" class="size-5 animate-spin text-muted-foreground" />
    </div>

    <div v-else-if="featured" class="grid gap-8 lg:grid-cols-12">
      <article
        class="group relative min-h-100 overflow-hidden rounded-sm border bg-base-300 lg:col-span-8"
      >
        <img
          :src="avatarSrc(featured)"
          :alt="featured.title ?? $t('chat.untitled')"
          class="absolute inset-0 size-full object-cover object-top transition-transform duration-700 group-hover:scale-[1.03]"
        />
        <div class="absolute inset-0 bg-linear-to-r from-black/65 via-black/15 to-transparent" />

        <div
          class="absolute right-0 bottom-0 left-0 border-t bg-base-100/95 p-6 shadow-xl backdrop-blur-sm sm:right-auto sm:max-w-lg sm:border-r sm:p-8"
        >
          <div class="mb-3 flex items-center gap-3">
            <span class="text-2xs font-semibold tracking-[0.18em] text-primary uppercase">
              {{ $t("home.continueTale") }}
            </span>
            <span class="h-px flex-1 bg-border" />
          </div>
          <h3 class="mb-2 font-story text-2xl font-semibold leading-snug text-foreground">
            {{ featured.title || $t("chat.untitled") }}
          </h3>
          <p
            v-if="featured.preview"
            class="mb-5 line-clamp-2 text-sm leading-relaxed text-muted-foreground"
          >
            {{ featured.preview }}
          </p>
          <div class="flex flex-wrap items-center justify-between gap-4">
            <div class="text-xs text-muted-foreground">
              <span>{{ featured.character.name }}</span>
              <span class="mx-1.5 text-border">·</span>
              <span>{{ timeAgo(featured.updated_at) }}</span>
            </div>
            <RouterLink
              :to="{ name: 'chat', params: { chatId: featured.id } }"
              class="group/action inline-flex h-10 items-center gap-2 rounded-sm bg-foreground px-4 text-xs font-semibold tracking-wide text-base-100 uppercase transition-colors hover:bg-primary hover:text-primary-content"
            >
              {{ $t("home.continueTale") }}
              <AppIcon
                name="i-lucide-arrow-right"
                class="size-3.5 transition-transform group-hover/action:translate-x-0.5"
              />
            </RouterLink>
          </div>
        </div>
      </article>

      <aside v-if="recent.length" class="flex flex-col lg:col-span-4">
        <div class="mb-5 flex items-center gap-3 border-b pb-3">
          <span
            class="font-story text-xs font-semibold tracking-[0.16em] text-muted-foreground uppercase"
          >
            {{ $t("nav.sessions") }}
          </span>
          <span class="font-story text-2xs text-primary">II–V</span>
        </div>
        <div class="divide-y">
          <RouterLink
            v-for="(session, i) in recent"
            :key="session.id"
            :to="{ name: 'chat', params: { chatId: session.id } }"
            class="group flex items-center gap-4 py-4 first:pt-0"
          >
            <img
              :src="avatarSrc(session)"
              :alt="session.character.name"
              class="h-18 w-14 shrink-0 rounded-sm object-cover grayscale-25 transition-all duration-500 group-hover:grayscale-0"
            />
            <div class="min-w-0 flex-1">
              <p
                class="truncate font-story text-sm font-medium text-foreground transition-colors group-hover:text-primary"
              >
                {{ session.title || $t("chat.untitled") }}
              </p>
              <p class="mt-1 truncate text-xs text-muted-foreground">
                {{ session.character.name }}
              </p>
              <p class="mt-2 text-2xs tracking-wider text-muted-foreground uppercase">
                {{ timeAgo(session.updated_at) }}
              </p>
            </div>
            <span class="font-story text-2xs text-muted-foreground">{{ i + 2 }}</span>
          </RouterLink>
        </div>
        <RouterLink
          to="/chats"
          class="mt-auto inline-flex items-center gap-1 self-start pt-4 text-2xs font-semibold tracking-[0.14em] text-muted-foreground uppercase transition-colors hover:text-primary"
        >
          {{ $t("home.browseAll") }}
          <AppIcon name="i-lucide-arrow-right" class="size-3" />
        </RouterLink>
      </aside>
    </div>
  </section>
</template>

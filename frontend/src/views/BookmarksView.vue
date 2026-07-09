<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import { useBookmarks } from "@/composables/useBookmarks";
import NarrativeText from "@/components/chat/NarrativeText.vue";
import EmptyState from "@/components/shared/EmptyState.vue";
import PageContainer from "@/components/layout/PageContainer.vue";

const { t } = useI18n();
const { characters, sessions, messages, loading, totalCount } = useBookmarks();

const scrollContainer = ref<HTMLElement | null>(null);

function scroll(direction: "left" | "right") {
  scrollContainer.value?.scrollBy({
    left: direction === "left" ? -320 : 320,
    behavior: "smooth",
  });
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return t("time.minutesAgo", { count: mins });
  const hours = Math.floor(mins / 60);
  if (hours < 24) return t("time.hoursAgo", { count: hours });
  const days = Math.floor(hours / 24);
  if (days < 7) return t("time.daysAgo", { count: days });
  const weeks = Math.floor(days / 7);
  return t("time.weeksAgo", { count: weeks });
}
</script>

<template>
  <PageContainer spacing-class="space-y-10">
    <template #header>
      <div>
        <h1 class="font-cinzel text-2xl font-bold tracking-wide text-foreground">
          {{ $t("bookmarks.title") }}
        </h1>
        <p class="mt-1 text-sm text-muted-foreground">
          {{ $t("bookmarks.subtitle") }}
        </p>
      </div>
    </template>

    <!-- Loading -->
    <div v-if="loading" class="flex flex-1 items-center justify-center py-20">
      <AppIcon name="i-lucide-loader-circle" class="size-6 animate-spin text-muted-foreground" />
    </div>

    <!-- Empty state -->
    <EmptyState
      v-else-if="totalCount === 0"
      icon="i-lucide-bookmark"
      :title="$t('bookmarks.noBookmarks')"
      description="You haven't bookmarked any sessions, messages, or favorite characters yet."
    />

    <template v-else>
      <!-- Section 1: Favorite Characters -->
      <section
        v-if="characters.length > 0"
        class="animate-fade-in-up"
        style="animation-delay: 100ms"
      >
        <div class="mb-5 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <h2 class="font-cinzel text-lg font-semibold tracking-wide text-foreground">
              {{ $t("bookmarks.favoriteCharacters") }}
            </h2>
            <span
              class="rounded-full bg-primary/15 px-2.5 py-0.5 text-[0.625rem] font-bold tracking-wide text-primary uppercase"
            >
              {{ characters.length }}
            </span>
          </div>
          <div class="flex items-center gap-1.5">
            <button
              class="flex size-8 items-center justify-center rounded-lg border text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
              :aria-label="$t('bookmarks.scrollLeft')"
              @click="scroll('left')"
            >
              <AppIcon name="i-lucide-chevron-left" class="size-4" />
            </button>
            <button
              class="flex size-8 items-center justify-center rounded-lg border text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
              :aria-label="$t('bookmarks.scrollRight')"
              @click="scroll('right')"
            >
              <AppIcon name="i-lucide-chevron-right" class="size-4" />
            </button>
          </div>
        </div>

        <div ref="scrollContainer" class="scrollbar-hide flex gap-5 overflow-x-auto pb-4">
          <RouterLink
            v-for="(char, i) in characters"
            :key="char.id"
            :to="`/characters/${char.id}`"
            class="group relative aspect-3/4 w-55 min-w-55 animate-fade-in-up cursor-pointer overflow-hidden rounded-xl border bg-base-200 transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_8px_32px_var(--color-primary)/0.12]"
            :style="{ animationDelay: `${i * 60}ms` }"
          >
            <img
              :src="char.avatar"
              :alt="char.name"
              class="absolute inset-0 size-full object-cover transition-transform duration-700 group-hover:scale-105"
            />
            <div
              class="absolute inset-0 bg-linear-to-t from-black/85 via-black/20 to-transparent"
            />
            <div class="absolute inset-x-0 bottom-0 p-4">
              <h3 class="font-cinzel text-sm font-semibold tracking-wide text-white">
                {{ char.name }}
              </h3>
              <div v-if="char.tags?.length" class="mt-1.5 flex flex-wrap gap-1">
                <span
                  v-for="tag in char.tags.slice(0, 2)"
                  :key="tag"
                  class="rounded-full border border-white/10 bg-white/10 px-2 py-0.5 text-[0.5rem] font-medium tracking-widest text-white/80 uppercase backdrop-blur-sm"
                >
                  {{ tag }}
                </span>
              </div>
            </div>
          </RouterLink>
        </div>
      </section>

      <!-- Section 2: Bookmarked Sessions -->
      <section v-if="sessions.length > 0" class="animate-fade-in-up" style="animation-delay: 200ms">
        <div class="mb-5 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <h2 class="font-cinzel text-lg font-semibold tracking-wide text-foreground">
              {{ $t("bookmarks.savedSessions") }}
            </h2>
            <span
              class="rounded-full bg-primary/15 px-2.5 py-0.5 text-[0.625rem] font-bold tracking-wide text-primary uppercase"
            >
              {{ sessions.length }}
            </span>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <RouterLink
            v-for="(session, i) in sessions"
            :key="session.id"
            :to="`/chats/${session.id}`"
            class="group flex animate-fade-in-up items-center gap-4 rounded-xl border bg-base-200/50 p-4 transition-all hover:bg-base-300/30"
            :style="{ animationDelay: `${i * 50 + 200}ms` }"
          >
            <img
              :src="session.character?.avatar_thumbnail || session.character?.avatar"
              :alt="session.character?.name"
              class="size-12 shrink-0 rounded-full object-cover ring-1 ring-border"
            />
            <div class="min-w-0 flex-1">
              <h3 class="truncate font-cinzel text-sm font-semibold text-foreground">
                {{ session.title }}
              </h3>
              <p class="mt-0.5 text-[0.625rem] font-medium tracking-wide text-primary uppercase">
                {{ $t("bookmarks.with", { name: session.character?.name }) }}
              </p>
            </div>
            <span class="text-[0.625rem] whitespace-nowrap text-muted-foreground">
              {{ timeAgo(session.bookmarked_at || session.updated_at) }}
            </span>
          </RouterLink>
        </div>
      </section>

      <!-- Section 3: Pinned Messages -->
      <section
        v-if="messages.length > 0"
        class="animate-fade-in-up pb-10"
        style="animation-delay: 300ms"
      >
        <div class="mb-5 flex items-center gap-3">
          <h2 class="font-cinzel text-lg font-semibold tracking-wide text-foreground">
            {{ $t("bookmarks.pinnedFragments") }}
          </h2>
          <span
            class="rounded-full bg-primary/15 px-2.5 py-0.5 text-[0.625rem] font-bold tracking-wide text-primary uppercase"
          >
            {{ messages.length }}
          </span>
        </div>

        <div class="space-y-5">
          <div
            v-for="(msg, i) in messages"
            :key="msg.id"
            class="group animate-fade-in-up rounded-xl border bg-base-200/50 p-5 transition-all hover:shadow-lg"
            :style="{ animationDelay: `${i * 60 + 300}ms` }"
          >
            <!-- Message header -->
            <div class="mb-3 flex items-start justify-between">
              <div class="flex items-center gap-3">
                <img
                  :src="msg.character.avatar"
                  :alt="msg.character.name"
                  class="size-10 rounded-full object-cover ring-1 ring-border"
                />
                <div>
                  <h4 class="font-cinzel text-sm font-bold text-foreground">
                    {{ msg.character.name }}
                  </h4>
                  <p class="text-[0.625rem] tracking-widest text-muted-foreground uppercase">
                    {{ $t("bookmarks.from") }}
                    <RouterLink :to="`/chats/${msg.chat.id}`" class="text-primary hover:underline">
                      {{ msg.chat.title }}
                    </RouterLink>
                  </p>
                </div>
              </div>
              <span class="text-[0.625rem] text-muted-foreground">
                {{ timeAgo(msg.created_at) }}
              </span>
            </div>

            <!-- Message content -->
            <NarrativeText :content="msg.content" />

            <!-- Footer -->
            <div class="mt-4 flex items-center justify-end border-t border-border/30 pt-3">
              <button
                class="text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 hover:text-error"
                :aria-label="$t('bookmarks.removeBookmark')"
              >
                <AppIcon name="i-lucide-trash-2" class="size-4" />
              </button>
            </div>
          </div>
        </div>
      </section>
    </template>
  </PageContainer>
</template>

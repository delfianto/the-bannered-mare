<script setup lang="ts">
import { ref } from "vue";
import { useBookmarks } from "@/composables/useBookmarks";
import NarrativeText from "@/components/chat/NarrativeText.vue";

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
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  const weeks = Math.floor(days / 7);
  return `${weeks}w ago`;
}
</script>

<template>
  <div class="space-y-10 px-8 py-8 lg:px-12">
    <!-- Loading -->
    <div v-if="loading" class="flex flex-1 items-center justify-center py-20">
      <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin text-muted-foreground" />
    </div>

    <!-- Empty state -->
    <div
      v-else-if="totalCount === 0"
      class="flex flex-col items-center justify-center gap-3 py-20"
    >
      <UIcon name="i-lucide-bookmark" class="h-10 w-10 text-muted-foreground/40" />
      <p class="text-sm text-muted-foreground">No bookmarks yet</p>
    </div>

    <template v-else>
      <!-- Header -->
      <header class="animate-fade-in-up">
        <div class="flex items-center gap-4">
          <div
            class="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary"
          >
            <UIcon name="i-lucide-bookmark" class="h-7 w-7" />
          </div>
          <div>
            <h1 class="font-cinzel text-2xl font-bold tracking-wide text-foreground">
              Bookmarks
            </h1>
            <p class="mt-0.5 text-sm text-muted-foreground">
              Curated highlights from your tales across the realms
            </p>
          </div>
        </div>
      </header>

      <!-- Section 1: Favorite Characters -->
      <section
        v-if="characters.length > 0"
        class="animate-fade-in-up"
        style="animation-delay: 100ms"
      >
        <div class="mb-5 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <h2
              class="font-cinzel text-lg font-semibold tracking-wide text-foreground"
            >
              Favorite Characters
            </h2>
            <span
              class="rounded-full bg-primary/15 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-primary"
            >
              {{ characters.length }}
            </span>
          </div>
          <div class="flex items-center gap-1.5">
            <button
              class="flex h-8 w-8 items-center justify-center rounded-lg border text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              aria-label="Scroll left"
              @click="scroll('left')"
            >
              <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
            </button>
            <button
              class="flex h-8 w-8 items-center justify-center rounded-lg border text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              aria-label="Scroll right"
              @click="scroll('right')"
            >
              <UIcon name="i-lucide-chevron-right" class="h-4 w-4" />
            </button>
          </div>
        </div>

        <div
          ref="scrollContainer"
          class="scrollbar-hide flex gap-5 overflow-x-auto pb-4"
        >
          <RouterLink
            v-for="(char, i) in characters"
            :key="char.id"
            :to="`/characters/${char.id}`"
            class="group relative aspect-[3/4] w-[220px] min-w-[220px] animate-fade-in-up cursor-pointer overflow-hidden rounded-xl border bg-card transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_8px_32px_var(--color-primary)/0.12]"
            :style="{ animationDelay: `${i * 60}ms` }"
          >
            <img
              :src="char.avatar"
              :alt="char.name"
              class="absolute inset-0 h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
            />
            <div
              class="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent"
            />
            <div class="absolute bottom-0 left-0 right-0 p-4">
              <h3
                class="font-cinzel text-sm font-semibold tracking-wide text-white"
              >
                {{ char.name }}
              </h3>
              <div v-if="char.tags?.length" class="mt-1.5 flex flex-wrap gap-1">
                <span
                  v-for="tag in char.tags.slice(0, 2)"
                  :key="tag"
                  class="rounded-full border border-white/10 bg-white/10 px-2 py-0.5 text-[8px] font-medium uppercase tracking-widest text-white/80 backdrop-blur-sm"
                >
                  {{ tag }}
                </span>
              </div>
            </div>
          </RouterLink>
        </div>
      </section>

      <!-- Section 2: Bookmarked Sessions -->
      <section
        v-if="sessions.length > 0"
        class="animate-fade-in-up"
        style="animation-delay: 200ms"
      >
        <div class="mb-5 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <h2
              class="font-cinzel text-lg font-semibold tracking-wide text-foreground"
            >
              Saved Sessions
            </h2>
            <span
              class="rounded-full bg-primary/15 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-primary"
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
            class="group flex animate-fade-in-up items-center gap-4 rounded-xl border bg-card/50 p-4 transition-all hover:bg-accent/30"
            :style="{ animationDelay: `${i * 50 + 200}ms` }"
          >
            <img
              :src="session.character?.avatar_thumbnail || session.character?.avatar"
              :alt="session.character?.name"
              class="h-12 w-12 flex-shrink-0 rounded-full object-cover ring-1 ring-border"
            />
            <div class="min-w-0 flex-1">
              <h3
                class="truncate font-cinzel text-sm font-semibold text-foreground"
              >
                {{ session.title }}
              </h3>
              <p
                class="mt-0.5 text-[10px] font-medium uppercase tracking-wide text-primary"
              >
                with {{ session.character?.name }}
              </p>
            </div>
            <span class="whitespace-nowrap text-[10px] text-muted-foreground">
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
          <h2
            class="font-cinzel text-lg font-semibold tracking-wide text-foreground"
          >
            Pinned Fragments
          </h2>
          <span
            class="rounded-full bg-primary/15 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-primary"
          >
            {{ messages.length }}
          </span>
        </div>

        <div class="space-y-5">
          <div
            v-for="(msg, i) in messages"
            :key="msg.id"
            class="group animate-fade-in-up rounded-xl border bg-card/50 p-5 transition-all hover:shadow-lg"
            :style="{ animationDelay: `${i * 60 + 300}ms` }"
          >
            <!-- Message header -->
            <div class="mb-3 flex items-start justify-between">
              <div class="flex items-center gap-3">
                <img
                  :src="msg.character.avatar"
                  :alt="msg.character.name"
                  class="h-10 w-10 rounded-full object-cover ring-1 ring-border"
                />
                <div>
                  <h4
                    class="font-cinzel text-sm font-bold text-foreground"
                  >
                    {{ msg.character.name }}
                  </h4>
                  <p class="text-[10px] uppercase tracking-widest text-muted-foreground">
                    From:
                    <RouterLink
                      :to="`/chats/${msg.chat.id}`"
                      class="text-primary hover:underline"
                    >
                      {{ msg.chat.title }}
                    </RouterLink>
                  </p>
                </div>
              </div>
              <span class="text-[10px] text-muted-foreground">
                {{ timeAgo(msg.created_at) }}
              </span>
            </div>

            <!-- Message content -->
            <NarrativeText :content="msg.content" />

            <!-- Footer -->
            <div
              class="mt-4 flex items-center justify-end border-t border-border/30 pt-3"
            >
              <button
                class="text-muted-foreground opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100"
                aria-label="Remove bookmark"
              >
                <UIcon name="i-lucide-trash-2" class="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

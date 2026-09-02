<script setup lang="ts">
import { useRouter } from "vue-router";
import { useChatSessions } from "@/composables/useChatSessions";
import { useCharacters } from "@/composables/useCharacters";
import SearchBar from "@/components/shared/SearchBar.vue";
import ContinueTaleSection from "@/components/shared/ContinueTaleSection.vue";
import DiscoverSection from "@/components/shared/DiscoverSection.vue";
import SetupPromptBanner from "@/components/shared/SetupPromptBanner.vue";
import EmptyState from "@/components/shared/EmptyState.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import { CATEGORIES } from "@/constants/discoverData";

const router = useRouter();
const { chatSessions, loading: chatsLoading } = useChatSessions({ pageSize: 8 });
// Home shows a curated preview; the full library (with endless scroll) is a click away.
const { characters, loading: charsLoading } = useCharacters({ pageSize: 12 });
</script>

<template>
  <PageContainer spacing-class="space-y-10">
    <template #header>
      <div
        class="mx-auto flex w-full max-w-7xl flex-col gap-6 md:flex-row md:items-end md:justify-between"
      >
        <div>
          <p class="mb-3 text-2xs font-semibold tracking-[0.22em] text-primary uppercase">
            The Bannered Mare
          </p>
          <h1
            class="mb-2 font-story text-3xl font-semibold tracking-wide text-foreground lg:text-4xl"
          >
            {{ $t("home.greeting") }}
          </h1>
          <p class="text-sm text-muted-foreground italic">
            {{ $t("home.tagline") }}
          </p>
        </div>
        <SearchBar v-if="characters.length > 0" class="w-full md:w-100" />
      </div>
    </template>

    <div class="mx-auto flex w-full max-w-7xl flex-1 flex-col space-y-12">
      <!-- Setup prompt (renders nothing once a ready profile exists — no gap) -->
      <SetupPromptBanner />

      <template v-if="charsLoading || chatsLoading">
        <div class="flex flex-1 items-center justify-center py-16">
          <AppIcon
            name="i-lucide-loader-circle"
            class="size-6 animate-spin text-muted-foreground"
          />
        </div>
      </template>
      <template v-else-if="characters.length === 0 && chatSessions.length === 0">
        <div class="flex flex-1 animate-fade-in-up flex-col" style="animation-delay: 80ms">
          <EmptyState
            icon="i-lucide-sparkles"
            title="Welcome to The Bannered Mare"
            description="Start your journey by creating your first character loadout, or import characters from SillyTavern."
            action-label="Create Your First Character"
            @action="router.push('/characters/create')"
          />
        </div>
      </template>
      <template v-else>
        <!-- Continue Your Tale (from API chats) -->
        <div
          v-if="chatSessions.length > 0"
          class="animate-fade-in-up"
          style="animation-delay: 80ms"
        >
          <ContinueTaleSection :sessions="chatSessions" :loading="chatsLoading" />
        </div>

        <!-- Discover Characters (from API characters) -->
        <div v-if="characters.length > 0" class="animate-fade-in-up" style="animation-delay: 160ms">
          <DiscoverSection
            :characters="characters"
            :categories="CATEGORIES"
            :loading="charsLoading"
            browse-all-to="/characters"
          />
        </div>
      </template>
    </div>
  </PageContainer>
</template>

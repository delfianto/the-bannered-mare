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
const { characters, loading: charsLoading } = useCharacters({ pageSize: 6 });
</script>

<template>
  <PageContainer>
    <template #header>
      <div>
        <h1 class="mb-1 font-cinzel text-2xl font-bold tracking-wide text-foreground">
          {{ $t("home.greeting") }}
        </h1>
        <p class="text-sm text-muted-foreground">
          {{ $t("home.tagline") }}
        </p>
      </div>
    </template>

    <div class="flex w-full flex-1 flex-col space-y-8">
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
        <!-- Search -->
        <div v-if="characters.length > 0" class="animate-fade-in-up" style="animation-delay: 80ms">
          <SearchBar />
        </div>

        <!-- Continue Your Tale (from API chats) -->
        <div
          v-if="chatSessions.length > 0"
          class="animate-fade-in-up"
          style="animation-delay: 160ms"
        >
          <ContinueTaleSection :sessions="chatSessions" :loading="chatsLoading" />
        </div>

        <!-- Discover Characters (from API characters) -->
        <div v-if="characters.length > 0" class="animate-fade-in-up" style="animation-delay: 240ms">
          <DiscoverSection
            :characters="characters"
            :categories="CATEGORIES"
            :loading="charsLoading"
          />
        </div>
      </template>
    </div>
  </PageContainer>
</template>

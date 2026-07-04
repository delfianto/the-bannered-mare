<script setup lang="ts">
import { useRouter } from "vue-router";
import { useChatSessions } from "@/composables/useChatSessions";
import { useCharacters } from "@/composables/useCharacters";
import SearchBar from "@/components/shared/SearchBar.vue";
import ContinueTaleSection from "@/components/shared/ContinueTaleSection.vue";
import DiscoverSection from "@/components/shared/DiscoverSection.vue";
import SetupPromptBanner from "@/components/shared/SetupPromptBanner.vue";
import EmptyState from "@/components/discover/EmptyState.vue";
import { CATEGORIES } from "@/constants/discoverData";

const router = useRouter();
const { chatSessions, loading: chatsLoading } = useChatSessions({ pageSize: 8 });
const { characters, loading: charsLoading } = useCharacters({ pageSize: 6 });
</script>

<template>
  <div class="space-y-8 px-12 py-8">
    <!-- Greeting -->
    <div class="animate-fade-in-up">
      <h1 class="mb-1 font-cinzel text-2xl font-bold tracking-wide text-foreground">
        {{ $t("home.greeting") }}
      </h1>
      <p class="text-sm text-muted-foreground">
        {{ $t("home.tagline") }}
      </p>
    </div>

    <!-- Setup prompt (only shown when no profiles exist yet) -->
    <div class="animate-fade-in-up" style="animation-delay: 40ms">
      <SetupPromptBanner />
    </div>

    <template v-if="charsLoading || chatsLoading">
      <div class="flex justify-center py-16">
        <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    </template>
    <template v-else-if="characters.length === 0 && chatSessions.length === 0">
      <div class="animate-fade-in-up" style="animation-delay: 80ms">
        <EmptyState :has-filters="false" @create-new="router.push('/characters/create')" />
      </div>
    </template>
    <template v-else>
      <!-- Search -->
      <div v-if="characters.length > 0" class="animate-fade-in-up" style="animation-delay: 80ms">
        <SearchBar />
      </div>

      <!-- Continue Your Tale (from API chats) -->
      <div v-if="chatSessions.length > 0" class="animate-fade-in-up" style="animation-delay: 160ms">
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
</template>

<script setup lang="ts">
import { useChatSessions } from "@/composables/useChatSessions";
import { useCharacters } from "@/composables/useCharacters";
import SearchBar from "@/components/shared/SearchBar.vue";
import ContinueTaleSection from "@/components/shared/ContinueTaleSection.vue";
import DiscoverSection from "@/components/shared/DiscoverSection.vue";
import { CATEGORIES } from "@/constants/discoverData";

const { chatSessions, loading: chatsLoading } = useChatSessions({ pageSize: 8 });
const { characters, loading: charsLoading } = useCharacters({ pageSize: 6 });
</script>

<template>
  <div class="space-y-8 px-12 py-8">
    <!-- Greeting -->
    <div class="animate-fade-in-up">
      <h1 class="mb-1 font-cinzel text-2xl font-bold tracking-wide text-foreground">
        Welcome back, Adventurer
      </h1>
      <p class="text-sm text-muted-foreground">
        Every tale begins with a spark. What story will you tell today?
      </p>
    </div>

    <!-- Search -->
    <div class="animate-fade-in-up" style="animation-delay: 80ms">
      <SearchBar />
    </div>

    <!-- Continue Your Tale (from API chats) -->
    <div class="animate-fade-in-up" style="animation-delay: 160ms">
      <ContinueTaleSection :sessions="chatSessions" :loading="chatsLoading" />
    </div>

    <!-- Discover Characters (from API characters) -->
    <div class="animate-fade-in-up" style="animation-delay: 240ms">
      <DiscoverSection :characters="characters" :categories="CATEGORIES" :loading="charsLoading" />
    </div>
  </div>
</template>

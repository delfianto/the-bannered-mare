<script setup lang="ts">
import SearchBar from "@/components/shared/SearchBar.vue";
import ContinueTaleSection from "@/components/shared/ContinueTaleSection.vue";
import DiscoverSection from "@/components/shared/DiscoverSection.vue";
import {
  CONTINUE_SESSIONS,
  DISCOVER_CHARACTERS,
  CATEGORIES,
} from "@/constants/homeData";
</script>

<template>
  <div class="mx-auto max-w-[960px] space-y-8 px-8 py-8">
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

    <!-- Continue Your Tale -->
    <div class="animate-fade-in-up" style="animation-delay: 160ms">
      <ContinueTaleSection :sessions="CONTINUE_SESSIONS" />
    </div>

    <!-- Discover Characters -->
    <div class="animate-fade-in-up" style="animation-delay: 240ms">
      <DiscoverSection :characters="DISCOVER_CHARACTERS" :categories="CATEGORIES" />
    </div>
  </div>
</template>

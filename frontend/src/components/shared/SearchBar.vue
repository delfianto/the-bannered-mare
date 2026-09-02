<script setup lang="ts">
import { ref } from "vue";

const focused = ref(false);
const query = ref("");
</script>

<template>
  <div class="relative border-b">
    <div
      class="flex h-10 items-center gap-2 transition-all duration-300"
      :class="focused ? 'border-primary' : 'border-border hover:border-muted-foreground/50'"
    >
      <AppIcon
        name="i-lucide-search"
        class="size-4 shrink-0 transition-colors duration-300"
        :class="focused ? 'text-primary' : 'text-muted-foreground'"
      />
      <input
        v-model="query"
        type="text"
        :placeholder="$t('home.searchPlaceholder')"
        :aria-label="$t('common.search')"
        autocomplete="off"
        class="min-w-0 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
        @focus="focused = true"
        @blur="focused = false"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

const focused = ref(false);
const query = ref("");
</script>

<template>
  <div class="relative">
    <div
      class="flex items-center gap-3 rounded-xl border px-4 py-3 transition-all duration-300"
      :class="
        focused
          ? 'border-primary bg-background shadow-[0_0_0_3px_var(--color-primary)/0.12]'
          : 'border-border bg-muted/40 hover:border-muted-foreground/30'
      "
    >
      <UIcon
        name="i-lucide-search"
        class="h-[18px] w-[18px] flex-shrink-0 transition-colors duration-300"
        :class="focused ? 'text-primary' : 'text-muted-foreground'"
      />
      <input
        v-model="query"
        type="text"
        placeholder="Search the library for tales, characters, worlds..."
        class="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
        @focus="focused = true"
        @blur="focused = false"
      />
    </div>
  </div>
</template>

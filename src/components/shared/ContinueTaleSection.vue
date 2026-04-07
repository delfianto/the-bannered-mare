<script setup lang="ts">
import { ref } from "vue";
import type { ContinueSession } from "@/types/home";

defineProps<{
  sessions: ContinueSession[];
}>();

const scrollContainer = ref<HTMLElement | null>(null);

function scroll(direction: "left" | "right") {
  if (!scrollContainer.value) return;
  scrollContainer.value.scrollBy({
    left: direction === "left" ? -320 : 320,
    behavior: "smooth",
  });
}
</script>

<template>
  <section>
    <div class="mb-4 flex items-center justify-between">
      <h2 class="font-cinzel text-lg font-semibold tracking-wide text-foreground">
        Continue Your Tale
      </h2>
      <div class="flex items-center gap-1.5">
        <button
          class="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border)] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          @click="scroll('left')"
        >
          <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
        </button>
        <button
          class="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border)] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          @click="scroll('right')"
        >
          <UIcon name="i-lucide-chevron-right" class="h-4 w-4" />
        </button>
      </div>
    </div>

    <div ref="scrollContainer" class="scrollbar-hide flex gap-4 overflow-x-auto pb-2">
      <div
        v-for="(session, i) in sessions"
        :key="session.id"
        class="group relative h-[160px] w-[280px] flex-shrink-0 cursor-pointer overflow-hidden rounded-xl animate-fade-in-up"
        :style="{ animationDelay: `${i * 80}ms` }"
      >
        <!-- Background image -->
        <img
          :src="session.imageUrl"
          :alt="session.title"
          class="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        />

        <!-- Gradient overlay -->
        <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent" />

        <!-- Content -->
        <div class="absolute bottom-0 left-0 right-0 p-4">
          <h3 class="mb-1 text-sm font-semibold text-white drop-shadow-md">
            {{ session.title }}
          </h3>
          <p class="mb-2 text-xs text-white/70">with {{ session.characterName }}</p>
          <div class="flex items-center gap-3 text-[11px] text-white/60">
            <span class="flex items-center gap-1">
              <UIcon name="i-lucide-clock" class="h-3 w-3" />
              {{ session.lastActivity }}
            </span>
            <span class="flex items-center gap-1">
              <UIcon name="i-lucide-message-square" class="h-3 w-3" />
              {{ session.messageCount }}
            </span>
          </div>
        </div>

        <!-- Hover glow ring -->
        <div
          class="absolute inset-0 rounded-xl ring-2 ring-inset ring-primary/40 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        />
      </div>
    </div>
  </section>
</template>

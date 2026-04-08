<script setup lang="ts">
import { computed } from "vue";
import type { CharacterData } from "@/types/creator";
import NarrativeText from "@/components/chat/NarrativeText.vue";

const props = defineProps<{
  data: CharacterData;
  completeness: { filled: number; total: number };
}>();

const pct = computed(() =>
  props.completeness.total > 0 ? (props.completeness.filled / props.completeness.total) * 100 : 0,
);

const circumference = 2 * Math.PI * 18;
const offset = computed(() => circumference - (pct.value / 100) * circumference);

const greetingPreview = computed(() => props.data.greeting?.slice(0, 300) || "");
</script>

<template>
  <div class="space-y-4">
    <!-- Character Card -->
    <div
      class="relative aspect-[3/4] max-h-[280px] overflow-hidden rounded-xl"
      style="box-shadow: 0 4px 20px var(--color-foreground) / 0.08"
    >
      <img v-if="data.avatarUrl" :src="data.avatarUrl" :alt="data.name" class="absolute inset-0 h-full w-full object-cover" />
      <div v-else class="absolute inset-0 flex items-center justify-center bg-muted">
        <UIcon name="i-lucide-user" class="h-16 w-16 text-muted-foreground/30" />
      </div>
      <div class="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent" />

      <div v-if="data.tags.length > 0" class="absolute left-3 top-3 flex flex-wrap gap-1">
        <span
          v-for="tag in data.tags.slice(0, 3)"
          :key="tag"
          class="rounded-full border border-white/10 bg-white/15 px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide text-white/80 backdrop-blur-sm"
        >
          {{ tag }}
        </span>
      </div>

      <div class="absolute bottom-0 left-0 right-0 p-4">
        <h3 class="truncate font-cinzel text-sm font-semibold text-white drop-shadow-lg" style="letter-spacing: 0.02em">
          {{ data.name || "Unnamed Character" }}
        </h3>
        <p v-if="data.title" class="mt-0.5 truncate text-[11px] text-white/60">{{ data.title }}</p>
        <p v-if="data.species" class="mt-1 text-[10px] text-white/40">
          {{ data.species }}{{ data.gender ? ` · ${data.gender}` : "" }}{{ data.age ? ` · ${data.age}` : "" }}
        </p>
      </div>
    </div>

    <!-- Greeting Preview -->
    <div class="space-y-2 rounded-xl border bg-card p-4">
      <div class="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
        <UIcon name="i-lucide-message-circle" class="h-3 w-3" />
        Greeting Preview
      </div>
      <div v-if="greetingPreview" class="text-xs leading-[1.7]">
        <NarrativeText :content="greetingPreview + (data.greeting.length > 300 ? '...' : '')" />
      </div>
      <span v-else class="text-xs italic text-muted-foreground">No greeting set yet...</span>
    </div>

    <!-- Completeness -->
    <div class="rounded-xl border bg-card p-4">
      <div class="flex items-center gap-3">
        <svg width="44" height="44" class="-rotate-90 flex-shrink-0">
          <circle cx="22" cy="22" r="18" fill="none" stroke="var(--border)" stroke-width="3" />
          <circle
            cx="22" cy="22" r="18" fill="none"
            stroke="var(--primary)"
            stroke-width="3"
            stroke-linecap="round"
            :stroke-dasharray="circumference"
            :stroke-dashoffset="offset"
            class="transition-all duration-500 ease-out"
          />
        </svg>
        <div>
          <p class="text-sm font-medium text-foreground">
            {{ completeness.filled }} of {{ completeness.total }} fields
          </p>
          <p class="text-[11px] text-muted-foreground">
            <span v-if="pct >= 100" class="flex items-center gap-1 text-primary">
              <UIcon name="i-lucide-check" class="h-3 w-3" /> Character complete
            </span>
            <span v-else-if="pct >= 50">Looking good — keep going!</span>
            <span v-else>Fill in more details</span>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

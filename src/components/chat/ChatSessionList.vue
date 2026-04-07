<script setup lang="ts">
import { ref, computed } from "vue";
import type { ChatSession } from "@/types/chat";

const props = defineProps<{
  sessions: ChatSession[];
  activeSessionId: string;
}>();

const emit = defineEmits<{
  select: [id: string];
}>();

const search = ref("");

const filtered = computed(() => {
  if (!search.value) return props.sessions;
  const q = search.value.toLowerCase();
  return props.sessions.filter(
    (s) =>
      s.character.name.toLowerCase().includes(q) ||
      s.sessionTitle.toLowerCase().includes(q),
  );
});
</script>

<template>
  <div class="flex h-full w-[300px] min-w-[300px] flex-col border-r border-border bg-secondary">
    <!-- Search -->
    <div class="px-3 pb-3 pt-4">
      <div
        class="flex items-center gap-2 rounded-lg border border-border bg-background/60 px-3 py-2"
      >
        <UIcon name="i-lucide-search" class="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
        <input
          v-model="search"
          type="text"
          placeholder="Search tales..."
          class="flex-1 bg-transparent text-xs text-foreground outline-none placeholder:text-muted-foreground"
        />
      </div>
    </div>

    <!-- Label -->
    <p
      class="mb-1.5 px-5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground"
    >
      Active Tales
    </p>

    <!-- Session List -->
    <div class="flex-1 space-y-0.5 overflow-y-auto px-2">
      <button
        v-for="session in filtered"
        :key="session.id"
        class="group relative flex w-full items-start gap-3 rounded-xl px-3 py-3 text-left transition-all duration-200"
        :class="session.id === activeSessionId ? 'bg-accent' : 'hover:bg-accent/50'"
        @click="emit('select', session.id)"
      >
        <!-- Active bar -->
        <span
          v-if="session.id === activeSessionId"
          class="absolute left-0 top-1/2 h-6 w-[3px] -translate-y-1/2 rounded-full bg-primary"
        />

        <!-- Avatar -->
        <div class="relative flex-shrink-0">
          <img
            :src="session.character.avatar"
            :alt="session.character.name"
            class="h-10 w-10 rounded-full object-cover ring-1 ring-border"
          />
          <div
            v-if="session.unread"
            class="absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-secondary bg-primary"
          />
        </div>

        <!-- Info -->
        <div class="min-w-0 flex-1">
          <div class="flex items-center justify-between gap-1">
            <p class="truncate text-sm font-medium text-foreground">
              {{ session.character.name }}
            </p>
            <span class="flex-shrink-0 text-[10px] text-muted-foreground">
              {{ session.lastActivity }}
            </span>
          </div>
          <p
            class="mt-0.5 truncate font-cinzel text-[11px] text-primary/80"
          >
            {{ session.sessionTitle }}
          </p>
          <p class="mt-0.5 line-clamp-1 text-[11px] italic leading-relaxed text-muted-foreground">
            {{ session.lastMessage }}
          </p>
        </div>
      </button>
    </div>
  </div>
</template>

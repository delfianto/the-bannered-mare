<script setup lang="ts">
import { useTheme } from "@/composables/useTheme";
import { APP_INFO } from "@/constants/appInfo";
import { RECENT_SESSIONS } from "@/constants/homeData";
import { useRoute } from "vue-router";

const route = useRoute();
const { isDark, toggleTheme } = useTheme();

const navItems = [
  { id: "home", to: "/", label: "Home", icon: "i-lucide-home" },
  { id: "chats", to: "/chats", label: "Chats", icon: "i-lucide-message-square" },
  { id: "characters", to: "/characters", label: "Characters", icon: "i-lucide-users" },
  { id: "world", to: "/world", label: "World Lore", icon: "i-lucide-globe" },
  { id: "memory", to: "/memory", label: "Memory", icon: "i-lucide-brain" },
];

function isActive(to: string) {
  if (to === "/") return route.path === "/";
  return route.path.startsWith(to);
}
</script>

<template>
  <aside
    class="hidden w-[320px] min-w-[320px] h-screen flex-col border-r border-border bg-secondary overflow-hidden lg:flex"
  >
    <!-- Brand Mark -->
    <div class="px-6 pt-6 pb-4">
      <div class="flex items-center gap-2.5">
        <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
          <span class="i-lucide-flame h-5 w-5 text-primary-foreground" />
        </div>
        <h1 class="font-cinzel text-xl font-semibold tracking-wider text-foreground">
          {{ APP_INFO.name }}
        </h1>
      </div>
    </div>

    <!-- Navigation -->
    <nav class="mt-2 px-3">
      <div class="space-y-0.5">
        <RouterLink
          v-for="item in navItems"
          :key="item.id"
          :to="item.to"
          class="relative flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-200"
          :class="
            isActive(item.to)
              ? 'text-foreground bg-accent'
              : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
          "
        >
          <!-- Active indicator bar -->
          <span
            v-if="isActive(item.to)"
            class="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-full bg-primary transition-all duration-300"
          />
          <span :class="[item.icon, 'h-[18px] w-[18px]']" />
          <span style="letter-spacing: 0.04em">{{ item.label }}</span>
        </RouterLink>
      </div>
    </nav>

    <!-- Divider -->
    <div class="mx-5 my-4 h-px bg-border" />

    <!-- Recent Sessions -->
    <div class="flex-1 overflow-y-auto px-3">
      <p
        class="mb-2.5 px-3 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground"
      >
        Recent Tales
      </p>
      <div class="space-y-0.5">
        <button
          v-for="(session, i) in RECENT_SESSIONS"
          :key="session.id"
          class="group flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-accent/50"
          :style="{ animationDelay: `${i * 60}ms` }"
        >
          <img
            :src="session.characterAvatar"
            :alt="session.characterName"
            class="h-8 w-8 flex-shrink-0 rounded-full object-cover ring-1 ring-border"
          />
          <div class="min-w-0 flex-1">
            <div class="flex items-center justify-between gap-2">
              <p class="truncate text-sm font-medium text-foreground">
                {{ session.characterName }}
              </p>
              <span class="flex-shrink-0 text-[10px] text-muted-foreground">
                {{ session.timestamp }}
              </span>
            </div>
            <p class="mt-0.5 line-clamp-2 text-xs italic leading-relaxed text-muted-foreground">
              {{ session.lastMessage }}
            </p>
          </div>
        </button>
      </div>
    </div>

    <!-- Footer: Settings + Theme Toggle -->
    <div class="border-t border-border px-3 py-3 space-y-0.5">
      <RouterLink
        to="/settings"
        class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent/50 hover:text-foreground"
        :class="isActive('/settings') ? 'text-foreground bg-accent' : ''"
      >
        <span class="i-lucide-settings h-[18px] w-[18px]" />
        <span style="letter-spacing: 0.04em">Settings</span>
      </RouterLink>

      <button
        class="flex w-full items-center justify-between rounded-lg px-3 py-2.5 transition-colors hover:bg-accent/50"
        @click="toggleTheme"
      >
        <div class="flex items-center gap-2.5">
          <span
            :class="isDark ? 'i-lucide-moon' : 'i-lucide-sun'"
            class="h-[18px] w-[18px] text-primary transition-transform duration-400"
          />
          <span class="text-sm font-medium text-foreground">
            {{ isDark ? "Dark Mode" : "Light Mode" }}
          </span>
        </div>
        <!-- Toggle switch -->
        <div
          class="flex h-[22px] w-10 items-center rounded-full px-[3px] transition-colors duration-300"
          :class="isDark ? 'bg-primary' : 'bg-muted-foreground/40'"
        >
          <span
            class="h-4 w-4 rounded-full shadow-sm transition-transform duration-300"
            :class="[
              isDark ? 'translate-x-4 bg-background' : 'translate-x-0 bg-white',
            ]"
          />
        </div>
      </button>
    </div>
  </aside>
</template>

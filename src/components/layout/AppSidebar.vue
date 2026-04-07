<script setup lang="ts">
import { useTheme } from "@/composables/useTheme";
import { useSidebar } from "@/composables/useSidebar";
import { APP_INFO } from "@/constants/appInfo";
import { RECENT_SESSIONS } from "@/constants/homeData";
import { useRoute } from "vue-router";

const route = useRoute();
const { isDark, toggleTheme } = useTheme();
const { collapsed, toggle: toggleSidebar } = useSidebar();

const navItems = [
  { id: "home", to: "/", label: "Home", icon: "i-lucide-home" },
  { id: "characters", to: "/characters", label: "Discover", icon: "i-lucide-compass" },
  { id: "world", to: "/world", label: "World Lore", icon: "i-lucide-globe" },
  { id: "memory", to: "/memory", label: "Data Bank", icon: "i-lucide-database" },
  { id: "chats", to: "/chats", label: "Sessions", icon: "i-lucide-scroll-text" },
  { id: "connections", to: "/connections", label: "Connections", icon: "i-lucide-cable" },
];

function isActive(to: string) {
  if (to === "/") return route.path === "/";
  return route.path.startsWith(to);
}
</script>

<template>
  <aside
    class="hidden h-screen flex-col border-r border-border bg-secondary overflow-hidden lg:flex transition-[width,min-width] duration-300 ease-in-out"
    :class="collapsed ? 'w-[68px] min-w-[68px]' : 'w-[320px] min-w-[320px]'"
  >
    <!-- Brand Mark -->
    <div class="pt-6 pb-4" :class="collapsed ? 'px-3' : 'px-6'">
      <div class="flex items-center justify-center gap-2.5">
        <button
          class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-primary transition-opacity hover:opacity-80"
          @click="toggleSidebar"
          :title="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        >
          <UIcon name="i-lucide-flame" class="h-5 w-5 text-primary-foreground" />
        </button>
        <h1
          v-if="!collapsed"
          class="font-cinzel text-xl font-semibold tracking-wider text-foreground whitespace-nowrap overflow-hidden"
        >
          {{ APP_INFO.name }}
        </h1>
      </div>
    </div>

    <!-- Navigation: Grid (expanded) / Vertical icons (collapsed) -->
    <nav class="px-3" :class="collapsed ? 'mt-2' : 'mt-1'">
      <!-- Expanded: 2-column tile grid -->
      <div v-if="!collapsed" class="grid grid-cols-2 gap-1.5">
        <RouterLink
          v-for="(item, i) in navItems"
          :key="item.id"
          :to="item.to"
          class="relative flex flex-col items-center gap-1.5 rounded-xl px-2 py-3 text-center transition-all duration-200"
          :class="[
            navItems.length % 2 !== 0 && i === navItems.length - 1 ? 'col-span-2' : '',
            isActive(item.to)
              ? 'bg-accent text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground hover:bg-accent/50',
          ]"
        >
          <span
            v-if="isActive(item.to)"
            class="absolute left-1.5 top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-full bg-primary"
          />
          <UIcon :name="item.icon" class="h-5 w-5" />
          <span class="text-[11px] font-medium tracking-wide">{{ item.label }}</span>
        </RouterLink>
      </div>

      <!-- Collapsed: vertical icon-only -->
      <div v-else class="space-y-0.5">
        <UTooltip
          v-for="item in navItems"
          :key="item.id"
          :text="item.label"
          :content="{ side: 'right', sideOffset: 8 }"
        >
          <RouterLink
            :to="item.to"
            class="relative flex w-full items-center justify-center rounded-lg py-2.5 transition-colors duration-200"
            :class="
              isActive(item.to)
                ? 'text-foreground bg-accent'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
            "
          >
            <span
              v-if="isActive(item.to)"
              class="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-full bg-primary"
            />
            <UIcon :name="item.icon" class="h-[18px] w-[18px]" />
          </RouterLink>
        </UTooltip>
      </div>
    </nav>

    <!-- Divider -->
    <div class="mx-3 my-4 h-px bg-border" />

    <!-- Recent Sessions (hidden when collapsed) -->
    <div v-if="!collapsed" class="flex-1 overflow-y-auto px-3">
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

    <!-- Spacer when collapsed -->
    <div v-else class="flex-1" />

    <!-- Footer: Settings + Theme Toggle -->
    <div class="border-t border-border px-2 py-3 space-y-0.5">
      <!-- Settings -->
      <UTooltip
        text="Settings"
        :content="{ side: 'right', sideOffset: 8 }"
        :disabled="!collapsed"
      >
        <RouterLink
          to="/settings"
          class="flex w-full items-center rounded-lg py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent/50 hover:text-foreground"
          :class="[
            collapsed ? 'justify-center px-0' : 'gap-3 px-3',
            isActive('/settings') ? 'text-foreground bg-accent' : '',
          ]"
        >
          <UIcon name="i-lucide-settings" class="h-[18px] w-[18px] flex-shrink-0" />
          <span v-if="!collapsed" style="letter-spacing: 0.04em">Settings</span>
        </RouterLink>
      </UTooltip>

      <!-- Theme Toggle -->
      <UTooltip
        :text="isDark ? 'Dark Mode' : 'Light Mode'"
        :content="{ side: 'right', sideOffset: 8 }"
        :disabled="!collapsed"
      >
        <button
          class="flex w-full items-center rounded-lg py-2.5 transition-colors hover:bg-accent/50"
          :class="collapsed ? 'justify-center px-0' : 'justify-between px-3'"
          @click="toggleTheme"
        >
          <div class="flex items-center" :class="collapsed ? '' : 'gap-2.5'">
            <UIcon
              :name="isDark ? 'i-lucide-moon' : 'i-lucide-sun'"
              class="h-[18px] w-[18px] flex-shrink-0 text-primary"
            />
            <span v-if="!collapsed" class="text-sm font-medium text-foreground">
              {{ isDark ? "Dark Mode" : "Light Mode" }}
            </span>
          </div>
          <div
            v-if="!collapsed"
            class="flex h-[22px] w-10 items-center rounded-full px-[3px] transition-colors duration-300"
            :class="isDark ? 'bg-primary' : 'bg-muted-foreground/40'"
          >
            <span
              class="h-4 w-4 rounded-full shadow-sm transition-transform duration-300"
              :class="isDark ? 'translate-x-4 bg-background' : 'translate-x-0 bg-white'"
            />
          </div>
        </button>
      </UTooltip>
    </div>
  </aside>
</template>

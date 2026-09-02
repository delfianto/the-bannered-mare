<script setup lang="ts">
import { computed } from "vue";
import { useTheme } from "@/composables/useTheme";
import { useSidebar } from "@/composables/useSidebar";
import { APP_INFO } from "@/constants/appInfo";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { useBookmarks } from "@/composables/useBookmarks";
import AppTooltip from "@/components/shared/AppTooltip.vue";

const { t } = useI18n();
const route = useRoute();
const { isDark, toggleTheme } = useTheme();
const { collapsed, toggle: toggleSidebar } = useSidebar();
const { sessions } = useBookmarks();

const navItems = [
  { id: "home", to: "/", label: t("nav.home"), icon: "i-lucide-home", chapter: "I" },
  {
    id: "chats",
    to: "/chats",
    label: t("nav.sessions"),
    icon: "i-lucide-scroll-text",
    chapter: "II",
  },
  {
    id: "characters",
    to: "/characters",
    label: t("nav.discover"),
    icon: "i-lucide-compass",
    chapter: "III",
  },
  {
    id: "lorebooks",
    to: "/lorebooks",
    label: t("nav.lorebooks"),
    icon: "i-lucide-book-open",
    chapter: "IV",
  },
  {
    id: "memory",
    to: "/memory",
    label: t("nav.dataBank"),
    icon: "i-lucide-database",
    chapter: "V",
  },
  {
    id: "bookmarks",
    to: "/bookmarks",
    label: t("nav.bookmarks"),
    icon: "i-lucide-bookmark",
    chapter: "VI",
  },
  {
    id: "connections",
    to: "/connections",
    label: t("nav.connections"),
    icon: "i-lucide-cable",
    chapter: "VII",
  },
  {
    id: "profiles",
    to: "/loadouts",
    label: t("nav.profiles"),
    icon: "i-lucide-layers",
    chapter: "VIII",
  },
];

function isActive(to: string) {
  if (to === "/") return route.path === "/";
  return route.path.startsWith(to);
}

const favorites = computed(() => {
  return sessions.value.slice(0, 4).map((session) => ({
    id: session.id,
    name: session.character?.name || "Unknown",
    avatar: session.character?.avatar_thumbnail || session.character?.avatar || "",
    chatPath: `/chats/${session.id}`,
  }));
});
</script>

<template>
  <aside
    class="hidden h-screen flex-col overflow-hidden border-r bg-base-100 transition-[width,min-width] duration-300 ease-in-out lg:flex"
    :class="collapsed ? 'w-18 min-w-18' : 'w-72 min-w-72'"
  >
    <!-- Brand Mark -->
    <div class="pt-7 pb-5" :class="collapsed ? 'px-3' : 'px-8'">
      <div
        class="flex items-center"
        :class="collapsed ? 'justify-center' : 'justify-between gap-3'"
      >
        <button
          class="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary transition-all hover:scale-105 hover:opacity-90"
          :title="$t(collapsed ? 'nav.expandSidebar' : 'nav.collapseSidebar')"
          :aria-label="$t(collapsed ? 'nav.expandSidebar' : 'nav.collapseSidebar')"
          @click="toggleSidebar"
        >
          <AppIcon name="i-lucide-flame" class="size-5 text-primary-content" />
        </button>
        <h1
          v-if="!collapsed"
          class="overflow-hidden font-medieval text-xl whitespace-nowrap text-foreground"
        >
          {{ APP_INFO.name }}
        </h1>
      </div>
    </div>

    <!-- Navigation: editorial contents (expanded) / icon rail (collapsed) -->
    <nav :class="collapsed ? 'mt-2 px-3' : 'mt-2 px-8'">
      <template v-if="!collapsed">
        <div class="mb-5 flex items-center gap-3 border-b pb-3">
          <span class="font-story text-2xs font-semibold tracking-[0.2em] text-primary uppercase"
            >Contents</span
          >
          <span class="h-px flex-1 bg-border" />
        </div>
        <div class="space-y-1">
          <RouterLink
            v-for="item in navItems"
            :key="item.id"
            :to="item.to"
            class="group relative flex items-center gap-3 py-2.5 text-sm transition-colors duration-200"
            :class="
              isActive(item.to) ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
            "
          >
            <span
              v-if="isActive(item.to)"
              class="absolute top-1/2 -left-4 size-1.5 -translate-y-1/2 rounded-full bg-primary"
            />
            <AppIcon :name="item.icon" class="size-4 shrink-0" />
            <span class="flex-1 font-medium tracking-wide">{{ item.label }}</span>
            <span class="font-story text-3xs text-muted-foreground">{{ item.chapter }}</span>
          </RouterLink>
        </div>
      </template>

      <div v-else class="space-y-0.5">
        <AppTooltip
          v-for="item in navItems"
          :key="item.id"
          :text="item.label"
          side="right"
          class="block"
        >
          <RouterLink
            :to="item.to"
            class="relative flex w-full items-center justify-center py-2.5 transition-colors duration-200"
            :class="
              isActive(item.to) ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
            "
          >
            <span
              v-if="isActive(item.to)"
              class="absolute top-1/2 -left-3 h-5 w-0.75 -translate-y-1/2 rounded-full bg-primary"
            />
            <AppIcon :name="item.icon" class="size-5" />
          </RouterLink>
        </AppTooltip>
      </div>
    </nav>

    <!-- Divider -->
    <div v-if="favorites.length > 0 && collapsed" class="m-3 h-px bg-border" />

    <!-- Favorites -->
    <div
      v-if="favorites.length > 0"
      class="flex-1 overflow-y-auto"
      :class="collapsed ? 'px-2' : 'px-3'"
    >
      <div v-if="!collapsed" class="mb-4 flex items-center gap-3 border-b pb-3">
        <p
          class="font-story text-2xs font-semibold tracking-[0.2em] text-muted-foreground uppercase"
        >
          {{ $t("nav.favorites") }}
        </p>
        <span class="h-px flex-1 bg-border" />
      </div>

      <div class="space-y-0.5">
        <!-- Expanded: list style with avatar + name -->
        <template v-if="!collapsed">
          <div class="flex flex-wrap gap-3 px-1">
            <AppTooltip v-for="char in favorites" :key="char.id" :text="char.name" side="top">
              <RouterLink :to="char.chatPath" class="group relative block">
                <img
                  :src="char.avatar"
                  :alt="char.name"
                  class="size-9 rounded-full object-cover ring-1 transition-all"
                  :class="
                    route.path === char.chatPath
                      ? 'ring-primary'
                      : 'ring-border group-hover:ring-primary/50'
                  "
                />
                <span
                  class="absolute right-0 bottom-0 size-2 rounded-full border border-base-100 bg-success"
                />
              </RouterLink>
            </AppTooltip>
          </div>
        </template>

        <!-- Collapsed: stacked avatars -->
        <template v-else>
          <AppTooltip
            v-for="char in favorites"
            :key="char.id"
            :text="char.name"
            side="right"
            class="block"
          >
            <RouterLink
              :to="char.chatPath"
              class="group relative flex w-full items-center justify-center py-1"
            >
              <img
                :src="char.avatar"
                :alt="char.name"
                class="size-9 rounded-full object-cover ring-2 transition-all duration-200"
                :class="
                  route.path === char.chatPath
                    ? 'ring-primary shadow-[0_0_8px_var(--color-primary)/0.3]'
                    : 'ring-transparent hover:ring-primary/40'
                "
              />
              <span
                class="absolute right-2.5 bottom-1 size-2 rounded-full border-[1.5px] border-base-200 bg-success"
              />
            </RouterLink>
          </AppTooltip>
        </template>
      </div>
    </div>

    <!-- Footer: Settings + Theme Toggle -->
    <div class="space-y-0.5 border-t px-2 py-4">
      <AppTooltip :text="$t('nav.settings')" side="right" :disabled="!collapsed" class="block">
        <RouterLink
          to="/settings"
          class="flex w-full items-center rounded-lg py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-base-300/50 hover:text-foreground"
          :class="[
            collapsed ? 'justify-center px-0' : 'gap-3 px-3',
            isActive('/settings') ? 'bg-base-300 text-foreground' : '',
          ]"
        >
          <AppIcon name="i-lucide-settings" class="size-5 shrink-0" />
          <span v-if="!collapsed" style="letter-spacing: 0.04em">{{ $t("nav.settings") }}</span>
        </RouterLink>
      </AppTooltip>

      <AppTooltip
        :text="$t('settings.interface.darkMode')"
        side="right"
        :disabled="!collapsed"
        class="block"
      >
        <button
          v-if="collapsed"
          class="flex w-full items-center justify-center rounded-lg py-2.5 transition-colors hover:bg-base-300/50"
          aria-label="Toggle theme"
          @click="toggleTheme"
        >
          <AppIcon
            :name="isDark ? 'i-lucide-moon' : 'i-lucide-sun'"
            class="size-5 shrink-0 text-primary"
          />
        </button>
        <label
          v-else
          class="flex w-full cursor-pointer items-center justify-between rounded-lg px-3 py-2.5 transition-colors hover:bg-base-300/50"
        >
          <span class="flex items-center gap-2.5">
            <AppIcon
              :name="isDark ? 'i-lucide-moon' : 'i-lucide-sun'"
              class="size-5 shrink-0 text-primary"
            />
            <span class="text-sm font-medium text-foreground">
              {{ $t("settings.interface.darkMode") }}
            </span>
          </span>
          <AppToggle :model-value="isDark" aria-label="Toggle theme" @change="toggleTheme" />
        </label>
      </AppTooltip>
    </div>
  </aside>
</template>

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
  { id: "home", to: "/", label: t("nav.home"), icon: "i-lucide-home" },
  { id: "chats", to: "/chats", label: t("nav.sessions"), icon: "i-lucide-scroll-text" },
  { id: "characters", to: "/characters", label: t("nav.discover"), icon: "i-lucide-compass" },
  { id: "lorebooks", to: "/lorebooks", label: t("nav.lorebooks"), icon: "i-lucide-book-open" },
  { id: "memory", to: "/memory", label: t("nav.dataBank"), icon: "i-lucide-database" },
  { id: "bookmarks", to: "/bookmarks", label: t("nav.bookmarks"), icon: "i-lucide-bookmark" },
  { id: "connections", to: "/connections", label: t("nav.connections"), icon: "i-lucide-cable" },
  { id: "profiles", to: "/loadouts", label: t("nav.profiles"), icon: "i-lucide-layers" },
];

function isActive(to: string) {
  if (to === "/") return route.path === "/";
  return route.path.startsWith(to);
}

const favorites = computed(() => {
  return sessions.value.slice(0, 4).map((session: any) => ({
    id: session.id,
    name: session.character?.name || "Unknown",
    avatar: session.character?.avatar_thumbnail || session.character?.avatar || "",
    chatPath: `/chats/${session.id}`,
  }));
});
</script>

<template>
  <aside
    class="hidden h-screen flex-col overflow-hidden border-r bg-base-200 transition-[width,min-width] duration-300 ease-in-out lg:flex"
    :class="collapsed ? 'w-[4.25rem] min-w-[4.25rem]' : 'w-[16.25rem] min-w-[16.25rem]'"
  >
    <!-- Brand Mark -->
    <div class="pt-6 pb-4" :class="collapsed ? 'px-3' : 'px-6'">
      <div class="flex items-center justify-center gap-2.5">
        <button
          class="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary transition-opacity hover:opacity-80"
          :title="$t(collapsed ? 'nav.expandSidebar' : 'nav.collapseSidebar')"
          :aria-label="$t(collapsed ? 'nav.expandSidebar' : 'nav.collapseSidebar')"
          @click="toggleSidebar"
        >
          <AppIcon name="i-lucide-flame" class="size-5 text-primary-content" />
        </button>
        <h1
          v-if="!collapsed"
          class="overflow-hidden font-cinzel text-xl font-semibold tracking-wider whitespace-nowrap text-foreground"
        >
          {{ APP_INFO.name }}
        </h1>
      </div>
    </div>

    <!-- Navigation: Grid (expanded) / Vertical icons (collapsed) -->
    <nav class="px-3" :class="collapsed ? 'mt-2' : 'mt-1'">
      <div v-if="!collapsed" class="grid grid-cols-2 gap-1.5">
        <RouterLink
          v-for="(item, i) in navItems"
          :key="item.id"
          :to="item.to"
          class="relative flex flex-col items-center gap-1.5 rounded-xl px-2 py-3 text-center transition-all duration-200"
          :class="[
            navItems.length % 2 !== 0 && i === navItems.length - 1 ? 'col-span-2' : '',
            isActive(item.to)
              ? 'bg-base-300 text-foreground shadow-sm'
              : 'text-muted-foreground hover:bg-base-300/50 hover:text-foreground',
          ]"
        >
          <span
            v-if="isActive(item.to)"
            class="absolute top-1/2 left-1.5 h-4 w-[3px] -translate-y-1/2 rounded-full bg-primary"
          />
          <AppIcon :name="item.icon" class="size-5" />
          <span class="text-[0.6875rem] font-medium tracking-wide">{{ item.label }}</span>
        </RouterLink>
      </div>

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
            class="relative flex w-full items-center justify-center rounded-lg py-2.5 transition-colors duration-200"
            :class="
              isActive(item.to)
                ? 'text-foreground bg-base-300'
                : 'text-muted-foreground hover:text-foreground hover:bg-base-300/50'
            "
          >
            <span
              v-if="isActive(item.to)"
              class="absolute top-1/2 left-0 h-5 w-[3px] -translate-y-1/2 rounded-full bg-primary"
            />
            <AppIcon :name="item.icon" class="size-5" />
          </RouterLink>
        </AppTooltip>
      </div>
    </nav>

    <!-- Divider -->
    <div v-if="favorites.length > 0" class="m-3 h-px bg-border" />

    <!-- Favorites -->
    <div
      v-if="favorites.length > 0"
      class="flex-1 overflow-y-auto"
      :class="collapsed ? 'px-2' : 'px-3'"
    >
      <p
        v-if="!collapsed"
        class="mb-2.5 px-3 text-[0.6875rem] font-semibold tracking-widest text-muted-foreground uppercase"
      >
        {{ $t("nav.favorites") }}
      </p>

      <div class="space-y-0.5">
        <!-- Expanded: list style with avatar + name -->
        <template v-if="!collapsed">
          <RouterLink
            v-for="char in favorites"
            :key="char.id"
            :to="char.chatPath"
            class="group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-base-300/50"
            :class="route.path === char.chatPath ? 'bg-base-300' : ''"
          >
            <div class="relative shrink-0">
              <img
                :src="char.avatar"
                :alt="char.name"
                class="size-10 rounded-full object-cover ring-1 ring-border"
              />
              <span
                class="absolute right-0 bottom-0 size-2.5 rounded-full border-2 border-base-200 bg-emerald-500"
              />
            </div>
            <p class="truncate text-sm font-medium text-foreground">
              {{ char.name }}
            </p>
          </RouterLink>
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
                class="absolute right-2.5 bottom-1 size-2 rounded-full border-[1.5px] border-base-200 bg-emerald-500"
              />
            </RouterLink>
          </AppTooltip>
        </template>
      </div>
    </div>

    <!-- Footer: Settings + Theme Toggle -->
    <div class="space-y-0.5 border-t px-2 py-3">
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

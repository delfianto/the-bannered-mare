import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", name: "home", component: () => import("@/views/HomeView.vue") },
  { path: "/chats", name: "chats", component: () => import("@/views/chat/ChatView.vue") },
  { path: "/chats/:chatId", name: "chat", component: () => import("@/views/chat/ChatView.vue") },
  {
    path: "/characters",
    name: "characters",
    component: () => import("@/views/CharactersView.vue"),
  },
  {
    path: "/characters/create",
    name: "character-create",
    component: () => import("@/views/CharacterCreateView.vue"),
  },
  {
    path: "/characters/:id/edit",
    name: "character-edit",
    component: () => import("@/views/CharacterCreateView.vue"),
  },
  {
    path: "/characters/:id",
    name: "character-detail",
    component: () => import("@/views/CharacterDetailView.vue"),
  },
  { path: "/bookmarks", name: "bookmarks", component: () => import("@/views/BookmarksView.vue") },
  { path: "/memory", name: "memory", component: () => import("@/views/MemoryView.vue") },
  {
    path: "/connections",
    name: "connections",
    component: () => import("@/views/ConnectionsView.vue"),
  },
  {
    path: "/loadouts",
    name: "profiles",
    component: () => import("@/views/ProfilesView.vue"),
  },
  {
    path: "/setup",
    name: "setup",
    component: () => import("@/views/SetupWizardView.vue"),
  },
  {
    path: "/lorebooks",
    name: "lorebooks",
    component: () => import("@/views/LorebooksView.vue"),
  },
  {
    // Personas moved into the Loadouts section; keep the old path as a redirect.
    path: "/persona",
    redirect: { path: "/loadouts", query: { tab: "personas" } },
  },

  {
    path: "/settings",
    name: "settings",
    component: () => import("@/views/settings/SettingsView.vue"),
  },
  {
    path: "/settings/providers/:id",
    name: "provider-edit",
    component: () => import("@/views/settings/ProviderView.vue"),
  },
  {
    path: "/settings/models/:id",
    name: "model-edit",
    component: () => import("@/views/settings/ModelView.vue"),
  },
  {
    path: "/settings/model-families/:id",
    name: "model-family-edit",
    component: () => import("@/views/settings/ModelFamilyView.vue"),
  },
  {
    path: "/settings/templates/create",
    name: "template-create",
    component: () => import("@/views/settings/TemplateCreateView.vue"),
  },
  {
    path: "/settings/templates/:id",
    name: "template-edit",
    component: () => import("@/views/settings/TemplateView.vue"),
  },
  {
    path: "/settings/fragments/create",
    name: "fragment-create",
    component: () => import("@/views/settings/FragmentCreateView.vue"),
  },
  {
    path: "/settings/fragments/:id",
    name: "fragment-edit",
    component: () => import("@/views/settings/FragmentView.vue"),
  },
  {
    path: "/settings/presets/:id",
    name: "preset-edit",
    component: () => import("@/views/settings/PresetView.vue"),
  },
  // Catch-all: any unmatched URL (typo, stale deep link, post-refactor path)
  // renders a 404 instead of a blank <RouterView>.
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: () => import("@/views/NotFoundView.vue"),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// A hashed lazy-view chunk can 404 after a redeploy (the loaded HTML references
// old filenames until a reload). Recover with a one-shot hard navigation to the
// target instead of leaving a blank <RouterView>; the sessionStorage guard stops
// a reload loop if the chunk is genuinely gone.
router.onError((error, to) => {
  const msg = (error as Error)?.message ?? "";
  const isChunkError =
    /Failed to fetch dynamically imported module|error loading dynamically imported module|Importing a module script failed/i.test(
      msg,
    );
  if (isChunkError && to?.fullPath) {
    const key = `chunk-reload:${to.fullPath}`;
    if (!sessionStorage.getItem(key)) {
      sessionStorage.setItem(key, "1");
      window.location.assign(to.fullPath);
    }
  }
});

// Clear the one-shot reload guard once a navigation actually completes.
router.afterEach((to) => {
  sessionStorage.removeItem(`chunk-reload:${to.fullPath}`);
});

export default router;

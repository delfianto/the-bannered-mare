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
  { path: "/world", name: "world", component: () => import("@/views/WorldLoreView.vue") },
  { path: "/memory", name: "memory", component: () => import("@/views/MemoryView.vue") },
  {
    path: "/connections",
    name: "connections",
    component: () => import("@/views/ConnectionsView.vue"),
  },
  {
    path: "/persona",
    name: "persona",
    component: () => import("@/views/settings/SettingsView.vue"),
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
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;

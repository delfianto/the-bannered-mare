import { onMounted } from "vue";
import { storeToRefs } from "pinia";
import type { components } from "@/api/schema";
import { client } from "@/api/client";
import { defineListStore } from "@/stores/listStore";

export type Profile = components["schemas"]["ProfileResponse"];
export type ProfileCreate = components["schemas"]["ProfileCreate"];
export type ProfileUpdate = components["schemas"]["ProfileUpdate"];

/**
 * Profiles list + CRUD, backed by a shared cached store singleton. Every
 * mutation flows through this store, so the cached list stays coherent in place
 * for all consumers (ProfilesTab, ProfileForm/Card, chat drawer, setup wizard)
 * with no per-consumer refetch.
 */
export const useProfilesStore = defineListStore<Profile, ProfileCreate, ProfileUpdate>("profiles", {
  label: "profile",
  singleDefault: true,
  list: () => client.GET("/api/profiles/", { params: { query: { limit: 50 } } }),
  create: (body) => client.POST("/api/profiles/", { body }),
  update: (id, body) =>
    client.PUT("/api/profiles/{profile_id}", { params: { path: { profile_id: id } }, body }),
  remove: (id) =>
    client.DELETE("/api/profiles/{profile_id}", { params: { path: { profile_id: id } } }),
  setDefault: (id) =>
    client.POST("/api/profiles/{profile_id}/default", { params: { path: { profile_id: id } } }),
});

export function useProfiles() {
  const store = useProfilesStore();
  const { items: profiles, loading, error } = storeToRefs(store);
  onMounted(() => store.ensureLoaded());

  return {
    profiles,
    loading,
    error,
    fetchProfiles: store.refresh,
    createProfile: store.createItem,
    updateProfile: store.updateItem,
    deleteProfile: store.removeItem,
    setDefault: store.setDefaultItem,
    refresh: store.refresh,
  };
}

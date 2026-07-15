import type { components } from "@/api/schema";
import { client } from "@/api/client";
import { useListCrud } from "@/composables/useListCrud";

export type Profile = components["schemas"]["ProfileResponse"];
export type ProfileCreate = components["schemas"]["ProfileCreate"];
export type ProfileUpdate = components["schemas"]["ProfileUpdate"];

export function useProfiles() {
  const {
    items,
    loading,
    error,
    fetchList,
    refresh,
    createItem,
    updateItem,
    removeItem,
    setDefaultItem,
  } = useListCrud<Profile, [], ProfileCreate, ProfileUpdate>({
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

  return {
    profiles: items,
    loading,
    error,
    fetchProfiles: fetchList,
    createProfile: createItem,
    updateProfile: updateItem,
    deleteProfile: removeItem,
    setDefault: setDefaultItem,
    refresh,
  };
}

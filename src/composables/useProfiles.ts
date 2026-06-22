import { ref, onMounted } from "vue";
import type { components } from "@/api/schema";
import { client } from "@/api/client";

export type Profile = components["schemas"]["ProfileResponse"];
export type ProfileCreate = components["schemas"]["ProfileCreate"];
export type ProfileUpdate = components["schemas"]["ProfileUpdate"];

export function useProfiles() {
  const profiles = ref<Profile[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);

  const fetchProfiles = async () => {
    loading.value = true;
    error.value = null;

    try {
      const { data, error: apiError } = await client.GET("/api/profiles/", {
        params: { query: { limit: 50 } },
      });

      if (apiError) {
        throw new Error(`Failed to load profiles: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        profiles.value = data.items;
      }
    } catch (err) {
      error.value = err instanceof Error ? err : new Error("Unknown error");
      console.error("Error loading profiles:", err);
    } finally {
      loading.value = false;
    }
  };

  const createProfile = async (payload: ProfileCreate): Promise<Profile | null> => {
    try {
      const { data, error: apiError } = await client.POST("/api/profiles/", { body: payload });

      if (apiError) {
        throw new Error(`Failed to create profile: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        if (data.is_default) profiles.value.forEach((p) => (p.is_default = false));
        profiles.value.unshift(data);
        return data;
      }
      return null;
    } catch (err) {
      console.error("Error creating profile:", err);
      return null;
    }
  };

  const updateProfile = async (id: string, payload: ProfileUpdate): Promise<Profile | null> => {
    try {
      const { data, error: apiError } = await client.PUT("/api/profiles/{profile_id}", {
        params: { path: { profile_id: id } },
        body: payload,
      });

      if (apiError) {
        throw new Error(`Failed to update profile: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        if (data.is_default) profiles.value.forEach((p) => (p.is_default = false));
        const idx = profiles.value.findIndex((p) => p.id === id);
        if (idx !== -1) profiles.value[idx] = data;
        return data;
      }
      return null;
    } catch (err) {
      console.error("Error updating profile:", err);
      return null;
    }
  };

  const deleteProfile = async (id: string): Promise<boolean> => {
    try {
      const { error: apiError } = await client.DELETE("/api/profiles/{profile_id}", {
        params: { path: { profile_id: id } },
      });

      if (apiError) {
        throw new Error(`Failed to delete profile: ${JSON.stringify(apiError)}`);
      }

      profiles.value = profiles.value.filter((p) => p.id !== id);
      return true;
    } catch (err) {
      console.error("Error deleting profile:", err);
      return false;
    }
  };

  const setDefault = async (id: string): Promise<Profile | null> => {
    try {
      const { data, error: apiError } = await client.POST("/api/profiles/{profile_id}/default", {
        params: { path: { profile_id: id } },
      });

      if (apiError) {
        throw new Error(`Failed to set default profile: ${JSON.stringify(apiError)}`);
      }

      if (data) {
        profiles.value.forEach((p) => (p.is_default = p.id === id));
        return data;
      }
      return null;
    } catch (err) {
      console.error("Error setting default profile:", err);
      return null;
    }
  };

  const refresh = () => {
    fetchProfiles();
  };

  onMounted(() => {
    fetchProfiles();
  });

  return {
    profiles,
    loading,
    error,
    fetchProfiles,
    createProfile,
    updateProfile,
    deleteProfile,
    setDefault,
    refresh,
  };
}

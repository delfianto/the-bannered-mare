import { ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { client } from "@/api/client";
import { useAppToast } from "@/composables/useToast";
import type { components } from "@/api/schema";

type Profile = components["schemas"]["ProfileResponse"];

export function useCreateChat() {
  const router = useRouter();
  const toast = useAppToast();
  const { t } = useI18n();
  const creating = ref(false);
  const profileChoices = ref<Profile[] | null>(null);
  let pendingCharacterId: string | null = null;

  async function createAndNavigate(characterId: string, profileId: string) {
    const { data, error } = await client.POST("/api/chats", {
      body: { character_id: characterId, profile_id: profileId, is_bookmarked: false },
    });
    if (error || !data) throw new Error("Failed to start chat");
    await router.push({ name: "chat", params: { chatId: data.id } });
    return data;
  }

  async function startTale(characterId: string) {
    creating.value = true;
    try {
      const { data, error } = await client.GET("/api/profiles/", {
        params: { query: { limit: 50 } },
      });
      if (error || !data) throw new Error("Failed to load profiles");
      // A profile with no model attached (e.g. an ST import that was never
      // finished) can't actually start a chat — don't offer it as a choice.
      const readyProfiles = data.items.filter((p) => p.model_id);

      if (readyProfiles.length === 0) {
        toast.info(t("chat.toast.setupProfile"));
        await router.push("/setup");
        return;
      }

      if (readyProfiles.length === 1) {
        await createAndNavigate(characterId, readyProfiles[0].id);
        return;
      }

      pendingCharacterId = characterId;
      profileChoices.value = readyProfiles;
    } catch (e) {
      toast.error(t("chat.toast.startFailed"));
      throw e;
    } finally {
      creating.value = false;
    }
  }

  async function chooseProfile(profileId: string) {
    if (!pendingCharacterId) return;
    const characterId = pendingCharacterId;
    profileChoices.value = null;
    pendingCharacterId = null;
    creating.value = true;
    try {
      await createAndNavigate(characterId, profileId);
    } catch {
      toast.error(t("chat.toast.startFailed"));
    } finally {
      creating.value = false;
    }
  }

  function cancelProfilePick() {
    profileChoices.value = null;
    pendingCharacterId = null;
  }

  return { creating, profileChoices, startTale, chooseProfile, cancelProfilePick };
}

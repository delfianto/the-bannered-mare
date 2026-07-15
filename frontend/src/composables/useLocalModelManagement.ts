import { type Ref } from "vue";
import { useI18n } from "vue-i18n";
import { useAppToast } from "@/composables/useToast";
import { useConfirm } from "@/composables/useConfirm";
import type { components } from "@/api/schema";

type ProviderResponse = components["schemas"]["ProviderResponse"];

/** The local-provider (Ollama/LM Studio) runtime actions, from `useProvider` + `useModels`. */
interface LocalModelApi {
  syncNow: (id: string) => Promise<void>;
  loadModel: (id: string, identifier: string) => Promise<void>;
  unloadModel: (id: string, identifier: string) => Promise<void>;
  deleteModel: (id: string, identifier: string) => Promise<void>;
  /** Refresh the persisted-models list (so a deleted model drops out). */
  reloadPersisted: () => void;
}

/**
 * Local-model load/unload/delete/sync handlers — the confirm + toast + refresh
 * wrappers around `useProvider`'s runtime actions — extracted out of ProviderView
 * (FE-M7) so the view stops doing this orchestration inline.
 */
export function useLocalModelManagement(
  provider: Ref<ProviderResponse | null>,
  api: LocalModelApi,
) {
  const { t } = useI18n();
  const toast = useAppToast();
  const { confirm } = useConfirm();

  async function handleSyncNow() {
    if (!provider.value) return;
    try {
      await api.syncNow(provider.value.id);
      toast.success(t("connections.provider.toast.synced"));
    } catch {
      toast.error(t("connections.provider.toast.syncFailed"));
    }
  }

  async function handleLoadModel(identifier: string) {
    if (!provider.value) return;
    if (!(await confirm({ message: `Load "${identifier}" into memory?` }))) return;
    try {
      await api.loadModel(provider.value.id, identifier);
      toast.success(t("connections.provider.toast.modelLoaded", { model: identifier }));
    } catch {
      toast.error(t("connections.provider.toast.loadFailed"));
    }
  }

  async function handleUnloadModel(identifier: string) {
    if (!provider.value) return;
    if (!(await confirm({ message: `Unload "${identifier}" from memory?` }))) return;
    try {
      await api.unloadModel(provider.value.id, identifier);
      toast.success(t("connections.provider.toast.modelUnloaded", { model: identifier }));
    } catch {
      toast.error(t("connections.provider.toast.unloadFailed"));
    }
  }

  async function handleDeleteModel(identifier: string) {
    if (!provider.value) return;
    const ok = await confirm({
      title: "Delete model",
      message: `Delete "${identifier}" from the provider server? This cannot be undone.`,
      confirmLabel: t("common.delete"),
      danger: true,
    });
    if (!ok) return;
    try {
      await api.deleteModel(provider.value.id, identifier);
      toast.success(t("connections.provider.toast.modelDeleted", { model: identifier }));
      api.reloadPersisted();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : t("connections.provider.toast.deleteFailed"));
    }
  }

  return { handleSyncNow, handleLoadModel, handleUnloadModel, handleDeleteModel };
}

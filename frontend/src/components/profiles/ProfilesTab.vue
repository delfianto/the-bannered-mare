<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import { useProfiles } from "@/composables/useProfiles";
import type { Profile, ProfileCreate } from "@/composables/useProfiles";
import { usePromptTemplates } from "@/composables/usePromptTemplates";
import { usePresets } from "@/composables/usePresets";
import { usePersonas } from "@/composables/usePersonas";
import { useModels } from "@/composables/useModels";
import { useAppToast } from "@/composables/useToast";
import ProfileCard from "@/components/profiles/ProfileCard.vue";
import ProfileForm from "@/components/profiles/ProfileForm.vue";
import EmptyState from "@/components/shared/EmptyState.vue";
import Modal from "@/components/shared/Modal.vue";

const { t } = useI18n();
const toast = useAppToast();

const {
  profiles,
  loading,
  error,
  createProfile,
  updateProfile,
  deleteProfile,
  setDefault,
  refresh,
} = useProfiles();
const { templates } = usePromptTemplates();
const { presets } = usePresets();
const { personas } = usePersonas();
const { models } = useModels({ pageSize: 100 });

function resolve(
  list: { id: string; name: string }[],
  id: string | null | undefined,
): string | null {
  if (!id) return null;
  return list.find((x) => x.id === id)?.name ?? id;
}

// ── Form state ───────────────────────────────────────────
const showForm = ref(false);
const editing = ref<Profile | null>(null);
const saving = ref(false);

function openCreate() {
  editing.value = null;
  showForm.value = true;
}

function openEdit(profile: Profile) {
  editing.value = profile;
  showForm.value = true;
}

function cancelForm() {
  showForm.value = false;
  editing.value = null;
}

async function onSubmit(payload: ProfileCreate) {
  saving.value = true;
  try {
    if (editing.value) {
      const res = await updateProfile(editing.value.id, payload);
      if (res) toast.success(t("profiles.toast.updated"));
      else toast.error(t("profiles.toast.updateFailed"));
    } else {
      const res = await createProfile(payload);
      if (res) toast.success(t("profiles.toast.created"));
      else toast.error(t("profiles.toast.createFailed"));
    }
    showForm.value = false;
    editing.value = null;
  } finally {
    saving.value = false;
  }
}

async function onSetDefault(profile: Profile) {
  const res = await setDefault(profile.id);
  if (res) toast.success(t("profiles.toast.defaultSet", { name: profile.name }));
}

// ── Two-click delete confirm ─────────────────────────────
const pendingDeleteId = ref<string | null>(null);

async function onDelete(profile: Profile) {
  if (pendingDeleteId.value === profile.id) {
    const ok = await deleteProfile(profile.id);
    if (ok) toast.success(t("profiles.toast.deleted"));
    pendingDeleteId.value = null;
  } else {
    pendingDeleteId.value = profile.id;
  }
}

function cancelDelete() {
  pendingDeleteId.value = null;
}
</script>

<template>
  <div class="space-y-6">
    <!-- Primary action lives on the tab bar (see ProfilesTabs) -->
    <Teleport defer to="#loadout-tab-action">
      <button
        v-if="!loading && profiles.length > 0"
        class="inline-flex items-center gap-1.5 rounded-lg border bg-base-200 px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-base-300"
        @click="openCreate"
      >
        <AppIcon name="i-lucide-plus" class="size-4" />
        {{ $t("profiles.newProfile") }}
      </button>
    </Teleport>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <AppIcon name="i-lucide-loader-2" class="size-6 animate-spin text-primary" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-20">
      <AppIcon name="i-lucide-alert-circle" class="size-8 text-error" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border px-4 py-2 text-sm text-foreground transition-colors hover:bg-base-300"
        @click="refresh()"
      >
        {{ $t("common.retry") }}
      </button>
    </div>

    <!-- Empty -->
    <EmptyState
      v-else-if="profiles.length === 0"
      icon="i-lucide-layers"
      :title="t('profiles.empty') || 'No Profiles'"
      description="Create a configuration profile to customize your character interaction settings."
      :action-label="t('profiles.newProfile') || 'New Profile'"
      @action="openCreate"
    />

    <!-- Profile grid -->
    <div v-else class="grid grid-cols-1 gap-3 lg:grid-cols-2">
      <ProfileCard
        v-for="(profile, index) in profiles"
        :key="profile.id"
        :profile="profile"
        :template-label="resolve(templates, profile.prompt_template_id)"
        :preset-label="resolve(presets, profile.preset_id)"
        :persona-label="resolve(personas, profile.persona_id)"
        :model-label="resolve(models, profile.model_id)"
        :pending-delete="pendingDeleteId === profile.id"
        class="animate-fade-in-up"
        :style="{ animationDelay: `${index * 30}ms` }"
        @edit="openEdit(profile)"
        @set-default="onSetDefault(profile)"
        @delete="onDelete(profile)"
        @mouseleave="cancelDelete"
      />
    </div>

    <!-- Create / Edit form (modal — keeps the list in view behind it) -->
    <Modal
      :show="showForm"
      :title="editing ? $t('profiles.form.editTitle') : $t('profiles.form.newTitle')"
      max-width="4xl"
      @close="cancelForm"
    >
      <ProfileForm
        :initial="editing"
        :templates="templates"
        :presets="presets"
        :personas="personas"
        :models="models"
        :saving="saving"
        @submit="onSubmit"
        @cancel="cancelForm"
      />
    </Modal>
  </div>
</template>

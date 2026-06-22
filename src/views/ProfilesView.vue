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

const { t } = useI18n();
const toast = useAppToast();

const { profiles, loading, error, createProfile, updateProfile, deleteProfile, setDefault, refresh } =
  useProfiles();
const { templates } = usePromptTemplates();
const { presets } = usePresets();
const { personas } = usePersonas();
// Load all models so every profile's model_id resolves to a name.
const { models } = useModels({ pageSize: 100 });

function resolve(list: { id: string; name: string }[], id: string | null | undefined): string | null {
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
  <div class="space-y-8 px-12 py-8">
    <!-- Header -->
    <div class="animate-fade-in-up flex items-start justify-between">
      <div>
        <h1 class="mb-1 font-cinzel text-2xl font-bold tracking-wide text-foreground">
          {{ $t('profiles.title') }}
        </h1>
        <p class="text-sm text-muted-foreground">{{ $t('profiles.subtitle') }}</p>
      </div>
      <button
        v-if="!showForm"
        class="flex items-center gap-2 rounded-lg border bg-card px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
        @click="openCreate"
      >
        <UIcon name="i-lucide-plus" class="h-4 w-4" />
        {{ $t('profiles.newProfile') }}
      </button>
    </div>

    <!-- Create / Edit form -->
    <ProfileForm
      v-if="showForm"
      :initial="editing"
      :templates="templates"
      :presets="presets"
      :personas="personas"
      :models="models"
      :saving="saving"
      @submit="onSubmit"
      @cancel="cancelForm"
    />

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <UIcon name="i-lucide-loader-2" class="h-6 w-6 animate-spin text-primary" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-20">
      <UIcon name="i-lucide-alert-circle" class="h-8 w-8 text-destructive" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent"
        @click="refresh()"
      >
        {{ $t('common.retry') }}
      </button>
    </div>

    <!-- Empty -->
    <div
      v-else-if="profiles.length === 0 && !showForm"
      class="flex flex-col items-center justify-center gap-3 py-20"
    >
      <UIcon name="i-lucide-layers" class="h-8 w-8 text-muted-foreground/40" />
      <p class="text-sm text-muted-foreground">{{ $t('profiles.empty') }}</p>
      <button
        class="flex items-center gap-2 rounded-lg border bg-card px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
        @click="openCreate"
      >
        <UIcon name="i-lucide-plus" class="h-4 w-4" />
        {{ $t('profiles.newProfile') }}
      </button>
    </div>

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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { client } from "@/api/client";
import { useProviders } from "@/composables/useProviders";
import { useProfiles } from "@/composables/useProfiles";
import { usePromptTemplates } from "@/composables/usePromptTemplates";
import { usePresets } from "@/composables/usePresets";
import { usePersonas } from "@/composables/usePersonas";
import { useModels } from "@/composables/useModels";
import { useAppToast } from "@/composables/useToast";
import ProfileForm from "@/components/profiles/ProfileForm.vue";
import ImportPresetModal from "@/components/connections/ImportPresetModal.vue";
import type { components } from "@/api/schema";

type DiscoveredModel = components["schemas"]["DiscoveredModel"];
type STImportResult = components["schemas"]["STImportResult"];
type ProfileCreate = components["schemas"]["ProfileCreate"];

const router = useRouter();
const toast = useAppToast();
const { t } = useI18n();

const step = ref<1 | 2 | 3>(1);
const createPath = ref<"choose" | "manual" | "import">("choose");

const { providers, loading: providersLoading } = useProviders();
const { profiles, createProfile, updateProfile } = useProfiles();
const { templates } = usePromptTemplates();
const { presets } = usePresets();
const { personas, createPersona } = usePersonas();
const { models } = useModels({ pageSize: 100 });

// Reka UI's Combobox forbids an item value of "" (it reserves the empty string
// for the cleared state), so the "None" option uses a sentinel that maps back
// to null on submit.
const NONE = "__none__";

function toOptions(list: { id: string; name: string }[], noneLabel: string) {
  return [{ label: noneLabel, value: NONE }, ...list.map((x) => ({ label: x.name, value: x.id }))];
}

// Stable reference so the large model list isn't re-patched on every render
// (an inline array crashes Reka UI's combobox popper — see ProfileForm).
// Models are registries labelled by display_name, not the generic `name`.
const modelOptions = computed(() => [
  { label: "Select a model...", value: NONE },
  ...models.value.map((m) => ({ label: m.display_name, value: m.id })),
]);

function labelFor(list: { id: string; name: string }[], id: string, noneLabel: string) {
  return list.find((x) => x.id === id)?.name ?? noneLabel;
}

function modelLabelFor(id: string) {
  return models.value.find((m) => m.id === id)?.display_name ?? "Select a model...";
}

// ── Quick persona creation (shown inline when none exist yet) ───
const quickPersonaName = ref("");
const creatingPersona = ref(false);

async function quickCreatePersona() {
  if (!quickPersonaName.value.trim()) return;
  creatingPersona.value = true;
  try {
    const created = await createPersona(quickPersonaName.value.trim(), true);
    if (created) {
      followUpPersonaId.value = created.id;
      quickPersonaName.value = "";
      toast.success(t("setup.toast.personaCreated"));
    } else {
      toast.error(t("setup.toast.personaFailed"));
    }
  } finally {
    creatingPersona.value = false;
  }
}

const providerTypeIcons: Record<string, string> = {
  openai: "i-lucide-bot",
  anthropic: "i-lucide-brain",
  google: "i-lucide-sparkles",
  ollama: "i-lucide-server",
  openrouter: "i-lucide-route",
  xai: "i-lucide-zap",
  lmstudio: "i-lucide-cpu",
  custom: "i-lucide-settings",
};

const localProviders = computed(() =>
  providers.value.filter((p) => p.provider_type === "ollama" || p.provider_type === "lmstudio"),
);
const cloudProviders = computed(() =>
  providers.value.filter(
    (p) => p.provider_type !== "ollama" && p.provider_type !== "lmstudio" && p.enabled,
  ),
);

interface LocalStatus {
  loading: boolean;
  models: DiscoveredModel[] | null;
  reachable: boolean;
}
const localStatus = ref<Record<string, LocalStatus>>({});

async function checkLocalProvider(id: string) {
  localStatus.value[id] = { loading: true, models: null, reachable: false };
  try {
    const { data, error } = await client.GET("/api/providers/{provider_id}/models/available", {
      params: { path: { provider_id: id } },
    });
    if (error || !data) throw new Error("unreachable");
    localStatus.value[id] = { loading: false, models: data.models, reachable: true };
  } catch {
    localStatus.value[id] = { loading: false, models: null, reachable: false };
  }
}

watch(
  localProviders,
  (list) => {
    for (const p of list) {
      if (!localStatus.value[p.id]) checkLocalProvider(p.id);
    }
  },
  { immediate: true },
);

function skip() {
  router.push("/loadouts");
}

// Profiles missing a model (e.g. an ST import that was never finished) can't
// actually start a chat — surface them so the user can resume instead of
// losing track of them the moment they navigate away.
const incompleteProfiles = computed(() => profiles.value.filter((p) => !p.model_id));

// ── Step 2: manual profile creation ──────────────────────
async function onManualSubmit(payload: ProfileCreate) {
  if (!payload.model_id) {
    toast.error(t("setup.toast.pickModel"));
    return;
  }
  const res = await createProfile({ ...payload, is_default: true });
  if (res) {
    toast.success(t("setup.toast.profileCreated"));
    step.value = 3;
  } else {
    toast.error(t("setup.toast.profileFailed"));
  }
}

// ── Step 2: import ST preset ─────────────────────────────
const showImportModal = ref(false);

// General "finish this profile" state — covers both a just-imported profile
// and resuming a previously-abandoned incomplete one.
const profileToFinish = ref<{ id: string; name: string } | null>(null);
const followUpModelId = ref(NONE);
const followUpPersonaId = ref(NONE);
const finishingImport = ref(false);

function onImported(result: STImportResult) {
  if (!result.profile_id) return;
  profileToFinish.value = {
    id: result.profile_id,
    name: result.profile_name ?? "Imported Profile",
  };
  showImportModal.value = false;
}

function resumeIncompleteProfile(profile: { id: string; name: string }) {
  profileToFinish.value = { id: profile.id, name: profile.name };
}

async function finishImportSetup() {
  if (!profileToFinish.value) return;
  if (followUpModelId.value === NONE) {
    toast.error(t("setup.toast.pickModel"));
    return;
  }
  finishingImport.value = true;
  try {
    const res = await updateProfile(profileToFinish.value.id, {
      model_id: followUpModelId.value === NONE ? null : followUpModelId.value,
      persona_id: followUpPersonaId.value === NONE ? null : followUpPersonaId.value,
      is_default: true,
    });
    if (res) {
      toast.success(t("setup.toast.profileReady"));
      step.value = 3;
    } else {
      toast.error(t("setup.toast.finishFailed"));
    }
  } finally {
    finishingImport.value = false;
  }
}

function finish() {
  router.push("/");
}
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-6 px-6 py-10">
    <!-- Header -->
    <div class="text-center">
      <h1 class="mb-1 font-cinzel text-2xl font-bold tracking-wide text-foreground">
        Let's Get You Set Up
      </h1>
      <p class="text-sm text-muted-foreground">
        A quick check of your providers, then create your first profile.
      </p>
    </div>

    <!-- Step indicator -->
    <div class="flex items-center justify-center gap-2 text-xs text-muted-foreground">
      <span :class="step >= 1 ? 'text-primary' : ''">1. Providers</span>
      <AppIcon name="i-lucide-chevron-right" class="size-3" />
      <span :class="step >= 2 ? 'text-primary' : ''">2. Profile</span>
      <AppIcon name="i-lucide-chevron-right" class="size-3" />
      <span :class="step >= 3 ? 'text-primary' : ''">3. Done</span>
    </div>

    <!-- Step 1: Provider readiness -->
    <div v-if="step === 1" class="space-y-4">
      <div class="rounded-xl border bg-base-200/50 p-5">
        <h2
          class="mb-3 font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
        >
          Local Providers
        </h2>
        <div v-if="providersLoading" class="flex justify-center py-4">
          <AppIcon name="i-lucide-loader-2" class="size-5 animate-spin text-muted-foreground" />
        </div>
        <div v-else-if="localProviders.length === 0" class="text-xs text-muted-foreground">
          No local providers configured.
        </div>
        <ul v-else class="space-y-2">
          <li
            v-for="provider in localProviders"
            :key="provider.id"
            class="flex items-center justify-between rounded-lg bg-base-300/40 px-3 py-2.5"
          >
            <span class="flex items-center gap-2 text-sm text-foreground">
              <AppIcon
                :name="providerTypeIcons[provider.provider_type] || 'i-lucide-settings'"
                class="size-4 text-muted-foreground"
              />
              {{ provider.name }}
            </span>
            <span
              v-if="localStatus[provider.id]?.loading"
              class="flex items-center gap-1.5 text-xs text-muted-foreground"
            >
              <AppIcon name="i-lucide-loader-2" class="size-3.5 animate-spin" />
              Checking...
            </span>
            <span
              v-else-if="localStatus[provider.id]?.reachable"
              class="inline-flex items-center gap-1.5 rounded-full bg-success/10 px-2.5 py-0.5 text-xs font-medium text-success"
            >
              <span class="size-1.5 rounded-full bg-success" />
              {{ localStatus[provider.id]?.models?.length ?? 0 }} models found
            </span>
            <span
              v-else
              class="inline-flex items-center gap-1.5 rounded-full bg-warning/10 px-2.5 py-0.5 text-xs font-medium text-warning"
            >
              <span class="size-1.5 rounded-full bg-warning" />
              Not reachable
            </span>
          </li>
        </ul>
      </div>

      <div class="rounded-xl border bg-base-200/50 p-5">
        <h2
          class="mb-3 font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
        >
          Cloud Providers
        </h2>
        <ul class="space-y-2">
          <li
            v-for="provider in cloudProviders"
            :key="provider.id"
            class="flex items-center justify-between rounded-lg bg-base-300/40 px-3 py-2.5"
          >
            <span class="flex items-center gap-2 text-sm text-foreground">
              <AppIcon
                :name="providerTypeIcons[provider.provider_type] || 'i-lucide-settings'"
                class="size-4 text-muted-foreground"
              />
              {{ provider.name }}
            </span>
            <span
              class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
              :class="
                provider.api_key_configured
                  ? 'bg-success/10 text-success'
                  : 'bg-warning/10 text-warning'
              "
            >
              <span
                class="size-1.5 rounded-full"
                :class="provider.api_key_configured ? 'bg-success' : 'bg-warning'"
              />
              {{ provider.api_key_configured ? "Key configured" : `Set ${provider.env_var_name}` }}
            </span>
          </li>
        </ul>
      </div>

      <div class="flex items-center justify-between">
        <button
          class="text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
          @click="skip"
        >
          I'll do this manually
        </button>
        <button
          class="flex h-9 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-content shadow-sm transition-all hover:shadow-[0_2px_12px_var(--color-primary)/0.3]"
          @click="step = 2"
        >
          Next
          <AppIcon name="i-lucide-arrow-right" class="size-4" />
        </button>
      </div>
    </div>

    <!-- Step 2: create profile -->
    <div v-else-if="step === 2" class="space-y-4">
      <div v-if="createPath === 'choose' && !profileToFinish">
        <!-- Unfinished profiles: resume instead of losing track of them -->
        <div
          v-if="incompleteProfiles.length > 0"
          class="mb-4 rounded-xl border border-warning/30 bg-warning/5 p-4"
        >
          <p class="mb-2 text-xs font-medium text-warning">
            {{
              incompleteProfiles.length === 1
                ? "You have an unfinished profile"
                : `You have ${incompleteProfiles.length} unfinished profiles`
            }}
          </p>
          <div class="space-y-2">
            <div
              v-for="p in incompleteProfiles"
              :key="p.id"
              class="flex items-center justify-between rounded-lg bg-base-300/40 px-3 py-2"
            >
              <span class="text-sm text-foreground">{{ p.name }}</span>
              <button
                type="button"
                class="rounded-lg border px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-base-300"
                @click="resumeIncompleteProfile(p)"
              >
                Finish Setup
              </button>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <button
            class="flex flex-col items-center gap-3 rounded-xl border bg-base-200/50 p-6 text-center transition-colors hover:border-primary/40 hover:bg-base-300"
            @click="createPath = 'manual'"
          >
            <AppIcon name="i-lucide-sliders-horizontal" class="size-8 text-primary" />
            <span class="font-cinzel text-sm font-semibold text-foreground">Create Manually</span>
            <span class="text-xs text-muted-foreground"
              >Pick a model, template, preset, and persona yourself.</span
            >
          </button>
          <button
            class="flex flex-col items-center gap-3 rounded-xl border bg-base-200/50 p-6 text-center transition-colors hover:border-primary/40 hover:bg-base-300"
            @click="showImportModal = true"
          >
            <AppIcon name="i-lucide-upload" class="size-8 text-primary" />
            <span class="font-cinzel text-sm font-semibold text-foreground">Import ST Preset</span>
            <span class="text-xs text-muted-foreground"
              >Bring in a SillyTavern chat-completion preset.</span
            >
          </button>
        </div>
      </div>

      <div v-else-if="createPath === 'manual'" class="space-y-4">
        <!-- No personas yet: offer to create one before the form's persona dropdown is reached -->
        <div v-if="personas.length === 0" class="rounded-xl border bg-base-200/50 p-5">
          <span class="mb-1.5 block text-xs font-medium text-muted-foreground"
            >You don't have a persona yet (optional, but recommended)</span
          >
          <div class="flex items-center gap-2">
            <input
              v-model="quickPersonaName"
              type="text"
              placeholder="Persona name (e.g. your name)"
              class="h-11 w-full rounded-lg border bg-base-100 px-3 text-sm text-foreground placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
              @keydown.enter="quickCreatePersona"
            />
            <button
              type="button"
              class="flex h-11 shrink-0 items-center gap-1.5 rounded-lg border px-3 text-sm text-foreground transition-colors hover:bg-base-300 disabled:opacity-50"
              :disabled="creatingPersona || !quickPersonaName.trim()"
              @click="quickCreatePersona"
            >
              <AppIcon
                :name="creatingPersona ? 'i-lucide-loader-2' : 'i-lucide-plus'"
                class="size-4"
                :class="{ 'animate-spin': creatingPersona }"
              />
              Create
            </button>
          </div>
        </div>

        <ProfileForm
          :templates="templates"
          :presets="presets"
          :personas="personas"
          :models="models"
          @submit="onManualSubmit"
          @cancel="createPath = 'choose'"
        />
      </div>

      <!-- Attach a model to finish a just-imported or previously-abandoned profile -->
      <div v-if="profileToFinish" class="rounded-xl border bg-base-200/50 p-6">
        <h2 class="mb-4 font-cinzel text-sm font-semibold tracking-wide text-foreground">
          Attach a Model
        </h2>
        <p class="mb-4 text-xs text-muted-foreground">
          Pick a model to finish setting up "{{ profileToFinish.name }}" as your default profile.
        </p>
        <div class="space-y-4">
          <div>
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Model</span>
            <SelectMenu
              v-model="followUpModelId"
              :items="modelOptions"
              value-key="value"
              :search-input="true"
            >
              <button
                type="button"
                class="flex h-11 w-full items-center justify-between gap-1.5 rounded-lg border bg-base-300/40 px-3 text-sm text-foreground outline-none"
              >
                <span class="flex min-w-0 items-center gap-2">
                  <AppIcon name="i-lucide-cpu" class="size-4 shrink-0 text-muted-foreground" />
                  <span class="truncate">{{ modelLabelFor(followUpModelId) }}</span>
                </span>
                <AppIcon
                  name="i-lucide-chevron-down"
                  class="size-4 shrink-0 text-muted-foreground"
                />
              </button>
            </SelectMenu>
          </div>

          <div>
            <span class="mb-1 block text-xs font-medium text-muted-foreground">Persona</span>

            <!-- No personas yet: guide the user to create one first -->
            <div v-if="personas.length === 0" class="flex items-center gap-2">
              <input
                v-model="quickPersonaName"
                type="text"
                placeholder="Persona name (e.g. your name)"
                class="h-11 w-full rounded-lg border bg-base-300/40 px-3 text-sm text-foreground placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
                @keydown.enter="quickCreatePersona"
              />
              <button
                type="button"
                class="flex h-11 shrink-0 items-center gap-1.5 rounded-lg border px-3 text-sm text-foreground transition-colors hover:bg-base-300 disabled:opacity-50"
                :disabled="creatingPersona || !quickPersonaName.trim()"
                @click="quickCreatePersona"
              >
                <AppIcon
                  :name="creatingPersona ? 'i-lucide-loader-2' : 'i-lucide-plus'"
                  class="size-4"
                  :class="{ 'animate-spin': creatingPersona }"
                />
                Create
              </button>
            </div>

            <SelectMenu
              v-else
              v-model="followUpPersonaId"
              :items="toOptions(personas, 'No persona')"
              value-key="value"
              :search-input="false"
            >
              <button
                type="button"
                class="flex h-11 w-full items-center justify-between gap-1.5 rounded-lg border bg-base-300/40 px-3 text-sm text-foreground outline-none"
              >
                <span class="flex min-w-0 items-center gap-2">
                  <AppIcon name="i-lucide-user" class="size-4 shrink-0 text-muted-foreground" />
                  <span class="truncate">{{
                    labelFor(personas, followUpPersonaId, "No persona")
                  }}</span>
                </span>
                <AppIcon
                  name="i-lucide-chevron-down"
                  class="size-4 shrink-0 text-muted-foreground"
                />
              </button>
            </SelectMenu>
          </div>

          <div class="flex items-center gap-3">
            <button
              class="flex h-9 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-content disabled:opacity-50"
              :disabled="finishingImport"
              @click="finishImportSetup"
            >
              <AppIcon
                :name="finishingImport ? 'i-lucide-loader-2' : 'i-lucide-check'"
                class="size-4"
                :class="{ 'animate-spin': finishingImport }"
              />
              Finish
            </button>
            <button
              class="rounded-lg border px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
              @click="profileToFinish = null"
            >
              Back
            </button>
          </div>
        </div>
      </div>

      <div class="flex items-center justify-between">
        <button
          class="text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
          @click="skip"
        >
          I'll do this manually
        </button>
      </div>
    </div>

    <!-- Step 3: done -->
    <div
      v-else
      class="flex flex-col items-center gap-4 rounded-xl border bg-base-200/50 p-10 text-center"
    >
      <AppIcon name="i-lucide-circle-check" class="size-10 text-success" />
      <h2 class="font-cinzel text-lg font-semibold text-foreground">You're all set</h2>
      <p class="text-sm text-muted-foreground">
        Your first profile is ready. Head back and start a tale.
      </p>
      <button
        class="flex h-9 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-content shadow-sm"
        @click="finish"
      >
        Done
      </button>
    </div>

    <ImportPresetModal
      v-if="showImportModal"
      @close="showImportModal = false"
      @imported="onImported"
    />
  </div>
</template>

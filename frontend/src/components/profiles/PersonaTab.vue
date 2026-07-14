<script setup lang="ts">
import { fallbackAvatarUrl } from "@/utils/avatar";
import { ref, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { client, extractApiError } from "@/api/client";
import type { components } from "@/api/schema";
import Modal from "@/components/shared/Modal.vue";

const { t } = useI18n();

type PersonaResponse = components["schemas"]["PersonaResponse"];

const personas = ref<PersonaResponse[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// ── Form state ──────────────────────────────────────────
const showForm = ref(false);
const editingId = ref<string | null>(null);
const formName = ref("");
const formDescription = ref("");
const formIsDefault = ref(false);
const formAvatarFile = ref<File | null>(null);
const formSaving = ref(false);

// ── Delete state ────────────────────────────────────────
const pendingDeleteId = ref<string | null>(null);

async function loadPersonas() {
  try {
    const { data, error: apiError } = await client.GET("/api/personas/");
    if (apiError) {
      error.value = t("settings.persona.failedLoad");
      return;
    }
    if (data) {
      personas.value = data.items;
    }
  } catch {
    error.value = "Failed to load personas";
  } finally {
    loading.value = false;
  }
}

onMounted(loadPersonas);

function getAvatarSrc(persona: PersonaResponse): string {
  return (
    persona.avatar_thumbnail ||
    persona.avatar ||
    fallbackAvatarUrl(persona.name, 80)
  );
}

// ── Create / Edit form ──────────────────────────────────
function openCreateForm() {
  editingId.value = null;
  formName.value = "";
  formDescription.value = "";
  formIsDefault.value = false;
  formAvatarFile.value = null;
  showForm.value = true;
}

function openEditForm(persona: PersonaResponse) {
  editingId.value = persona.id;
  formName.value = persona.name;
  formDescription.value = persona.description || "";
  formIsDefault.value = persona.is_default;
  formAvatarFile.value = null;
  showForm.value = true;
}

function cancelForm() {
  showForm.value = false;
  editingId.value = null;
}

function onAvatarChange(event: Event) {
  const target = event.target as HTMLInputElement;
  formAvatarFile.value = target.files?.[0] || null;
}

async function saveForm() {
  if (!formName.value.trim()) return;
  formSaving.value = true;

  try {
    const formData = new FormData();
    formData.append("name", formName.value);
    formData.append("description", formDescription.value);
    formData.append("is_default", String(formIsDefault.value));
    if (formAvatarFile.value) {
      formData.append("avatar", formAvatarFile.value);
    }

    if (editingId.value) {
      // Update
      const response = await fetch(`/api/personas/${editingId.value}`, {
        method: "PUT",
        body: formData,
      });
      if (!response.ok) throw new Error("Update failed");
      const updated: PersonaResponse = await response.json();

      // If this became default, unset others locally
      if (updated.is_default) {
        personas.value.forEach((p) => {
          if (p.id !== updated.id) p.is_default = false;
        });
      }

      const idx = personas.value.findIndex((p) => p.id === editingId.value);
      if (idx !== -1) personas.value[idx] = updated;
    } else {
      // Create
      const response = await fetch("/api/personas/", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) throw new Error("Create failed");
      const created: PersonaResponse = await response.json();

      // If this became default, unset others locally
      if (created.is_default) {
        personas.value.forEach((p) => (p.is_default = false));
      }

      personas.value.unshift(created);
    }

    showForm.value = false;
    editingId.value = null;
  } catch {
    // Silently fail for mock — in production would show toast
  } finally {
    formSaving.value = false;
  }
}

// ── Delete ──────────────────────────────────────────────
function onDeleteClick(personaId: string) {
  if (pendingDeleteId.value === personaId) {
    confirmDelete(personaId);
  } else {
    pendingDeleteId.value = personaId;
  }
}

async function confirmDelete(personaId: string) {
  try {
    const { error: apiError } = await client.DELETE("/api/personas/{persona_id}", {
      params: { path: { persona_id: personaId } },
    });
    if (apiError) throw extractApiError(apiError, "Failed to delete persona");
    personas.value = personas.value.filter((p) => p.id !== personaId);
  } catch {
    // Silently fail for mock
  } finally {
    pendingDeleteId.value = null;
  }
}

function cancelDelete() {
  pendingDeleteId.value = null;
}

// ── Set Default ─────────────────────────────────────────
async function setDefault(personaId: string) {
  try {
    const { data, error: apiError } = await client.POST("/api/personas/{persona_id}/set-default", {
      params: { path: { persona_id: personaId } },
    });
    if (apiError || !data) throw extractApiError(apiError, "Failed to set default persona");

    // Update local state
    personas.value.forEach((p) => {
      p.is_default = p.id === data.id;
    });
  } catch {
    // Silently fail for mock
  }
}
</script>

<template>
  <div class="mx-auto max-w-2xl animate-fade-in-up">
    <!-- Primary action lives on the tab bar (see ProfilesTabs) -->
    <Teleport defer to="#loadout-tab-action">
      <button
        class="inline-flex items-center gap-1.5 rounded-lg border bg-base-200 px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-base-300"
        @click="openCreateForm"
      >
        <AppIcon name="i-lucide-plus" class="size-4" />
        {{ $t("settings.persona.createPersona") }}
      </button>
    </Teleport>

    <!-- Create/Edit form (modal — keeps the list in view behind it) -->
    <Modal
      :show="showForm"
      :title="editingId ? $t('settings.persona.editPersona') : $t('settings.persona.newPersona')"
      max-width="xl"
      @close="cancelForm"
    >
      <div class="space-y-4">
        <label class="block">
          <span class="mb-1 block text-xs font-medium text-muted-foreground">{{
            $t("settings.persona.name")
          }}</span>
          <input
            v-model="formName"
            type="text"
            :placeholder="$t('settings.persona.namePlaceholder')"
            class="w-full rounded-lg border bg-base-100 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
          />
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-medium text-muted-foreground">{{
            $t("settings.persona.description")
          }}</span>
          <textarea
            v-model="formDescription"
            rows="3"
            :placeholder="$t('settings.persona.descriptionPlaceholder')"
            class="w-full resize-y rounded-lg border bg-base-100 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
          />
        </label>
        <div class="flex items-center gap-3">
          <label class="flex items-center gap-2 text-sm text-foreground">
            <input
              v-model="formIsDefault"
              type="checkbox"
              class="rounded text-primary focus:ring-primary"
            />
            {{ $t("settings.persona.setAsDefault") }}
          </label>
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-muted-foreground">{{
            $t("settings.persona.avatar")
          }}</label>
          <input
            type="file"
            accept="image/*"
            class="w-full text-sm text-muted-foreground file:mr-3 file:rounded-lg file:border file:border-border file:bg-base-100 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-foreground hover:file:bg-base-300"
            @change="onAvatarChange"
          />
        </div>
        <div class="flex items-center gap-3">
          <button
            class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-content transition-colors hover:bg-primary/90 disabled:opacity-50"
            :disabled="formSaving || !formName.trim()"
            @click="saveForm"
          >
            <span v-if="formSaving" class="flex items-center gap-2">
              <AppIcon name="i-lucide-loader-2" class="size-3.5 animate-spin" />
              {{ $t("common.saving") }}
            </span>
            <span v-else>
              {{
                editingId
                  ? $t("settings.persona.saveChanges")
                  : $t("settings.persona.createPersona")
              }}
            </span>
          </button>
          <button
            class="rounded-lg border px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
            @click="cancelForm"
          >
            {{ $t("common.cancel") }}
          </button>
        </div>
      </div>
    </Modal>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-16">
      <AppIcon name="i-lucide-loader-2" class="size-6 animate-spin text-muted-foreground" />
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="rounded-xl border bg-base-200/50 p-8 text-center">
      <AppIcon name="i-lucide-alert-circle" class="mx-auto mb-2 size-8 text-muted-foreground" />
      <p class="text-sm text-muted-foreground">{{ error }}</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="personas.length === 0" class="rounded-xl border bg-base-200/50 p-8 text-center">
      <AppIcon name="i-lucide-user-circle" class="mx-auto mb-2 size-8 text-muted-foreground" />
      <p class="text-sm text-muted-foreground">{{ $t("settings.persona.noPersonas") }}</p>
    </div>

    <!-- Persona List -->
    <div v-else class="space-y-3">
      <div
        v-for="persona in personas"
        :key="persona.id"
        class="group flex items-center gap-4 rounded-xl border bg-base-200/50 p-4 transition-colors hover:bg-base-200/80"
      >
        <!-- Avatar -->
        <img
          :src="getAvatarSrc(persona)"
          :alt="persona.name"
          class="size-12 shrink-0 rounded-full object-cover ring-1 ring-border"
        />

        <!-- Info -->
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2">
            <p class="font-cinzel text-sm font-semibold tracking-wide text-foreground">
              {{ persona.name }}
            </p>
            <button v-if="persona.is_default" class="cursor-default">
              <span
                class="inline-flex items-center rounded-md bg-primary/10 px-2 py-0.5 text-[0.6875rem] font-medium text-primary"
              >
                {{ $t("settings.persona.default") }}
              </span>
            </button>
            <button
              v-else
              class="opacity-0 transition-opacity group-hover:opacity-100"
              title="Set as default"
              @click="setDefault(persona.id)"
            >
              <span
                class="inline-flex items-center rounded-md border px-2 py-0.5 text-[0.6875rem] font-medium text-muted-foreground transition-colors hover:bg-base-300"
              >
                {{ $t("settings.persona.setDefault") }}
              </span>
            </button>
          </div>
          <p v-if="persona.description" class="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
            {{ persona.description }}
          </p>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <button
            class="inline-flex size-8 items-center justify-center rounded-md text-sm text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
            title="Edit persona"
            aria-label="Edit persona"
            @click="openEditForm(persona)"
          >
            <AppIcon name="i-lucide-pencil" class="size-4" />
          </button>
          <button
            class="inline-flex size-8 items-center justify-center rounded-md text-sm transition-colors"
            :class="
              pendingDeleteId === persona.id
                ? 'bg-error/10 text-error'
                : 'text-muted-foreground hover:bg-base-300 hover:text-foreground'
            "
            :title="pendingDeleteId === persona.id ? 'Click again to confirm' : 'Delete persona'"
            :aria-label="
              pendingDeleteId === persona.id ? 'Click again to confirm' : 'Delete persona'
            "
            @click.stop="onDeleteClick(persona.id)"
            @mouseleave="cancelDelete"
          >
            <AppIcon
              :name="
                pendingDeleteId === persona.id ? 'i-lucide-alert-triangle' : 'i-lucide-trash-2'
              "
              class="size-4"
            />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

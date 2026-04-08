<script setup lang="ts">
import { ref, onMounted } from "vue";
import { client } from "@/api/client";
import type { components } from "@/api/schema";

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
      error.value = "Failed to load personas";
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
  return persona.avatar_thumbnail
    || persona.avatar
    || `https://ui-avatars.com/api/?name=${encodeURIComponent(persona.name)}&background=C9922E&color=fff&size=80`;
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
    const response = await fetch(`/api/personas/${personaId}`, {
      method: "DELETE",
    });
    if (!response.ok) throw new Error("Delete failed");
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
    const response = await fetch(`/api/personas/${personaId}/set-default`, {
      method: "POST",
    });
    if (!response.ok) throw new Error("Set default failed");
    const updated: PersonaResponse = await response.json();

    // Update local state
    personas.value.forEach((p) => {
      p.is_default = p.id === updated.id;
    });
  } catch {
    // Silently fail for mock
  }
}
</script>

<template>
  <div class="mx-auto max-w-2xl animate-fade-in-up">
    <!-- Header Row -->
    <div class="mb-4 flex items-center justify-between">
      <h3 class="font-cinzel text-sm font-semibold uppercase tracking-widest text-muted-foreground">
        Your Personas
      </h3>
      <UButton
        icon="i-lucide-plus"
        label="Create Persona"
        size="sm"
        variant="outline"
        @click="openCreateForm"
      />
    </div>

    <!-- Inline Create/Edit Form -->
    <div
      v-if="showForm"
      class="mb-4 animate-fade-in-up rounded-xl border bg-card/50 p-5"
    >
      <h4 class="mb-4 font-cinzel text-sm font-semibold tracking-wide text-foreground">
        {{ editingId ? "Edit Persona" : "New Persona" }}
      </h4>
      <div class="space-y-4">
        <div>
          <label class="mb-1 block text-xs font-medium text-muted-foreground">Name</label>
          <input
            v-model="formName"
            type="text"
            placeholder="Persona name..."
            class="w-full rounded-lg border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-muted-foreground">Description</label>
          <textarea
            v-model="formDescription"
            rows="3"
            placeholder="Describe this persona for RP context..."
            class="w-full resize-y rounded-lg border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
        <div class="flex items-center gap-3">
          <label class="flex items-center gap-2 text-sm text-foreground">
            <input
              v-model="formIsDefault"
              type="checkbox"
              class="rounded text-primary focus:ring-primary"
            />
            Set as default
          </label>
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-muted-foreground">Avatar</label>
          <input
            type="file"
            accept="image/*"
            class="w-full text-sm text-muted-foreground file:mr-3 file:rounded-lg file:border file:border-border file:bg-background file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-foreground hover:file:bg-accent"
            @change="onAvatarChange"
          />
        </div>
        <div class="flex items-center gap-3">
          <button
            class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
            :disabled="formSaving || !formName.trim()"
            @click="saveForm"
          >
            <span v-if="formSaving" class="flex items-center gap-2">
              <UIcon name="i-lucide-loader-2" class="h-3.5 w-3.5 animate-spin" />
              Saving...
            </span>
            <span v-else>
              {{ editingId ? "Save Changes" : "Create Persona" }}
            </span>
          </button>
          <button
            class="rounded-lg border px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            @click="cancelForm"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-16">
      <UIcon name="i-lucide-loader-2" class="h-6 w-6 animate-spin text-muted-foreground" />
    </div>

    <!-- Error State -->
    <div
      v-else-if="error"
      class="rounded-xl border bg-card/50 p-8 text-center"
    >
      <UIcon name="i-lucide-alert-circle" class="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
      <p class="text-sm text-muted-foreground">{{ error }}</p>
    </div>

    <!-- Empty State -->
    <div
      v-else-if="personas.length === 0"
      class="rounded-xl border bg-card/50 p-8 text-center"
    >
      <UIcon name="i-lucide-user-circle" class="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
      <p class="text-sm text-muted-foreground">No personas found. Create one to get started.</p>
    </div>

    <!-- Persona List -->
    <div v-else class="space-y-3">
      <div
        v-for="persona in personas"
        :key="persona.id"
        class="group flex items-center gap-4 rounded-xl border bg-card/50 p-4 transition-colors hover:bg-card/80"
      >
        <!-- Avatar -->
        <img
          :src="getAvatarSrc(persona)"
          :alt="persona.name"
          class="h-12 w-12 flex-shrink-0 rounded-full object-cover ring-1 ring-border"
        />

        <!-- Info -->
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2">
            <p class="font-cinzel text-sm font-semibold tracking-wide text-foreground">
              {{ persona.name }}
            </p>
            <button
              v-if="persona.is_default"
              class="cursor-default"
            >
              <UBadge
                label="Default"
                size="sm"
                variant="subtle"
                color="primary"
              />
            </button>
            <button
              v-else
              class="opacity-0 transition-opacity group-hover:opacity-100"
              title="Set as default"
              @click="setDefault(persona.id)"
            >
              <UBadge
                label="Set Default"
                size="sm"
                variant="outline"
                color="neutral"
                class="cursor-pointer hover:bg-accent"
              />
            </button>
          </div>
          <p
            v-if="persona.description"
            class="mt-0.5 line-clamp-2 text-xs text-muted-foreground"
          >
            {{ persona.description }}
          </p>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <UButton
            icon="i-lucide-pencil"
            size="sm"
            variant="ghost"
            color="neutral"
            @click="openEditForm(persona)"
          />
          <button
            class="inline-flex h-8 w-8 items-center justify-center rounded-md text-sm transition-colors"
            :class="
              pendingDeleteId === persona.id
                ? 'bg-destructive/10 text-destructive'
                : 'text-muted-foreground hover:bg-accent hover:text-foreground'
            "
            :title="pendingDeleteId === persona.id ? 'Click again to confirm' : 'Delete persona'"
            @click.stop="onDeleteClick(persona.id)"
            @mouseleave="cancelDelete"
          >
            <UIcon
              :name="pendingDeleteId === persona.id ? 'i-lucide-alert-triangle' : 'i-lucide-trash-2'"
              class="h-4 w-4"
            />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

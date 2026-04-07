<script setup lang="ts">
import { ref, onMounted } from "vue";
import { client, getPersonaAvatarUrl } from "@/api/client";
import type { components } from "@/api/schema";

type PersonaResponse = components["schemas"]["PersonaResponse"];

const personas = ref<PersonaResponse[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

onMounted(async () => {
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
});

function getAvatarSrc(persona: PersonaResponse): string {
  if (persona.avatar) {
    return getPersonaAvatarUrl(persona.id);
  }
  const encoded = encodeURIComponent(persona.name);
  return `https://ui-avatars.com/api/?name=${encoded}&background=b45309&color=fff&size=80`;
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
        disabled
      />
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-16">
      <UIcon name="i-lucide-loader-2" class="h-6 w-6 animate-spin text-muted-foreground" />
    </div>

    <!-- Error State -->
    <div
      v-else-if="error"
      class="rounded-xl border border-[var(--border)] bg-card/50 p-8 text-center"
    >
      <UIcon name="i-lucide-alert-circle" class="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
      <p class="text-sm text-muted-foreground">{{ error }}</p>
    </div>

    <!-- Empty State -->
    <div
      v-else-if="personas.length === 0"
      class="rounded-xl border border-[var(--border)] bg-card/50 p-8 text-center"
    >
      <UIcon name="i-lucide-user-circle" class="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
      <p class="text-sm text-muted-foreground">No personas found. Create one to get started.</p>
    </div>

    <!-- Persona List -->
    <div v-else class="space-y-3">
      <div
        v-for="persona in personas"
        :key="persona.id"
        class="flex items-center gap-4 rounded-xl border border-[var(--border)] bg-card/50 p-4 transition-colors hover:bg-card/80"
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
            <UBadge
              v-if="persona.is_default"
              label="Default"
              size="sm"
              variant="subtle"
              color="primary"
            />
          </div>
          <p
            v-if="persona.description"
            class="mt-0.5 line-clamp-2 text-xs text-muted-foreground"
          >
            {{ persona.description }}
          </p>
        </div>

        <!-- Edit Button -->
        <UButton
          icon="i-lucide-pencil"
          size="sm"
          variant="ghost"
          color="neutral"
          disabled
        />
      </div>
    </div>
  </div>
</template>

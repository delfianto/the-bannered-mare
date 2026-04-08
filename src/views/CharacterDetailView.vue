<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { client } from "@/api/client";
import type { components } from "@/api/schema";
import NarrativeText from "@/components/chat/NarrativeText.vue";

type CharacterResponse = components["schemas"]["CharacterResponse"];

const route = useRoute();
const router = useRouter();
const { t } = useI18n();

const character = ref<CharacterResponse | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

const characterId = computed(() => route.params.id as string);

onMounted(async () => {
  try {
    const { data, error: apiError } = await client.GET("/api/characters/{character_id}", {
      params: { path: { character_id: characterId.value } },
    });

    if (apiError) {
      error.value = t("characters.notFound");
      return;
    }

    if (data) {
      character.value = data;
    }
  } catch {
    error.value = t("characters.failedLoad");
  } finally {
    loading.value = false;
  }
});

function avatarSrc(): string {
  if (!character.value) return "";
  return (
    character.value.avatar
    || character.value.avatar_thumbnail
    || `https://ui-avatars.com/api/?name=${encodeURIComponent(character.value.name)}&background=C9922E&color=fff&size=600`
  );
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function genderLabel(gender: string | null | undefined, customGender: string | null | undefined): string {
  if (!gender) return t("characters.detail.notSpecified");
  if (gender === "others" && customGender) return customGender;
  return gender.charAt(0).toUpperCase() + gender.slice(1);
}

function startTale() {
  router.push({
    path: "/tales",
    query: { new: "true", character: characterId.value },
  });
}
</script>

<template>
  <!-- Loading -->
  <div v-if="loading" class="flex flex-1 items-center justify-center py-20">
    <UIcon name="i-lucide-loader-2" class="h-8 w-8 animate-spin text-primary" />
  </div>

  <!-- Error -->
  <div v-else-if="error || !character" class="flex flex-1 flex-col items-center justify-center gap-4 py-20">
    <UIcon name="i-lucide-alert-circle" class="h-10 w-10 text-muted-foreground/40" />
    <p class="text-sm text-muted-foreground">{{ error || $t('characters.notFound') }}</p>
    <button
      class="rounded-lg border px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent"
      @click="router.push('/characters')"
    >
      {{ $t('characters.detail.backToLibrary') }}
    </button>
  </div>

  <!-- Character Detail -->
  <div v-else class="space-y-8 px-12 py-8">
    <!-- Header -->
    <div class="animate-fade-in-up flex items-center justify-between">
      <div class="flex items-center gap-4">
        <button
          class="flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          @click="router.push('/characters')"
        >
          <UIcon name="i-lucide-arrow-left" class="h-4 w-4" />
          {{ $t('common.back') }}
        </button>
        <h1 class="font-cinzel text-2xl font-bold tracking-wide text-foreground">
          {{ character.name }}
        </h1>
      </div>
      <button
        class="flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
        @click="router.push(`/characters/${characterId}/edit`)"
      >
        <UIcon name="i-lucide-pencil" class="h-4 w-4" />
        {{ $t('common.edit') }}
      </button>
    </div>

    <!-- Two-column layout -->
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <!-- Left column (2 cols) -->
      <div class="space-y-6 lg:col-span-2">
        <!-- Character Card with Avatar -->
        <div
          class="animate-fade-in-up overflow-hidden rounded-xl border bg-card/50"
          style="animation-delay: 60ms"
        >
          <!-- Avatar (full-bleed with gradient) -->
          <div class="relative h-72 overflow-hidden">
            <img
              :src="avatarSrc()"
              :alt="character.name"
              class="h-full w-full object-cover"
            />
            <div class="absolute inset-0 bg-gradient-to-t from-card/95 via-transparent to-transparent" />
            <div class="absolute bottom-0 left-0 right-0 p-6">
              <h2 class="font-cinzel text-xl font-bold text-foreground drop-shadow-lg">
                {{ character.name }}
              </h2>
              <div v-if="character.tags?.length" class="mt-2 flex flex-wrap gap-1.5">
                <span
                  v-for="tag in character.tags"
                  :key="tag"
                  class="rounded-full border border-white/10 bg-white/15 px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-white/80 backdrop-blur-sm"
                >
                  {{ tag }}
                </span>
              </div>
            </div>
          </div>

          <!-- Content -->
          <div class="space-y-5 p-6">
            <!-- Description -->
            <div v-if="character.description">
              <h3 class="mb-2 font-cinzel text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                {{ $t('characters.detail.description') }}
              </h3>
              <p class="text-sm leading-relaxed text-foreground">
                {{ character.description }}
              </p>
            </div>

            <!-- Personality -->
            <div v-if="character.personality">
              <h3 class="mb-2 font-cinzel text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                {{ $t('characters.detail.personality') }}
              </h3>
              <p class="text-sm leading-relaxed text-foreground">
                {{ character.personality }}
              </p>
            </div>

            <!-- First Message -->
            <div v-if="character.first_message">
              <h3 class="mb-2 font-cinzel text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                {{ $t('characters.detail.firstMessage') }}
              </h3>
              <div class="rounded-lg border border-border/50 bg-background/50 p-4">
                <NarrativeText :content="character.first_message" />
              </div>
            </div>

            <!-- Example Dialogues -->
            <div v-if="character.example_dialogues?.length">
              <h3 class="mb-2 font-cinzel text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                {{ $t('characters.detail.exampleDialogues') }}
              </h3>
              <div class="space-y-2">
                <div
                  v-for="(dialogue, i) in character.example_dialogues"
                  :key="i"
                  class="rounded-lg border border-border/50 bg-background/50 p-3"
                >
                  <NarrativeText :content="dialogue" />
                </div>
              </div>
            </div>

            <!-- Scenario -->
            <div v-if="character.scenario">
              <h3 class="mb-2 font-cinzel text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                {{ $t('characters.detail.scenario') }}
              </h3>
              <p class="text-sm leading-relaxed text-foreground">
                {{ character.scenario }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Right column (1 col) -->
      <div class="space-y-6">
        <!-- Metadata Card -->
        <div
          class="animate-fade-in-up rounded-xl border bg-card/50 p-4"
          style="animation-delay: 120ms"
        >
          <h3 class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            {{ $t('characters.detail.details') }}
          </h3>
          <div class="space-y-3 text-sm">
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">{{ $t('characters.detail.gender') }}</span>
              <span class="text-foreground">{{ genderLabel(character.gender, character.custom_gender) }}</span>
            </div>
            <div class="border-t border-border/30" />
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">{{ $t('characters.detail.creator') }}</span>
              <span class="text-foreground">{{ character.creator || "Unknown" }}</span>
            </div>
            <div class="border-t border-border/30" />
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">{{ $t('characters.detail.version') }}</span>
              <span class="text-foreground">v{{ character.version }}</span>
            </div>
            <div class="border-t border-border/30" />
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">{{ $t('characters.detail.created') }}</span>
              <span class="text-foreground">{{ formatDate(character.created_at) }}</span>
            </div>
            <div class="border-t border-border/30" />
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">{{ $t('characters.detail.updated') }}</span>
              <span class="text-foreground">{{ formatDate(character.updated_at) }}</span>
            </div>
          </div>
        </div>

        <!-- Start Tale Button -->
        <div
          class="animate-fade-in-up"
          style="animation-delay: 180ms"
        >
          <button
            class="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3 font-cinzel text-sm font-semibold tracking-wide text-primary-foreground transition-colors hover:bg-primary/90"
            @click="startTale"
          >
            <UIcon name="i-lucide-message-square-plus" class="h-5 w-5" />
            {{ $t('characters.detail.startTale') }}
          </button>
        </div>

        <!-- Post History Instructions -->
        <div
          v-if="character.post_history_instructions"
          class="animate-fade-in-up rounded-xl border bg-card/50 p-4"
          style="animation-delay: 240ms"
        >
          <h3 class="mb-2 font-cinzel text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            {{ $t('characters.detail.postHistory') }}
          </h3>
          <p class="text-xs leading-relaxed text-muted-foreground">
            {{ character.post_history_instructions }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

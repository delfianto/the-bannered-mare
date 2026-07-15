<script setup lang="ts">
import { fallbackAvatarUrl } from "@/utils/avatar";
import { formatDate as fmtDate } from "@/utils/date";
import { ref, onMounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { client } from "@/api/client";
import type { components } from "@/api/schema";
import NarrativeText from "@/components/chat/NarrativeText.vue";
import CollapsibleField from "@/components/discover/CollapsibleField.vue";
import ProfilePickerModal from "@/components/profiles/ProfilePickerModal.vue";
import { useCreateChat } from "@/composables/useCreateChat";

type CharacterResponse = components["schemas"]["CharacterResponse"];

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const {
  creating,
  profileChoices,
  startTale: createTale,
  chooseProfile,
  cancelProfilePick,
} = useCreateChat();

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

function portraitSrc(): string {
  if (!character.value) return "";
  // Large tier: the contained portrait card renders at a few hundred px, so the
  // <=512px large avatar is sharp while staying far lighter than the original.
  return (
    character.value.avatar_large ||
    character.value.avatar ||
    fallbackAvatarUrl(character.value.name, 600)
  );
}

function goBack() {
  // Retrace to wherever the user came from; fall back to the library on a cold
  // load (deep link / refresh) where there is no in-app history entry to pop.
  if (window.history.state?.back != null) {
    router.back();
  } else {
    router.push("/characters");
  }
}

function formatDate(dateStr: string): string {
  return fmtDate(dateStr, { year: "numeric", month: "long", day: "numeric" }, "en-US");
}

function genderLabel(
  gender: string | null | undefined,
  customGender: string | null | undefined,
): string {
  if (!gender) return t("characters.detail.notSpecified");
  if (gender === "others" && customGender) return customGender;
  return gender.charAt(0).toUpperCase() + gender.slice(1);
}

async function startTale() {
  try {
    await createTale(characterId.value);
  } catch {
    // toast already surfaced by useCreateChat
  }
}
</script>

<template>
  <!-- Loading -->
  <div v-if="loading" class="flex flex-1 items-center justify-center py-20">
    <AppIcon name="i-lucide-loader-2" class="size-8 animate-spin text-primary" />
  </div>

  <!-- Error -->
  <div
    v-else-if="error || !character"
    class="flex flex-1 flex-col items-center justify-center gap-4 py-20"
  >
    <AppIcon name="i-lucide-alert-circle" class="size-10 text-muted-foreground/40" />
    <p class="text-sm text-muted-foreground">{{ error || $t("characters.notFound") }}</p>
    <button
      class="rounded-lg border px-4 py-2 text-sm text-foreground transition-colors hover:bg-base-300"
      @click="router.push('/characters')"
    >
      {{ $t("characters.detail.backToLibrary") }}
    </button>
  </div>

  <!-- Character Detail -->
  <div v-else class="space-y-8 px-12 py-8">
    <!-- Header -->
    <div class="flex animate-fade-in-up items-center justify-between">
      <div class="flex items-center gap-4">
        <button
          class="flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
          @click="goBack"
        >
          <AppIcon name="i-lucide-arrow-left" class="size-4" />
          {{ $t("common.back") }}
        </button>
        <h1 class="font-cinzel text-2xl font-bold tracking-wide text-foreground">
          {{ character.name }}
        </h1>
      </div>
      <button
        class="flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-base-300"
        @click="router.push(`/characters/${characterId}/edit`)"
      >
        <AppIcon name="i-lucide-pencil" class="size-4" />
        {{ $t("common.edit") }}
      </button>
    </div>

    <!-- Two-column layout -->
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <!-- Left column (2 cols) -->
      <div class="space-y-6 lg:col-span-2">
        <!-- Portrait — mobile only; on desktop it moves to the top of the right
             column, beside the details. A contained thumbnail rather than a
             full-bleed hero, so no text ever sits over the image and contrast
             stops being a problem entirely. -->
        <div
          class="animate-fade-in-up overflow-hidden rounded-xl border bg-base-200/50 lg:hidden"
          style="animation-delay: 60ms"
        >
          <img
            :src="portraitSrc()"
            :alt="character.name"
            class="h-72 w-full object-cover object-top"
          />
        </div>

        <!-- Character info card -->
        <div
          class="animate-fade-in-up overflow-hidden rounded-xl border bg-base-200/50"
          style="animation-delay: 60ms"
        >
          <!-- Content -->
          <div class="space-y-5 p-6">
            <!-- Tags — kept below the portrait rather than overlaid: imported
                 cards can carry dozens of tags that overflow the hero and defeat
                 any fixed overlay text colour. On the card surface they always
                 read and wrap cleanly. -->
            <div v-if="character.tags?.length" class="flex flex-wrap gap-1.5">
              <span
                v-for="tag in character.tags"
                :key="tag"
                class="rounded-full bg-base-300 px-2.5 py-0.5 text-3xs font-medium tracking-wide text-base-content uppercase"
              >
                {{ tag }}
              </span>
            </div>

            <!-- Creator Notes / Tagline -->
            <div v-if="character.creator_notes">
              <h3
                class="mb-2 font-cinzel text-xs font-semibold tracking-widest text-muted-foreground uppercase"
              >
                Tagline / Creator Notes
              </h3>
              <p class="text-sm leading-relaxed text-foreground italic">
                {{ character.creator_notes }}
              </p>
            </div>

            <!-- Long-form fields — collapsed by default, scrollable when open.
                 Card creators often dump the entire character sheet into one of
                 these (description especially), so they need a bounded viewport. -->
            <CollapsibleField
              v-if="character.description"
              :label="$t('characters.detail.description')"
              :content="character.description"
            />

            <CollapsibleField
              v-if="character.system_prompt"
              label="System Prompt Override"
              :content="character.system_prompt"
              mono
            />

            <CollapsibleField
              v-if="character.personality"
              :label="$t('characters.detail.personality')"
              :content="character.personality"
            />

            <!-- First Message -->
            <div v-if="character.first_message">
              <h3
                class="mb-2 font-cinzel text-xs font-semibold tracking-widest text-muted-foreground uppercase"
              >
                {{ $t("characters.detail.firstMessage") }}
              </h3>
              <div class="rounded-lg border border-border/50 bg-base-100/50 p-4">
                <NarrativeText :content="character.first_message" />
              </div>
            </div>

            <!-- Example Dialogues -->
            <div v-if="character.example_dialogues?.length">
              <h3
                class="mb-2 font-cinzel text-xs font-semibold tracking-widest text-muted-foreground uppercase"
              >
                {{ $t("characters.detail.exampleDialogues") }}
              </h3>
              <div class="space-y-2">
                <div
                  v-for="(dialogue, i) in character.example_dialogues"
                  :key="i"
                  class="rounded-lg border border-border/50 bg-base-100/50 p-3"
                >
                  <NarrativeText :content="dialogue" />
                </div>
              </div>
            </div>

            <!-- Scenario -->
            <CollapsibleField
              v-if="character.scenario"
              :label="$t('characters.detail.scenario')"
              :content="character.scenario"
            />
          </div>
        </div>
      </div>

      <!-- Right column (1 col) -->
      <div class="space-y-6">
        <!-- Portrait — desktop only (on mobile it sits at the top of the page).
             Shown above the details, per the desktop layout. Capped so it renders
             at the same size as the creator's live-preview portrait (uniformity)
             and doesn't balloon on wide screens. -->
        <div
          class="animate-fade-in-up hidden max-w-90 overflow-hidden rounded-xl border bg-base-200/50 lg:block"
          style="animation-delay: 60ms"
        >
          <img
            :src="portraitSrc()"
            :alt="character.name"
            class="aspect-3/4 w-full object-cover object-top"
          />
        </div>

        <!-- Metadata Card -->
        <div
          class="animate-fade-in-up rounded-xl border bg-base-200/50 p-4"
          style="animation-delay: 120ms"
        >
          <h3
            class="mb-4 font-cinzel text-xs font-semibold tracking-widest text-muted-foreground uppercase"
          >
            {{ $t("characters.detail.details") }}
          </h3>
          <div class="space-y-3 text-sm">
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">{{ $t("characters.detail.gender") }}</span>
              <span class="text-foreground">{{
                genderLabel(character.gender, character.custom_gender)
              }}</span>
            </div>
            <div class="border-t border-border/30" />
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">{{ $t("characters.detail.creator") }}</span>
              <span class="text-foreground">{{ character.creator || "Unknown" }}</span>
            </div>
            <div class="border-t border-border/30" />
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">{{ $t("characters.detail.version") }}</span>
              <span class="text-foreground">v{{ character.version }}</span>
            </div>
            <div class="border-t border-border/30" />
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">{{ $t("characters.detail.created") }}</span>
              <span class="text-foreground">{{ formatDate(character.created_at) }}</span>
            </div>
            <div class="border-t border-border/30" />
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">{{ $t("characters.detail.updated") }}</span>
              <span class="text-foreground">{{ formatDate(character.updated_at) }}</span>
            </div>
          </div>
        </div>

        <!-- Start Tale Button -->
        <div class="animate-fade-in-up" style="animation-delay: 180ms">
          <button
            class="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3 font-cinzel text-sm font-semibold tracking-wide text-primary-content transition-colors hover:bg-primary/90 disabled:pointer-events-none disabled:opacity-60"
            :disabled="creating"
            @click="startTale"
          >
            <AppIcon
              :name="creating ? 'i-lucide-loader-2' : 'i-lucide-message-square-plus'"
              class="size-5"
              :class="{ 'animate-spin': creating }"
            />
            {{ $t("characters.detail.startTale") }}
          </button>
        </div>

        <!-- Post History Instructions -->
        <div
          v-if="character.post_history_instructions"
          class="animate-fade-in-up rounded-xl border bg-base-200/50 p-4"
          style="animation-delay: 240ms"
        >
          <h3
            class="mb-2 font-cinzel text-xs font-semibold tracking-widest text-muted-foreground uppercase"
          >
            {{ $t("characters.detail.postHistory") }}
          </h3>
          <p class="text-xs leading-relaxed text-muted-foreground">
            {{ character.post_history_instructions }}
          </p>
        </div>
      </div>
    </div>
  </div>

  <ProfilePickerModal
    v-if="profileChoices"
    :profiles="profileChoices"
    @choose="chooseProfile"
    @cancel="cancelProfilePick"
  />
</template>

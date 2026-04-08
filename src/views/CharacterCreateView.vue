<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useCharacterForm } from "@/composables/useCharacterForm";
import { useLorebooks } from "@/composables/useLorebooks";
import CharacterTab from "@/components/creator/CharacterTab.vue";
import BehaviorTab from "@/components/creator/BehaviorTab.vue";
import WorldTab from "@/components/creator/WorldTab.vue";
import CharacterPreview from "@/components/creator/CharacterPreview.vue";
import type { CreatorTab, CharacterData } from "@/types/creator";

const router = useRouter();
const route = useRoute();
const activeTab = ref<CreatorTab>("character");
const saved = ref(false);
const saveError = ref("");

const form = useCharacterForm();
const loreApi = useLorebooks();
const lorebookId = ref<string | null>(null);

const editId = computed(() => route.params.id as string | undefined);
const isEditMode = computed(() => !!editId.value);
const pageTitle = computed(() => (isEditMode.value ? "Edit Character" : "Create Character"));

const tabs: { id: CreatorTab; label: string; icon: string }[] = [
  { id: "character", label: "Character", icon: "i-lucide-user" },
  { id: "behavior", label: "Behavior", icon: "i-lucide-brain" },
  { id: "world", label: "World", icon: "i-lucide-globe" },
];

onMounted(async () => {
  if (editId.value) {
    try {
      await form.loadFromApi(editId.value);
      // Load lorebook entries for this character from the API
      await loreApi.fetchLorebooks(editId.value);
      if (loreApi.lorebooks.value.length > 0) {
        const lb = loreApi.lorebooks.value[0];
        lorebookId.value = lb.id;
        await loreApi.fetchLorebook(lb.id);
        if (loreApi.currentLorebook.value?.entries) {
          form.data.lorebook = loreApi.currentLorebook.value.entries.map((e) => ({
            id: e.id,
            keywords: e.keys || [],
            content: e.content || "",
            enabled: e.enabled,
          }));
        }
      }
    } catch (e) {
      saveError.value = "Failed to load character.";
    }
  }
});

async function handleSave() {
  saveError.value = "";
  try {
    const result = await form.saveCharacter();

    // Sync lorebook entries to API
    if (form.data.lorebook.length > 0) {
      // Ensure a lorebook exists for this character
      if (!lorebookId.value) {
        const lb = await loreApi.createLorebook({
          name: `${form.data.name} Lorebook`,
          is_global: false,
          character_id: result.id,
        });
        if (lb) lorebookId.value = lb.id;
      }

      if (lorebookId.value) {
        // Sync each entry — create new ones, update existing
        for (const entry of form.data.lorebook) {
          const isExisting = loreApi.currentLorebook.value?.entries.some((e) => e.id === entry.id);
          if (isExisting) {
            await loreApi.updateEntry(lorebookId.value, entry.id, {
              keys: entry.keywords,
              content: entry.content,
              enabled: entry.enabled,
            });
          } else {
            await loreApi.createEntry(lorebookId.value, {
              name: entry.keywords[0] || "Untitled",
              content: entry.content,
              keys: entry.keywords,
              enabled: entry.enabled,
              secondary_logic: "and_any",
              case_sensitive: false,
              match_whole_words: false,
              use_regex: false,
              constant: false,
              position: "after_character",
              depth: 4,
              role: "system",
              priority: 100,
              ignore_budget: false,
              order: 0,
            });
          }
        }
      }
    }

    saved.value = true;
    setTimeout(() => {
      router.push("/characters");
    }, 500);
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : "Failed to save character.";
  }
}

async function handleDelete() {
  if (!editId.value) return;
  saveError.value = "";
  try {
    await form.deleteCharacter(editId.value);
    router.push("/characters");
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : "Failed to delete character.";
  }
}

function handleExport() {
  const json = JSON.stringify(form.data, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${form.data.name || "character"}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function handleImport(data: CharacterData) {
  form.loadCharacter(data);
}
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <!-- Loading overlay -->
    <div
      v-if="form.loading.value"
      class="absolute inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
    >
      <div class="flex flex-col items-center gap-3">
        <UIcon name="i-lucide-loader-2" class="h-6 w-6 animate-spin text-primary" />
        <span class="text-sm text-muted-foreground">Loading character...</span>
      </div>
    </div>

    <!-- Header -->
    <header class="z-20 flex h-[60px] flex-shrink-0 items-center justify-between border-b bg-background/80 px-6 backdrop-blur-sm">
      <div class="flex items-center gap-3">
        <button
          class="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          @click="router.back()"
        >
          <UIcon name="i-lucide-arrow-left" class="h-[18px] w-[18px]" />
        </button>
        <div class="flex items-center gap-2">
          <div class="flex h-6 w-6 items-center justify-center rounded-md bg-primary">
            <UIcon name="i-lucide-flame" class="h-3.5 w-3.5 text-primary-foreground" />
          </div>
          <h1 class="font-cinzel text-base font-semibold tracking-wider text-foreground">
            {{ pageTitle }}
          </h1>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <!-- Error message -->
        <span v-if="saveError" class="text-xs text-destructive">{{ saveError }}</span>

        <!-- Delete button (edit mode only) -->
        <button
          v-if="isEditMode"
          class="flex h-9 items-center gap-2 rounded-lg border border-destructive/30 px-4 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
          :disabled="form.deleting.value"
          @click="handleDelete"
        >
          <UIcon
            :name="form.deleting.value ? 'i-lucide-loader-2' : 'i-lucide-trash-2'"
            class="h-4 w-4"
            :class="{ 'animate-spin': form.deleting.value }"
          />
          {{ form.deleting.value ? "Deleting..." : "Delete" }}
        </button>

        <button
          class="flex h-9 items-center gap-2 rounded-lg border px-4 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          @click="handleExport"
        >
          <UIcon name="i-lucide-download" class="h-4 w-4" />
          Export
        </button>
        <button
          class="flex h-9 items-center gap-2 rounded-lg px-5 text-sm font-medium transition-all active:scale-[0.96]"
          :class="
            !saved
              ? 'bg-primary text-primary-foreground shadow-sm hover:shadow-[0_2px_12px_var(--color-primary)/0.3]'
              : 'bg-muted text-muted-foreground'
          "
          :disabled="form.saving.value"
          @click="handleSave"
        >
          <UIcon
            :name="form.saving.value ? 'i-lucide-loader-2' : 'i-lucide-save'"
            class="h-4 w-4"
            :class="{ 'animate-spin': form.saving.value }"
          />
          {{ form.saving.value ? "Saving..." : saved ? "Saved" : "Save" }}
        </button>
      </div>
    </header>

    <!-- Tab Nav -->
    <div class="flex-shrink-0 border-b bg-background/60">
      <div class="flex items-center gap-1 px-8">
        <div class="mx-auto flex max-w-[580px] items-center gap-1">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="relative flex items-center gap-2 px-5 py-3 text-sm font-medium transition-colors"
          :class="activeTab === tab.id ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'"
          @click="activeTab = tab.id"
        >
          <UIcon :name="tab.icon" class="h-4 w-4" />
          <span style="letter-spacing: 0.03em">{{ tab.label }}</span>
          <span
            v-if="activeTab === tab.id"
            class="absolute bottom-0 left-2 right-2 h-[2px] rounded-full bg-primary transition-all"
          />
        </button>
        </div>
      </div>
    </div>

    <!-- Content: Form + Preview -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Form Panel -->
      <div class="flex-1 overflow-y-auto px-8 py-6" style="min-width: 0">
        <div class="mx-auto max-w-[580px]">
          <CharacterTab
            v-if="activeTab === 'character'"
            :data="form.data"
            @update:field="(field: any, val: any) => form.updateField(field, val)"
            @add:tag="form.addTag"
            @remove:tag="form.removeTag"
          />
          <BehaviorTab
            v-if="activeTab === 'behavior'"
            :data="form.data"
            @update:field="(field: any, val: any) => form.updateField(field, val)"
            @add-dialogue="form.addDialogue"
            @update-dialogue="form.updateDialogue"
            @remove-dialogue="form.removeDialogue"
          />
          <WorldTab
            v-if="activeTab === 'world'"
            :data="form.data"
            @update:field="(field: any, val: any) => form.updateField(field, val)"
            @add-lorebook="form.addLorebook"
            @update-lorebook="form.updateLorebook"
            @remove-lorebook="form.removeLorebook"
            @export="handleExport"
            @import="handleImport"
          />
        </div>
      </div>

      <!-- Preview Panel -->
      <div class="hidden w-[340px] min-w-[340px] overflow-y-auto border-l bg-secondary/30 px-5 py-6 xl:block">
        <div class="sticky top-0">
          <p class="mb-4 font-cinzel text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
            Live Preview
          </p>
          <CharacterPreview :data="form.data" :completeness="form.completeness.value" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { useCharacterForm } from "@/composables/useCharacterForm";
import { downloadJson } from "@/utils/download";
import CharacterTab from "@/components/creator/CharacterTab.vue";
import BehaviorTab from "@/components/creator/BehaviorTab.vue";
import WorldTab from "@/components/creator/WorldTab.vue";
import CharacterPreview from "@/components/creator/CharacterPreview.vue";
import type { CreatorTab, CharacterData } from "@/types/creator";

const router = useRouter();
const route = useRoute();
const { t } = useI18n();
const activeTab = ref<CreatorTab>("character");
const saved = ref(false);
const saveError = ref("");

const form = useCharacterForm();

const editId = computed(() => route.params.id as string | undefined);
const isEditMode = computed(() => !!editId.value);
const pageTitle = computed(() =>
  isEditMode.value ? t("characters.form.editCharacter") : t("characters.form.createCharacter"),
);

const tabs = computed<{ id: CreatorTab; label: string; icon: string }[]>(() => [
  { id: "character", label: t("characters.form.tabCharacter"), icon: "i-lucide-user" },
  { id: "behavior", label: t("characters.form.tabBehavior"), icon: "i-lucide-brain" },
  { id: "world", label: t("characters.form.tabWorld"), icon: "i-lucide-globe" },
]);

onMounted(async () => {
  if (editId.value) {
    try {
      // loadFromApi loads the character AND its lorebook entries into form.data.
      await form.loadFromApi(editId.value);
    } catch (e) {
      saveError.value = t("characters.failedLoad");
    }
  }
});

async function handleSave() {
  saveError.value = "";
  try {
    // saveCharacter persists the character AND fully syncs its lorebook entries
    // (create/update/delete). The view previously re-ran a second, delete-less
    // sync here that double-created entries — removed.
    await form.saveCharacter();
    saved.value = true;
    setTimeout(() => {
      router.push("/characters");
    }, 500);
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : t("characters.failedSave");
  }
}

async function handleDelete() {
  if (!editId.value) return;
  saveError.value = "";
  try {
    await form.deleteCharacter(editId.value);
    router.push("/characters");
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : t("characters.failedDelete");
  }
}

function handleExport() {
  downloadJson(`${form.data.name || "character"}.json`, form.data);
}

function handleImport(data: CharacterData) {
  form.loadCharacter(data);
}

function handleAvatarChange(file: File) {
  form.updateField("avatarFile", file);
  form.updateField("avatarUrl", URL.createObjectURL(file));
}
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <!-- Loading overlay -->
    <div
      v-if="form.loading.value"
      class="absolute inset-0 z-50 flex items-center justify-center bg-base-100/80 backdrop-blur-sm"
    >
      <div class="flex flex-col items-center gap-3">
        <AppIcon name="i-lucide-loader-2" class="size-6 animate-spin text-primary" />
        <span class="text-sm text-muted-foreground">{{ $t("common.loading") }}</span>
      </div>
    </div>

    <!-- Header -->
    <header
      class="z-20 flex h-15 shrink-0 items-center justify-between border-b bg-base-100/80 px-6 backdrop-blur-sm"
    >
      <div class="flex items-center gap-3">
        <button
          class="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
          @click="router.back()"
        >
          <AppIcon name="i-lucide-arrow-left" class="size-5" />
        </button>
        <div class="flex items-center gap-2">
          <div class="flex size-6 items-center justify-center rounded-md bg-primary">
            <AppIcon name="i-lucide-flame" class="size-3.5 text-primary-content" />
          </div>
          <h1 class="font-cinzel text-base font-semibold tracking-wider text-foreground">
            {{ pageTitle }}
          </h1>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <!-- Error message -->
        <span v-if="saveError" class="text-xs text-error">{{ saveError }}</span>

        <!-- Delete button (edit mode only) -->
        <button
          v-if="isEditMode"
          class="flex h-9 items-center gap-2 rounded-lg border border-error/30 px-4 text-sm font-medium text-error transition-colors hover:bg-error/10"
          :disabled="form.deleting.value"
          @click="handleDelete"
        >
          <AppIcon
            :name="form.deleting.value ? 'i-lucide-loader-2' : 'i-lucide-trash-2'"
            class="size-4"
            :class="{ 'animate-spin': form.deleting.value }"
          />
          {{ form.deleting.value ? $t("common.deleting") : $t("common.delete") }}
        </button>

        <button
          class="flex h-9 items-center gap-2 rounded-lg border px-4 text-sm font-medium text-foreground transition-colors hover:bg-base-300"
          @click="handleExport"
        >
          <AppIcon name="i-lucide-download" class="size-4" />
          {{ $t("common.export") }}
        </button>
        <button
          class="flex h-9 items-center gap-2 rounded-lg px-5 text-sm font-medium transition-all active:scale-0.96"
          :class="
            !saved
              ? 'bg-primary text-primary-content shadow-sm hover:shadow-[0_2px_12px_var(--color-primary)/0.3]'
              : 'bg-base-300 text-muted-foreground'
          "
          :disabled="form.saving.value"
          @click="handleSave"
        >
          <AppIcon
            :name="form.saving.value ? 'i-lucide-loader-2' : 'i-lucide-save'"
            class="size-4"
            :class="{ 'animate-spin': form.saving.value }"
          />
          {{
            form.saving.value ? $t("common.saving") : saved ? $t("common.saved") : $t("common.save")
          }}
        </button>
      </div>
    </header>

    <!-- Tab Nav -->
    <div class="shrink-0 border-b bg-base-100/60">
      <div class="flex items-center gap-1 px-8">
        <div class="mx-auto flex max-w-145 items-center gap-1">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            class="relative flex items-center gap-2 px-5 py-3 text-sm font-medium transition-colors"
            :class="
              activeTab === tab.id
                ? 'text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            "
            @click="activeTab = tab.id"
          >
            <AppIcon :name="tab.icon" class="size-4" />
            <span style="letter-spacing: 0.03em">{{ tab.label }}</span>
            <span
              v-if="activeTab === tab.id"
              class="absolute inset-x-2 bottom-0 h-0.5 rounded-full bg-primary transition-all"
            />
          </button>
        </div>
      </div>
    </div>

    <!-- Content: Form + Preview -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Form Panel -->
      <div class="flex-1 overflow-y-auto px-8 py-6" style="min-width: 0">
        <div class="mx-auto max-w-145">
          <CharacterTab
            v-if="activeTab === 'character'"
            :data="form.data"
            @update:field="(field, val) => form.updateField(field, val)"
            @add:tag="form.addTag"
            @remove:tag="form.removeTag"
            @change="handleAvatarChange"
          />
          <BehaviorTab
            v-if="activeTab === 'behavior'"
            :data="form.data"
            @update:field="(field, val) => form.updateField(field, val)"
            @add-dialogue="form.addDialogue"
            @update-dialogue="form.updateDialogue"
            @remove-dialogue="form.removeDialogue"
          />
          <WorldTab
            v-if="activeTab === 'world'"
            :data="form.data"
            @update:field="(field, val) => form.updateField(field, val)"
            @add-lorebook="form.addLorebook"
            @update-lorebook="form.updateLorebook"
            @remove-lorebook="form.removeLorebook"
            @export="handleExport"
            @import="handleImport"
          />
        </div>
      </div>

      <!-- Preview Panel -->
      <div
        class="hidden w-100 min-w-100 overflow-y-auto border-l bg-base-200/30 px-5 py-6 xl:block"
      >
        <div class="sticky top-0">
          <p
            class="mb-4 font-cinzel text-3xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
          >
            {{ $t("characters.form.livePreview") }}
          </p>
          <CharacterPreview
            :data="form.data"
            :completeness="form.completeness.value"
            @change="handleAvatarChange"
          />
        </div>
      </div>
    </div>
  </div>
</template>

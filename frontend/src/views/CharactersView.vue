<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useCharacters } from "@/composables/useCharacters";
import { useCreateChat } from "@/composables/useCreateChat";
import { useLibraryFilters } from "@/composables/useLibraryFilters";
import { useAppToast } from "@/composables/useToast";
import { CATEGORIES } from "@/constants/discoverData";
import DiscoverHeader from "@/components/discover/DiscoverHeader.vue";
import FilterBar from "@/components/discover/FilterBar.vue";
import CategoryPills from "@/components/discover/CategoryPills.vue";
import BulkActionBar from "@/components/discover/BulkActionBar.vue";
import CharacterCard from "@/components/discover/CharacterCard.vue";
import CharacterListRow from "@/components/discover/CharacterListRow.vue";
import EmptyState from "@/components/shared/EmptyState.vue";

import ConfirmModal from "@/components/shared/ConfirmModal.vue";
import ProfilePickerModal from "@/components/profiles/ProfilePickerModal.vue";
import PageContainer from "@/components/layout/PageContainer.vue";

const router = useRouter();
const { t } = useI18n();
const { success, error: toastError } = useAppToast();
const { startTale, profileChoices, chooseProfile, cancelProfilePick } = useCreateChat();

// Deletion confirmation state
const showDeleteConfirm = ref(false);
const characterToDelete = ref<string | null>(null);
const bulkDeleteMode = ref(false);
const deleteLoading = ref(false);

// Fetch characters from API
const { characters, loading, refresh } = useCharacters({ pageSize: 50 });

// Filter the API data locally
const { filters, filtered, setSearch, setCategory, setSort, setViewMode } =
  useLibraryFilters(characters);

const selectMode = ref(false);
const selected = ref(new Set<string>());

const hasFilters = computed(() => filters.search !== "" || filters.category !== "All");

function toggleSelect(id: string) {
  const next = new Set(selected.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  selected.value = next;
}

function cancelSelect() {
  selectMode.value = false;
  selected.value = new Set();
}

function handleBulkExport() {
  console.log("Exporting:", [...selected.value]);
}

function handleBulkDelete() {
  if (selected.value.size === 0) return;
  bulkDeleteMode.value = true;
  showDeleteConfirm.value = true;
}

async function handleContextAction(action: string, id: string) {
  if (action === "edit") {
    router.push(`/characters/${id}/edit`);
  } else if (action === "delete") {
    characterToDelete.value = id;
    bulkDeleteMode.value = false;
    showDeleteConfirm.value = true;
  } else if (action === "start-tale") {
    try {
      await startTale(id);
    } catch {
      // toast already surfaced by useCreateChat
    }
  } else {
    console.log("Context action:", action, id);
  }
}

async function executeDelete() {
  deleteLoading.value = true;
  try {
    if (bulkDeleteMode.value) {
      const count = selected.value.size;
      const deletePromises = [...selected.value].map((id) =>
        fetch(`/api/characters/${id}`, { method: "DELETE" }),
      );
      const responses = await Promise.all(deletePromises);
      const failedCount = responses.filter((r) => !r.ok && r.status !== 204).length;
      if (failedCount > 0) {
        throw new Error(`${failedCount} deletions failed`);
      }
      success(t("characters.deleted"), `${count} character(s) deleted.`);
      cancelSelect();
    } else if (characterToDelete.value) {
      const id = characterToDelete.value;
      const response = await fetch(`/api/characters/${id}`, { method: "DELETE" });
      if (!response.ok && response.status !== 204) {
        throw new Error(`Failed to delete character: ${response.status}`);
      }
      success(t("characters.deleted"), t("characters.deleteSuccess"));
    }
    refresh();
  } catch {
    toastError(t("characters.deleteFailed"), t("characters.deleteError"));
  } finally {
    deleteLoading.value = false;
    showDeleteConfirm.value = false;
    characterToDelete.value = null;
    bulkDeleteMode.value = false;
  }
}

function navigateToCreate() {
  router.push("/characters/create");
}

// ── Import flow ─────────────────────────────────────────
const fileInputRef = ref<HTMLInputElement | null>(null);
const importing = ref(false);

function openImportDialog() {
  fileInputRef.value?.click();
}

async function onFileSelected(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  importing.value = true;

  try {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("/api/characters/import", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Import failed: ${response.status}`);
    }

    success(t("characters.imported"), t("characters.importSuccess", { name: file.name }));
    refresh();
  } catch {
    toastError(t("characters.importFailed"), t("characters.importError"));
  } finally {
    importing.value = false;
    // Reset file input so same file can be re-selected
    if (target) target.value = "";
  }
}
</script>

<template>
  <PageContainer>
    <template #header>
      <DiscoverHeader
        :character-count="filtered.length"
        :show-actions="characters.length > 0"
        @import="openImportDialog"
        @create-new="navigateToCreate"
      />
    </template>

    <!-- Hidden file input for import -->
    <input
      ref="fileInputRef"
      type="file"
      accept=".json,.png"
      class="hidden"
      @change="onFileSelected"
    />

    <div class="flex flex-1 flex-col space-y-6">
      <!-- Filters -->
      <div v-if="characters.length > 0" class="animate-fade-in-up" style="animation-delay: 60ms">
        <FilterBar
          :search="filters.search"
          :sort="filters.sort"
          :view-mode="filters.viewMode"
          :select-mode="selectMode"
          @update:search="setSearch"
          @update:sort="setSort"
          @update:view-mode="setViewMode"
          @update:select-mode="(v: boolean) => (v ? (selectMode = true) : cancelSelect())"
        />
      </div>

      <!-- Category pills -->
      <div v-if="characters.length > 0" class="animate-fade-in-up" style="animation-delay: 120ms">
        <CategoryPills :active="filters.category" :categories="CATEGORIES" @change="setCategory" />
      </div>

      <!-- Bulk action bar -->
      <BulkActionBar
        :selected-count="selected.size"
        :visible="selectMode"
        @export="handleBulkExport"
        @delete="handleBulkDelete"
        @cancel="cancelSelect"
      />

      <!-- Import loading overlay -->
      <div
        v-if="importing"
        class="flex items-center justify-center gap-3 rounded-xl border border-primary/30 bg-primary/5 px-6 py-4"
      >
        <AppIcon name="i-lucide-loader-2" class="size-5 animate-spin text-primary" />
        <span class="text-sm text-foreground">{{ $t("characters.importing") }}</span>
      </div>

      <!-- Loading -->
      <div v-if="loading && characters.length === 0" class="flex justify-center py-16">
        <AppIcon name="i-lucide-loader-circle" class="size-6 animate-spin text-muted-foreground" />
      </div>

      <!-- Grid view -->
      <div
        v-else-if="filtered.length > 0 && filters.viewMode === 'grid'"
        class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4"
      >
        <CharacterCard
          v-for="(character, i) in filtered"
          :key="character.id"
          :character="character"
          :index="i"
          :select-mode="selectMode"
          :selected="selected.has(character.id)"
          @select="toggleSelect"
          @context-action="handleContextAction"
        />
      </div>

      <!-- List view -->
      <div
        v-else-if="filtered.length > 0 && filters.viewMode === 'list'"
        class="grid grid-cols-1 gap-3 lg:grid-cols-2"
      >
        <CharacterListRow
          v-for="(character, i) in filtered"
          :key="character.id"
          :character="character"
          :index="i"
          :select-mode="selectMode"
          :selected="selected.has(character.id)"
          @select="toggleSelect"
          @context-action="handleContextAction"
        />
      </div>

      <!-- Empty state -->
      <EmptyState
        v-if="!loading && filtered.length === 0"
        :has-filters="hasFilters"
        @action="navigateToCreate"
      >
        <template v-if="!hasFilters" #action>
          <div class="flex items-center gap-3">
            <button
              class="flex items-center gap-1.5 rounded-lg border px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-base-300/60"
              @click="openImportDialog"
            >
              <AppIcon name="i-lucide-download" class="size-4" />
              {{ $t("characters.importBtn") }}
            </button>
            <button
              class="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-content transition-colors hover:bg-primary/90"
              @click="navigateToCreate"
            >
              <AppIcon name="i-lucide-plus" class="size-4" />
              {{ $t("characters.createNew") }}
            </button>
          </div>
        </template>
      </EmptyState>
    </div>

    <!-- Delete Confirmation Modal -->
    <ConfirmModal
      :show="showDeleteConfirm"
      :title="bulkDeleteMode ? 'Delete Selected Characters' : 'Delete Character'"
      :message="
        bulkDeleteMode
          ? `Are you sure you want to delete the ${selected.size} selected characters? This action cannot be undone.`
          : 'Are you sure you want to delete this character? This action cannot be undone.'
      "
      :confirm-text="t('common.delete') || 'Delete'"
      :cancel-text="t('common.cancel') || 'Cancel'"
      :loading="deleteLoading"
      destructive
      @confirm="executeDelete"
      @close="showDeleteConfirm = false"
    />

    <ProfilePickerModal
      v-if="profileChoices"
      :profiles="profileChoices"
      @choose="chooseProfile"
      @cancel="cancelProfilePick"
    />
  </PageContainer>
</template>

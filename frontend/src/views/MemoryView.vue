<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useDataBank } from "@/composables/useDataBank";
import { useKeyedConfirmAction } from "@/composables/useConfirmAction";
import { client } from "@/api/client";
import type { DataBankCreate, DataBankUpdate, DataBankEntry } from "@/composables/useDataBank";
import type { components } from "@/api/schema";
import EmptyState from "@/components/shared/EmptyState.vue";
import PageContainer from "@/components/layout/PageContainer.vue";

const { t } = useI18n();

type RetrievedChunk = components["schemas"]["RetrievedChunk"];

const { entries, loading, error, fetchEntries, createEntry, updateEntry, deleteEntry, refresh } =
  useDataBank();

// ── RAG Search ──────────────────────────────────────────
const searchQuery = ref("");
const searchLoading = ref(false);
const searchResults = ref<RetrievedChunk[]>([]);
const hasSearched = ref(false);
const ragIndexedCount = ref<number | null>(null);

onMounted(async () => {
  try {
    const { data } = await client.GET("/api/rag/status");
    if (data && typeof data === "object" && "indexed_count" in data) {
      ragIndexedCount.value = (data as { indexed_count: number }).indexed_count;
    }
  } catch {
    // RAG status is non-critical
  }
});

async function onSearch() {
  if (!searchQuery.value.trim()) return;
  searchLoading.value = true;
  hasSearched.value = true;

  try {
    const { data } = await client.POST("/api/rag/search", {
      body: {
        query: searchQuery.value,
        max_results: 5,
        threshold: 0.3,
      },
    });
    searchResults.value = data ?? [];
  } catch {
    searchResults.value = [];
  } finally {
    searchLoading.value = false;
  }
}

function scoreColor(score: number): string {
  if (score >= 0.85) return "bg-emerald-500/15 text-emerald-400";
  if (score >= 0.7) return "bg-blue-500/15 text-blue-400";
  if (score >= 0.5) return "bg-amber-500/15 text-amber-400";
  return "bg-zinc-500/15 text-zinc-400";
}

function sourceTypeBadge(type: string): string {
  switch (type) {
    case "data_bank":
      return "bg-blue-500/15 text-blue-400";
    case "lorebook":
      return "bg-purple-500/15 text-purple-400";
    case "character":
      return "bg-amber-500/15 text-amber-400";
    default:
      return "bg-base-300 text-foreground";
  }
}

// ── Data Bank ───────────────────────────────────────────
const scopeFilter = ref<string>("all");
const scopes = computed(() => [
  { id: "all", label: t("memory.scopes.all") },
  { id: "global", label: t("memory.scopes.global") },
  { id: "character", label: t("memory.scopes.character") },
  { id: "chat", label: t("memory.scopes.chat") },
]);

const filteredEntries = computed(() => {
  if (scopeFilter.value === "all") return entries.value;
  return entries.value.filter((e) => e.scope === scopeFilter.value);
});

function onScopeChange(scope: string) {
  scopeFilter.value = scope;
  if (scope === "all") {
    fetchEntries();
  } else {
    fetchEntries(scope);
  }
}

// ── Inline form state ────────────────────────────────────
const showForm = ref(false);
const editingId = ref<string | null>(null);
const formName = ref("");
const formScope = ref("global");
const formContent = ref("");

function openCreateForm() {
  editingId.value = null;
  formName.value = "";
  formScope.value = "global";
  formContent.value = "";
  showForm.value = true;
}

function openEditForm(entry: DataBankEntry) {
  editingId.value = entry.id;
  formName.value = entry.name;
  formScope.value = entry.scope;
  formContent.value = entry.content;
  showForm.value = true;
}

function cancelForm() {
  showForm.value = false;
  editingId.value = null;
}

async function saveForm() {
  if (!formName.value.trim() || !formContent.value.trim()) return;

  if (editingId.value) {
    const payload: DataBankUpdate = {
      name: formName.value,
      content: formContent.value,
      scope: formScope.value,
    };
    await updateEntry(editingId.value, payload);
  } else {
    const payload: DataBankCreate = {
      name: formName.value,
      content: formContent.value,
      scope: formScope.value,
    };
    await createEntry(payload);
  }

  showForm.value = false;
  editingId.value = null;
}

// ── Delete with two-click confirm (auto-disarms) ─────────
const { isArmed: isDeleteArmed, trigger: onDeleteClick, reset: cancelDelete } =
  useKeyedConfirmAction();

function clearFilters() {
  searchQuery.value = "";
  searchResults.value = [];
  hasSearched.value = false;
  onScopeChange("all");
}

function scopeBadgeClass(scope: string): string {
  switch (scope) {
    case "global":
      return "bg-blue-500/15 text-blue-400";
    case "character":
      return "bg-purple-500/15 text-purple-400";
    case "chat":
      return "bg-amber-500/15 text-amber-400";
    default:
      return "bg-base-300 text-foreground";
  }
}
</script>

<template>
  <PageContainer>
    <template #header>
      <div class="flex items-start justify-between">
        <div>
          <div class="flex items-center gap-3">
            <h1 class="mb-1 font-cinzel text-2xl font-bold tracking-wide text-foreground">
              {{ $t("memory.title") }}
            </h1>
            <span
              v-if="ragIndexedCount !== null"
              class="rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-[0.625rem] font-medium text-emerald-400"
            >
              {{ $t("memory.indexed", { count: ragIndexedCount }) }}
            </span>
          </div>
          <p class="text-sm text-muted-foreground">
            {{ $t("memory.subtitle") }}
          </p>
        </div>
        <button
          v-if="entries.length > 0"
          class="flex items-center gap-2 rounded-lg border bg-base-200 px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-base-300"
          @click="openCreateForm"
        >
          <AppIcon name="i-lucide-plus" class="size-4" />
          {{ $t("memory.addEntry") }}
        </button>
      </div>
    </template>

    <div class="flex w-full flex-1 flex-col space-y-8">
      <!-- Inline Create/Edit Form -->
      <div v-if="showForm" class="animate-fade-in-up rounded-xl border bg-base-200/50 p-6">
        <h2 class="mb-4 font-cinzel text-sm font-semibold tracking-wide text-foreground">
          {{ editingId ? $t("memory.form.editEntry") : $t("memory.form.newEntry") }}
        </h2>
        <div class="space-y-4">
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">{{
              $t("memory.form.name")
            }}</span>
            <input
              v-model="formName"
              type="text"
              :placeholder="$t('memory.form.namePlaceholder')"
              class="w-full rounded-lg border bg-base-100 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
            />
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">{{
              $t("memory.form.scope")
            }}</span>
            <select
              v-model="formScope"
              class="w-full rounded-lg border bg-base-100 px-3 py-2 text-sm text-foreground focus:ring-1 focus:ring-primary focus:outline-none"
            >
              <option value="global">{{ $t("memory.scopes.global") }}</option>
              <option value="character">{{ $t("memory.scopes.character") }}</option>
              <option value="chat">{{ $t("memory.scopes.chat") }}</option>
            </select>
          </label>
          <label class="block">
            <span class="mb-1 block text-xs font-medium text-muted-foreground">{{
              $t("memory.form.content")
            }}</span>
            <textarea
              v-model="formContent"
              rows="4"
              :placeholder="$t('memory.form.contentPlaceholder')"
              class="w-full resize-y rounded-lg border bg-base-100 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary focus:outline-none"
            />
          </label>
          <div class="flex items-center gap-3">
            <button
              class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-content transition-colors hover:bg-primary/90"
              @click="saveForm"
            >
              {{ editingId ? $t("memory.form.saveChanges") : $t("memory.form.createEntry") }}
            </button>
            <button
              class="rounded-lg border px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
              @click="cancelForm"
            >
              {{ $t("common.cancel") }}
            </button>
          </div>
        </div>
      </div>

      <template v-else>
        <!-- Loading -->
        <div
          v-if="loading && entries.length === 0"
          class="flex flex-1 items-center justify-center py-20"
        >
          <AppIcon name="i-lucide-loader-2" class="size-6 animate-spin text-primary" />
        </div>

        <!-- Error -->
        <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-20">
          <AppIcon name="i-lucide-alert-circle" class="size-8 text-error" />
          <p class="text-sm text-muted-foreground">{{ error.message }}</p>
          <button
            class="rounded-lg border px-4 py-2 text-sm text-foreground transition-colors hover:bg-base-300"
            @click="refresh()"
          >
            {{ $t("common.retry") }}
          </button>
        </div>

        <!-- Total Empty State -->
        <EmptyState
          v-else-if="entries.length === 0"
          icon="i-lucide-database"
          :title="$t('memory.noEntries')"
          description="No custom memory entries added to the Data Bank yet."
          action-label="Add Memory Entry"
          @action="openCreateForm"
        />

        <template v-else>
          <!-- RAG Search Section -->
          <div
            class="animate-fade-in-up rounded-xl border bg-base-200/50 p-5"
            style="animation-delay: 30ms"
          >
            <h2
              class="mb-3 font-cinzel text-sm font-semibold tracking-widest text-muted-foreground uppercase"
            >
              {{ $t("memory.semanticSearch") }}
            </h2>
            <div class="flex items-center gap-3">
              <div class="relative flex-1">
                <AppIcon
                  name="i-lucide-search"
                  class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground/50"
                />
                <input
                  v-model="searchQuery"
                  type="text"
                  :placeholder="$t('memory.searchPlaceholder')"
                  aria-label="Semantic search"
                  autocomplete="off"
                  class="w-full rounded-lg border bg-base-100 py-2 pr-3 pl-10 text-sm text-foreground transition-shadow placeholder:text-muted-foreground/50 focus:shadow-[0_0_12px_var(--color-primary)/0.15] focus:ring-1 focus:ring-primary focus:outline-none"
                  @keydown.enter="onSearch"
                />
              </div>
              <button
                class="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-content transition-colors hover:bg-primary/90 disabled:opacity-50"
                :disabled="searchLoading || !searchQuery.trim()"
                @click="onSearch"
              >
                <AppIcon
                  v-if="searchLoading"
                  name="i-lucide-loader-2"
                  class="size-4 animate-spin"
                />
                <AppIcon v-else name="i-lucide-search" class="size-4" />
                {{ $t("common.search") }}
              </button>
            </div>

            <!-- Search Results -->
            <div v-if="searchLoading" class="mt-4 flex items-center justify-center py-6">
              <AppIcon name="i-lucide-loader-2" class="size-5 animate-spin text-primary" />
            </div>

            <div
              v-else-if="hasSearched && searchResults.length === 0"
              class="mt-4 py-6 text-center"
            >
              <AppIcon
                name="i-lucide-search-x"
                class="mx-auto mb-2 size-6 text-muted-foreground/40"
              />
              <p class="text-sm text-muted-foreground">
                {{ $t("memory.searchNoResults", { query: searchQuery }) }}
              </p>
            </div>

            <div v-else-if="searchResults.length > 0" class="mt-4 space-y-3">
              <div
                v-for="(result, i) in searchResults"
                :key="i"
                class="rounded-lg border border-border/50 bg-base-100/50 p-4 transition-colors hover:bg-base-100/80"
              >
                <div class="mb-2 flex items-center gap-2">
                  <span
                    class="rounded-full px-2 py-0.5 text-[0.5625rem] font-medium tracking-wide uppercase"
                    :class="sourceTypeBadge(result.source_type)"
                  >
                    {{ result.source_type.replace("_", " ") }}
                  </span>
                  <span
                    class="rounded-full px-2 py-0.5 text-[0.5625rem] font-medium tracking-wide"
                    :class="scoreColor(result.score)"
                  >
                    {{ $t("memory.matchPercent", { score: (result.score * 100).toFixed(0) }) }}
                  </span>
                </div>
                <p class="line-clamp-3 text-xs leading-relaxed text-muted-foreground">
                  {{ result.content }}
                </p>
              </div>
            </div>
          </div>

          <!-- Scope Filter Pills -->
          <div class="flex animate-fade-in-up items-center gap-2" style="animation-delay: 60ms">
            <button
              v-for="scope in scopes"
              :key="scope.id"
              class="rounded-full px-4 py-1.5 text-xs font-medium tracking-wide transition-colors"
              :class="
                scopeFilter === scope.id
                  ? 'bg-primary text-primary-content'
                  : 'bg-base-300/60 text-muted-foreground hover:bg-base-300 hover:text-foreground'
              "
              @click="onScopeChange(scope.id)"
            >
              {{ scope.label }}
            </button>
          </div>

          <!-- Filtered Empty State -->
          <EmptyState
            v-if="filteredEntries.length === 0"
            icon="i-lucide-search-x"
            title="No Matching Entries"
            description="Try adjusting your search query or scope filter."
            action-label="Clear Filters"
            @action="clearFilters"
          />

          <!-- Entry Cards Grid -->
          <div v-else class="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <div
              v-for="(entry, index) in filteredEntries"
              :key="entry.id"
              class="group relative flex animate-fade-in-up flex-col rounded-xl border bg-base-200/50 p-4 pb-8 transition-all hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
              :style="{ animationDelay: `${index * 30}ms` }"
            >
              <!-- Header -->
              <div class="mb-2 flex items-start justify-between gap-2">
                <h3 class="font-cinzel text-sm font-semibold tracking-wide text-foreground">
                  {{ entry.name }}
                </h3>
                <span
                  class="shrink-0 rounded-full px-2 py-0.5 text-[0.5625rem] font-medium tracking-wide uppercase"
                  :class="scopeBadgeClass(entry.scope)"
                >
                  {{ entry.scope }}
                </span>
              </div>

              <!-- Content preview (3-line clamp) -->
              <p class="mb-3 line-clamp-3 text-xs leading-relaxed text-muted-foreground">
                {{ entry.content }}
              </p>

              <!-- Spacer -->
              <div class="flex-1" />

              <!-- Bottom details -->
              <div
                class="space-y-1.5 border-t border-border/30 pt-3 text-[0.6875rem] text-muted-foreground"
              >
                <div class="flex items-center gap-1.5">
                  <AppIcon name="i-lucide-clock" class="size-3 shrink-0" />
                  <span>{{ new Date(entry.updated_at).toLocaleDateString() }}</span>
                </div>
              </div>

              <!-- Action buttons (bottom-right) -->
              <div
                class="absolute right-3 bottom-3 flex items-center gap-2 text-[0.625rem] text-muted-foreground/0 transition-colors group-hover:text-muted-foreground/60"
              >
                <button
                  class="flex items-center gap-1 hover:text-foreground"
                  @click.stop="openEditForm(entry)"
                >
                  <AppIcon name="i-lucide-pencil" class="size-3" />
                  {{ $t("common.edit") }}
                </button>
                <button
                  class="flex items-center gap-1"
                  :class="isDeleteArmed(entry.id) ? 'text-error!' : 'hover:text-error'"
                  @click.stop="onDeleteClick(entry.id, () => deleteEntry(entry.id))"
                  @mouseleave="cancelDelete"
                >
                  <AppIcon name="i-lucide-trash-2" class="size-3" />
                  {{ isDeleteArmed(entry.id) ? $t("memory.confirmDelete") : $t("common.delete") }}
                </button>
              </div>
            </div>
          </div>
        </template>
      </template>
    </div>
  </PageContainer>
</template>

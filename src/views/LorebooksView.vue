<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useLorebooks } from "@/composables/useLorebooks";
import type {
  LorebookResponse,
  LorebookCreate,
  LoreEntryResponse,
  LoreEntryCreate,
} from "@/composables/useLorebooks";
import { useAppToast } from "@/composables/useToast";
import LoreEntryCard from "@/components/lorebooks/LoreEntryCard.vue";
import LoreEntryForm from "@/components/lorebooks/LoreEntryForm.vue";

const { t } = useI18n();
const toast = useAppToast();
const {
  lorebooks,
  currentLorebook,
  loading,
  fetchLorebooks,
  fetchLorebook,
  createLorebook,
  updateLorebook,
  deleteLorebook,
  createEntry,
  updateEntry,
  deleteEntry,
} = useLorebooks();

const selectedId = ref<string | null>(null);
const entries = computed(() => currentLorebook.value?.entries ?? []);

// ── Lorebook form state (inline) ─────────────────────────
const showLorebookForm = ref(false);
const editingLorebook = ref<LorebookResponse | null>(null);
const lbName = ref("");
const lbDescription = ref("");
const lbIsGlobal = ref(true);
const savingLorebook = ref(false);
const pendingDeleteLb = ref<string | null>(null);

// ── Entry form state ─────────────────────────────────────
const showEntryForm = ref(false);
const editingEntry = ref<LoreEntryResponse | null>(null);
const savingEntry = ref(false);
const pendingDeleteEntry = ref<string | null>(null);

function resetForms() {
  showLorebookForm.value = false;
  showEntryForm.value = false;
  editingLorebook.value = null;
  editingEntry.value = null;
  pendingDeleteLb.value = null;
  pendingDeleteEntry.value = null;
}

async function selectLorebook(id: string) {
  selectedId.value = id;
  resetForms();
  await fetchLorebook(id);
}

onMounted(async () => {
  await fetchLorebooks();
  if (lorebooks.value.length > 0) await selectLorebook(lorebooks.value[0].id);
});

// ── Lorebook CRUD ────────────────────────────────────────
function openNewLorebook() {
  editingLorebook.value = null;
  lbName.value = "";
  lbDescription.value = "";
  lbIsGlobal.value = true;
  showEntryForm.value = false;
  showLorebookForm.value = true;
}

function openEditLorebook() {
  if (!currentLorebook.value) return;
  editingLorebook.value = currentLorebook.value;
  lbName.value = currentLorebook.value.name;
  lbDescription.value = currentLorebook.value.description ?? "";
  lbIsGlobal.value = currentLorebook.value.is_global;
  showEntryForm.value = false;
  showLorebookForm.value = true;
}

async function submitLorebook() {
  if (!lbName.value.trim()) return;
  savingLorebook.value = true;
  try {
    const payload: LorebookCreate = {
      name: lbName.value.trim(),
      description: lbDescription.value.trim() || null,
      is_global: lbIsGlobal.value,
    };
    if (editingLorebook.value) {
      const res = await updateLorebook(editingLorebook.value.id, payload);
      if (res) {
        toast.success(t("lorebooks.toast.updated"));
        await fetchLorebook(editingLorebook.value.id);
      }
    } else {
      const res = await createLorebook(payload);
      if (res) {
        toast.success(t("lorebooks.toast.created"));
        await selectLorebook(res.id);
      }
    }
    showLorebookForm.value = false;
    editingLorebook.value = null;
  } finally {
    savingLorebook.value = false;
  }
}

async function onDeleteLorebook() {
  if (!currentLorebook.value) return;
  if (pendingDeleteLb.value === currentLorebook.value.id) {
    const ok = await deleteLorebook(currentLorebook.value.id);
    if (ok) {
      toast.success(t("lorebooks.toast.deleted"));
      currentLorebook.value = null;
      selectedId.value = null;
      pendingDeleteLb.value = null;
      if (lorebooks.value.length > 0) await selectLorebook(lorebooks.value[0].id);
    }
  } else {
    pendingDeleteLb.value = currentLorebook.value.id;
  }
}

// ── Entry CRUD ───────────────────────────────────────────
function openNewEntry() {
  editingEntry.value = null;
  showLorebookForm.value = false;
  showEntryForm.value = true;
}

function openEditEntry(entry: LoreEntryResponse) {
  editingEntry.value = entry;
  showLorebookForm.value = false;
  showEntryForm.value = true;
}

async function submitEntry(payload: LoreEntryCreate) {
  if (!currentLorebook.value) return;
  savingEntry.value = true;
  try {
    const lbId = currentLorebook.value.id;
    if (editingEntry.value) {
      const res = await updateEntry(lbId, editingEntry.value.id, payload);
      if (res) toast.success(t("lorebooks.toast.entrySaved"));
    } else {
      const res = await createEntry(lbId, payload);
      if (res) toast.success(t("lorebooks.toast.entryAdded"));
    }
    showEntryForm.value = false;
    editingEntry.value = null;
  } finally {
    savingEntry.value = false;
  }
}

async function onDeleteEntry(entry: LoreEntryResponse) {
  if (!currentLorebook.value) return;
  if (pendingDeleteEntry.value === entry.id) {
    const ok = await deleteEntry(currentLorebook.value.id, entry.id);
    if (ok) toast.success(t("lorebooks.toast.entryDeleted"));
    pendingDeleteEntry.value = null;
  } else {
    pendingDeleteEntry.value = entry.id;
  }
}

async function toggleEntry(entry: LoreEntryResponse) {
  if (!currentLorebook.value) return;
  await updateEntry(currentLorebook.value.id, entry.id, { enabled: !entry.enabled });
}
</script>

<template>
  <div class="flex h-full overflow-hidden">
    <!-- Left: lorebook list -->
    <div class="flex w-[300px] shrink-0 flex-col border-r">
      <div class="flex items-center justify-between px-5 pb-3 pt-6">
        <h1 class="font-cinzel text-lg font-bold tracking-wide text-foreground">
          {{ $t('lorebooks.title') }}
        </h1>
        <button
          class="flex h-8 w-8 items-center justify-center rounded-lg border bg-card text-foreground transition-colors hover:bg-accent"
          :title="$t('lorebooks.newLorebook')"
          @click="openNewLorebook"
        >
          <UIcon name="i-lucide-plus" class="h-4 w-4" />
        </button>
      </div>
      <div class="flex-1 space-y-1.5 overflow-y-auto px-3 pb-4">
        <button
          v-for="lb in lorebooks"
          :key="lb.id"
          class="w-full rounded-lg border px-3 py-2.5 text-left transition-colors"
          :class="selectedId === lb.id ? 'border-primary/40 bg-accent' : 'hover:bg-accent/50'"
          @click="selectLorebook(lb.id)"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="truncate font-cinzel text-sm font-medium text-foreground">{{ lb.name }}</span>
            <span
              v-if="lb.is_global"
              class="shrink-0 rounded-full bg-primary/15 px-1.5 py-0.5 text-[8px] font-medium uppercase tracking-wide text-primary"
            >
              {{ $t('lorebooks.global') }}
            </span>
          </div>
          <p v-if="lb.description" class="mt-0.5 line-clamp-1 text-[11px] text-muted-foreground">
            {{ lb.description }}
          </p>
        </button>

        <div v-if="loading && lorebooks.length === 0" class="flex justify-center py-8">
          <UIcon name="i-lucide-loader-2" class="h-5 w-5 animate-spin text-primary" />
        </div>
        <div v-else-if="lorebooks.length === 0" class="px-3 py-8 text-center text-xs text-muted-foreground">
          {{ $t('lorebooks.empty') }}
        </div>
      </div>
    </div>

    <!-- Right: detail -->
    <div class="flex-1 overflow-y-auto">
      <!-- Lorebook create/edit form -->
      <div v-if="showLorebookForm" class="px-8 py-6">
        <div class="animate-fade-in-up rounded-xl border bg-card/50 p-6">
          <h2 class="mb-4 font-cinzel text-sm font-semibold tracking-wide text-foreground">
            {{ editingLorebook ? $t('lorebooks.form.editTitle') : $t('lorebooks.form.newTitle') }}
          </h2>
          <div class="space-y-4">
            <label class="block">
              <span class="mb-1 block text-xs font-medium text-muted-foreground">{{ $t('lorebooks.form.name') }}</span>
              <input
                v-model="lbName"
                type="text"
                :placeholder="$t('lorebooks.form.namePlaceholder')"
                class="w-full rounded-lg border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </label>
            <label class="block">
              <span class="mb-1 block text-xs font-medium text-muted-foreground">{{ $t('lorebooks.form.description') }}</span>
              <textarea
                v-model="lbDescription"
                rows="2"
                :placeholder="$t('lorebooks.form.descriptionPlaceholder')"
                class="w-full resize-y rounded-lg border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </label>
            <button
              type="button"
              class="flex items-center gap-2 rounded-lg border bg-muted/40 px-3 py-2"
              role="switch"
              :aria-checked="lbIsGlobal"
              @click="lbIsGlobal = !lbIsGlobal"
            >
              <span
                class="flex h-[20px] w-9 items-center rounded-full px-[3px] transition-colors duration-300"
                :class="lbIsGlobal ? 'bg-primary' : 'bg-muted-foreground/40'"
              >
                <span
                  class="h-3.5 w-3.5 rounded-full shadow-sm transition-transform duration-300"
                  :class="lbIsGlobal ? 'translate-x-[14px] bg-background' : 'translate-x-0 bg-white'"
                />
              </span>
              <span class="text-sm text-foreground">{{ $t('lorebooks.form.isGlobal') }}</span>
            </button>
            <div class="flex items-center gap-3 pt-1">
              <button
                class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
                :disabled="savingLorebook || !lbName.trim()"
                @click="submitLorebook"
              >
                {{ editingLorebook ? $t('lorebooks.form.save') : $t('lorebooks.form.create') }}
              </button>
              <button
                class="rounded-lg border px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                @click="showLorebookForm = false"
              >
                {{ $t('common.cancel') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Selected lorebook detail -->
      <template v-else-if="currentLorebook">
        <div class="space-y-6 px-8 py-6">
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <h2 class="font-cinzel text-xl font-bold text-foreground">{{ currentLorebook.name }}</h2>
                <span
                  v-if="currentLorebook.is_global"
                  class="rounded-full bg-primary/15 px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide text-primary"
                >
                  {{ $t('lorebooks.global') }}
                </span>
              </div>
              <p v-if="currentLorebook.description" class="mt-1 text-sm text-muted-foreground">
                {{ currentLorebook.description }}
              </p>
              <p class="mt-1 text-xs text-muted-foreground">
                {{ $t('lorebooks.entryCount', { count: entries.length }) }}
              </p>
            </div>
            <div class="flex shrink-0 items-center gap-2">
              <button
                class="flex h-9 w-9 items-center justify-center rounded-lg border text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                :title="$t('lorebooks.editLorebook')"
                @click="openEditLorebook"
              >
                <UIcon name="i-lucide-pencil" class="h-4 w-4" />
              </button>
              <button
                class="flex h-9 items-center gap-1.5 rounded-lg border px-3 text-sm transition-colors"
                :class="
                  pendingDeleteLb === currentLorebook.id
                    ? 'border-destructive text-destructive'
                    : 'text-muted-foreground hover:bg-accent hover:text-destructive'
                "
                @click="onDeleteLorebook"
                @mouseleave="pendingDeleteLb = null"
              >
                <UIcon name="i-lucide-trash-2" class="h-4 w-4" />
                {{ pendingDeleteLb === currentLorebook.id ? $t('lorebooks.confirmDelete') : '' }}
              </button>
              <button
                class="flex h-9 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                @click="openNewEntry"
              >
                <UIcon name="i-lucide-plus" class="h-4 w-4" />
                {{ $t('lorebooks.addEntry') }}
              </button>
            </div>
          </div>

          <LoreEntryForm
            v-if="showEntryForm"
            :initial="editingEntry"
            :saving="savingEntry"
            @submit="submitEntry"
            @cancel="showEntryForm = false"
          />

          <div v-if="entries.length" class="grid grid-cols-1 gap-3 xl:grid-cols-2">
            <LoreEntryCard
              v-for="entry in entries"
              :key="entry.id"
              :entry="entry"
              :pending-delete="pendingDeleteEntry === entry.id"
              @edit="openEditEntry(entry)"
              @delete="onDeleteEntry(entry)"
              @toggle-enabled="toggleEntry(entry)"
              @mouseleave="pendingDeleteEntry = null"
            />
          </div>
          <div v-else-if="!showEntryForm" class="py-12 text-center text-sm text-muted-foreground">
            {{ $t('lorebooks.noEntries') }}
          </div>
        </div>
      </template>

      <!-- Nothing selected -->
      <div v-else class="flex h-full items-center justify-center">
        <div class="text-center">
          <UIcon name="i-lucide-book-open" class="mx-auto mb-2 h-8 w-8 text-muted-foreground/40" />
          <p class="text-sm text-muted-foreground">{{ $t('lorebooks.selectPrompt') }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

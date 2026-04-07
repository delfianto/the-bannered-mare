<script setup lang="ts">
import { ref, computed } from "vue";
import { useDataBank } from "@/composables/useDataBank";
import type { DataBankCreate, DataBankUpdate, DataBankEntry } from "@/composables/useDataBank";

const { entries, loading, error, fetchEntries, createEntry, updateEntry, deleteEntry, refresh } =
  useDataBank();

const scopeFilter = ref<string>("all");
const scopes = [
  { id: "all", label: "All" },
  { id: "global", label: "Global" },
  { id: "character", label: "Character" },
  { id: "chat", label: "Chat" },
];

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

// ── Delete with two-click confirm ────────────────────────
const pendingDeleteId = ref<string | null>(null);

function onDeleteClick(entryId: string) {
  if (pendingDeleteId.value === entryId) {
    deleteEntry(entryId);
    pendingDeleteId.value = null;
  } else {
    pendingDeleteId.value = entryId;
  }
}

function cancelDelete() {
  pendingDeleteId.value = null;
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
      return "bg-accent text-foreground";
  }
}
</script>

<template>
  <div class="space-y-8 px-12 py-8">
    <!-- Header -->
    <div class="animate-fade-in-up">
      <div class="flex items-start justify-between">
        <div>
          <h1 class="mb-1 font-cinzel text-2xl font-bold tracking-wide text-foreground">
            Data Bank
          </h1>
          <p class="text-sm text-muted-foreground">
            Persistent memory entries injected into conversations by scope
          </p>
        </div>
        <button
          class="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          @click="openCreateForm"
        >
          <UIcon name="i-lucide-plus" class="h-4 w-4" />
          Add Entry
        </button>
      </div>
    </div>

    <!-- Scope Filter Pills -->
    <div class="animate-fade-in-up flex items-center gap-2" style="animation-delay: 60ms">
      <button
        v-for="scope in scopes"
        :key="scope.id"
        class="rounded-full px-4 py-1.5 text-xs font-medium tracking-wide transition-colors"
        :class="
          scopeFilter === scope.id
            ? 'bg-primary text-primary-foreground'
            : 'bg-accent/60 text-muted-foreground hover:bg-accent hover:text-foreground'
        "
        @click="onScopeChange(scope.id)"
      >
        {{ scope.label }}
      </button>
    </div>

    <!-- Inline Create/Edit Form -->
    <div
      v-if="showForm"
      class="animate-fade-in-up rounded-xl border border-[var(--border)] bg-card/50 p-6"
    >
      <h2 class="mb-4 font-cinzel text-sm font-semibold tracking-wide text-foreground">
        {{ editingId ? "Edit Entry" : "New Entry" }}
      </h2>
      <div class="space-y-4">
        <div>
          <label class="mb-1 block text-xs font-medium text-muted-foreground">Name</label>
          <input
            v-model="formName"
            type="text"
            placeholder="Entry name..."
            class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-muted-foreground">Scope</label>
          <select
            v-model="formScope"
            class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="global">Global</option>
            <option value="character">Character</option>
            <option value="chat">Chat</option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-muted-foreground">Content</label>
          <textarea
            v-model="formContent"
            rows="4"
            placeholder="Entry content..."
            class="w-full resize-y rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
        <div class="flex items-center gap-3">
          <button
            class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            @click="saveForm"
          >
            {{ editingId ? "Save Changes" : "Create Entry" }}
          </button>
          <button
            class="rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            @click="cancelForm"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <UIcon name="i-lucide-loader-2" class="h-6 w-6 animate-spin text-primary" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-20">
      <UIcon name="i-lucide-alert-circle" class="h-8 w-8 text-destructive" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border border-border px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent"
        @click="refresh()"
      >
        Retry
      </button>
    </div>

    <!-- Empty -->
    <div
      v-else-if="filteredEntries.length === 0"
      class="flex flex-col items-center justify-center gap-3 py-20"
    >
      <UIcon name="i-lucide-database" class="h-8 w-8 text-muted-foreground/40" />
      <p class="text-sm text-muted-foreground">No entries found</p>
    </div>

    <!-- Entry Cards Grid -->
    <div v-else class="grid grid-cols-1 gap-3 lg:grid-cols-2">
      <div
        v-for="(entry, index) in filteredEntries"
        :key="entry.id"
        class="group relative flex animate-fade-in-up flex-col rounded-xl border border-[var(--border)] bg-card/50 p-4 pb-8 transition-all hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
        :style="{ animationDelay: `${index * 30}ms` }"
      >
        <!-- Header -->
        <div class="mb-2 flex items-start justify-between gap-2">
          <h3 class="font-cinzel text-sm font-semibold tracking-wide text-foreground">
            {{ entry.name }}
          </h3>
          <span
            class="shrink-0 rounded-full px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide"
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
        <div class="space-y-1.5 border-t border-border/30 pt-3 text-[11px] text-muted-foreground">
          <div class="flex items-center gap-1.5">
            <UIcon name="i-lucide-clock" class="h-3 w-3 shrink-0" />
            <span>{{ new Date(entry.updated_at).toLocaleDateString() }}</span>
          </div>
        </div>

        <!-- Action buttons (bottom-right) -->
        <div
          class="absolute bottom-3 right-3 flex items-center gap-2 text-[10px] text-muted-foreground/0 transition-colors group-hover:text-muted-foreground/60"
        >
          <button
            class="flex items-center gap-1 hover:text-foreground"
            @click.stop="openEditForm(entry)"
          >
            <UIcon name="i-lucide-pencil" class="h-3 w-3" />
            Edit
          </button>
          <button
            class="flex items-center gap-1"
            :class="
              pendingDeleteId === entry.id
                ? 'text-destructive!'
                : 'hover:text-destructive'
            "
            @click.stop="onDeleteClick(entry.id)"
            @mouseleave="cancelDelete"
          >
            <UIcon name="i-lucide-trash-2" class="h-3 w-3" />
            {{ pendingDeleteId === entry.id ? "Confirm?" : "Delete" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

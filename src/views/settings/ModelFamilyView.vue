<script setup lang="ts">
import { ref, reactive, onMounted, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useModelFamily } from "@/composables/useModelFamily";
import { useAppToast } from "@/composables/useToast";

const router = useRouter();
const route = useRoute();
const { family, loading, saving, deleting, error, fetchFamily, saveFamily, deleteFamily } = useModelFamily();
const toast = useAppToast();

const confirmDelete = ref(false);

const form = reactive({
  name: "",
  family_identifier: "",
  description: "",
});

onMounted(async () => {
  const id = route.params.id as string;
  await fetchFamily(id);
});

watch(family, (f) => {
  if (f) {
    form.name = f.name;
    form.family_identifier = f.family_identifier;
    form.description = f.description || "";
  }
});

async function handleSave() {
  if (!family.value) return;
  const updates: Record<string, unknown> = {};
  if (form.name !== family.value.name) updates.name = form.name;
  if (form.family_identifier !== family.value.family_identifier) updates.family_identifier = form.family_identifier;
  if (form.description !== (family.value.description || "")) updates.description = form.description || null;

  if (Object.keys(updates).length === 0) {
    toast.info("No changes to save");
    return;
  }

  try {
    await saveFamily(family.value.id, updates);
    toast.success("Model family updated");
  } catch (e) {
    toast.error("Failed to save model family");
  }
}

async function handleDelete() {
  if (!family.value) return;
  if (!confirmDelete.value) {
    confirmDelete.value = true;
    setTimeout(() => {
      confirmDelete.value = false;
    }, 3000);
    return;
  }
  try {
    await deleteFamily(family.value.id);
    toast.success("Model family deleted");
    router.push("/connections");
  } catch (e) {
    toast.error("Failed to delete model family");
    confirmDelete.value = false;
  }
}

function getParamType(schema: any): string {
  return schema?.type || "unknown";
}

function getParamDefault(schema: any): string {
  if (schema?.default === null || schema?.default === undefined) return "none";
  if (typeof schema.default === "object") return JSON.stringify(schema.default);
  return String(schema.default);
}

function getParamRange(schema: any): string | null {
  if (schema?.min_value !== undefined && schema?.max_value !== undefined) {
    return `${schema.min_value} - ${schema.max_value}`;
  }
  if (schema?.min_value !== undefined) return `>= ${schema.min_value}`;
  if (schema?.max_value !== undefined) return `<= ${schema.max_value}`;
  return null;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <!-- Loading overlay -->
    <div
      v-if="loading"
      class="absolute inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
    >
      <div class="flex flex-col items-center gap-3">
        <UIcon name="i-lucide-loader-2" class="h-6 w-6 animate-spin text-primary" />
        <span class="text-sm text-muted-foreground">Loading model family...</span>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error && !loading" class="flex flex-1 flex-col items-center justify-center gap-3">
      <UIcon name="i-lucide-alert-circle" class="h-8 w-8 text-destructive" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border border-border px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent"
        @click="router.back()"
      >
        Go Back
      </button>
    </div>

    <template v-if="family && !loading">
      <!-- Header -->
      <header class="z-20 flex h-[60px] flex-shrink-0 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur-sm">
        <div class="flex items-center gap-3">
          <button
            class="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            @click="router.push('/connections')"
          >
            <UIcon name="i-lucide-arrow-left" class="h-[18px] w-[18px]" />
          </button>
          <div class="flex items-center gap-2">
            <div class="flex h-6 w-6 items-center justify-center rounded-md bg-primary">
              <UIcon name="i-lucide-layers" class="h-3.5 w-3.5 text-primary-foreground" />
            </div>
            <h1 class="font-cinzel text-base font-semibold tracking-wider text-foreground">
              Edit Model Family
            </h1>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <!-- Delete button -->
          <button
            class="flex h-9 items-center gap-2 rounded-lg border px-4 text-sm font-medium transition-colors"
            :class="
              confirmDelete
                ? 'border-destructive bg-destructive/10 text-destructive'
                : 'border-destructive/30 text-destructive hover:bg-destructive/10'
            "
            :disabled="deleting"
            @click="handleDelete"
          >
            <UIcon
              :name="deleting ? 'i-lucide-loader-2' : 'i-lucide-trash-2'"
              class="h-4 w-4"
              :class="{ 'animate-spin': deleting }"
            />
            {{ deleting ? "Deleting..." : confirmDelete ? "Confirm?" : "Delete" }}
          </button>

          <!-- Save button -->
          <button
            class="flex h-9 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm transition-all hover:shadow-[0_2px_12px_var(--color-primary)/0.3] active:scale-[0.96]"
            :disabled="saving"
            @click="handleSave"
          >
            <UIcon
              :name="saving ? 'i-lucide-loader-2' : 'i-lucide-save'"
              class="h-4 w-4"
              :class="{ 'animate-spin': saving }"
            />
            {{ saving ? "Saving..." : "Save" }}
          </button>
        </div>
      </header>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <div class="mx-auto max-w-2xl space-y-6">
          <!-- Basic Info card -->
          <div class="rounded-xl border border-[var(--border)] bg-card/50 p-5">
            <h2 class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
              Basic Info
            </h2>
            <div class="space-y-4">
              <!-- Name -->
              <div>
                <label class="mb-1.5 block font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                  Name
                </label>
                <input
                  v-model="form.name"
                  type="text"
                  placeholder="Family name"
                  class="h-11 w-full rounded-lg border border-[var(--border)] bg-muted/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                />
              </div>

              <!-- Family Identifier -->
              <div>
                <label class="mb-1.5 block font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                  Family Identifier
                </label>
                <input
                  v-model="form.family_identifier"
                  type="text"
                  placeholder="provider/model-family"
                  class="h-11 w-full rounded-lg border border-[var(--border)] bg-muted/40 px-4 font-mono text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                />
              </div>

              <!-- Description -->
              <div>
                <label class="mb-1.5 block font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                  Description
                </label>
                <textarea
                  v-model="form.description"
                  rows="3"
                  placeholder="Describe this model family..."
                  class="w-full rounded-lg border border-[var(--border)] bg-muted/40 px-4 py-3 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                />
              </div>
            </div>
          </div>

          <!-- Provider Types card -->
          <div class="rounded-xl border border-[var(--border)] bg-card/50 p-5">
            <h2 class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
              Provider Types
            </h2>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="pt in family.provider_types"
                :key="pt"
                class="rounded-full bg-accent px-3 py-1 text-xs font-medium uppercase tracking-wide text-foreground"
              >
                {{ pt }}
              </span>
              <span v-if="!family.provider_types?.length" class="text-xs text-muted-foreground">
                No provider types configured
              </span>
            </div>
          </div>

          <!-- Parameter Schema card -->
          <div v-if="family.parameters && Object.keys(family.parameters).length" class="rounded-xl border border-[var(--border)] bg-card/50 p-5">
            <h2 class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
              Parameter Schema
            </h2>
            <div class="space-y-3">
              <div
                v-for="(schema, key) in family.parameters"
                :key="key"
                class="rounded-lg border border-border/50 bg-muted/20 p-3"
              >
                <div class="flex items-center gap-2">
                  <code class="text-sm font-semibold text-primary">{{ key }}</code>
                  <span class="rounded bg-accent px-1.5 py-0.5 text-[10px] font-medium uppercase text-muted-foreground">
                    {{ getParamType(schema) }}
                  </span>
                </div>
                <div class="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                  <span>
                    Default: <code class="text-foreground/70">{{ getParamDefault(schema) }}</code>
                  </span>
                  <span v-if="getParamRange(schema)">
                    Range: <code class="text-foreground/70">{{ getParamRange(schema) }}</code>
                  </span>
                  <span v-if="(schema as any)?.str_values">
                    Values: <code class="text-foreground/70">{{ (schema as any).str_values.join(", ") }}</code>
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Unsupported Parameters card -->
          <div v-if="family.unsupported_parameters?.length" class="rounded-xl border border-[var(--border)] bg-card/50 p-5">
            <h2 class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
              Unsupported Parameters
            </h2>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="param in family.unsupported_parameters"
                :key="param"
                class="rounded-full bg-red-500/10 px-3 py-1 font-mono text-xs font-medium text-red-400"
              >
                {{ param }}
              </span>
            </div>
          </div>

          <!-- Timestamps -->
          <div class="flex items-center justify-between px-1 text-[11px] text-muted-foreground/60">
            <span>Created {{ formatDate(family.created_at) }}</span>
            <span>Updated {{ formatDate(family.updated_at) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

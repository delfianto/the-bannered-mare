<script setup lang="ts">
import { ref, reactive, onMounted, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { usePromptFragment } from "@/composables/usePromptFragment";
import { useAppToast } from "@/composables/useToast";

const router = useRouter();
const route = useRoute();
const { fragment, loading, saving, deleting, error, fetchFragment, saveFragment, deleteFragment } =
  usePromptFragment();
const toast = useAppToast();

const confirmDelete = ref(false);

const fragmentTypeOptions = [
  { label: "System", value: "system" },
  { label: "NSFW", value: "nsfw" },
  { label: "Jailbreak", value: "jailbreak" },
  { label: "Instruction", value: "instruction" },
  { label: "Context", value: "context" },
];

const form = reactive({
  name: "",
  description: "",
  fragment_type: "instruction",
  content: "",
  is_global: false,
});

onMounted(async () => {
  const id = route.params.id as string;
  await fetchFragment(id);
});

watch(fragment, (f) => {
  if (f) {
    form.name = f.name;
    form.description = f.description || "";
    form.fragment_type = f.fragment_type;
    form.content = f.content;
    form.is_global = f.is_global;
  }
});

function toggleGlobal() {
  form.is_global = !form.is_global;
}

async function handleSave() {
  if (!fragment.value) return;
  const updates: Record<string, unknown> = {};
  if (form.name !== fragment.value.name) updates.name = form.name;
  if (form.description !== (fragment.value.description || ""))
    updates.description = form.description || null;
  if (form.fragment_type !== fragment.value.fragment_type)
    updates.fragment_type = form.fragment_type;
  if (form.content !== fragment.value.content) updates.content = form.content;
  if (form.is_global !== fragment.value.is_global) updates.is_global = form.is_global;

  if (Object.keys(updates).length === 0) {
    toast.info("No changes to save");
    return;
  }

  try {
    await saveFragment(fragment.value.id, updates);
    toast.success("Fragment updated");
  } catch (e) {
    toast.error("Failed to save fragment");
  }
}

async function handleDelete() {
  if (!fragment.value) return;
  if (!confirmDelete.value) {
    confirmDelete.value = true;
    setTimeout(() => {
      confirmDelete.value = false;
    }, 3000);
    return;
  }
  try {
    await deleteFragment(fragment.value.id);
    toast.success("Fragment deleted");
    router.push({ path: "/connections", query: { tab: "fragments" } });
  } catch (e) {
    toast.error("Failed to delete fragment");
    confirmDelete.value = false;
  }
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
        <span class="text-sm text-muted-foreground">Loading fragment...</span>
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

    <template v-if="fragment && !loading">
      <!-- Header -->
      <header
        class="z-20 flex h-[60px] flex-shrink-0 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur-sm"
      >
        <div class="flex items-center gap-3">
          <button
            class="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            @click="router.push({ path: '/connections', query: { tab: 'fragments' } })"
          >
            <UIcon name="i-lucide-arrow-left" class="h-[18px] w-[18px]" />
          </button>
          <div class="flex items-center gap-2">
            <div class="flex h-6 w-6 items-center justify-center rounded-md bg-primary">
              <UIcon name="i-lucide-puzzle" class="h-3.5 w-3.5 text-primary-foreground" />
            </div>
            <h1 class="font-cinzel text-base font-semibold tracking-wider text-foreground">
              Edit Fragment
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
        <div class="mx-auto max-w-3xl space-y-6">
          <!-- Basic Info card -->
          <div class="rounded-xl border border-border bg-card/50 p-5">
            <h2
              class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground"
            >
              Basic Info
            </h2>
            <div class="space-y-4">
              <!-- Name -->
              <div>
                <label
                  class="mb-1.5 block font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground"
                >
                  Name
                </label>
                <input
                  v-model="form.name"
                  type="text"
                  placeholder="Fragment name"
                  class="h-11 w-full rounded-lg border border-border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                />
              </div>

              <!-- Description -->
              <div>
                <label
                  class="mb-1.5 block font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground"
                >
                  Description
                </label>
                <textarea
                  v-model="form.description"
                  rows="3"
                  placeholder="Fragment description"
                  class="w-full rounded-lg border border-border bg-muted/40 px-4 py-3 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                />
              </div>

              <!-- Fragment Type -->
              <div>
                <label
                  class="mb-1.5 block font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground"
                >
                  Fragment Type
                </label>
                <USelectMenu
                  v-model="form.fragment_type"
                  :items="fragmentTypeOptions.map((o) => ({ label: o.label, value: o.value }))"
                  value-key="value"
                  :search-input="false"
                  class="w-full"
                  :ui="{
                    base: 'w-full border-none shadow-none ring-0 outline-none p-0 bg-transparent',
                    content:
                      'w-[var(--reka-popper-anchor-width)] border border-border bg-card ring-0 outline-none shadow-lg',
                    item: 'text-muted-foreground data-highlighted:text-foreground data-highlighted:bg-accent',
                  }"
                >
                  <button
                    class="flex h-11 w-full items-center rounded-lg border border-border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all hover:border-muted-foreground/30"
                  >
                    {{
                      fragmentTypeOptions.find((o) => o.value === form.fragment_type)?.label ||
                      form.fragment_type
                    }}
                  </button>
                </USelectMenu>
              </div>

              <!-- Is Global toggle -->
              <div class="flex items-center justify-between">
                <label
                  class="font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground"
                >
                  Global
                </label>
                <button @click="toggleGlobal" class="cursor-pointer">
                  <div
                    class="flex h-[22px] w-10 items-center rounded-full px-[3px] transition-colors duration-300"
                    :class="form.is_global ? 'bg-primary' : 'bg-muted-foreground/40'"
                  >
                    <span
                      class="h-4 w-4 rounded-full shadow-sm transition-transform duration-300"
                      :class="
                        form.is_global
                          ? 'translate-x-4 bg-background'
                          : 'translate-x-0 bg-white'
                      "
                    />
                  </div>
                </button>
              </div>
            </div>
          </div>

          <!-- Content card -->
          <div class="rounded-xl border border-border bg-card/50 p-5">
            <h2
              class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground"
            >
              Fragment Content
            </h2>
            <textarea
              v-model="form.content"
              rows="8"
              placeholder="Jinja2 template content..."
              class="min-h-[200px] w-full rounded-lg border border-border bg-muted/40 px-4 py-3 font-mono text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
            />
            <p class="mt-2 text-[11px] text-muted-foreground/60">
              Jinja2 template content injected into prompt templates
            </p>
          </div>

          <!-- Metadata -->
          <div class="flex items-center justify-between px-1 text-[11px] text-muted-foreground/60">
            <span>Created {{ formatDate(fragment.created_at) }}</span>
            <span>Updated {{ formatDate(fragment.updated_at) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

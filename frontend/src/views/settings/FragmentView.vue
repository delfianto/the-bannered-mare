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
      class="absolute inset-0 z-50 flex items-center justify-center bg-base-100/80 backdrop-blur-sm"
    >
      <div class="flex flex-col items-center gap-3">
        <AppIcon name="i-lucide-loader-2" class="size-6 animate-spin text-primary" />
        <span class="text-sm text-muted-foreground">{{ $t("common.loading") }}</span>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error && !loading" class="flex flex-1 flex-col items-center justify-center gap-3">
      <AppIcon name="i-lucide-alert-circle" class="size-8 text-error" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border px-4 py-2 text-sm text-foreground transition-colors hover:bg-base-300"
        @click="router.back()"
      >
        {{ $t("common.goBack") }}
      </button>
    </div>

    <template v-if="fragment && !loading">
      <!-- Header -->
      <header
        class="z-20 flex h-[60px] shrink-0 items-center justify-between border-b bg-base-100/80 px-6 backdrop-blur-sm"
      >
        <div class="flex items-center gap-3">
          <button
            class="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
            :aria-label="$t('connections.fragment.backToFragments')"
            @click="router.push({ path: '/connections', query: { tab: 'fragments' } })"
          >
            <AppIcon name="i-lucide-arrow-left" class="size-[18px]" />
          </button>
          <div class="flex items-center gap-2">
            <div class="flex size-6 items-center justify-center rounded-md bg-primary">
              <AppIcon name="i-lucide-puzzle" class="size-3.5 text-primary-content" />
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
                ? 'border-error bg-error/10 text-error'
                : 'border-error/30 text-error hover:bg-error/10'
            "
            :disabled="deleting"
            @click="handleDelete"
          >
            <AppIcon
              :name="deleting ? 'i-lucide-loader-2' : 'i-lucide-trash-2'"
              class="size-4"
              :class="{ 'animate-spin': deleting }"
            />
            {{
              deleting
                ? $t("common.deleting")
                : confirmDelete
                  ? $t("common.deleteConfirm")
                  : $t("common.delete")
            }}
          </button>

          <!-- Save button -->
          <button
            class="flex h-9 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-content shadow-sm transition-all hover:shadow-[0_2px_12px_var(--color-primary)/0.3] active:scale-[0.96]"
            :disabled="saving"
            @click="handleSave"
          >
            <AppIcon
              :name="saving ? 'i-lucide-loader-2' : 'i-lucide-save'"
              class="size-4"
              :class="{ 'animate-spin': saving }"
            />
            {{ saving ? $t("common.saving") : $t("common.save") }}
          </button>
        </div>
      </header>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <div class="mx-auto max-w-3xl space-y-6">
          <!-- Basic Info card -->
          <div class="rounded-xl border bg-base-200/50 p-5">
            <h2
              class="mb-4 font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
            >
              Basic Info
            </h2>
            <div class="space-y-4">
              <!-- Name -->
              <label class="block">
                <span
                  class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  {{ $t("connections.fragment.name") }}
                </span>
                <input
                  v-model="form.name"
                  type="text"
                  placeholder="Fragment name"
                  class="h-11 w-full rounded-lg border bg-base-300/40 px-4 text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                />
              </label>

              <!-- Description -->
              <label class="block">
                <span
                  class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  {{ $t("connections.fragment.description") }}
                </span>
                <textarea
                  v-model="form.description"
                  rows="3"
                  placeholder="Fragment description"
                  class="w-full rounded-lg border bg-base-300/40 px-4 py-3 text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                />
              </label>

              <!-- Fragment Type -->
              <div>
                <label
                  class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  {{ $t("connections.fragment.type") }}
                </label>
                <SelectMenu
                  v-model="form.fragment_type"
                  :items="fragmentTypeOptions.map((o) => ({ label: o.label, value: o.value }))"
                  value-key="value"
                  :search-input="false"
                  class="w-full"
                >
                  <button
                    class="flex h-11 w-full items-center rounded-lg border bg-base-300/40 px-4 text-sm text-foreground transition-all outline-none hover:border-muted-foreground/30"
                  >
                    {{
                      fragmentTypeOptions.find((o) => o.value === form.fragment_type)?.label ||
                      form.fragment_type
                    }}
                  </button>
                </SelectMenu>
              </div>

              <!-- Is Global toggle -->
              <div class="flex items-center justify-between">
                <label
                  class="font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  {{ $t("connections.fragment.isGlobal") }}
                </label>
                <AppToggle
                  :model-value="form.is_global"
                  aria-label="Global fragment"
                  @change="toggleGlobal"
                />
              </div>
            </div>
          </div>

          <!-- Content card -->
          <div class="rounded-xl border bg-base-200/50 p-5">
            <h2
              class="mb-4 font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
            >
              {{ $t("connections.fragment.content") }}
            </h2>
            <textarea
              v-model="form.content"
              rows="8"
              :placeholder="$t('connections.fragment.contentPlaceholder')"
              class="min-h-[200px] w-full rounded-lg border bg-base-300/40 px-4 py-3 font-mono text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
            />
            <p class="mt-2 text-[11px] text-muted-foreground/60">
              {{ $t("connections.fragment.contentHint") }}
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

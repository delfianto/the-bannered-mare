<script setup lang="ts">
import { reactive, onMounted, watch, computed } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter, useRoute } from "vue-router";
import { usePromptFragment } from "@/composables/usePromptFragment";
import { useConfirmAction } from "@/composables/useConfirmAction";
import { useAppToast } from "@/composables/useToast";
import { formatDate } from "@/utils/date";
import { routeParam } from "@/utils/route";

const router = useRouter();
const route = useRoute();
const { fragment, loading, saving, deleting, error, fetchFragment, saveFragment, deleteFragment } =
  usePromptFragment();
const toast = useAppToast();
const { t } = useI18n();

const fragmentTypeOptions = computed(() => [
  { label: t("connections.fragment.typeSystem"), value: "system" },
  { label: t("connections.fragment.typeNsfw"), value: "nsfw" },
  { label: t("connections.fragment.typeJailbreak"), value: "jailbreak" },
  { label: t("connections.fragment.typeInstruction"), value: "instruction" },
  { label: t("connections.fragment.typeContext"), value: "context" },
]);

const form = reactive({
  name: "",
  description: "",
  fragment_type: "instruction",
  content: "",
  is_global: false,
});

onMounted(async () => {
  const id = routeParam(route.params.id);
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
    toast.info(t("connections.fragment.toast.noChanges"));
    return;
  }

  try {
    await saveFragment(fragment.value.id, updates);
    toast.success(t("connections.fragment.toast.updated"));
  } catch (e) {
    toast.error(t("connections.fragment.toast.saveFailed"));
  }
}

const { armed: confirmDelete, trigger: handleDelete } = useConfirmAction(async () => {
  if (!fragment.value) return;
  try {
    await deleteFragment(fragment.value.id);
    toast.success(t("connections.fragment.toast.deleted"));
    router.push({ path: "/loadouts", query: { tab: "fragments" } });
  } catch {
    toast.error(t("connections.fragment.toast.deleteFailed"));
  }
});
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
        class="z-20 flex h-15 shrink-0 items-center justify-between border-b bg-base-100/80 px-6 backdrop-blur-sm"
      >
        <div class="flex items-center gap-3">
          <button
            class="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
            :aria-label="$t('connections.fragment.backToFragments')"
            @click="router.push({ path: '/loadouts', query: { tab: 'fragments' } })"
          >
            <AppIcon name="i-lucide-arrow-left" class="size-5" />
          </button>
          <div class="flex items-center gap-2">
            <div class="flex size-6 items-center justify-center rounded-md bg-primary">
              <AppIcon name="i-lucide-puzzle" class="size-3.5 text-primary-content" />
            </div>
            <h1 class="font-cinzel text-base font-semibold tracking-wider text-foreground">
              {{ $t("connections.fragment.editTitle") }}
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
            class="flex h-9 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-content shadow-sm transition-all hover:shadow-[0_2px_12px_var(--color-primary)/0.3] active:scale-0.96"
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
              {{ $t("common.basicInfo") }}
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
                  :placeholder="$t('connections.fragment.namePlaceholder')"
                  class="input-field"
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
                  :placeholder="$t('connections.fragment.descriptionPlaceholder')"
                  class="w-full rounded-lg border bg-base-300/40 px-4 py-3 text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:focus-ring"
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
                  :aria-label="$t('connections.fragment.isGlobal')"
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
              class="min-h-50 w-full rounded-lg border bg-base-300/40 px-4 py-3 font-mono text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:focus-ring"
            />
            <p class="mt-2 text-2xs text-muted-foreground/60">
              {{ $t("connections.fragment.contentHint") }}
            </p>
          </div>

          <!-- Metadata -->
          <div class="flex items-center justify-between px-1 text-2xs text-muted-foreground/60">
            <span>{{ $t("common.created") }} {{ formatDate(fragment.created_at) }}</span>
            <span>{{ $t("common.updated") }} {{ formatDate(fragment.updated_at) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

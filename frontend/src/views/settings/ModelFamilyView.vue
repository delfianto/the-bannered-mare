<script setup lang="ts">
import { reactive, onMounted, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter, useRoute } from "vue-router";
import { useModelFamily } from "@/composables/useModelFamily";
import { useConfirmAction } from "@/composables/useConfirmAction";
import { useAppToast } from "@/composables/useToast";
import { formatDate } from "@/utils/date";
import { routeParam } from "@/utils/route";
import type { ParamSchema } from "@/types/params";

const { t } = useI18n();

const router = useRouter();
const route = useRoute();
const { family, loading, saving, deleting, error, fetchFamily, saveFamily, deleteFamily } =
  useModelFamily();
const toast = useAppToast();

const form = reactive({
  name: "",
  family_identifier: "",
  description: "",
});

onMounted(async () => {
  const id = routeParam(route.params.id);
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
  if (form.family_identifier !== family.value.family_identifier)
    updates.family_identifier = form.family_identifier;
  if (form.description !== (family.value.description || ""))
    updates.description = form.description || null;

  if (Object.keys(updates).length === 0) {
    toast.info(t("connections.family.toast.noChanges"));
    return;
  }

  try {
    await saveFamily(family.value.id, updates);
    toast.success(t("connections.family.toast.updated"));
  } catch (e) {
    toast.error(t("connections.family.toast.saveFailed"));
  }
}

const { armed: confirmDelete, trigger: handleDelete } = useConfirmAction(async () => {
  if (!family.value) return;
  try {
    await deleteFamily(family.value.id);
    toast.success(t("connections.family.toast.deleted"));
    router.push({ path: "/connections", query: { tab: "model-families" } });
  } catch {
    toast.error(t("connections.family.toast.deleteFailed"));
  }
});

function getParamType(schema: unknown): string {
  return (schema as ParamSchema)?.type || "unknown";
}

function getParamDefault(schema: unknown): string {
  const s = schema as ParamSchema;
  if (s?.default === null || s?.default === undefined) return "none";
  if (typeof s.default === "object") return JSON.stringify(s.default);
  return String(s.default);
}

function getParamRange(schema: unknown): string | null {
  const s = schema as ParamSchema;
  if (s?.min_value !== undefined && s?.max_value !== undefined) {
    return `${s.min_value} - ${s.max_value}`;
  }
  if (s?.min_value !== undefined) return `>= ${s.min_value}`;
  if (s?.max_value !== undefined) return `<= ${s.max_value}`;
  return null;
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

    <template v-if="family && !loading">
      <!-- Header -->
      <header
        class="z-20 flex h-15 shrink-0 items-center justify-between border-b bg-base-100/80 px-6 backdrop-blur-sm"
      >
        <div class="flex items-center gap-3">
          <button
            class="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
            :aria-label="$t('connections.family.backToFamilies')"
            @click="router.push({ path: '/connections', query: { tab: 'model-families' } })"
          >
            <AppIcon name="i-lucide-arrow-left" class="size-5" />
          </button>
          <div class="flex items-center gap-2">
            <div class="flex size-6 items-center justify-center rounded-md bg-primary">
              <AppIcon name="i-lucide-layers" class="size-3.5 text-primary-content" />
            </div>
            <h1 class="font-story text-base font-semibold tracking-wider text-foreground">
              {{ $t("connections.family.editTitle") }}
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
        <div class="mx-auto max-w-2xl space-y-6">
          <!-- Basic Info card -->
          <div class="rounded-xl border bg-base-200/50 p-5">
            <div class="space-y-4">
              <!-- Name -->
              <label class="block">
                <span
                  class="mb-1.5 block font-story text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  {{ $t("connections.family.name") }}
                </span>
                <input
                  v-model="form.name"
                  type="text"
                  :placeholder="$t('connections.family.namePlaceholder')"
                  class="input-field"
                />
              </label>

              <!-- Family Identifier -->
              <label class="block">
                <span
                  class="mb-1.5 block font-story text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  {{ $t("connections.family.identifier") }}
                </span>
                <input
                  v-model="form.family_identifier"
                  type="text"
                  :placeholder="$t('connections.family.identifierPlaceholder')"
                  class="input-field font-mono"
                />
              </label>

              <!-- Description -->
              <label class="block">
                <span
                  class="mb-1.5 block font-story text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  {{ $t("connections.family.description") }}
                </span>
                <textarea
                  v-model="form.description"
                  rows="3"
                  :placeholder="t('connections.family.descriptionPlaceholder')"
                  class="w-full rounded-lg border bg-base-300/40 px-4 py-3 text-sm text-foreground transition-all outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:focus-ring"
                />
              </label>
            </div>
          </div>

          <!-- Provider Types card -->
          <div class="rounded-xl border bg-base-200/50 p-5">
            <h2
              class="mb-4 font-story text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
            >
              {{ $t("connections.family.providerTypes") }}
            </h2>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="pt in family.provider_types"
                :key="pt"
                class="rounded-full bg-base-300 px-3 py-1 text-xs font-medium tracking-wide text-foreground uppercase"
              >
                {{ pt }}
              </span>
              <span v-if="!family.provider_types?.length" class="text-xs text-muted-foreground">
                {{ $t("connections.family.noProviderTypes") }}
              </span>
            </div>
          </div>

          <!-- Capabilities card -->
          <div
            v-if="family.extra_metadata && Object.keys(family.extra_metadata).length"
            class="rounded-xl border bg-base-200/50 p-5"
          >
            <h2
              class="mb-4 font-story text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
            >
              {{ $t("connections.family.capabilities") }}
            </h2>
            <div class="flex flex-wrap gap-2">
              <span
                v-if="family.extra_metadata.supports_prompt_caching"
                class="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-500"
              >
                <AppIcon name="i-lucide-database" class="size-3" />
                {{ $t("connections.family.capabilityPromptCaching") }}
              </span>
              <span
                v-if="family.extra_metadata.supports_vision"
                class="inline-flex items-center gap-1 rounded-full bg-blue-500/10 px-3 py-1 text-xs font-medium text-blue-400"
              >
                <AppIcon name="i-lucide-eye" class="size-3" />
                {{ $t("connections.family.capabilityVision") }}
              </span>
              <span
                v-if="family.extra_metadata.supports_function_calling"
                class="inline-flex items-center gap-1 rounded-full bg-purple-500/10 px-3 py-1 text-xs font-medium text-purple-400"
              >
                <AppIcon name="i-lucide-puzzle" class="size-3" />
                {{ $t("connections.family.capabilityFunctionCalling") }}
              </span>
              <span
                v-if="
                  family.extra_metadata.reasoning_mode &&
                  family.extra_metadata.reasoning_mode !== 'none'
                "
                class="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-500"
              >
                <AppIcon name="i-lucide-brain" class="size-3" />
                {{
                  $t("connections.family.capabilityReasoning", {
                    mode: family.extra_metadata.reasoning_mode,
                  })
                }}
              </span>
            </div>
          </div>

          <!-- Parameter Schema card -->
          <div
            v-if="family.parameters && Object.keys(family.parameters).length"
            class="rounded-xl border bg-base-200/50 p-5"
          >
            <h2
              class="mb-4 font-story text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
            >
              {{ $t("connections.family.parameterSchema") }}
            </h2>
            <div class="space-y-3">
              <div
                v-for="(schema, key) in family.parameters"
                :key="key"
                class="rounded-lg border border-border/50 bg-base-300/20 p-3"
              >
                <div class="flex items-center gap-2">
                  <code class="text-sm font-semibold text-primary">{{ key }}</code>
                  <span
                    class="rounded bg-base-300 px-1.5 py-0.5 text-3xs font-medium text-muted-foreground uppercase"
                  >
                    {{ getParamType(schema) }}
                  </span>
                </div>
                <div class="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                  <span>
                    {{ $t("connections.family.paramDefault") }}:
                    <code class="text-foreground/70">{{ getParamDefault(schema) }}</code>
                  </span>
                  <span v-if="getParamRange(schema)">
                    {{ $t("connections.family.paramRange") }}:
                    <code class="text-foreground/70">{{ getParamRange(schema) }}</code>
                  </span>
                  <span v-if="(schema as ParamSchema)?.str_values">
                    {{ $t("connections.family.paramValues") }}:
                    <code class="text-foreground/70">{{
                      (schema as ParamSchema).str_values?.join(", ")
                    }}</code>
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Unsupported Parameters card -->
          <div
            v-if="family.unsupported_parameters?.length"
            class="rounded-xl border bg-base-200/50 p-5"
          >
            <h2
              class="mb-4 font-story text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
            >
              {{ $t("connections.family.unsupportedParams") }}
            </h2>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="param in family.unsupported_parameters"
                :key="param"
                class="rounded-full bg-error/10 px-3 py-1 font-mono text-xs font-medium text-error"
              >
                {{ param }}
              </span>
            </div>
          </div>

          <!-- Timestamps -->
          <div class="flex items-center justify-between px-1 text-2xs text-muted-foreground/60">
            <span>{{ $t("common.created") }} {{ formatDate(family.created_at) }}</span>
            <span>{{ $t("common.updated") }} {{ formatDate(family.updated_at) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

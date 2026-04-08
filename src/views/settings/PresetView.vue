<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { usePreset } from "@/composables/usePreset";
import { useAppToast } from "@/composables/useToast";
const router = useRouter();
const route = useRoute();
const { preset, loading, saving, deleting, error, fetchPreset, savePreset, deletePreset, setDefault } =
  usePreset();
const toast = useAppToast();

const confirmDelete = ref(false);

const form = reactive({
  name: "",
  description: "",
  is_default: false,
  parameters: [] as { key: string; value: string }[],
});

onMounted(async () => {
  const id = route.params.id as string;
  await fetchPreset(id);
});

watch(preset, (p) => {
  if (p) {
    form.name = p.name;
    form.description = p.description || "";
    form.is_default = p.is_default;
    form.parameters = p.parameters
      ? Object.entries(p.parameters).map(([key, value]) => ({
          key,
          value: String(value),
        }))
      : [];
  }
});

const parameterCount = computed(() => form.parameters.length);

function toggleDefault() {
  form.is_default = !form.is_default;
}

function addParameter() {
  form.parameters.push({ key: "", value: "" });
}

function removeParameter(index: number) {
  form.parameters.splice(index, 1);
}

function parametersToObject(): Record<string, unknown> {
  const obj: Record<string, unknown> = {};
  for (const param of form.parameters) {
    if (!param.key.trim()) continue;
    const num = Number(param.value);
    obj[param.key.trim()] = isNaN(num) || param.value.trim() === "" ? param.value : num;
  }
  return obj;
}

async function handleSave() {
  if (!preset.value) return;
  const updates: Record<string, unknown> = {};
  if (form.name !== preset.value.name) updates.name = form.name;
  if (form.description !== (preset.value.description || ""))
    updates.description = form.description || null;
  if (form.is_default !== preset.value.is_default) updates.is_default = form.is_default;
  updates.parameters = parametersToObject();

  if (Object.keys(updates).length === 0) {
    toast.info("No changes to save");
    return;
  }

  try {
    await savePreset(preset.value.id, updates);
    toast.success("Preset updated");
  } catch {
    toast.error("Failed to save preset");
  }
}

async function handleDelete() {
  if (!preset.value) return;
  if (!confirmDelete.value) {
    confirmDelete.value = true;
    setTimeout(() => {
      confirmDelete.value = false;
    }, 3000);
    return;
  }
  try {
    await deletePreset(preset.value.id);
    toast.success("Preset deleted");
    router.push({ path: "/connections", query: { tab: "presets" } });
  } catch {
    toast.error("Failed to delete preset");
    confirmDelete.value = false;
  }
}

async function handleSetDefault() {
  if (!preset.value) return;
  try {
    await setDefault(preset.value.id);
    toast.success("Preset set as default");
  } catch {
    toast.error("Failed to set default");
  }
}

function isNumericValue(value: string): boolean {
  return value.trim() !== "" && !isNaN(Number(value));
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
        <span class="text-sm text-muted-foreground">{{ $t('common.loading') }}</span>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error && !loading" class="flex flex-1 flex-col items-center justify-center gap-3">
      <UIcon name="i-lucide-alert-circle" class="h-8 w-8 text-destructive" />
      <p class="text-sm text-muted-foreground">{{ error.message }}</p>
      <button
        class="rounded-lg border px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent"
        @click="router.back()"
      >
        {{ $t('common.goBack') }}
      </button>
    </div>

    <template v-if="preset && !loading">
      <!-- Header -->
      <header
        class="z-20 flex h-[60px] flex-shrink-0 items-center justify-between border-b bg-background/80 px-6 backdrop-blur-sm"
      >
        <div class="flex items-center gap-3">
          <button
            class="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            :aria-label="$t('connections.preset.backToPresets')"
            @click="router.push({ path: '/connections', query: { tab: 'presets' } })"
          >
            <UIcon name="i-lucide-arrow-left" class="h-[18px] w-[18px]" />
          </button>
          <div class="flex items-center gap-2">
            <div class="flex h-6 w-6 items-center justify-center rounded-md bg-primary">
              <UIcon name="i-lucide-sliders-horizontal" class="h-3.5 w-3.5 text-primary-foreground" />
            </div>
            <h1 class="font-cinzel text-base font-semibold tracking-wider text-foreground">
              Edit Preset
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
            {{ deleting ? $t('common.deleting') : confirmDelete ? $t('common.deleteConfirm') : $t('common.delete') }}
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
            {{ saving ? $t('common.saving') : $t('common.save') }}
          </button>
        </div>
      </header>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <div class="mx-auto grid max-w-6xl gap-6 lg:grid-cols-5">
          <!-- Left column (3 cols) -->
          <div class="space-y-6 lg:col-span-3">
            <!-- Basic Info card -->
            <div class="rounded-xl border bg-card/50 p-5">
              <h2
                class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground"
              >
                Basic Info
              </h2>
              <div class="space-y-4">
                <!-- Name -->
                <label class="block">
                  <span
                    class="mb-1.5 block font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground"
                  >
                    {{ $t('connections.preset.name') }}
                  </span>
                  <input
                    v-model="form.name"
                    type="text"
                    placeholder="Preset name"
                    class="h-11 w-full rounded-lg border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                  />
                </label>

                <!-- Description -->
                <label class="block">
                  <span
                    class="mb-1.5 block font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground"
                  >
                    {{ $t('connections.preset.description') }}
                  </span>
                  <textarea
                    v-model="form.description"
                    rows="3"
                    placeholder="Preset description"
                    class="w-full rounded-lg border bg-muted/40 px-4 py-3 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                  />
                </label>

                <!-- Is Default toggle -->
                <div class="flex items-center justify-between">
                  <label
                    class="font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground"
                  >
                    {{ $t('connections.preset.isDefault') }}
                  </label>
                  <button @click="toggleDefault" role="switch" :aria-checked="form.is_default" aria-label="Default preset" class="cursor-pointer">
                    <div
                      class="flex h-[22px] w-10 items-center rounded-full px-[3px] transition-colors duration-300"
                      :class="form.is_default ? 'bg-primary' : 'bg-muted-foreground/40'"
                    >
                      <span
                        class="h-4 w-4 rounded-full shadow-sm transition-transform duration-300"
                        :class="
                          form.is_default
                            ? 'translate-x-4 bg-background'
                            : 'translate-x-0 bg-white'
                        "
                      />
                    </div>
                  </button>
                </div>
              </div>
            </div>

            <!-- Parameters card -->
            <div class="rounded-xl border bg-card/50 p-5">
              <h2
                class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground"
              >
                {{ $t('connections.preset.params') }}
              </h2>
              <div class="space-y-2">
                <div
                  v-for="(param, index) in form.parameters"
                  :key="index"
                  class="flex items-center gap-3"
                >
                  <!-- Parameter name -->
                  <input
                    v-model="param.key"
                    type="text"
                    placeholder="parameter_name"
                    class="h-11 w-[200px] shrink-0 rounded-lg border bg-muted/40 px-4 font-mono text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                  />
                  <!-- Parameter value -->
                  <input
                    v-model="param.value"
                    :type="isNumericValue(param.value) ? 'number' : 'text'"
                    :step="isNumericValue(param.value) ? 'any' : undefined"
                    placeholder="value"
                    class="h-11 flex-1 rounded-lg border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                  />
                  <!-- Remove button -->
                  <button
                    class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
                    :aria-label="$t('connections.preset.removeParam')"
                    @click="removeParameter(index)"
                  >
                    <UIcon name="i-lucide-x" class="h-4 w-4" />
                  </button>
                </div>
              </div>
              <button
                class="mt-3 flex items-center gap-2 rounded-lg border border-dashed px-4 py-2 text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                @click="addParameter"
              >
                <UIcon name="i-lucide-plus" class="h-4 w-4" />
                {{ $t('connections.preset.addParam') }}
              </button>
            </div>
          </div>

          <!-- Right column (2 cols) -->
          <div class="space-y-6 lg:col-span-2">
            <!-- Metadata card -->
            <div class="rounded-xl border bg-card/50 p-5">
              <h2
                class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground"
              >
                {{ $t('connections.preset.metadata') }}
              </h2>
              <div class="space-y-3">
                <!-- Is Default status -->
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Default</span>
                  <span
                    class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
                    :class="
                      preset.is_default
                        ? 'bg-emerald-500/10 text-emerald-500'
                        : 'bg-muted text-muted-foreground'
                    "
                  >
                    <span
                      class="h-1.5 w-1.5 rounded-full"
                      :class="preset.is_default ? 'bg-emerald-500' : 'bg-muted-foreground'"
                    />
                    {{ preset.is_default ? "Yes" : "No" }}
                  </span>
                </div>

                <!-- Set as Default button -->
                <button
                  v-if="!preset.is_default"
                  class="flex w-full items-center justify-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent"
                  :disabled="saving"
                  @click="handleSetDefault"
                >
                  <UIcon
                    :name="saving ? 'i-lucide-loader-2' : 'i-lucide-star'"
                    class="h-4 w-4"
                    :class="{ 'animate-spin': saving }"
                  />
                  {{ saving ? $t('common.saving') : $t('connections.preset.setDefault') }}
                </button>

                <div class="h-px bg-border/50" />

                <!-- Parameter count -->
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Parameters</span>
                  <span class="text-sm text-foreground">{{ parameterCount }}</span>
                </div>

                <!-- Timestamps -->
                <div class="border-t border-border/50 pt-3">
                  <div class="space-y-1.5 text-[11px] text-muted-foreground/60">
                    <div class="flex justify-between">
                      <span>Created</span>
                      <span>{{ formatDate(preset.created_at) }}</span>
                    </div>
                    <div class="flex justify-between">
                      <span>Updated</span>
                      <span>{{ formatDate(preset.updated_at) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter, useRoute } from "vue-router";
import { usePromptTemplate } from "@/composables/usePromptTemplate";
import { useAppToast } from "@/composables/useToast";

const { t } = useI18n();

const router = useRouter();
const route = useRoute();
const {
  template,
  attachedFragments,
  preview,
  loading,
  saving,
  deleting,
  previewing,
  error,
  fetchTemplate,
  saveTemplate,
  deleteTemplate,
  previewTemplate,
  fetchAttachedFragments,
  detachFragment,
} = usePromptTemplate();
const toast = useAppToast();

const confirmDelete = ref(false);

const form = reactive({
  name: "",
  description: "",
  is_default: false,
  system_template: "",
  component_order: [] as string[],
  components_enabled: {} as Record<string, boolean>,
  max_history_tokens: null as number | null,
});

onMounted(async () => {
  const id = route.params.id as string;
  await fetchTemplate(id);
  await fetchAttachedFragments(id);
});

watch(template, (t) => {
  if (t) {
    form.name = t.name;
    form.description = t.description || "";
    form.is_default = t.is_default;
    form.system_template = t.system_template;
    form.component_order = t.component_order ? [...t.component_order] : [];
    form.components_enabled = t.components_enabled ? { ...t.components_enabled } : {};
    form.max_history_tokens = t.max_history_tokens ?? null;
  }
});

function toggleDefault() {
  form.is_default = !form.is_default;
}

function toggleComponent(key: string) {
  form.components_enabled[key] = !form.components_enabled[key];
}

function humanize(str: string): string {
  return str
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const positionColors: Record<string, string> = {
  after_system: "bg-blue-500/15 text-blue-400",
  pre_history: "bg-amber-500/15 text-amber-400",
  post_history: "bg-emerald-500/15 text-emerald-400",
};

function typeBadgeClass(type: string): string {
  switch (type) {
    case "nsfw":
      return "bg-red-500/15 text-red-400";
    case "instruction":
      return "bg-blue-500/15 text-blue-400";
    case "system":
      return "bg-purple-500/15 text-purple-400";
    case "jailbreak":
      return "bg-orange-500/15 text-orange-400";
    case "context":
      return "bg-teal-500/15 text-teal-400";
    default:
      return "bg-accent text-foreground";
  }
}

async function handleSave() {
  if (!template.value) return;
  const updates: Record<string, unknown> = {};
  if (form.name !== template.value.name) updates.name = form.name;
  if (form.description !== (template.value.description || "")) updates.description = form.description || null;
  if (form.is_default !== template.value.is_default) updates.is_default = form.is_default;
  if (form.system_template !== template.value.system_template) updates.system_template = form.system_template;
  updates.component_order = form.component_order;
  updates.components_enabled = form.components_enabled;
  if (form.max_history_tokens !== template.value.max_history_tokens) updates.max_history_tokens = form.max_history_tokens;

  if (Object.keys(updates).length === 0) {
    toast.info("No changes to save");
    return;
  }

  try {
    await saveTemplate(template.value.id, updates);
    toast.success("Template updated");
  } catch (e) {
    toast.error("Failed to save template");
  }
}

async function handleDelete() {
  if (!template.value) return;
  if (!confirmDelete.value) {
    confirmDelete.value = true;
    setTimeout(() => {
      confirmDelete.value = false;
    }, 3000);
    return;
  }
  try {
    await deleteTemplate(template.value.id);
    toast.success("Template deleted");
    router.push({ path: "/connections", query: { tab: "templates" } });
  } catch (e) {
    toast.error("Failed to delete template");
    confirmDelete.value = false;
  }
}

async function handlePreview() {
  if (!template.value) return;
  try {
    await previewTemplate(template.value.id, {
      character_name: "Alice",
      character_description: "A helpful AI assistant",
      character_personality: "Friendly and knowledgeable",
      character_scenario: "Casual conversation",
      persona_name: "User",
      persona_description: "A curious person",
    });
  } catch (e) {
    toast.error("Failed to preview template");
  }
}

async function handleDetachFragment(fragmentId: string) {
  if (!template.value) return;
  try {
    await detachFragment(template.value.id, fragmentId);
    toast.success("Fragment detached");
  } catch (e) {
    toast.error("Failed to detach fragment");
  }
}

function handleAttachFragment() {
  console.log("Attach fragment clicked — fragment picker modal needed");
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

    <template v-if="template && !loading">
      <!-- Header -->
      <header class="z-20 flex h-[60px] flex-shrink-0 items-center justify-between border-b bg-background/80 px-6 backdrop-blur-sm">
        <div class="flex items-center gap-3">
          <button
            class="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            :aria-label="$t('connections.template.backToTemplates')"
            @click="router.push({ path: '/connections', query: { tab: 'templates' } })"
          >
            <UIcon name="i-lucide-arrow-left" class="h-[18px] w-[18px]" />
          </button>
          <div class="flex items-center gap-2">
            <div class="flex h-6 w-6 items-center justify-center rounded-md bg-primary">
              <UIcon name="i-lucide-file-text" class="h-3.5 w-3.5 text-primary-foreground" />
            </div>
            <h1 class="font-cinzel text-base font-semibold tracking-wider text-foreground">
              Edit Template
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
              <h2 class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                Basic Info
              </h2>
              <div class="space-y-4">
                <!-- Name -->
                <label class="block">
                  <span class="mb-1.5 block font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                    {{ $t('connections.template.name') }}
                  </span>
                  <input
                    v-model="form.name"
                    type="text"
                    placeholder="Template name"
                    class="h-11 w-full rounded-lg border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                  />
                </label>

                <!-- Description -->
                <label class="block">
                  <span class="mb-1.5 block font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                    {{ $t('connections.template.description') }}
                  </span>
                  <textarea
                    v-model="form.description"
                    rows="3"
                    placeholder="Template description"
                    class="w-full rounded-lg border bg-muted/40 px-4 py-3 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                  />
                </label>

                <!-- Is Default toggle -->
                <div class="flex items-center justify-between">
                  <label class="font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                    {{ $t('connections.template.isDefault') }}
                  </label>
                  <button @click="toggleDefault" role="switch" :aria-checked="form.is_default" aria-label="Default template" class="cursor-pointer">
                    <div
                      class="flex h-[22px] w-10 items-center rounded-full px-[3px] transition-colors duration-300"
                      :class="form.is_default ? 'bg-primary' : 'bg-muted-foreground/40'"
                    >
                      <span
                        class="h-4 w-4 rounded-full shadow-sm transition-transform duration-300"
                        :class="form.is_default ? 'translate-x-4 bg-background' : 'translate-x-0 bg-white'"
                      />
                    </div>
                  </button>
                </div>
              </div>
            </div>

            <!-- System Template card -->
            <div class="rounded-xl border bg-card/50 p-5">
              <h2 class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                {{ $t('connections.template.systemTemplate') }}
              </h2>
              <textarea
                v-model="form.system_template"
                rows="8"
                :placeholder="t('connections.template.systemTemplatePlaceholder')"
                class="min-h-[200px] w-full rounded-lg border bg-muted/40 px-4 py-3 font-mono text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
              />
              <p class="mt-2 text-[11px] text-muted-foreground/60">
                {{ $t('connections.template.systemTemplateHint') }}
              </p>
            </div>

            <!-- Component Ordering card -->
            <div class="rounded-xl border bg-card/50 p-5">
              <h2 class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                {{ $t('connections.template.components') }}
              </h2>
              <div v-if="form.component_order.length > 0" class="space-y-2">
                <div
                  v-for="component in form.component_order"
                  :key="component"
                  class="flex items-center justify-between rounded-lg border border-border/50 bg-muted/20 px-4 py-3"
                >
                  <div class="flex items-center gap-3">
                    <UIcon name="i-lucide-grip-vertical" class="h-4 w-4 text-muted-foreground/40" />
                    <span class="text-sm text-foreground">{{ humanize(component) }}</span>
                  </div>
                  <button @click="toggleComponent(component)" role="switch" :aria-checked="form.components_enabled[component]" :aria-label="component" class="cursor-pointer">
                    <div
                      class="flex h-[22px] w-10 items-center rounded-full px-[3px] transition-colors duration-300"
                      :class="form.components_enabled[component] ? 'bg-primary' : 'bg-muted-foreground/40'"
                    >
                      <span
                        class="h-4 w-4 rounded-full shadow-sm transition-transform duration-300"
                        :class="form.components_enabled[component] ? 'translate-x-4 bg-background' : 'translate-x-0 bg-white'"
                      />
                    </div>
                  </button>
                </div>
              </div>
              <p v-else class="text-sm text-muted-foreground">{{ $t('connections.template.noComponents') }}</p>
            </div>

            <!-- Attached Fragments card -->
            <div class="rounded-xl border bg-card/50 p-5">
              <h2 class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                {{ $t('connections.template.fragments') }}
              </h2>
              <div v-if="attachedFragments.length > 0" class="space-y-2">
                <div
                  v-for="tf in attachedFragments"
                  :key="tf.id"
                  class="flex items-center justify-between rounded-lg border border-border/50 bg-muted/20 px-4 py-3"
                >
                  <div class="flex items-center gap-3">
                    <div class="min-w-0">
                      <p class="text-sm font-medium text-foreground">{{ tf.fragment.name }}</p>
                      <div class="mt-1 flex items-center gap-2">
                        <span
                          class="rounded-full px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide"
                          :class="typeBadgeClass(tf.fragment.fragment_type)"
                        >
                          {{ tf.fragment.fragment_type }}
                        </span>
                        <span
                          class="rounded-full px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide"
                          :class="positionColors[tf.position] || 'bg-accent text-foreground'"
                        >
                          {{ humanize(tf.position) }}
                        </span>
                        <span class="text-[10px] text-muted-foreground/60">
                          #{{ tf.ordinal }}
                        </span>
                      </div>
                    </div>
                  </div>
                  <button
                    class="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
                    :aria-label="$t('connections.template.detachFragment')"
                    @click="handleDetachFragment(tf.fragment_id)"
                  >
                    <UIcon name="i-lucide-x" class="h-4 w-4" />
                  </button>
                </div>
              </div>
              <p v-else class="mb-3 text-sm text-muted-foreground">{{ $t('connections.template.noFragments') }}</p>
              <button
                class="mt-3 flex items-center gap-2 rounded-lg border border-dashed px-4 py-2 text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                @click="handleAttachFragment"
              >
                <UIcon name="i-lucide-plus" class="h-4 w-4" />
                {{ $t('connections.template.attachFragment') }}
              </button>
            </div>
          </div>

          <!-- Right column (2 cols) -->
          <div class="space-y-6 lg:col-span-2">
            <!-- Metadata card -->
            <div class="rounded-xl border bg-card/50 p-5">
              <h2 class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                Metadata
              </h2>
              <div class="space-y-3">
                <!-- Max History Tokens -->
                <label class="block">
                  <span class="mb-1.5 block text-sm text-muted-foreground">
                    {{ $t('connections.template.maxHistoryTokens') }}
                  </span>
                  <input
                    :value="form.max_history_tokens ?? ''"
                    type="number"
                    placeholder="e.g. 4096"
                    class="h-11 w-full rounded-lg border bg-muted/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                    @input="(e) => { const v = (e.target as HTMLInputElement).value; form.max_history_tokens = v === '' ? null : Number(v); }"
                  />
                </label>

                <div class="h-px bg-border/50" />

                <!-- Is Default -->
                <div class="flex items-center justify-between">
                  <span class="text-sm text-muted-foreground">Default</span>
                  <span
                    class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
                    :class="
                      form.is_default
                        ? 'bg-emerald-500/10 text-emerald-500'
                        : 'bg-muted text-muted-foreground'
                    "
                  >
                    <span
                      class="h-1.5 w-1.5 rounded-full"
                      :class="form.is_default ? 'bg-emerald-500' : 'bg-muted-foreground'"
                    />
                    {{ form.is_default ? "Yes" : "No" }}
                  </span>
                </div>

                <!-- Timestamps -->
                <div class="border-t border-border/50 pt-3">
                  <div class="space-y-1.5 text-[11px] text-muted-foreground/60">
                    <div class="flex justify-between">
                      <span>Created</span>
                      <span>{{ formatDate(template.created_at) }}</span>
                    </div>
                    <div class="flex justify-between">
                      <span>Updated</span>
                      <span>{{ formatDate(template.updated_at) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Preview card -->
            <div class="rounded-xl border bg-card/50 p-5">
              <h2 class="mb-4 font-cinzel text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                {{ $t('connections.template.preview') }}
              </h2>
              <button
                class="flex w-full items-center justify-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-accent"
                :disabled="previewing"
                @click="handlePreview"
              >
                <UIcon
                  :name="previewing ? 'i-lucide-loader-2' : 'i-lucide-eye'"
                  class="h-4 w-4"
                  :class="{ 'animate-spin': previewing }"
                />
                {{ previewing ? $t('common.loading') : $t('connections.template.previewTemplate') }}
              </button>
              <div
                v-if="preview"
                class="mt-4 rounded-lg border border-border/50 bg-muted/20 p-4"
              >
                <pre class="whitespace-pre-wrap font-mono text-xs leading-relaxed text-foreground">{{ preview.rendered }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

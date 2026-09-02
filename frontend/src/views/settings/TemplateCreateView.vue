<script setup lang="ts">
import { reactive, ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter, onBeforeRouteLeave } from "vue-router";
import { usePromptTemplate } from "@/composables/usePromptTemplate";
import { useAppToast } from "@/composables/useToast";
import { useConfirm } from "@/composables/useConfirm";

const router = useRouter();
const { createTemplate, saving } = usePromptTemplate();
const toast = useAppToast();
const { t } = useI18n();
const { confirm } = useConfirm();

const form = reactive({
  name: "",
  description: "",
  system_template: "",
  is_default: false,
});

const initialSnapshot = JSON.stringify(form);
const saved = ref(false);
const dirty = computed(() => !saved.value && JSON.stringify(form) !== initialSnapshot);

const canCreate = computed(() => !!form.name.trim() && !!form.system_template.trim());

async function handleCreate() {
  if (!canCreate.value) {
    toast.error(t("connections.template.toast.required"));
    return;
  }
  try {
    const created = await createTemplate({
      name: form.name.trim(),
      description: form.description.trim() || null,
      system_template: form.system_template,
      is_default: form.is_default,
    });
    saved.value = true; // suppress the unsaved-changes guard on the redirect
    toast.success(t("connections.template.toast.created"));
    router.push(`/settings/templates/${created.id}`);
  } catch {
    toast.error(t("connections.template.toast.createFailed"));
  }
}

function toggleDefault() {
  form.is_default = !form.is_default;
}

function goBack() {
  router.push({ path: "/loadouts", query: { tab: "templates" } });
}

// --- Unsaved-changes guards ---
function beforeUnloadHandler(e: BeforeUnloadEvent) {
  if (dirty.value) {
    e.preventDefault();
    e.returnValue = "";
  }
}
onMounted(() => window.addEventListener("beforeunload", beforeUnloadHandler));
onBeforeUnmount(() => window.removeEventListener("beforeunload", beforeUnloadHandler));

onBeforeRouteLeave(async () => {
  if (!dirty.value) return true;
  return confirm({
    title: "Unsaved changes",
    message: "You have unsaved changes. Leave and discard them?",
    confirmLabel: "Discard",
    danger: true,
  });
});
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <!-- Header -->
    <header
      class="z-20 flex h-15 shrink-0 items-center justify-between border-b bg-base-100/80 px-6 backdrop-blur-sm"
    >
      <div class="flex items-center gap-3">
        <button
          class="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
          aria-label="Back to templates"
          @click="goBack"
        >
          <AppIcon name="i-lucide-arrow-left" class="size-5" />
        </button>
        <div class="flex items-center gap-2">
          <div class="flex size-6 items-center justify-center rounded-md bg-primary">
            <AppIcon name="i-lucide-file-text" class="size-3.5 text-primary-content" />
          </div>
          <h1 class="font-story text-base font-semibold tracking-wider text-foreground">
            New Template
          </h1>
        </div>
      </div>

      <button
        class="flex h-9 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-content shadow-sm transition-all hover:shadow-[0_2px_12px_var(--color-primary)/0.3] active:scale-[0.96] disabled:pointer-events-none disabled:opacity-50"
        :disabled="saving || !canCreate"
        @click="handleCreate"
      >
        <AppIcon
          :name="saving ? 'i-lucide-loader-2' : 'i-lucide-save'"
          class="size-4"
          :class="{ 'animate-spin': saving }"
        />
        {{ saving ? "Creating..." : "Create Template" }}
      </button>
    </header>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-6">
      <div class="mx-auto max-w-3xl space-y-6">
        <div class="rounded-xl border bg-base-200/50 p-5">
          <div class="space-y-4">
            <!-- Name -->
            <label class="block">
              <span
                class="mb-1.5 block font-story text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                Name
              </span>
              <input
                v-model="form.name"
                type="text"
                placeholder="Template name"
                class="input-field"
              />
            </label>

            <!-- Description -->
            <label class="block">
              <span
                class="mb-1.5 block font-story text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                Description
                <span class="normal-case text-muted-foreground/60">(optional)</span>
              </span>
              <input
                v-model="form.description"
                type="text"
                placeholder="What is this template for?"
                class="input-field"
              />
            </label>

            <!-- System template -->
            <label class="block">
              <span
                class="mb-1.5 block font-story text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                System Template
              </span>
              <textarea
                v-model="form.system_template"
                rows="12"
                placeholder="The Jinja2 system prompt template…"
                class="w-full resize-y rounded-lg border bg-base-300/40 px-4 py-2.5 font-mono text-sm text-foreground outline-none transition-all placeholder:font-sans placeholder:text-muted-foreground focus:border-primary/40 focus:focus-ring"
              />
              <span class="mt-1 block text-3xs text-muted-foreground/70">
                Supports Jinja2. Component ordering and attached fragments can be tuned after
                creating.
              </span>
            </label>

            <!-- Default toggle -->
            <div class="flex items-center justify-between">
              <div class="min-w-0">
                <span
                  class="block font-story text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  Set as Default
                </span>
                <span class="text-3xs text-muted-foreground/70">
                  Used for new chats when no template is chosen.
                </span>
              </div>
              <AppToggle
                :model-value="form.is_default"
                aria-label="Set as default"
                @change="toggleDefault"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

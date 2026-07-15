<script setup lang="ts">
import { reactive, ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter, onBeforeRouteLeave } from "vue-router";
import { usePromptFragment } from "@/composables/usePromptFragment";
import { useAppToast } from "@/composables/useToast";

const router = useRouter();
const { createFragment, saving } = usePromptFragment();
const toast = useAppToast();
const { t } = useI18n();

const form = reactive({
  name: "",
  description: "",
  fragment_type: "instruction",
  content: "",
  is_global: false,
});

const initialSnapshot = JSON.stringify(form);
const saved = ref(false);
const dirty = computed(() => !saved.value && JSON.stringify(form) !== initialSnapshot);

const canCreate = computed(() => !!form.name.trim() && !!form.content.trim());

async function handleCreate() {
  if (!canCreate.value) {
    toast.error(t("connections.fragment.toast.required"));
    return;
  }
  try {
    const created = await createFragment({
      name: form.name.trim(),
      description: form.description.trim() || null,
      fragment_type: form.fragment_type.trim() || "instruction",
      content: form.content,
      is_global: form.is_global,
    });
    saved.value = true; // suppress the unsaved-changes guard on the redirect
    toast.success(t("connections.fragment.toast.created"));
    router.push(`/settings/fragments/${created.id}`);
  } catch {
    toast.error(t("connections.fragment.toast.createFailed"));
  }
}

function toggleGlobal() {
  form.is_global = !form.is_global;
}

function goBack() {
  router.push({ path: "/loadouts", query: { tab: "fragments" } });
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

onBeforeRouteLeave(() => {
  if (dirty.value) {
    return window.confirm("You have unsaved changes. Leave and discard them?");
  }
  return true;
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
          aria-label="Back to fragments"
          @click="goBack"
        >
          <AppIcon name="i-lucide-arrow-left" class="size-5" />
        </button>
        <div class="flex items-center gap-2">
          <div class="flex size-6 items-center justify-center rounded-md bg-primary">
            <AppIcon name="i-lucide-puzzle" class="size-3.5 text-primary-content" />
          </div>
          <h1 class="font-cinzel text-base font-semibold tracking-wider text-foreground">
            New Fragment
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
        {{ saving ? "Creating..." : "Create Fragment" }}
      </button>
    </header>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-6">
      <div class="mx-auto max-w-3xl space-y-6">
        <div class="rounded-xl border bg-base-200/50 p-5">
          <div class="space-y-4">
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <!-- Name -->
              <label class="block">
                <span
                  class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  Name
                </span>
                <input
                  v-model="form.name"
                  type="text"
                  placeholder="Fragment name"
                  class="h-11 w-full rounded-lg border bg-base-300/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                />
              </label>

              <!-- Type -->
              <label class="block">
                <span
                  class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  Type
                </span>
                <input
                  v-model="form.fragment_type"
                  type="text"
                  placeholder="instruction"
                  class="h-11 w-full rounded-lg border bg-base-300/40 px-4 font-mono text-sm text-foreground outline-none transition-all placeholder:font-sans placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
                />
              </label>
            </div>

            <!-- Description -->
            <label class="block">
              <span
                class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                Description
                <span class="normal-case text-muted-foreground/60">(optional)</span>
              </span>
              <input
                v-model="form.description"
                type="text"
                placeholder="What is this fragment for?"
                class="h-11 w-full rounded-lg border bg-base-300/40 px-4 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
              />
            </label>

            <!-- Content -->
            <label class="block">
              <span
                class="mb-1.5 block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
              >
                Content
              </span>
              <textarea
                v-model="form.content"
                rows="10"
                placeholder="The Jinja2 fragment content…"
                class="w-full resize-y rounded-lg border bg-base-300/40 px-4 py-2.5 font-mono text-sm text-foreground outline-none transition-all placeholder:font-sans placeholder:text-muted-foreground focus:border-primary/40 focus:shadow-[0_0_0_3px_var(--color-primary)/0.08]"
              />
              <span class="mt-1 block text-3xs text-muted-foreground/70"> Supports Jinja2. </span>
            </label>

            <!-- Global toggle -->
            <div class="flex items-center justify-between">
              <div class="min-w-0">
                <span
                  class="block font-cinzel text-xs font-semibold tracking-[0.15em] text-muted-foreground uppercase"
                >
                  Global
                </span>
                <span class="text-3xs text-muted-foreground/70">
                  Global fragments apply to every template automatically.
                </span>
              </div>
              <AppToggle
                :model-value="form.is_global"
                aria-label="Global fragment"
                @change="toggleGlobal"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onErrorCaptured, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import AppSidebar from "./AppSidebar.vue";
import ServerStatusBanner from "./ServerStatusBanner.vue";
import WorkspacePanel from "./WorkspacePanel.vue";
import AppIcon from "@/components/shared/AppIcon.vue";

const { t } = useI18n();
const route = useRoute();

// Route-level error boundary: a view that throws while rendering (or a lazy
// chunk failure that slips past router.onError) shows a recoverable fallback
// instead of a blank pane. Cleared when the user navigates elsewhere.
const renderError = ref<Error | null>(null);
watch(
  () => route.fullPath,
  () => (renderError.value = null),
);
onErrorCaptured((err) => {
  renderError.value = err instanceof Error ? err : new Error(String(err));
  return false;
});

function reload() {
  window.location.reload();
}
</script>

<template>
  <div
    class="relative isolate flex h-screen overflow-hidden bg-base-100 text-foreground transition-colors duration-400"
  >
    <div aria-hidden="true" class="pointer-events-none absolute inset-0 overflow-hidden">
      <div
        class="absolute -top-40 -left-28 size-140 rounded-full bg-primary/20 blur-3xl dark:bg-primary/15"
      />
      <div
        class="absolute top-[42%] -left-32 size-96 rounded-full bg-primary/12 blur-3xl dark:bg-primary/10"
      />
      <div
        class="absolute right-[-12%] bottom-[-28%] size-160 rounded-full bg-primary/8 blur-3xl dark:bg-primary/6"
      />
    </div>
    <AppSidebar />
    <main class="relative z-10 flex min-h-0 flex-1 flex-col overflow-hidden">
      <ServerStatusBanner />
      <WorkspacePanel>
        <div class="flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto">
          <div
            v-if="renderError"
            class="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center"
          >
            <AppIcon name="i-lucide-triangle-alert" class="size-10 text-error" />
            <p class="font-story text-lg text-foreground">{{ t("common.errorBoundary.title") }}</p>
            <p class="max-w-md text-sm text-muted-foreground">
              {{ t("common.errorBoundary.description") }}
            </p>
            <button
              class="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-content transition-colors hover:bg-primary/90"
              @click="reload"
            >
              <AppIcon name="i-lucide-rotate-cw" class="size-4" />
              {{ t("common.errorBoundary.reload") }}
            </button>
          </div>
          <RouterView v-else />
        </div>
      </WorkspacePanel>
    </main>
  </div>
</template>

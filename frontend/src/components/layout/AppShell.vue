<script setup lang="ts">
import { onErrorCaptured, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import AppSidebar from "./AppSidebar.vue";
import ServerStatusBanner from "./ServerStatusBanner.vue";
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
    class="flex h-screen overflow-hidden bg-base-100 text-foreground transition-colors duration-400"
  >
    <AppSidebar />
    <main class="flex flex-1 flex-col overflow-y-auto">
      <ServerStatusBanner />
      <div
        v-if="renderError"
        class="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center"
      >
        <AppIcon name="i-lucide-triangle-alert" class="size-10 text-error" />
        <p class="font-cinzel text-lg text-foreground">{{ t("common.errorBoundary.title") }}</p>
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
    </main>
  </div>
</template>

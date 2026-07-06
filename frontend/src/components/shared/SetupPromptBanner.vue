<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useProfiles } from "@/composables/useProfiles";

const DISMISS_KEY = "bannered-mare:setup-dismissed";

const router = useRouter();
const { profiles, loading } = useProfiles();

// A profile with no model attached (e.g. an abandoned ST import) can't
// actually start a chat, so it shouldn't count as "already set up".
const hasReadyProfile = computed(() => profiles.value.some((p) => p.model_id));

const dismissed = ref(localStorage.getItem(DISMISS_KEY) === "true");

function getStarted() {
  router.push("/setup");
}

function dismiss() {
  dismissed.value = true;
  localStorage.setItem(DISMISS_KEY, "true");
}
</script>

<template>
  <div
    v-if="!loading && !dismissed && !hasReadyProfile"
    class="flex items-center justify-between gap-4 rounded-xl border border-primary/30 bg-primary/5 p-4"
  >
    <div class="flex items-center gap-3">
      <div class="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/15">
        <UIcon name="i-lucide-sparkles" class="size-4.5 text-primary" />
      </div>
      <div>
        <p class="text-sm font-medium text-foreground">Let's get your first profile set up</p>
        <p class="text-xs text-muted-foreground">You'll need one before you can start a tale.</p>
      </div>
    </div>
    <div class="flex shrink-0 items-center gap-3">
      <button
        class="text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        @click="dismiss"
      >
        I'll do it manually
      </button>
      <button
        class="flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3.5 text-xs font-medium text-primary-foreground shadow-sm transition-all hover:shadow-[0_2px_12px_var(--color-primary)/0.3]"
        @click="getStarted"
      >
        Get Started
      </button>
    </div>
  </div>
</template>

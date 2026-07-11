<script setup lang="ts">
import { onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import type { Profile } from "@/composables/useProfiles";

interface PickerModel {
  id: string;
  display_name: string;
}

const props = defineProps<{
  show: boolean;
  models: PickerModel[];
  currentModelId?: string | null;
  profiles: Profile[];
  currentProfileName?: string | null;
}>();

const emit = defineEmits<{
  close: [];
  changeModel: [modelId: string];
  applyProfile: [profileId: string];
}>();

const router = useRouter();

// Mirror Modal.vue's timer-driven open/close: `visible` gates mounting,
// `entered` drives the slide/fade CSS (nested transitions can drop leave hooks).
const DURATION = 200;
const visible = ref(props.show);
const entered = ref(props.show);
let closeTimer: ReturnType<typeof setTimeout> | undefined;

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === "Escape" && props.show) emit("close");
}

watch(
  () => props.show,
  (show) => {
    if (closeTimer) clearTimeout(closeTimer);
    if (show) {
      visible.value = true;
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
      entered.value = false;
      requestAnimationFrame(() => requestAnimationFrame(() => (entered.value = true)));
    } else {
      entered.value = false;
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
      closeTimer = setTimeout(() => (visible.value = false), DURATION);
    }
  },
  { immediate: true },
);

onUnmounted(() => {
  if (closeTimer) clearTimeout(closeTimer);
  document.body.style.overflow = "";
  window.removeEventListener("keydown", handleKeyDown);
});

function chooseModel(m: PickerModel) {
  if (m.id !== props.currentModelId) emit("changeModel", m.id);
}

function chooseProfile(p: Profile) {
  // Always (re-)apply — re-applying the current profile re-pulls its latest axes.
  emit("applyProfile", p.id);
}

function goManage() {
  emit("close");
  router.push("/loadouts");
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="fixed inset-0 z-50" role="dialog" aria-modal="true">
      <!-- Backdrop -->
      <div
        class="fixed inset-0 bg-black/50 backdrop-blur-[2px] transition-opacity duration-200"
        :class="entered ? 'opacity-100' : 'opacity-0'"
        @click="emit('close')"
      />

      <!-- Panel (slides in from the right) -->
      <div
        class="fixed inset-y-0 right-0 flex w-80 max-w-full flex-col border-l bg-base-200 shadow-2xl transition-transform duration-200 ease-out"
        :class="entered ? 'translate-x-0' : 'translate-x-full'"
      >
        <!-- Header -->
        <div class="flex h-15.5 shrink-0 items-center justify-between border-b px-4">
          <h2 class="font-cinzel text-sm font-semibold tracking-wide text-foreground">
            {{ $t("chat.settings.title") }}
          </h2>
          <button
            :aria-label="$t('common.close')"
            class="flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-base-300 hover:text-foreground"
            @click="emit('close')"
          >
            <AppIcon name="i-lucide-x" class="size-4" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto py-2">
          <!-- Model -->
          <div
            class="px-4 py-1.5 text-[0.625rem] font-semibold tracking-wider text-muted-foreground uppercase"
          >
            {{ $t("chat.model.title") }}
          </div>
          <button
            v-for="m in models"
            :key="m.id"
            class="flex w-full items-center gap-2 px-4 py-2 text-left transition-colors hover:bg-base-300/50"
            @click="chooseModel(m)"
          >
            <AppIcon
              name="i-lucide-check"
              class="size-3.5 shrink-0"
              :class="m.id === currentModelId ? 'text-primary' : 'text-transparent'"
            />
            <span class="block min-w-0 truncate font-cinzel text-sm text-foreground">
              {{ m.display_name }}
            </span>
          </button>
          <div
            v-if="models.length === 0"
            class="px-4 py-2 text-center text-xs text-muted-foreground"
          >
            {{ $t("chat.model.empty") }}
          </div>
          <p class="px-4 py-1.5 text-[0.625rem] leading-snug text-muted-foreground/70">
            {{ $t("chat.model.overrideHint") }}
          </p>

          <div class="my-2 h-px bg-border" />

          <!-- Profile -->
          <div
            class="px-4 py-1.5 text-[0.625rem] font-semibold tracking-wider text-muted-foreground uppercase"
          >
            {{ $t("chat.profile.title") }}
          </div>
          <button
            v-for="p in profiles"
            :key="p.id"
            class="flex w-full items-start gap-2 px-4 py-2 text-left transition-colors hover:bg-base-300/50"
            @click="chooseProfile(p)"
          >
            <AppIcon
              name="i-lucide-check"
              class="mt-0.5 size-3.5 shrink-0"
              :class="p.name === currentProfileName ? 'text-primary' : 'text-transparent'"
            />
            <span class="min-w-0 flex-1">
              <span class="block truncate font-cinzel text-sm text-foreground">{{ p.name }}</span>
              <span
                v-if="p.description"
                class="block truncate text-[0.6875rem] text-muted-foreground"
              >
                {{ p.description }}
              </span>
            </span>
            <span
              v-if="p.name === currentProfileName"
              class="mt-0.5 shrink-0 text-[0.625rem] font-medium tracking-wider text-primary uppercase"
            >
              {{ $t("chat.profile.reapply") }}
            </span>
          </button>
          <div
            v-if="profiles.length === 0"
            class="px-4 py-2 text-center text-xs text-muted-foreground"
          >
            {{ $t("chat.profile.empty") }}
          </div>
          <button
            class="flex w-full items-center gap-2 px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-base-300/50 hover:text-foreground"
            @click="goManage"
          >
            <AppIcon name="i-lucide-settings-2" class="size-4" />
            {{ $t("chat.profile.manage") }}
          </button>
          <p class="px-4 py-1.5 text-[0.625rem] leading-snug text-muted-foreground/70">
            {{ $t("chat.profile.hint") }}
          </p>
        </div>
      </div>
    </div>
  </Teleport>
</template>

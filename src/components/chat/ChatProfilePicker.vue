<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import type { Profile } from "@/composables/useProfiles";

const props = defineProps<{
  profiles: Profile[];
  currentProfileName?: string | null;
}>();

const emit = defineEmits<{
  apply: [profileId: string];
}>();

const router = useRouter();
const open = ref(false);
const rootRef = ref<HTMLElement | null>(null);

function toggle() {
  open.value = !open.value;
}

function choose(p: Profile) {
  open.value = false;
  if (p.name !== props.currentProfileName) emit("apply", p.id);
}

function goManage() {
  open.value = false;
  router.push("/profiles");
}

function onClickOutside(e: MouseEvent) {
  if (rootRef.value && !rootRef.value.contains(e.target as Node)) open.value = false;
}

onMounted(() => document.addEventListener("click", onClickOutside, true));
onUnmounted(() => document.removeEventListener("click", onClickOutside, true));
</script>

<template>
  <div ref="rootRef" class="relative">
    <button
      class="flex h-9 items-center gap-1.5 rounded-lg border bg-muted/40 px-3 text-xs text-muted-foreground transition-colors hover:text-foreground"
      :title="$t('chat.profile.title')"
      @click="toggle"
    >
      <UIcon name="i-lucide-layers" class="h-3.5 w-3.5 shrink-0" />
      <span class="max-w-[120px] truncate">{{ currentProfileName || $t('chat.profile.none') }}</span>
      <UIcon name="i-lucide-chevron-down" class="h-3.5 w-3.5 shrink-0" />
    </button>

    <div
      v-if="open"
      class="absolute right-0 top-full z-20 mt-1 w-64 rounded-lg border bg-card py-1 shadow-lg"
    >
      <div class="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {{ $t('chat.profile.title') }}
      </div>

      <button
        v-for="p in profiles"
        :key="p.id"
        class="flex w-full items-start gap-2 px-3 py-2 text-left transition-colors hover:bg-accent/50"
        @click="choose(p)"
      >
        <UIcon
          name="i-lucide-check"
          class="mt-0.5 h-3.5 w-3.5 shrink-0"
          :class="p.name === currentProfileName ? 'text-primary' : 'text-transparent'"
        />
        <span class="min-w-0">
          <span class="block truncate font-cinzel text-sm text-foreground">{{ p.name }}</span>
          <span v-if="p.description" class="block truncate text-[11px] text-muted-foreground">
            {{ p.description }}
          </span>
        </span>
      </button>

      <div v-if="profiles.length === 0" class="px-3 py-3 text-center text-xs text-muted-foreground">
        {{ $t('chat.profile.empty') }}
      </div>

      <div class="my-1 h-px bg-border" />

      <button
        class="flex w-full items-center gap-2 px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent/50 hover:text-foreground"
        @click="goManage"
      >
        <UIcon name="i-lucide-settings-2" class="h-4 w-4" />
        {{ $t('chat.profile.manage') }}
      </button>

      <p class="px-3 py-1.5 text-[10px] leading-snug text-muted-foreground/70">
        {{ $t('chat.profile.hint') }}
      </p>
    </div>
  </div>
</template>

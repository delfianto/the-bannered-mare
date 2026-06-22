<script setup lang="ts">
import type { Profile } from "@/composables/useProfiles";

defineProps<{
  profile: Profile;
  templateLabel: string | null;
  presetLabel: string | null;
  personaLabel: string | null;
  modelLabel: string | null;
  pendingDelete?: boolean;
}>();

defineEmits<{
  edit: [];
  setDefault: [];
  delete: [];
}>();
</script>

<template>
  <div
    class="group relative flex flex-col rounded-xl border bg-card/50 p-4 pb-8 transition-all hover:shadow-[0_4px_16px_var(--color-primary)/0.08]"
  >
    <!-- Header -->
    <div class="mb-2 flex items-start justify-between gap-2">
      <h3 class="font-cinzel text-sm font-semibold tracking-wide text-foreground">
        {{ profile.name }}
      </h3>
      <div class="flex shrink-0 items-center gap-1.5">
        <span
          v-if="profile.source === 'sillytavern'"
          class="rounded-full bg-accent px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide text-muted-foreground"
        >
          {{ $t('profiles.sourceSillyTavern') }}
        </span>
        <span
          v-if="profile.is_default"
          class="flex items-center gap-1 rounded-full bg-primary/15 px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide text-primary"
        >
          <UIcon name="i-lucide-star" class="h-3 w-3" />
          {{ $t('profiles.default') }}
        </span>
      </div>
    </div>

    <!-- Description -->
    <p
      v-if="profile.description"
      class="mb-3 line-clamp-2 text-xs leading-relaxed text-muted-foreground"
    >
      {{ profile.description }}
    </p>

    <!-- Bundled components (template / preset / persona / model) -->
    <div class="grid grid-cols-2 gap-x-3 gap-y-2 border-t border-border/30 pt-3">
      <div class="flex min-w-0 items-center gap-1.5 text-[11px]">
        <UIcon name="i-lucide-scroll-text" class="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        <span class="truncate" :class="templateLabel ? 'text-foreground' : 'italic text-muted-foreground/50'">
          {{ templateLabel ?? $t('profiles.none') }}
        </span>
      </div>
      <div class="flex min-w-0 items-center gap-1.5 text-[11px]">
        <UIcon name="i-lucide-sliders-horizontal" class="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        <span class="truncate" :class="presetLabel ? 'text-foreground' : 'italic text-muted-foreground/50'">
          {{ presetLabel ?? $t('profiles.none') }}
        </span>
      </div>
      <div class="flex min-w-0 items-center gap-1.5 text-[11px]">
        <UIcon name="i-lucide-user" class="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        <span class="truncate" :class="personaLabel ? 'text-foreground' : 'italic text-muted-foreground/50'">
          {{ personaLabel ?? $t('profiles.none') }}
        </span>
      </div>
      <div class="flex min-w-0 items-center gap-1.5 text-[11px]">
        <UIcon name="i-lucide-cpu" class="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        <span class="truncate" :class="modelLabel ? 'text-foreground' : 'italic text-muted-foreground/50'">
          {{ modelLabel ?? $t('profiles.none') }}
        </span>
      </div>
    </div>

    <!-- Hover actions -->
    <div
      class="absolute bottom-3 right-3 flex items-center gap-2 text-[10px] text-muted-foreground/0 transition-colors group-hover:text-muted-foreground/60"
    >
      <button
        v-if="!profile.is_default"
        class="flex items-center gap-1 hover:text-primary"
        @click="$emit('setDefault')"
      >
        <UIcon name="i-lucide-star" class="h-3 w-3" />
        {{ $t('profiles.setDefault') }}
      </button>
      <button class="flex items-center gap-1 hover:text-foreground" @click="$emit('edit')">
        <UIcon name="i-lucide-pencil" class="h-3 w-3" />
        {{ $t('common.edit') }}
      </button>
      <button
        class="flex items-center gap-1"
        :class="pendingDelete ? 'text-destructive!' : 'hover:text-destructive'"
        @click="$emit('delete')"
      >
        <UIcon name="i-lucide-trash-2" class="h-3 w-3" />
        {{ pendingDelete ? $t('profiles.confirmDelete') : $t('common.delete') }}
      </button>
    </div>
  </div>
</template>

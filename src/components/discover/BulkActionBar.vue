<script setup lang="ts">
defineProps<{
  selectedCount: number;
  visible: boolean;
}>();

defineEmits<{
  export: [];
  delete: [];
  cancel: [];
}>();
</script>

<template>
  <Transition
    enter-active-class="transition duration-200 ease-out"
    enter-from-class="translate-y-2 opacity-0"
    enter-to-class="translate-y-0 opacity-100"
    leave-active-class="transition duration-150 ease-in"
    leave-from-class="translate-y-0 opacity-100"
    leave-to-class="translate-y-2 opacity-0"
  >
    <div
      v-if="visible && selectedCount > 0"
      class="flex items-center justify-between rounded-xl border bg-card px-4 py-2.5 shadow-lg"
    >
      <p class="text-sm font-medium text-foreground">
        {{ $t('common.selected', { count: selectedCount }) }}
      </p>
      <div class="flex items-center gap-2">
        <button
          class="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-muted/60"
          @click="$emit('export')"
        >
          <UIcon name="i-lucide-download" class="h-3.5 w-3.5" />
          {{ $t('characters.bulkExport') }}
        </button>
        <button
          class="flex items-center gap-1.5 rounded-lg bg-destructive px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-destructive/90"
          @click="$emit('delete')"
        >
          <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
          {{ $t('characters.bulkDelete') }}
        </button>
        <button
          :aria-label="$t('characters.cancelSelection')"
          class="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
          @click="$emit('cancel')"
        >
          <UIcon name="i-lucide-x" class="h-4 w-4" />
        </button>
      </div>
    </div>
  </Transition>
</template>
